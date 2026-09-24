# 745-SP

745-SP is a personal, experimental build of [sunnypilot](https://github.com/sunnypilot/sunnypilot) for a **comma 4** paired with an **NVIDIA Jetson Orin Nano Super**. It includes sunnypilot pull request [#2001](https://github.com/sunnypilot/sunnypilot/pull/2001), which adds the Jetlink accelerator integration.

**This is a custom build for my car. Do not use this.**

## What this build does

The comma remains responsible for the safety- and vehicle-facing work: cameras, image warp, model-output parsing, vehicle interface, driver monitoring, and CAN communication. The Jetson has no CAN access; it runs the selected large driving model with TensorRT and returns model outputs to the comma over USB.

```text
comma 4                                                     Jetson Orin Nano Super
cameras -> local image warp -> USB 3 -> model history -> TensorRT inference
vehicle controls <- model parser <- USB 3 <- model outputs
```

The built-in small model starts first. If the Jetson is still booting, the comma continues with that model and joins the large Jetlink model after the USB link and cached TensorRT engine are ready. If the link is lost, the system falls back to the local model and retries the connection. A loss while engaged is a soft-disable condition.

## Included configuration

- sunnypilot master snapshot with Jetlink support from PR #2001
- Jetlink server pinned as the `jetlink_repo` submodule
- USB FunctionFS transport: **Jetson USB-A -> comma USB-C**
- Accelerator Link control in **Settings -> Models**, visible before the Jetson is detected
- Large-model selection, download/provisioning progress, cached-engine validation, telemetry, reconnect, and native-model fallback
- The default available Jetlink model is **Cinque Terre**. Its ONNX object is fetched only when it is needed; it is intentionally not included in the normal comma install.

The model ONNX is about **766 MB**. The TensorRT engine is stored separately on the Jetson and is of similar size, so leave several GB free for the container, model, engine cache, and updates.

## Hardware and software requirements

| Component | Expected setup |
| --- | --- |
| Driving device | comma 4 |
| Accelerator | Jetson Orin Nano Super, 8 GB |
| Jetson software | JetPack 6.1 / L4T r36.4, TensorRT 10.3, Docker with NVIDIA runtime |
| Data link | USB 3 Type-A to Type-C **data** cable; Jetson is the USB host |
| Jetson power | Separate regulated supply sized for the 25 W Jetson power mode |
| Storage | Several GB free under `/mnt/data/jetlink` |

Use the Jetson's USB-A host port. The Orin Nano devkit USB-C port is not the Jetlink data connection. Keep the Jetson at its configured **25 W** mode and ensure its cooling path is clear.

## Install on the comma

1. Factory-reset the comma if replacing an existing custom build. Connect it to stable Wi-Fi or Ethernet and leave it powered through installation and the first boot.
2. On the comma, open **Custom Software** and enter:

   ```text
   installer.comma.ai/ryanafdahl/745-SP
   ```

3. Let the installer finish. The first boot can take longer while system packages, prebuilt assets, and the local model initialize. Do not interrupt power during that work.
4. Complete normal comma setup and calibration before testing the accelerator. Confirm the vehicle is recognized and that native driving functions correctly with the Jetson disconnected.
5. While parked, open **Settings -> Models** and turn on **Accelerator Link**. The toggle is intentionally available even before USB detection.

The short form `ryanafdahl/745-SP` may also be accepted by the Custom Software screen; the full URL above is the unambiguous installer address.

## Set up and pair the Jetson

Use the Jetlink revision pinned by this repository for both the comma integration and Jetson server. The upstream Jetlink [setup guide](https://github.com/zoompilot/jetlink/tree/1f0767fd3368c2894929f96e4f934b8824fc2500) contains the server, transport, cache, and service commands.

1. Set up the Jetson while parked, with stable internet, cooling, storage, and its 25 W power supply.
2. Build and run the Jetlink server with USB transport. Keep it running while bringing up the comma link.
3. Connect **Jetson USB-A -> comma USB-C** with a USB 3 data cable.
4. On the comma, enable **Accelerator Link**, choose a large model, and stay offroad until download and engine preparation complete.
5. Wait for the engine to be cached on the Jetson. A first engine build normally takes a few minutes; subsequent starts reuse the cached engine.

Do not update one side of the pair independently. Updating, reflashing, changing TensorRT, changing GPU architecture, or selecting a different model can require a matching engine rebuild.

## Verify before a road test

The GPU icon is only a quick status signal. A green icon means the connected accelerator is reporting ready; a flashing icon can mean the server is booting, the model is downloading, or an engine is being prepared.

Before driving, verify all of the following while parked:

- The Jetlink server is running on the Jetson: `sudo systemctl status jetlink-server`
- The comma sees the USB gadget after the Jetson powers up
- The selected engine is ready and the GPU icon becomes green
- Jetson telemetry reports temperature, power, GPU activity, and inference timing
- The comma can fall back to its native model if the Jetson is disconnected

For a diagnostic drive, keep the first route short and retain logs from both devices. `modelV2.big=true`, live Jetlink telemetry, and no frame drops or reconnect/fallback events are stronger evidence than the icon alone.

## Honda Clarity and modified EPS note

Vehicle support and any modified-EPS behavior depend on the exact fingerprint and EPS firmware seen by the comma. This repository does not make a torque modification itself and does not prove that a particular modified EPS is safe or supported. Validate the normal, stock vehicle interface first; treat modified-EPS testing as a separate, supervised validation effort.

## Troubleshooting

| Symptom | First checks |
| --- | --- |
| No USB icon | Confirm the USB-A-to-USB-C data path, Jetson power, and that Accelerator Link is enabled. |
| Flashing GPU icon | Allow Jetson boot, model transfer, and TensorRT engine preparation to finish; inspect `journalctl -u jetlink-server -b`. |
| Green icon never appears | Confirm both ends use the paired Jetlink revision, the server is running, and the selected model has a cached engine. |
| GPU connects then drops | Check cable seating, USB SuperSpeed negotiation, Jetson supply voltage, cooling, and Jetlink logs on both devices. |
| Model build fails | Check free space under `/mnt/data/jetlink`, JetPack/TensorRT compatibility, and the server log. |

Raw driving logs can contain location, video, CAN, and device data. Keep them private unless they have been deliberately sanitized.

## Sources and licenses

745-SP is based on [sunnypilot](https://github.com/sunnypilot/sunnypilot), [comma.ai openpilot](https://github.com/commaai/openpilot), and [Zoompilot Jetlink](https://github.com/zoompilot/jetlink). See [LICENSE](LICENSE) and [LICENSE.md](LICENSE.md) for license notices and disclaimers.
