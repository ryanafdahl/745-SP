# JetLink Android APK

[Download jetlink-0.8.0-clarity-tensor.1-pixel.apk](https://github.com/ryanafdahl/Clarity-Pilot/raw/refs/heads/main/android/jetlink-0.8.0-clarity-tensor.1-pixel.apk)

This is the exact APK built and installed on the Pixel 11 Pro XL on October 3, 2026. It is the upstream JetLink app with the [Clarity Tensor support patch](tensor/README.md). It uses protocol v3 and matches this repository's JetLink client and the upgraded Jetson server.

| Field | Value |
| --- | --- |
| Version / code | `0.8.0-clarity-tensor.1` / `801` |
| Package | `io.zoompilot.jetlink.android` |
| Source | [zoompilot/jetlink at 9f3d318](https://github.com/zoompilot/jetlink/tree/9f3d3187758b810adc99b06cc0a1a19ab73b7acb) |
| Architecture | ARM64 |
| APK bytes | `103523312` |
| SHA-256 | `e519d6e775775bd185b2a9d104eb5c3e4579d19767d92d3e5cc5627e789b714e` |
| Build tools | Swift 6.4.0 + matching Android SDK, Android platform 37, NDK 30.0.16248370, JDK 17, Ubuntu under WSL |
| Signing | Local debug key, as configured by upstream's release build; private key is not included |

## Install on the Pixel

Enable Developer options and USB debugging, connect to a computer with Android platform-tools, and authorize its debugging prompt. From the repository root:

```powershell
Get-FileHash .\android\jetlink-0.8.0-clarity-tensor.1-pixel.apk -Algorithm SHA256
adb devices
adb install -r .\android\jetlink-0.8.0-clarity-tensor.1-pixel.apk
adb shell am start -n io.zoompilot.jetlink.android/io.zoompilot.jetlink.MainActivity
```

Compare the hash above before installing. If several phones are connected, add `-s YOUR_DEVICE_SERIAL` after `adb`. Alternatively, download the APK onto the phone and allow the file manager to install it. Allow JetLink notifications so its foreground service can remain active.

An update must use the same signing key. A signature mismatch means it came from a different builder; do not uninstall automatically, because that removes app data and prepared models. Keep the original signing key privately for future builds.

The Pixel now offers **Settings → Processor → Tensor TPU (desk only)**, using the Google Tensor SDK and LiteRT NPU dispatch. Its V2 model compiled all 2,424 operators to one TPU partition and executed on the phone. **USB serving is disabled in Tensor mode:** the 32-frame reference comparison failed the plan-output tolerance, and inference p95 exceeded 50 ms. See the [measured results and model import instructions](tensor/README.md). GPU and CPU remain separate choices; Qualcomm QNN is not used for Tensor. Models are not bundled in the APK.

While parked, enable **Settings → Models → Accelerator Link** on the comma. Connect the Pixel through a USB 3 hub with USB-C power pass-through, then a USB-A-to-C data cable from the hub to the comma. Accept Android's USB permission prompt and check for **Connected over USB 3**. Choose either the Pixel or Jetson as the attached accelerator.

## Validation and rebuilding

The release build and all **53 Android unit tests** passed, including Tensor selection and its USB guard. Native manifest tests passed (three tests, including four mismatch cases). Actual TPU execution and 100 measured desk frames were verified on Pixel 11 Pro XL / Android 17. Numerical parity failed for V2; no sustained or direct comma USB qualification is claimed.

The Tensor option currently cannot serve over USB. A future qualified implementation must pass numerical parity first. Before any phone driving use, complete the pinned upstream guide's one-minute and ten-minute benchmarks while charging in the intended mount, output-parity check, and parked comma USB test. See the [Android user guide](https://github.com/zoompilot/jetlink/blob/9f3d3187758b810adc99b06cc0a1a19ab73b7acb/docs/android-app.md) and [build instructions](https://github.com/zoompilot/jetlink/blob/9f3d3187758b810adc99b06cc0a1a19ab73b7acb/android/README.md).

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

The prior [upstream 0.8.0 APK](jetlink-0.8.0-pixel.apk) remains available as an archive. It has version code 800, so a rollback from 801 may require an explicitly permitted downgrade; do not uninstall automatically. The SDK compiler and compiled model are kept locally and are not redistributed in this repository.
