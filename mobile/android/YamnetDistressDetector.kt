package com.careconnect.safety

import android.content.Context
import org.tensorflow.lite.task.audio.classifier.AudioClassifier
import java.util.concurrent.atomic.AtomicBoolean

/**
 * YAMNet Lite model contract:
 * - mono 16 kHz PCM
 * - TFLite output contains 521 AudioSet classes
 * - class index 11 is "Screaming" in the published YAMNet class map.
 *
 * Download the model into app/src/main/assets/:
 * lite-model_yamnet_classification_tflite_1.tflite
 *
 * The model is an environmental sound baseline, not a medical device. For a
 * final CareConnect release, fine-tune/validate a small distress classifier
 * with consented data and measure false positives before enabling auto-SOS.
 */
class YamnetDistressDetector(private val context: Context) {
    private val running = AtomicBoolean(false)
    private val classifier: AudioClassifier =
        AudioClassifier.createFromFile(context, "lite-model_yamnet_classification_tflite_1.tflite")
    private val audioTensor = classifier.createInputTensorAudio()
    private val recorder = classifier.createAudioRecord()

    fun start(onDistress: (Float) -> Unit) {
        if (!running.compareAndSet(false, true)) return
        recorder.startRecording()

        Thread {
            var consecutive = 0
            try {
                while (running.get()) {
                    audioTensor.load(recorder)
                    val results = classifier.classify(audioTensor)
                    val scream = results
                        .flatMap { it.categories }
                        .firstOrNull { it.index == 11 }?.score ?: 0f

                    // Require two consecutive high-scoring windows.
                    consecutive = if (scream >= 0.75f) consecutive + 1 else 0
                    if (consecutive >= 2) {
                        onDistress(scream)
                        consecutive = 0
                        Thread.sleep(30_000) // local debounce
                    }
                }
            } finally {
                recorder.stop()
            }
        }.start()
    }

    fun stop() {
        running.set(false)
    }
}
