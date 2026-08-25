import Foundation
import AVFoundation
import TensorFlowLite

/// YAMNet Lite: input is 15,600 Float32 samples at 16 kHz; output is 521 scores.
/// The published YAMNet class map uses output index 11 for "Screaming".
final class IOSYamnetDistressDetector {
    private let interpreter: Interpreter
    private let sampleCount = 15_600
    private var lastTrigger = Date.distantPast
    var token = ""

    init?() {
        guard let path = Bundle.main.path(
            forResource: "lite-model_yamnet_classification_tflite_1",
            ofType: "tflite"
        ) else { return nil }
        do {
            interpreter = try Interpreter(modelPath: path)
            try interpreter.allocateTensors()
        } catch {
            return nil
        }
    }

    func classify(samples16kMono: [Float]) -> Float {
        guard samples16kMono.count >= sampleCount else { return 0 }
        let input = Array(samples16kMono.prefix(sampleCount))
        let data = input.withUnsafeBufferPointer { Data(buffer: $0) }

        do {
            try interpreter.copy(data, toInputAt: 0)
            try interpreter.invoke()
            let output = try interpreter.output(at: 0)
            let scores = output.data.toFloatArray()
            return scores.count > 11 ? scores[11] : 0
        } catch {
            return 0
        }
    }

    func handle(samples16kMono: [Float]) {
        let probability = classify(samples16kMono: samples16kMono)
        guard probability >= 0.75,
              Date().timeIntervalSince(lastTrigger) >= 30 else { return }
        lastTrigger = Date()

        SafetyAPI.post(
            path: "signals/",
            json: [
                "signal_type": "voice_distress",
                "confidence": probability,
                "metadata": [
                    "model": "yamnet_classification_tflite",
                    "class": "Screaming",
                    "class_index": 11,
                    "window_samples": 15_600
                ]
            ],
            token: token
        )
    }
}

private extension Data {
    func toFloatArray() -> [Float] {
        withUnsafeBytes { raw in
            Array(raw.bindMemory(to: Float32.self))
        }
    }
}
