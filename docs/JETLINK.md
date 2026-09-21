# Jetlink integration

This branch starts from sunnypilot and ports the comma-side Jetlink integration
from Zoompilot's `jetson-trt` branch. The Jetlink server itself remains the
version pinned in the `jetlink_repo` submodule; keep the two revisions paired.

## Scope and compatibility

- The supported accelerator host is an NVIDIA **Jetson Orin Nano Super 8 GB**
  running JetPack 6.2 (L4T r36.4.3). “Jetson Nano Super” is not a separate
  tested target.
- Jetlink needs a USB 3 **A-to-C data** cable from a Jetson USB-A host port to
  the comma USB-C port. Give the comma and Jetson separate, adequately sized
  power supplies; the comma must not power the Jetson.
- The comma keeps camera capture and vehicle control. The Jetson runs the large
  model. If the link drops while the large model is active, the system is
  designed to soft-disable and return to the small model.
- This code port does **not** validate a Honda Clarity, a comma four, or any
  3x-EPS modification. Verify the vehicle interface, CAN safety model, steering
  limits, wiring, and local legal requirements independently before any
  on-road use. Start with bench and closed-course testing.

## Developer checkout

Clone with submodules, or initialize the pinned server after checkout:

```sh
git submodule update --init --recursive
```

To prepare the Jetson host, follow the pinned server's instructions:

```sh
cd jetlink_repo
git rev-parse HEAD
```

Use the matching Jetson release image or build from that checkout. Do not point
the comma at an arbitrary newer Jetlink server revision: the link protocol and
model format are paired releases.

## Comma UI

After a device build containing this branch is installed, enable **Settings >
Models > Accelerator Link** while parked and online. Wait for the status to
show ready before driving. Keep the small model configured as the fallback.

For server logs, power behavior, and model preparation guidance, read
`jetlink_repo/docs/jetson.md` and `jetlink_repo/docs/transport.md`.
