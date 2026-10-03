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
