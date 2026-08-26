import Foundation
import CoreMotion
import CoreLocation
import AVFoundation
import CallKit
import UserNotifications

// CareConnect Safety & Companion — additive iOS implementation.
// API requests use the existing JWT stored by the CareConnect app.

final class SafetyAPI {
    static let baseURL = URL(string: "https://YOUR-CARECONNECT-DOMAIN")!

    static func post(path: String, json: [String: Any], token: String, completion: ((Error?) -> Void)? = nil) {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/safety-companion/\(path)"))
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: json)
        URLSession.shared.dataTask(with: request) { _, _, error in
            completion?(error)
        }.resume()
    }

    static func patchProfile(enabled: Bool, token: String) {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/safety-companion/profile/"))
        request.httpMethod = "PATCH"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["voice_distress_enabled": enabled])
        URLSession.shared.dataTask(with: request).resume()
    }
}

// 1. SILENT TRIPLE-PRESS — app-specific implementation.
// iOS does not expose a general global hardware-key listener to ordinary apps.
// Use a UIKeyCommand or approved system shortcut for an in-app implementation.
final class SilentTriplePress {
    private var times: [TimeInterval] = []
    private let window: TimeInterval = 0.9
    private let location = CLLocationManager()

    func press(token: String) {
        let now = Date().timeIntervalSince1970
        times = times.filter { now - $0 <= window }
        times.append(now)
        guard times.count >= 3 else { return }
        times.removeAll()

        location.requestLocation()
        let loc = location.location
        // No UI, sound, haptic or confirmation is shown here.
        SafetyAPI.post(
            path: "silent-sos/",
            json: [
                "latitude": loc?.coordinate.latitude as Any,
                "longitude": loc?.coordinate.longitude as Any,
                "trigger_id": UUID().uuidString,
                "client_timestamp": ISO8601DateFormatter().string(from: Date()),
                "source": "ios_rapid_triple_press"
            ],
            token: token
        )
    }
}

// 2. LOCAL DECOY CALL.
// For a user-tapped decoy, CallKit can present the system call UI locally.
// A background VoIP-style incoming call still requires Apple's PushKit/CallKit rules.
final class FakeCallManager: NSObject, CXProviderDelegate {
    private let provider: CXProvider

    override init() {
        let config = CXProviderConfiguration(localizedName: "CareConnect")
        config.supportsVideo = false
        config.maximumCallsPerCallGroup = 1
        config.supportedHandleTypes = [.generic]
        provider = CXProvider(configuration: config)
        super.init()
        provider.setDelegate(self, queue: nil)
    }

    func startFakeCall() {
        let update = CXCallUpdate()
        update.localizedCallerName = "Mom"
        update.hasVideo = false
        provider.reportNewIncomingCall(with: UUID(), update: update) { _ in }
    }

    func providerDidReset(_ provider: CXProvider) {}
    func provider(_ provider: CXProvider, perform action: CXAnswerCallAction) {
        action.fulfill()
    }
    func provider(_ provider: CXProvider, perform action: CXEndCallAction) {
        action.fulfill()
    }
}

// 3 + 4. MOTION + INACTIVITY.
final class SafetyMotionEngine: NSObject {
    private let motion = CMMotionManager()
    private let queue = OperationQueue()
    private let location = CLLocationManager()
    private var lowGAt: Date?
    private var impactAt: Date?
    private var impactG: Double = 0
    private var lastMotionAt = Date()

    var token = ""

    func start() {
        guard motion.isAccelerometerAvailable else { return }
        motion.accelerometerUpdateInterval = 0.05
        motion.startAccelerometerUpdates(to: queue) { [weak self] data, _ in
            guard let self, let a = data?.acceleration else { return }
            let g = sqrt(a.x*a.x + a.y*a.y + a.z*a.z)
            let now = Date()

            if abs(g - 1.0) > 0.12 { self.lastMotionAt = now }
            if g < 0.60 { self.lowGAt = now }

            if let low = self.lowGAt, now.timeIntervalSince(low) < 1.2, g > 2.5 {
                self.impactAt = now
                self.impactG = g
                self.lowGAt = nil
            }

            if let impact = self.impactAt,
               now.timeIntervalSince(impact) >= 8,
               now.timeIntervalSince(impact) <= 15,
               g >= 0.88, g <= 1.12 {
                self.send(type: "fall", confidence: 0.90,
                          metadata: ["impact_g": self.impactG])
                self.impactAt = nil
            }

            if now.timeIntervalSince(self.lastMotionAt) >= 60 * 60 {
                self.send(type: "inactivity", confidence: 0.90,
                          metadata: ["inactive_minutes": 60])
                self.lastMotionAt = now
            }
        }
    }

    func stop() { motion.stopAccelerometerUpdates() }

    private func send(type: String, confidence: Double, metadata: [String: Any]) {
        location.requestLocation()
        SafetyAPI.post(
            path: "signals/",
            json: [
                "signal_type": type,
                "confidence": confidence,
                "latitude": location.location?.coordinate.latitude as Any,
                "longitude": location.location?.coordinate.longitude as Any,
                "metadata": metadata
            ],
            token: token
        )
    }
}

// 5. ON-DEVICE AUDIO.
// Connect AVAudioEngine microphone taps to the TFLite Swift interpreter.
// The model contract should be: 16 kHz mono PCM -> distress probability.
// Only the probability is sent to CareConnect after a local threshold.
final class DistressAudioEngine {
    private let engine = AVAudioEngine()
    private var triggerLock = Date.distantPast
    var token = ""

    func start() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: [.duckOthers])
        try session.setActive(true)

        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.installTap(onBus: 0, bufferSize: 2048, format: format) { [weak self] buffer, _ in
            guard let self else { return }
            // Feed buffer.floatChannelData into the TFLite interpreter.
            // Replace `runTFLite` with the TensorFlow Lite Swift interpreter call.
            let probability = self.runTFLite(buffer: buffer)
            guard probability >= 0.75,
                  Date().timeIntervalSince(self.triggerLock) > 30 else { return }
            self.triggerLock = Date()
            SafetyAPI.post(
                path: "signals/",
                json: [
                    "signal_type": "voice_distress",
                    "confidence": probability,
                    "metadata": ["model": "distress_detector_v1", "window_ms": 2000]
                ],
                token: self.token
            )
        }
        try engine.start()
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        try? AVAudioSession.sharedInstance().setActive(false)
    }

    private func runTFLite(buffer: AVAudioPCMBuffer) -> Double {
        // Production implementation: normalize/resample to the model's expected
        // 16-kHz tensor, invoke Interpreter, and read the distress probability.
        // Keep all PCM in memory and never upload it.
        return 0.0
    }
}

// 6. WELLNESS LOCAL PROMPT.
func scheduleWellnessPrompt(hour: Int = 9, minute: Int = 0) {
    let content = UNMutableNotificationContent()
    content.title = "CareConnect wellness check"
    content.body = "Are you okay? Tap to confirm your safety."
    content.sound = .default

    var date = DateComponents()
    date.hour = hour
    date.minute = minute
    let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
    let request = UNNotificationRequest(
        identifier: "careconnect-daily-wellness",
        content: content,
        trigger: trigger
    )
    UNUserNotificationCenter.current().add(request)
}
