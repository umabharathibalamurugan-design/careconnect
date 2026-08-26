$ErrorActionPreference = "Stop"
$dir = Join-Path $PSScriptRoot "android/app/src/main/assets"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$url = "https://tfhub.dev/google/lite-model/yamnet/classification/tflite/1?lite-format=tflite"
$out = Join-Path $dir "lite-model_yamnet_classification_tflite_1.tflite"
Invoke-WebRequest -Uri $url -OutFile $out
Write-Host "YAMNet model downloaded to $out"
