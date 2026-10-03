# Google Tensor TPU support

**The 2,400-frame parked USB run failed sustained timing after shorter 120- and 1,200-frame passes. Driving remains blocked in Tensor mode.** The Pixel runs Cinque Terre V2 on Tensor G6 using LiteRT 2.2.0 and the locally supplied Google Tensor SDK. The installed app is `0.8.0-clarity-tensor.3` (code 803), adding phone telemetry and automatic test stops. The failed hot-car run used the archived `.2` build.

## Driving-test preparation

The `.3` build records phone health over the existing USB/TCP protocol even when the app screen is hidden. Each snapshot includes Android thermal status, battery temperature/percentage, external power, actual charging state, power saver, and sample age. Experimental Tensor engine requests and inference stop when telemetry is missing, malformed, five seconds old, Android thermal status is severe (3+) or battery temperature reaches 43°C. A thermal refusal revokes that session's test request. These are conservative validation thresholds, not a certification of safe operating temperature. The OS thermal protections and charging settings are unchanged.

The updated harness requests health alongside each frame, saves samples about once per second, records actual elapsed time and 100-frame timing blocks, and stops at the first 100 ms exchange or failing block (p95 >=50 ms). The desk harness applies that stop to phone/server time; direct USB also applies it to the full exchange. The existing final USB gate is unchanged. Output files cannot silently overwrite earlier runs. Normal driving clients still fail the parked-only handshake.

A new driving test remains pending the following evidence, in order:

1. Repeat direct USB with the final APK and intended powered hub/cable, first 120, then 1,200, then up to 6,000 measured frames. Require fresh phone telemetry, SuperSpeed, finite outputs, every completed 100-frame p95 below 50 ms, and no exchange reaching 100 ms. Retain the earlier failures alongside new results.
2. Validate cooling/charging in the intended mount and repeat unplug/reconnect. Do not repeat a hot, uncomfortable car session just to collect data. The current comma harness still requires ignition off; an engine-on/A/C test needs separate USB ownership isolation and live Park/zero-speed/disengagement checks before it can be supported. Disabling Accelerator Link alone does not prove that an already-running modeld released USB.
3. Validate camera-derived inputs and model outputs, and verify the installed modeld's timeout/disconnect fallback with controls disengaged before considering a supervised drive. Synthetic numerical parity and desk timing do not establish driving quality.

The new APK and guarded scripts are preparation for those checks. No driving enable flag or vehicle-control behavior was changed, and no powered-on test was started.

## Indoor check of the installed `.3` build

The new APK completed **6,000 measured frames plus 20 warmups in 308.86 seconds**, using desk USB ADB forwarding. All outputs were finite, with no protocol, health or timing-stop errors. Phone/server p95 was **36.85 ms**, maximum **43.22 ms**, and **0/6,000** server samples exceeded 50 ms. Inference p95 was **35.52 ms**, maximum **40.93 ms**. All **60** consecutive 100-frame phone timing blocks passed; the worst block p95 was **37.87 ms**.

The protocol recorded **302 phone health samples**, including while JetLink was behind the Android home screen. Thermal status stayed **0**, phone samples rose from **25.6°C to 30.4°C**, and external USB power remained connected. Charging was separately recorded and was not true for every sample. The largest phone sample age was **1.00 second**. The parallel ADB samples are retained in the report for comparison. [Full timing and health evidence](health-validation-2026-10-03.json).

ADB full round-trip p95 was **57.64 ms**, maximum **74.15 ms**, with **2,274/6,000** exchanges above 50 ms: **the desk transport did not pass the direct-USB timing requirement**. This cold indoor recovery does not establish the cause of the earlier hot-car slowdown or qualify the intended car mount.

A fresh **32-frame, seed-0 numerical capture** passed all **15 output slices** against the existing original-model reference; all 64 input arrays were verified byte-identical before comparison. [Parity result](parity-health-32-seed0.txt). The new build passed **54 Android tests**, **29 native tests across 10 suites**, and **25 Python harness/guard tests**. Installed APK SHA-256 was read back from the Pixel and matched `519e7c0bd9cac8c66458eeef43ae769bab02fee75274793b7a7a00f537e9a2e0`; a live ordinary ENGINE_REQ was still rejected as `parked_only`.

The updated scripts were staged and syntax-checked at `/data/clarity-tensor-validation-803/`, with source hashes verified. The comma stayed offroad, with Accelerator Link enabled. No physical USB test window was opened. The `.2` results below remain historical evidence for that earlier build.

## Results on October 3, 2026

Explicit FP16 compilation fixed the earlier plan-output mismatch. Image history now retains bytes instead of converting bytes to half precision and back. Tensor runtime burst mode improved the desk and short parked tests, but did not sustain the required timing in the later 2,400-frame parked run. The original ONNX model, output interpretation, and numerical acceptance thresholds are unchanged.

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
- **ADB transport comparison:** ADB round-trip mean **49.75 ms**, p95 **54.39 ms**, p99 **63.75 ms**, max **113.94 ms**; 3,943/12,000 exchanges exceeded 50 ms. ADB forwarding is not the comma's direct USB transport. Its full round-trip timing did **not** pass a 50 ms p95 gate. The separate direct-USB results below measure the comma path; these are different runs and conditions.
- **Archived `.2` APK:** the soak candidate used the same inference and queue implementation; the final APK adds the parked-only protocol gate and temporary USB switch. A fresh [32-frame parity capture](parity-installed-32-seed0.txt) passed on the final installed APK. Its [separate one-minute check](installed-check-2026-10-03.json) completed 1,200 frames, with inference p95 35.35 ms, server p95 36.65 ms, max server 39.75 ms, and zero failures. APK SHA-256: `b1bebef66960a0a3e0129f87b2b8176ec2bacb5e588444218e8947b176a0cfd1`.
- **Regression checks:** release build; 54 Android tests; 24 native tests across 9 suites (including byte-exact queue wrap/reset/conformance tests and parked-protocol rejection); 57 Python transport tests; 16 Linux parked-harness tests. The comma reconnect fix also passed all 59 isolated daemon tests on the device. The complete patch applies to the pinned upstream commit. An initial broad host suite also included an unrelated ONNX Runtime version check; that check failed because the host runtime was not loaded, and is excluded from these targeted passing counts.

The previous automatic-precision experiment remains in [the initial report](results-2026-10-03-initial.md).

## Direct comma USB results

Ignition remained off. Each run used 20 warmup frames, deterministic synthetic images and inputs, the full 18,452-element output, and 50 ms pacing. The peer identified as Tensor G6 with LiteRT 2.2.0 over USB SuperSpeed. No cameras, modeld, or controls were started by the harness.

| Measured run | Round-trip mean | p95 | p99 | Maximum | Frames over 50 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Short: 120 frames](parked-short-2026-10-03.json) | 39.49 ms | 41.84 ms | 43.16 ms | 55.58 ms | 1 / 120 |
| [One minute: 1,200 frames](parked-minute-2026-10-03.json) | 40.06 ms | 42.80 ms | 47.25 ms | 97.39 ms | 7 / 1,200 |
| [Extended: 2,400 frames](parked-extended-2026-10-03.json) | 53.41 ms | **98.86 ms** | 102.32 ms | **109.68 ms** | **876 / 2,400** |

The first two runs passed the predeclared synthetic gate: every requested frame completed with finite outputs and no protocol errors, round-trip p95 below 50 ms, and maximum below 100 ms. This is not an every-frame deadline pass: the minute run missed 50 ms on 0.58% of frames, and its worst case was close to the 100 ms limit. On that run, TPU inference mean was 34.03 ms, p95 35.81 ms, and max 65.41 ms; server-total p95 was 37.40 ms and max 65.98 ms.

The extended run completed all 2,400 requested frames with finite outputs and no protocol errors, but **failed the same timing gate**: p95 exceeded 50 ms and maximum exceeded 100 ms. **36.5%** of exchanges missed 50 ms. TPU inference itself reached p95 **92.22 ms** (max **99.17 ms**); queue p95 stayed **2.38 ms** and server-total p95 was **93.29 ms**. The observed slowdown is in phone-side inference rather than merely transport overhead. Live frame logs showed inference rising from roughly 34 ms to sustained 65–95 ms. A stop was requested after observing this, but the run had already completed; the report is a completed timing failure, not an interrupted sample.

The user confirmed the car was fully off and the Pixel had cooled before this run. Both raw ignition signals were read as false, with valid/live panda and device-state messages, during the connection window. The test was planned for two minutes at 20 Hz; slower exchanges extend that duration, and this harness revision did not record exact elapsed time. Accelerator Link was restored and no test process remained afterward. After the run, the user reported roughly 110°F outdoor conditions and that the Pixel felt very hot without air conditioning. This is user-reported environmental context, not a logged battery or chipset temperature. No Pixel temperature or charging samples were obtained, so thermal throttling is a strong suspect, not a confirmed cause. Temperature, thermal status, charging state, and per-window timings are needed during a controlled repeat before further performance tuning.

The short passes establish USB functionality, while the extended failure leaves sustained readiness unresolved. Camera-input numerical checks, sustained charging/temperature testing in the intended mount, repeated physical reconnects, and driving validation remain open. Phone thermal telemetry was not collected during these direct-USB runs. Normal driving requests remain refused in Tensor mode.

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

**Parked USB Test** defaults to off and must be enabled explicitly while present at the car; turn it off after each supervised session. The switch is not saved across app process restarts and closes after 10 minutes with unchanged server settings. Switching processor closes it. Tensor also rejects normal engine requests and raw inference without the explicit `validation_mode=parked` handshake; ordinary modeld clients remain blocked.

1. Keep the car parked with ignition off and Accelerator Link enabled. Attach only the Pixel as the accelerator, using the powered USB 3 hub and data cable described in [Android installation](../README.md).
2. On the Pixel, select **Tensor TPU (parked test)** and turn on **Parked USB Test**. Accept the USB permission prompt. Do not start a drive.
3. The script is already staged on the comma at `/data/clarity-tensor-validation-803/parked-test.py`. From your computer run:

   ```sh
   ssh comma@COMMA_IP '/usr/local/venv/bin/python /data/clarity-tensor-validation-803/parked-test.py --legacy-owner --frames 120 --output /data/clarity-parked-brief.json'
   ```

   For another installation, copy [parked-test.py](parked-test.py) and [validation.py](validation.py) into the same directory first. Choose a new result filename for each run. Start with 120 measured frames; repeat with `--frames 1200` only after a clean short check. `--legacy-owner` matches this comma's installed offroad daemon: it temporarily disables Accelerator Link, waits for the daemon to exit and USB to unbind, then opens the interface exclusively. It closes USB and restores Accelerator Link afterward, including on failure. A USB prompt or one deliberate reconnect during this ownership handoff is separate from repeated connect/disconnect cycling. On newer installations whose daemon exposes `/dev/shm/jetlink-lend.sock`, omit this flag to borrow the existing owner's endpoints without changing settings.
4. Review protocol success, negotiated USB speed, round-trip p95/p99/max, and missed 50 ms deadlines. The script refuses ignition-on/camera/model activity, checks offroad state before each inference, and releases USB even on failure. Legacy ownership temporarily changes only the enable setting; engine readiness is never written by the harness. It does not start cameras/controls or send steering commands.
5. Turn **Parked USB Test off** when finished. A passing synthetic parked result is one transport milestone; camera-input parity, in-mount charging/heat, reconnect behavior, and driving validation remain separate.

The installed comma daemon uses exclusive USB ownership rather than the newer loan service. The harness supports both methods and waits up to 60 seconds for USB to configure before sending HELLO (`--connect-timeout`, 10–120 seconds). It refuses a network loan so the report cannot mislabel TCP results as direct USB.

The first two attempts completed zero inference frames: [no reader before the write watchdog](parked-connection-2026-10-03.json), then [no host configured before the transport timeout](parked-connection-second-2026-10-03.json). Live logs also exposed the repeated connect/disconnect: ordinary provisioning sent ENGINE_REQ to a parked-only peer, its refusal caused an unbind/rebind, and the resulting attach edge reset the retry delay. The daemon now recognizes `validation=parked_only` in HELLO, holds USB, displays “connected for parked testing,” and makes no normal engine request. It does not mark the peer ready for driving. Unplugging or disabling clears this attachment restriction, so a subsequent Jetson can provision normally.

After installing that fix, the phone negotiated SuperSpeed and all three supervised USB runs completed. The short runs passed timing; the extended run failed timing as detailed above. Accelerator Link was restored after each run. The phone APK and model were unchanged.

## Repeat desk validation

Use upstream `scripts/verify_parity.py capture --parked`, followed by `reference` with the original ONNX and `compare`. Only the explicit parked handshake was added; comparison thresholds are unchanged. The patch also makes TCP writes work on Windows sockets without `sendmsg`.

For timing, put the patched upstream checkout on `PYTHONPATH`, create `adb forward tcp:5599 tcp:5599`, and run [benchmark.py](benchmark.py) with the source hash/size, output path, transport label, and optional ADB executable for thermal sampling. Default pacing is 50 ms; `--frames 12000` repeats the soak. Both harnesses now require the `.3` app health telemetry and the adjacent [validation.py](validation.py) module. The tool stops for non-finite outputs, protocol failure, stale/missing health, Android thermal status 3+, battery temperature 43°C+, or the windowed phone timing limits above. Remove forwarding afterward with `adb forward --remove tcp:5599`.

## References

- [Android thermal status and headroom API](https://developer.android.com/reference/android/os/PowerManager)

- [Google Tensor support](https://developers.google.com/edge/litert/next/tensor-sdk)
- [Compiler precision and sharding flags](https://developers.google.com/edge/tensor-sdk/compilation-flags)
- [LiteRT 2.2.0 Tensor performance modes](https://github.com/google-ai-edge/LiteRT/blob/v2.2.0/litert/c/options/litert_google_tensor_options_type.h)
- [Official LiteRT 2.2.0 release](https://github.com/google-ai-edge/LiteRT/releases/tag/v2.2.0)
