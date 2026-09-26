# 745-SP

745-SP is a personal, experimental [sunnypilot](https://github.com/sunnypilot/sunnypilot) build for a **comma 4** paired with an **NVIDIA Jetson Orin Nano Super Developer Kit (8 GB)**. It uses [JetLink](https://github.com/zoompilot/jetlink) to run a large driving model on the Jetson over USB, while keeping the selected small model available on the comma.

**This is a custom build for my car. Do not use this.**

[Setup](#jetson-setup) · [Models](#models) · [Validation](#what-has-been-verified) · [Troubleshooting](#troubleshooting) · [Reports](#logs-and-reports)

## How it works

The comma handles cameras, image warp, model-output parsing, vehicle control, driver monitoring, and communication with the car. The Jetson runs TensorRT inference and returns model outputs. It has no CAN connection.

```text
comma 4                                    Jetson Orin Nano Super
cameras → image warp ─── USB 3 ────────────→ model history → TensorRT
vehicle control ← model parser ←── USB 3 ─── model outputs
```

The small model starts first. Once the USB link and large-model engine are ready, JetLink can join without restarting the drive. A link failure returns inference to the selected small model and starts reconnection attempts. Loss of the large model while engaged is a soft-disable condition; fallback does not guarantee uninterrupted engagement.

## Verified hardware and software

This configuration was checked on September 26, 2026:

| Component | Verified configuration |
| --- | --- |
| Driving device | comma 4 |
| Accelerator | NVIDIA Jetson Orin Nano Super Developer Kit, 8 GB |
| Jetson OS | Ubuntu 24.04.4, JetPack 7.2.1 / L4T 39.2.1 |
| JetLink server | v0.4.0, `ghcr.io/zoompilot/jetlink:0.4.0-cuda` |
| Inference runtime | TensorRT 10.16.2.10 |
| Power profile | MAXN_SUPER, mode 2 |
| Car power behavior | Switched with the car; suspend timer disabled |
| Data connection | Jetson USB-A host port → comma USB-C, USB 3 data cable |
| Model cache | `/mnt/data/jetlink` on the Jetson |

### Which Jetson is it?

A live SSH check returned this device-tree model:

```text
NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super
```

The identifiers are module `P3767-0005`, carrier `P3768-0000`, and SoC `tegra234`, with the `-super` configuration. NVIDIA identifies that module as the [Jetson Orin Nano 8 GB](https://docs.nvidia.com/jetson/archives/r36.5/DeveloperGuide/IN/QuickStart.html#jetson-modules-and-configurations), and calls the kit the [Jetson Orin Nano Super Developer Kit](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/). **“Orin” is part of the full product name.** This confirms the current platform; it does not establish whether the original retail package predated the Super software update.

Use a separate regulated Jetson supply sized for the selected power profile, with adequate cooling. The Jetson's USB-A port carries the data connection; its USB-C port is not the JetLink host connection to the comma.

## Models

| Role | Repository default | Behavior |
| --- | --- | --- |
| Small model on the comma | **The Cool Peoples Model v3 (TCPMV3)**, October 10, 2025 | Fresh installs download and select it while parked. Existing selections are preserved. |
| Large model on the Jetson | **Cinque Terre Model V2**, September 8, 2026 | Available through Accelerator Link; downloaded and prepared when selected. |

Interrupted first-install small-model downloads retry while parked. Explicitly cancelling the download or choosing another small model stops automatic selection. The bundled model remains available during initial provisioning.

The September 26 drive used the previously selected **Cinque Terre Model, September 4, 2026**, not V2. Its model selection was preserved during the Jetson update. Most models in this repository's JetLink catalog are about 766 MB before engine preparation; allow several GB for downloads, engines, containers, and updates.

The comma client remains pinned by the `jetlink_repo` submodule at `1f0767fd3368c2894929f96e4f934b8824fc2500`. The tested Jetson server is v0.4.0. The deployed client's protocol file matched v0.4.0, and the paired drive exercised this combination. That does not establish compatibility with arbitrary future client or server updates.

## Repository and comma installation

The source of record is **[ryanafdahl/745-SP](https://github.com/ryanafdahl/745-SP), branch `main`**. For a development checkout:

```sh
git clone --recurse-submodules --branch main https://github.com/ryanafdahl/745-SP.git
cd 745-SP
```

Continue with the [development environment guide](tools/README.md), using this checkout in place of its upstream clone example. Cloning on a development computer does not install the software on the comma.

The earlier installation address, `installer.comma.ai/ryanafdahl/745-SP`, selects the **`745-SP` branch of `ryanafdahl/openpilot`**. The [comma fork installer](https://github.com/commaai/openpilot/wiki/Forks#url-installers) uses an owner and branch and assumes the repository is named `openpilot`. The captured comma deployment came from that separate repository. A dedicated Custom Software installer for this repository's `main` has not been verified, and pushing here does not update the comma automatically.

Before changing a device installation, preserve its settings and needed logs and confirm its repository, branch, and commit. Once the intended build is installed, complete normal vehicle setup and calibration, leave it online while parked for model downloads, and confirm the small model works before pairing the accelerator.

## Jetson setup

The tested release is **[JetLink v0.4.0](https://github.com/zoompilot/jetlink/releases/tag/v0.4.0)**. Its [Jetson guide](https://github.com/zoompilot/jetlink/blob/v0.4.0/docs/jetson.md) supports JetPack 7.2.1 and 6.2. This project's device already runs 7.2.1; the previous README's JetPack 6.1 / TensorRT 10.3 / fixed 25 W instructions describe an older setup.

With the Jetson on a stable supply and connected to the internet, run the release-pinned installer on the Jetson:

```sh
curl -fsSL https://raw.githubusercontent.com/zoompilot/jetlink/v0.4.0/install.sh -o install-v0.4.0.sh && \
  sudo bash install-v0.4.0.sh --ref v0.4.0
```

For this car, retain **MAXN SUPER** and choose **switched power**. Keep the existing model cache when updating. Follow any reboot instruction from the installer, then check:

```sh
jetlink status
sudo nvpmodel -q
sudo systemctl status jetlink-server.service --no-pager
```

While parked, connect **Jetson USB-A → comma USB-C** with a USB 3 data cable. On the comma, open **Settings → Models**, enable **Accelerator Link**, and choose the large model. The toggle is available before the Jetson is detected. Keep both devices powered and the comma online until download and engine preparation finish.

A TensorRT or model change can require a new engine even when the ONNX download is already cached. The recorded rebuild took 185 seconds; build time varies. For manual preparation, follow the [model preparation guide](https://github.com/zoompilot/jetlink/blob/v0.4.0/docs/models.md): stop the server before preparing an engine in a separate process, then start it again.

`jetlink update` retains the saved release ref. An installation pinned to `v0.4.0` stays on that ref; choosing a newer release requires an explicit installer `--ref`. Preserve the prior settings and engine cache for rollback. The [update record](docs/JETSON_UPDATE_2026-09-26.md) contains the installed image digest, backup details, and compatibility checks.

## What has been verified

The [September 26 short drive](docs/JETLINK_DRIVE_2026-09-26.md) recorded 3 minutes 50 seconds, including about 3 minutes on the large model. Sampled large-model execution averaged **31.70 ms**, with **33.79 ms p95**. The largest sample, **204.81 ms**, occurred at the initial large-model join. These are sampled inference timings, not complete camera-to-control latency or a guarantee that every frame met its deadline.

A later desk boot exposed a CDI/nvpmodel startup-order problem. The applied fix passed **one software reboot**, with the engine ready **20.61 seconds after boot**. The drive preceded that fix. A new car power-cycle test and complete full-rate logs for the short drive remain pending; the final USB disconnect occurred about two seconds before modeld stopped, and its precise cause is unconfirmed.

The drive used comma commit `d57c4b533558bb2314f542a2ea78c3271b265eda` from the separate deployment repository. These results describe that device configuration, not a road validation of every change on this repository's `main`.

For the next parked check, confirm the server and engine are ready, the comma shows a green accelerator indicator, and telemetry is live. `modelV2.big=true` in full-rate logs or `drivingModelData.big=true` in qlogs confirms large-model output. Keep logs from both devices when investigating a join, fallback, or disconnect; the icon alone cannot establish continuous operation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| JetLink is inactive after boot | Inspect `nvpmodel.service`, `nvidia-cdi-refresh.service`, and `jetlink-server.service`. Exit status 234 from nvpmodel can block JetLink; see the boot-order note below. |
| Accelerator never becomes ready | Check the USB-A-to-USB-C data cable, Accelerator Link toggle, server status, selected model, and engine-preparation log. |
| Delay or lag at startup | Separate small-model initialization, Jetson boot, engine loading, and the first USB inference exchange. Startup outliers do not establish steady-state GPU slowdown. |
| USB link drops | Compare both devices' logs with the timing of power changes; inspect the cable, USB negotiation, supply, and cooling. Preserve fallback protections. |
| Model preparation fails | Check runtime compatibility and available cache space. Avoid concurrent engine builds against the same cache. |
| Repeated catalog DNS warnings | Check offroad internet access. The catalog manager retries both sources every second when its cache is expired; cached models may remain usable. Retry backoff has not yet been added. |

The tracked [CDI dependency drop-in](scripts/jetson/nvidia-cdi-refresh.service.d/20-after-nvpmodel.conf) makes CDI wait for successful power initialization. It was applied to this Jetson, whose nvpmodel unit has `RemainAfterExit=yes`. **Do not copy it blindly onto a stock unit with `RemainAfterExit=no`.** The [boot-order investigation](docs/JETLINK_DRIVE_2026-09-26.md#jetson-boot-failure-and-applied-fix) explains the prerequisite, validation, and rollback.

For a bounded startup capture on the Jetson:

```sh
sudo journalctl -b -u nvpmodel.service -u nvidia-cdi-refresh.service -u jetlink-server.service -n 150 --no-pager
```

## Logs and reports

| Report | Covers |
| --- | --- |
| [Comma drive analysis](docs/COMMA_LOG_ANALYSIS_2026-09-26.md) | Two earlier drives, first-frame delays, and the isolated selfdrive-loop lag investigation |
| [Jetson v0.4.0 update](docs/JETSON_UPDATE_2026-09-26.md) | Release pin, runtime, power configuration, backups, and engine rebuild |
| [Post-update drive and boot repair](docs/JETLINK_DRIVE_2026-09-26.md) | Short-drive results, DNS retries, startup fix, and remaining validation |
| [Earlier device review](docs/DEVICE_LOG_ANALYSIS_2026-09.md) | Historical platform observations and storage concerns; predates the update |

From a development checkout, summarize a saved JetLink server log with:

```sh
python tools/analyze_jetlink_log.py jetlink-server.log
```

For qlogs, use the openpilot Python environment with its dependencies available:

```sh
python tools/analyze_comma_routes.py '/path/to/extracted/*/qlog.zst'
```

The server analyzer summarizes logged slow-frame warnings, not every inference. The route analyzer reports sampled model metrics, mode transitions, and event-message counts. Raw routes and device logs can contain location, video, CAN, and identifiers; keep them in ignored `diagnostics/` rather than committing them.

## Vehicle scope and credits

Vehicle support, including Honda Clarity and modified-EPS behavior, depends on the exact fingerprint and firmware. This repository does not perform an EPS torque modification or establish that a modified EPS is supported. See the project's [safety documentation](docs/SAFETY.md) and [limitations](docs/LIMITATIONS.md).

Built on [sunnypilot](https://github.com/sunnypilot/sunnypilot), [comma.ai openpilot](https://github.com/commaai/openpilot), and [Zoompilot JetLink](https://github.com/zoompilot/jetlink), including the accelerator integration from sunnypilot [PR #2001](https://github.com/sunnypilot/sunnypilot/pull/2001). See [LICENSE](LICENSE) and [LICENSE.md](LICENSE.md) for the applicable notices.
