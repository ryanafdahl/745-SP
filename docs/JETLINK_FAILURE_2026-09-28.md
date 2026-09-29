# JetLink connection failure — September 28, 2026

## Result

The comma evidence confirms no large-model operation in any of today's five recorded drives. The cause remains unresolved because Jetson SSH authentication is unavailable. Its SSH server responds at the previously used address, but `username` key authentication fails. The owner confirms the Jetson is now at the desktop and disconnected from the comma; current USB absence is expected.

## Evidence collected

Collected 712 application logs and 185 qlogs into ignored `diagnostics/2026-09-28-no-jetlink/`, plus a live comma snapshot, kernel USB events, deployed-code excerpts, and route-analysis JSON. The archive contains 897 files (99,261,202 bytes); SHA256 is `D6C1A35F47198B25D74F4E615A881562FC21654B453340976648B90EC9B2140B`.

Selection begins September 28 at 07:00 UTC (midnight PDT), using file modification times. Application-event times below are PDT. No Jetson logs have yet been retrieved in this investigation. No device settings, services, or software were changed.

The comma runs deployed commit `d57c4b533558bb2314f542a2ea78c3271b265eda`. Live `JetlinkEnabled=1`, cached model specification exists, gadget setup marker is `ok`, and the offroad jetlinkd process runs. `JetlinkEngineReady` was absent from the live parameter listing. These are capture-time observations, not a reconstruction of every drive-time parameter.

## Recorded drives

The existing `tools/analyze_comma_routes.py` ran in the comma's openpilot Python environment. All 185 qlogs parsed without errors.

| Drive order | Approximate start PDT from modeld | Segments | Recorded span (minutes) | Small-model samples | Large-model samples |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 05:41 | 5 | 4.20 | 493 | 0 |
| 2 | 05:48 | 54 | 53.62 | 6,424 | 0 |
| 3 | 11:21 | 39 | 38.48 | 4,606 | 0 |
| 4 | 12:01 | 11 | 10.78 | 1,283 | 0 |
| 5 | 15:37 | 76 | 75.28 | 9,023 | 0 |

Total: 21,829 small-model samples over approximately 182.36 recorded minutes. Qlogs are sampled evidence, not every inference frame. There are no observed transitions to the large model. The last drive's small-model execution mean is 28.61 ms, p95 30.18 ms, with a 2,051 ms maximum; this maximum alone does not diagnose the connection failure.

## Connection timeline and indicator

Application logs record `gadget presented, waiting for a jetson` at 05:46:02, 06:41:36, 11:59:28, 12:12:09, and 16:52:19. The captured day's JetLink events contain no successful attach, engine-ready, or Jetson telemetry event. Manager stopping jetlinkd at drive startup is the normal offroad/onroad process handoff and does not itself prove a crash.

Kernel logs show repeated Type-C source connections and disconnects during the morning, starting at 05:41:57. The afternoon shows connections at 15:38:23 and 15:38:52, with disconnects at 15:38:46 and 15:40:18. These establish electrical Type-C connection changes, not successful JetLink protocol communication or the identity of the attached host. Some USB power-delivery log entries say `pd_phy_signal: failed ret 0`; those messages alone do not establish the root cause.

The deployed helper requires the USB device controller to reach `configured` before reporting an attached host. The deployed UI returns `DISCONNECTED` when no accelerator is present, even onroad; a detected pending join can instead show `LOADING`. This explains why no blinking indicator is consistent with a failure before recognized accelerator attachment, rather than merely a long model build.

The deployed stock modeld also gates JetLink startup on `accelerators.ready()` and `accelerators.prepare()`. Readiness requires the matching engine-ready marker. A cached model specification alone does not satisfy that gate. This provides a plausible explanation for ordinary small-model startup without connection retries once provisioning has not completed; historical readiness values were not recorded directly in this capture.

## What remains to distinguish

The current evidence does not distinguish a Jetson boot/service failure from car power trouble, USB cable/port trouble, or a gadget/host configuration problem. The September 26 nvpmodel/CDI ordering issue is a relevant prior incident, not proof that the same failure recurred today.

Next, authenticate to the Jetson and collect hostname/uptime, boot list, jetlink-server/nvpmodel/nvidia-cdi-refresh status and unit definitions, targeted service and kernel logs, and retained syslog including rotated files. The prior car boot used an unset clock, so include boot identifiers and monotonic times rather than filtering only by today's date. Inspect the installed CDI ordering drop-in and look for nvpmodel failure, dependency failure, engine readiness, USB enumeration, or repeated resets. Preserve this evidence before any restart or repair. A connected test will still be needed to validate the car USB/power path after the fault is identified.
