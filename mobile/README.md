# Native Safety Companion integration

The supplied Django project is a web/Django application. The native snippets in this folder are designed to be copied into your existing Android/iOS app.

## Android

1. Copy `android/SafetyCompanion.kt` and `android/YamnetDistressDetector.kt`.
2. Add the TensorFlow Lite Task Audio dependency.
3. Put the YAMNet `.tflite` model in `app/src/main/assets/`.
4. Run `download_yamnet.ps1` from PowerShell if you want the public YAMNet baseline.
5. Replace `YOUR-CARECONNECT-DOMAIN` in `SafetyApi`.
6. Connect your existing JWT and FusedLocationProviderClient.
7. Add the fake-call activity to your existing navigation.

YAMNet is an audio-event baseline. Its published class map places `Screaming` at index 11. Validate it with your own consented distress dataset before treating it as a safety-critical detector.

## iOS

1. Add TensorFlowLiteSwift through Swift Package Manager.
2. Copy `ios/SafetyCompanion.swift`.
3. Add microphone/location/call permissions to Info.plist.
4. Wire the motion manager and audio engine into the existing app lifecycle.
5. Implement the TFLite interpreter with the same model contract used by the Android client.
6. Do not claim global hardware-key interception on iOS; use app shortcuts/approved system controls.

## Native API contract

All native triggers send only event metadata:

- `POST /api/safety-companion/silent-sos/`
- `POST /api/safety-companion/signals/`

Continuous microphone frames and raw motion streams remain on-device.
