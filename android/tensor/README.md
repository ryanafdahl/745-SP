# Google Tensor TPU support

This patch adds Google Tensor TPU execution to JetLink 0.8.0 for Tensor G5/G6. It preserves the existing GPU, CPU, and Qualcomm choices. Google Tensor uses LiteRT 2.2.0 AOT compilation; the SDK compiler runs on an x86-64 Linux workstation, while the APK contains only the matching, hash-verified Tensor dispatch runtime.

## Verified result on October 3, 2026

- Pixel 11 Pro XL, Tensor G6, Android 17; app version `0.8.0-clarity-tensor.1` / code 801. Its previous processor setting was CPU.
- Cinque Terre V2 source SHA-256: `09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec` (766,040,736 bytes).
- SDK compiler SHA-256: `d74bea45081aa90a39505a675c15f566d46dbcc35e55a98f755c02017464cd1f`.
- Automatic-precision compiled model SHA-256: `3868bc302c17f53f98b3e3d639a11de48d114e6f63b33e207da435decec879de` (834,554,128 bytes). All **2,424/2,424 operators** offloaded to **one TPU partition**. The runtime's full-delegation check passed.
- 32 synthetic, varying-input frames returned finite outputs. Against the original ONNX, **14 of 15 output slices passed**; the **plan** slice failed the unchanged upstream parity criteria (worst pooled column correlation 0.998291 versus the 0.999 requirement).
- 100 measured desk Wi-Fi frames after 10 warmups: TPU inference mean **49.55 ms**, p95 **52.71 ms**, max **53.55 ms**, 60/100 above 50 ms. Server total mean **53.49 ms**, p95 **57.38 ms**. Full round-trip mean **74.16 ms**, p95 **81.99 ms**, 100/100 above 50 ms. [Machine-readable timing summary](benchmark-2026-10-03.json).
- **USB is disabled for Tensor mode** because numerical and timing qualification has not passed. Existing GPU/CPU/Qualcomm USB choices retain their behavior. This is working TPU integration for desk research, not a driving-ready Pixel accelerator.
- Explicit FP16 and no-truncation compilation attempts did not produce usable models. One failure was a logged Linux OOM; later attempts ended with WSL process/session failure, including `Wsl/Service/E_UNEXPECTED`. Maximum sharding and temporary swap did not resolve it. Temporary swap was removed; no permanent WSL configuration was changed.
- Release build and 53 Android tests passed; three native manifest tests passed, including four mismatch cases. Pixel storage had 341 GiB free before these model imports.

## Rebuild the app

Start with upstream commit `9f3d3187758b810adc99b06cc0a1a19ab73b7acb` and the toolchains documented in `android/README.md` upstream. Apply `tensor-support.patch` from this directory to that checkout:

```sh
git apply /path/to/Clarity-Pilot/android/tensor/tensor-support.patch
cd android
./gradlew :app:assembleRelease :app:testDebugUnitTest
```

The `tensorDispatch` build task downloads the official LiteRT 2.2.0 runtime ZIP and verifies the selected library's SHA-256. It does not download or distribute the private Tensor SDK compiler. Keep your existing signing key to update an installed app without losing its models/settings.

## Compile a model

Extract the supplied SDK archive locally. The `--sdk` directory must contain `liblitert_plugin_compiler.so`. Use an isolated Python environment with `ai-edge-litert==2.2.0`. Stop Gradle daemons before compiling a large model on a 16 GiB WSL instance; compilation and app builds together exceeded that limit in testing.

Convert the original ONNX using the patched app's own converter, preserving its inputs, outputs, and queue layout:

```sh
cd JetlinkKit
swift build --product tensor-convert -c release
.build/release/tensor-convert /path/to/source.onnx /path/to/converted
cd ..
python android/scripts/compile-tensor.py \
  --source /path/to/source.onnx \
  --model /path/to/converted/model.tflite \
  --sdk /path/to/google_tensor_ml_sdk \
  --output /path/to/tensor-compiled \
  --soc Tensor_G6 --precision auto
```

Use the actual target SoC; do not relabel a G5 model as G6. The output directory is named after the full ONNX SHA-256 and contains `model.tflite` plus `manifest.json`. The manifest records source/model/SDK hashes, target SoC, runtime version, and precision. Keep a separate output directory for each precision experiment. `--precision auto` reproduces the running candidate above, which failed parity. The script defaults to `half`; `half`, `no_truncation`, and optional `--sharding maximum` remain precision experiments, not validated replacements.

## Import into the Pixel

Install the patched APK and open it once so Android creates its app-owned `tensor-models` directory. Copy the two files directly into that directory, naming both with the full source-model SHA-256. Do not create a nested directory with ADB; a shell-owned subdirectory may be inaccessible to the app.

```sh
adb push /path/to/tensor-compiled/SOURCE_SHA256/model.tflite /sdcard/Android/data/io.zoompilot.jetlink.android/files/tensor-models/SOURCE_SHA256.tflite
adb push /path/to/tensor-compiled/SOURCE_SHA256/manifest.json /sdcard/Android/data/io.zoompilot.jetlink.android/files/tensor-models/SOURCE_SHA256.json
```

Replace `SOURCE_SHA256` everywhere with the 64-character hash. Select **Settings → Processor → Tensor TPU (desk only)**. In Models select the matching original ONNX model, then prepare it. The compiled file is verified and copied into the private engine cache. An updated compiled hash invalidates the old engine on the next model load; restart the app after importing a replacement.

The app rejects missing/wrong model identity, chipset, runtime, compiled checksum, or incomplete TPU delegation. It does not silently fall back to CPU or GPU in Tensor mode. CPU/GPU remain explicit processor choices. Qualcomm's Keep NPU Awake option is not applied to Google Tensor.

## Validation

Run `scripts/verify_parity.py` from the patched upstream checkout: capture a bounded set of frames, compute the reference from the unchanged ONNX, then compare using the upstream thresholds. Do not relax tolerances to make a new accelerator pass. Benchmark inference, queue preparation, and full round-trip separately; the protocol's historical `gpu` timing field means accelerator inference even when the selected processor is Tensor TPU.

Synthetic desk/TCP validation is separate from a sustained thermal test and a supervised parked comma USB test. The comma and Jetson deployments were not changed by this phone integration.

## References

- [Google Tensor support and supported SoCs](https://developers.google.com/edge/litert/next/tensor-sdk)
- [Google Tensor compiler precision flags](https://developers.google.com/edge/tensor-sdk/compilation-flags)
- [Official LiteRT 2.2.0 runtime release](https://github.com/google-ai-edge/LiteRT/releases/tag/v2.2.0)
