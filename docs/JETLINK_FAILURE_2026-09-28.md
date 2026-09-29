# JetLink connection failure — September 28, 2026

## Result

The comma evidence confirms no large-model operation in any of today's five recorded drives. Paired logs and deployed code identify a missing comma readiness marker as the leading explanation, following the previous evening's Pixel parked test. The Jetson successfully loads its engine, but the comma's missing marker prevents its onroad JetLink connection path from starting. A connected parked recovery test remains necessary. The Jetson is currently at the desktop and disconnected from the comma; current USB absence is expected.

## Evidence collected

Collected 712 application logs and 185 qlogs into ignored `diagnostics/2026-09-28-no-jetlink/`, plus a live comma snapshot, kernel USB events, deployed-code excerpts, and route-analysis JSON. The archive contains 897 files (99,261,202 bytes); SHA256 is `D6C1A35F47198B25D74F4E615A881562FC21654B453340976648B90EC9B2140B`.

Selection begins September 28 at 07:00 UTC (midnight PDT), using file modification times. Application-event times below are PDT. Jetson logs were subsequently retrieved over Ethernet at 192.168.1.187 after authenticated login. No device settings, services, or software were changed.

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

## Jetson evidence recovered

Retrieved service definitions/status, retained service journal, filtered syslog, recent unfiltered syslog, dmesg, container logs, and boot records. Archive `jetlink-diag-20260928.tar.gz` SHA256: `E3D49DA5C199A437AD68CA73CDC88F8CBF65261CC1391357975CBCF5E8E5CC96`. Additional boot context is in `jetlink-diag-20260928-extra.tar.gz`.

The desktop boot has active JetLink, successful nvpmodel, successful CDI generation, and the installed `20-after-nvpmodel.conf` ordering fix. The container loads TensorRT 10.16.2.10 and the expected `e8d821733be15ebe` engine, captures its CUDA graph, and reports engine ready. It waits for USB gadget `1209:0001`, as expected while disconnected.

After the last inference-bearing boot in retained syslog, seven successive boot blocks contain successful nvpmodel initialization and no comma gadget enumeration. Six contain explicit engine-ready messages; one block ends after service start without a readiness result. None of these seven blocks shows nvpmodel failure. See `syslog-filtered.txt` lines 11456-11820. Their unset/reset clocks prevent assigning exact September 28 drive times or treating the journal boot list as complete. These logs do not support recurrence of the earlier nvpmodel/CDI failure. They also do not independently rule out a physical USB fault.

## Readiness loss after the Pixel test

The previous evening's comma logs identify the connected server as `Pixel 11 Pro XL / Tensor G6 trt None`. At 19:43:29, normal JetLink provisioning fails with `engine build failed: Model accuracy unqualified: parked test client and exact model required`. That message is emitted by the Pixel test app. The generic log wording `jetson attached` therefore must not be treated as proof that this was the NVIDIA device.

At **20:09:57.221 PDT on September 27**, jetlinkd logs `disabled, releasing the link`. The verified deployed `jetlinkd.step()` branch immediately calls `helpers.set_engine_ready(None)`, removing `JetlinkEngineReady`. At 20:12:02, the daemon restarts; at 20:12:03 it presents the gadget and waits for a host. No subsequent engine-ready success appears in the collected readiness history or September 28 application logs. The marker remains absent during live inspection, while `JetlinkEnabled=1`.

The local parked-test helper `tools/pixel_jetlink/parked_comma.py` saves `JetlinkEnabled`, disables it to release USB for the isolated test, then restores only that saved enable setting. It does not preserve or re-establish `JetlinkEngineReady`. The adjacent Pixel project's recorded September 27 test result confirms that the enable setting was restored to 1 afterward. The timing, log messages, and helper behavior strongly support a test cleanup side effect; there is no need to assume the owner manually changed the setting.

The resulting startup sequence explains today's symptom:

1. The readiness marker is absent, even though the Jetson's cached engine still exists.
2. Manager stops the offroad jetlinkd daemon when the drive starts.
3. Stock modeld checks `accelerators.ready()` once at startup. With no marker, it does not create the JetLink joining model or present its USB gadget.
4. A Jetson that becomes available after that transition cannot complete offroad provisioning or join this modeld instance. The small model runs, and the UI has no configured accelerator to show as loading.

This is a software readiness/reconnection gap. It explains the consistent all-small-model drives and missing indicator, and is more directly supported than a GPU or TensorRT failure. Historical per-drive readiness values and paired USB traces are incomplete, so a connected test is still required to establish the full causal chain and exclude an additional cable/port issue.

## Recovery and remaining validation

With both devices connected by USB and powered, keep the comma offroad long enough for its normal daemon to detect the real Jetson and verify the cached engine. Confirm an `engine ready` event and a matching `JetlinkEngineReady` value before testing a subsequent drive transition. Do not manufacture a readiness marker simply to bypass verification.

A durable code change should address both the parked-test cleanup side effect and the onroad inability to reconnect without a pre-existing readiness marker, while retaining model identity verification. Neither change has been deployed in this diagnostic pass. No device settings, services, or software were changed; no connected validation or recovery has yet been performed.
