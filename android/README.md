# JetLink Android APK

[Download jetlink-0.8.0-clarity-tensor.2-pixel.apk](https://github.com/ryanafdahl/Clarity-Pilot/raw/refs/heads/main/android/jetlink-0.8.0-clarity-tensor.2-pixel.apk)

This is the exact APK built and installed on the Pixel 11 Pro XL on October 3, 2026. It is the upstream JetLink app with the [Clarity Tensor support patch](tensor/README.md). It uses protocol v3 and matches this repository's JetLink client and the upgraded Jetson server.

| Field | Value |
| --- | --- |
| Version / code | `0.8.0-clarity-tensor.2` / `802` |
| Package | `io.zoompilot.jetlink.android` |
| Source | [zoompilot/jetlink at 9f3d318](https://github.com/zoompilot/jetlink/tree/9f3d3187758b810adc99b06cc0a1a19ab73b7acb) |
| Architecture | ARM64 |
| APK bytes | `103522196` |
| SHA-256 | `b1bebef66960a0a3e0129f87b2b8176ec2bacb5e588444218e8947b176a0cfd1` |
| Build tools | Swift 6.4.0 + matching Android SDK, Android platform 37, NDK 30.0.16248370, JDK 17, Ubuntu under WSL |
| Signing | Local debug key, as configured by upstream's release build; private key is not included |

## Install on the Pixel

Enable Developer options and USB debugging, connect to a computer with Android platform-tools, and authorize its debugging prompt. From the repository root:

```powershell
Get-FileHash .\android\jetlink-0.8.0-clarity-tensor.2-pixel.apk -Algorithm SHA256
adb devices
adb install -r .\android\jetlink-0.8.0-clarity-tensor.2-pixel.apk
adb shell am start -n io.zoompilot.jetlink.android/io.zoompilot.jetlink.MainActivity
```

Compare the hash above before installing. If several phones are connected, add `-s YOUR_DEVICE_SERIAL` after `adb`. Alternatively, download the APK onto the phone and allow the file manager to install it. Allow JetLink notifications so its foreground service can remain active.

An update must use the same signing key. A signature mismatch means it came from a different builder; do not uninstall automatically, because that removes app data and prepared models. Keep the original signing key privately for future builds.

The Pixel now offers **Settings → Processor → Tensor TPU (parked test)**. Explicit FP16 V2 passes the unchanged numerical checks, and the optimized TPU implementation completed 12,000 desk frames with server-total p95 36.72 ms. **Tensor remains restricted to synthetic parked tests:** its USB switch starts off and normal driving clients are blocked. Models are not bundled in the APK. [Full results, import steps, and supervised parked-test instructions](tensor/README.md).

For the parked test, use a powered USB 3 hub with USB-C power pass-through and a USB-A-to-C data cable from the hub to the comma. Accept Android's USB permission prompt. Attach one accelerator at a time and keep ignition off while using the Tensor test harness.

## Validation and rebuilding

The release build and **54 Android tests** passed, plus 24 native queue/protocol/manifest tests, 57 Python transport tests, and 5 parked-harness tests. A fresh 32-frame parity capture passed on this exact installed APK. The inference implementation completed a 10-minute soak; the final APK adds a parked-only gate and was checked separately for one minute. Full ADB round-trip p95 remained above 50 ms, and direct comma USB timing is pending. See the [evidence and limits](tensor/README.md).

After installing the documented toolchains on Linux or macOS:

```sh
git clone https://github.com/zoompilot/jetlink.git
cd jetlink
git checkout 9f3d3187758b810adc99b06cc0a1a19ab73b7acb
git apply /path/to/Clarity-Pilot/android/tensor/tensor-support.patch
cd android
./gradlew :app:assembleRelease :app:testDebugUnitTest
```

A rebuild is not guaranteed to have this APK's exact bytes or signature. JetLink's [MIT license](LICENSE-JetLink) is included. The APK also bundles LiteRT (Apache 2.0), ONNX Runtime (MIT), and Qualcomm QNN libraries under the Qualcomm AI Stack License; see upstream's [license notes](https://github.com/zoompilot/jetlink/blob/9f3d3187758b810adc99b06cc0a1a19ab73b7acb/android/README.md#licenses). QNN libraries are distributed inside the app, not separately.

The prior [initial Tensor APK](jetlink-0.8.0-clarity-tensor.1-pixel.apk) (code 801) and [upstream APK](jetlink-0.8.0-pixel.apk) (code 800) remain as archives. Downgrades from code 802 may require explicit Android downgrade support; do not uninstall automatically. The private SDK compiler and compiled model are not redistributed.
