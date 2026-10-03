# Google Tensor TPU support

**Ready for a supervised synthetic parked-car USB test. Driving remains blocked in Tensor mode.** The Pixel runs Cinque Terre V2 on Tensor G6 using LiteRT 2.2.0 and the locally supplied Google Tensor SDK. The installed app is `0.8.0-clarity-tensor.2` (code 802).

## Results on October 3, 2026

Explicit FP16 compilation fixed the earlier plan-output mismatch. Image history now retains bytes instead of converting bytes to half precision and back. Tensor runtime burst mode supplies the latency margin needed for the next test. The original ONNX model, output interpretation, and numerical acceptance thresholds are unchanged.

| Short desk comparison | Inference mean | Inference p95 | Queue mean | Server p95 |
| --- | ---: | ---: | ---: | ---: |
| Initial automatic precision | 49.55 ms | 52.71 ms | 3.86 ms | 57.38 ms |
| Explicit FP16 | 49.03 ms | 51.58 ms | 4.34 ms | 56.42 ms |
| FP16 + byte image history | 49.31 ms | 51.83 ms | 1.08 ms | 53.20 ms |
| Above + sustained mode | 46.26 ms | 47.94 ms | 0.96 ms | 49.14 ms |
| Above + burst mode, selected | **32.97 ms** | **34.05 ms** | **0.77 ms** | **35.22 ms** |

These comparisons used the same seeded workload over Wi-Fi, with 10 warmups and 100 measured frames each; they are short experiments, not a thermal qualification. [Raw comparisons](comparisons-2026-10-03.json). Maximum sharding was also tested and was slower (38.39 ms mean inference over 200 ADB desk frames versus 33.62 ms with minimal sharding), so minimal sharding is retained. [Sharding result](sharding-comparison-2026-10-03.json).

- **Accuracy:** all 15 slices passed the unchanged upstream criteria on 32 recurrent frames (seed 0), then 128 frames (seed 7). The 128-frame plan's worst correlated column was **0.999916**, above 0.999; maximum plan absolute difference was 0.7812 across mixed-unit raw outputs. Small/quiet columns use upstream's existing absolute-error rules. This is numerical agreement on synthetic inputs, not an assessment of driving quality. [32-frame results](parity-32-seed0.txt), [128-frame results](parity-128-seed7.txt).
- **10-minute soak:** 12,000 measured frames after 20 warmups, about 612 seconds. Every output was finite; zero protocol/inference failures. Inference mean **33.88 ms**, p95 **35.47 ms**, max **44.02 ms**. Server total mean **34.92 ms**, p95 **36.72 ms**, max **44.66 ms**; **0/12,000** server samples above 50 ms. Per-1,200-frame server p95 stayed between 36.58 and 36.88 ms. [Full soak summary](soak-2026-10-03.json).
- **Thermals:** Android thermal status remained 0 at all 61 samples; battery temperature rose from 28.3°C to a maximum of 34.6°C while connected to the desk USB cable. This does not establish performance in a hot car or intended mount.
- **Transport remains open:** ADB round-trip mean **49.75 ms**, p95 **54.39 ms**, p99 **63.75 ms**, max **113.94 ms**; 3,943/12,000 exchanges exceeded 50 ms. ADB forwarding is not the comma's direct USB transport. Its full round-trip timing did **not** pass a 50 ms p95 gate. The next parked test measures the actual USB path.
- **Final APK:** the soak candidate used the same inference and queue implementation; the final APK adds the parked-only protocol gate and temporary USB switch. A fresh [32-frame parity capture](parity-installed-32-seed0.txt) passed on the final installed APK. Its [separate one-minute check](installed-check-2026-10-03.json) completed 1,200 frames, with inference p95 35.35 ms, server p95 36.65 ms, max server 39.75 ms, and zero failures. APK SHA-256: `b1bebef66960a0a3e0129f87b2b8176ec2bacb5e588444218e8947b176a0cfd1`.
- **Regression checks:** release build; 54 Android tests; 24 native tests across 9 suites (including byte-exact queue wrap/reset/conformance tests and parked-protocol rejection); 57 Python transport tests; 5 Linux parked-harness tests. The complete patch applies to the pinned upstream commit. An initial broad host suite also included an unrelated ONNX Runtime version check; that check failed because the host runtime was not loaded, and is excluded from these targeted passing counts.

The previous automatic-precision experiment remains in [the initial report](results-2026-10-03-initial.md).

## Exact model and compiler

- Original V2 ONNX: `09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec`, 766,040,736 bytes.
- Selected compiled model: `fc393523c5c1ddba9774382db513a5c62fad50cb187968ea25bc96db5480b51b`, 834,528,528 bytes.
- Compiler: `d74bea45081aa90a39505a675c15f566d46dbcc35e55a98f755c02017464cd1f`.
- Target `Tensor_G6`, precision `half`, sharding `minimal`, LiteRT `2.2.0`; all **2,424/2,424** operators compiled to one TPU partition. The app requires full delegation and does not silently fall back.
- [Machine-readable manifest](qualified-model.json). The SDK compiler and compiled model stay local and are not redistributed in this repo.

The successful FP16 compile took 98 seconds, with maximum compiler RSS around 14.7 GiB. A temporary 22 GiB WSL limit allowed it to finish where the default 15 GiB environment failed. Build daemons were stopped during compilation. The temporary WSL configuration was removed after testing.

## Rebuild and compile

Start from upstream `9f3d3187758b810adc99b06cc0a1a19ab73b7acb` and apply [tensor-support.patch](tensor-support.patch). Use the toolchains in [the Android README](../README.md), keeping the same signing key:

```sh
git apply /path/to/Clarity-Pilot/android/tensor/tensor-support.patch
cd android
./gradlew :app:assembleRelease :app:testDebugUnitTest
```

The build fetches the official LiteRT 2.2.0 Tensor dispatch library and checks its SHA-256. It does not fetch the private SDK compiler. Extract your SDK locally and use Python with `ai-edge-litert==2.2.0`:

```sh
cd JetlinkKit
swift build --product tensor-convert -c release
.build/release/tensor-convert /path/to/source.onnx /path/to/converted
cd ..
python android/scripts/compile-tensor.py \
  --source /path/to/source.onnx --model /path/to/converted/model.tflite \
  --sdk /path/to/google_tensor_ml_sdk --output /path/to/compiled \
  --soc Tensor_G6 --precision half --sharding minimal
```

Use the real target chipset. Automatic precision is an archived failed candidate for this model. The app's converter preserves its model interface; the new byte history preserves the previous queue's inputs exactly, including resets and wraparound. Feature/desire history retains its half-precision rounding.

## Import into the Pixel

Install the APK and open it once to create the app-owned `tensor-models` folder. Copy the two compiler outputs directly into it, replacing `SOURCE_SHA256` with the full original ONNX hash above:

```sh
adb push /path/to/compiled/SOURCE_SHA256/model.tflite /sdcard/Android/data/io.zoompilot.jetlink.android/files/tensor-models/SOURCE_SHA256.tflite
adb push /path/to/compiled/SOURCE_SHA256/manifest.json /sdcard/Android/data/io.zoompilot.jetlink.android/files/tensor-models/SOURCE_SHA256.json
```

Do not create a shell-owned nested folder with ADB. Restart the app after replacing a model. Select **Settings → Processor → Tensor TPU (parked test)**, then prepare Cinque Terre V2. Source/chipset/runtime/compiled-file checks protect imports; a changed compiled hash invalidates the old cache. Other models and compiler settings require their own numerical and timing validation.

## Supervised parked test

The Pixel was left with **Parked USB Test off**. It must be enabled explicitly while present at the car. The switch is not saved across app process restarts and closes after 10 minutes with unchanged server settings. Switching processor closes it. Tensor also rejects normal engine requests and raw inference without the explicit `validation_mode=parked` handshake; ordinary modeld clients remain blocked.

1. Keep the car parked with ignition off and Accelerator Link enabled. Attach only the Pixel as the accelerator, using the powered USB 3 hub and data cable described in [Android installation](../README.md).
2. On the Pixel, select **Tensor TPU (parked test)** and turn on **Parked USB Test**. Accept the USB permission prompt. Do not start a drive.
3. The script is already staged on the comma at `/data/clarity-tensor-parked-test.py`. From your computer run:

   ```sh
   ssh comma@COMMA_IP '/usr/local/venv/bin/python /data/clarity-tensor-parked-test.py --legacy-owner --frames 120 --output /data/clarity-parked-brief.json'
   ```

   For another installation, copy [parked-test.py](parked-test.py) to that path first. Choose a new result filename for each run. Start with 120 measured frames; repeat with `--frames 1200` only after a clean short check. `--legacy-owner` matches this comma's installed offroad daemon: it temporarily disables Accelerator Link, waits for the daemon to exit and USB to unbind, then opens the interface exclusively. It closes USB and restores Accelerator Link afterward, including on failure. On newer installations whose daemon exposes `/dev/shm/jetlink-lend.sock`, omit this flag to borrow the existing owner's endpoints without changing settings.
4. Review protocol success, negotiated USB speed, round-trip p95/p99/max, and missed 50 ms deadlines. The script refuses ignition-on/camera/model activity, checks offroad state before each inference, and releases USB even on failure. Legacy ownership temporarily changes only the enable setting; engine readiness is never written by the harness. It does not start cameras/controls or send steering commands.
5. Turn **Parked USB Test off** when finished. A passing synthetic parked result is one transport milestone; camera-input parity, in-mount charging/heat, reconnect behavior, and driving validation remain separate.

Live inspection on October 3 found that the client library has a loan API but the installed offroad daemon does not expose it. The harness now supports that older daemon explicitly; all 11 harness regression tests pass. The [first direct-USB attempt](parked-connection-2026-10-03.json) completed **zero inference frames**: the phone did not read HELLO before the 15-second write watchdog expired. Cleanup restored Accelerator Link and its offroad daemon. This is an incomplete connection check, not a TPU timing result; confirm the Pixel's test switch and USB permission before retrying.

## Repeat desk validation

Use upstream `scripts/verify_parity.py capture --parked`, followed by `reference` with the original ONNX and `compare`. Only the explicit parked handshake was added; comparison thresholds are unchanged. The patch also makes TCP writes work on Windows sockets without `sendmsg`.

For timing, put the patched upstream checkout on `PYTHONPATH`, create `adb forward tcp:5599 tcp:5599`, and run [benchmark.py](benchmark.py) with the source hash/size, output path, transport label, and optional ADB executable for thermal sampling. Default pacing is 50 ms; `--frames 12000` repeats the soak. The tool stops for non-finite outputs, protocol failure, Android thermal status 3+, or battery temperature 43°C+. Remove forwarding afterward with `adb forward --remove tcp:5599`.

## References

- [Google Tensor support](https://developers.google.com/edge/litert/next/tensor-sdk)
- [Compiler precision and sharding flags](https://developers.google.com/edge/tensor-sdk/compilation-flags)
- [LiteRT 2.2.0 Tensor performance modes](https://github.com/google-ai-edge/LiteRT/blob/v2.2.0/litert/c/options/litert_google_tensor_options_type.h)
- [Official LiteRT 2.2.0 release](https://github.com/google-ai-edge/LiteRT/releases/tag/v2.2.0)
