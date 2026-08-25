# iOS dependencies and permissions

Add TensorFlowLiteSwift through Swift Package Manager.

Info.plist keys:

- `NSLocationWhenInUseUsageDescription`
- `NSLocationAlwaysAndWhenInUseUsageDescription` if your approved background location design needs it
- `NSMicrophoneUsageDescription`

For a local decoy call, add CallKit usage to the app's call architecture and test on a real device. Do not claim arbitrary background incoming calls without the Apple-approved VoIP/PushKit path.

For TFLite, add `lite-model_yamnet_classification_tflite_1.tflite` to the app target's Copy Bundle Resources.
