#!/usr/bin/env python3
"""Supervised, ignition-off Tensor USB test. Never starts cameras or controls.

Uses the comma's existing JetLink loan API; does not change its enable/readiness
parameters or gadget configuration. Run only when physically present at the car.
"""
import argparse
import json
from pathlib import Path
import signal
import sys
import time
import numpy as np

sys.path.insert(0, '/data/openpilot')
sys.path.insert(0, '/data/openpilot/jetlink_repo')
from openpilot.common.params import Params
from jetlink import protocol as P
from jetlink.client import JetlinkClient
from jetlink.comma.lending import borrow

SOURCE = '09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec'
SOURCE_BYTES = 766040736


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frames', type=int, default=1200)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not 20 <= a.frames <= 2400: p.error('frames must be 20..2400')
    if a.output.exists(): p.error('output already exists; choose a new filename')
    params = Params()
    def parked():
        if not params.get_bool('IsOffroad'):
            raise RuntimeError('Ignition must stay off; test stopped')
    parked()
    if not params.get_bool('JetlinkEnabled'):
        raise RuntimeError('Enable Accelerator Link while parked before this test')
    for entry in Path('/proc').glob('[0-9]*/cmdline'):
        try: argv = entry.read_bytes().split(b'\0')
        except OSError: continue
        if any(Path(v.decode(errors='replace')).name in ('modeld', 'camerad') or v == b'openpilot.selfdrive.modeld.modeld' for v in argv):
            raise RuntimeError('Camera/model processes are active; test refused')
    def interrupted(*_): raise RuntimeError('Test interrupted or timed out')
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM): signal.signal(sig, interrupted)
    signal.alarm(180)
    client = loan = None
    rows = []
    report = {'source_sha256':SOURCE, 'transport':'direct comma USB', 'driving_ready':False,
              'requested_frames':a.frames, 'warmup_frames':20, 'failures':[]}
    try:
        loan = borrow(name='clarity-parked-test', timeout=10)
        if loan is None: raise RuntimeError('JetLink owner could not lend USB; no settings were changed')
        parked()
        client = JetlinkClient.open_loan(loan, name='clarity-parked-test', want_hidden=True, deadline=2)
        hello = client.hello(timeout=20)
        parked()
        if hello.get('validation') != 'parked_only' or hello.get('device') != 'tensor-Tensor_G6':
            raise RuntimeError('Expected the Tensor G6 parked-only app; peer did not match')
        report['runtime'] = hello.get('runtime_version')
        report['link'] = client.t.link_info()
        send_json = client.t.send_json
        def parked_request(kind, seq, data, flags=0):
            if kind == P.Msg.ENGINE_REQ: data = dict(data, validation_mode='parked')
            return send_json(kind, seq, data, flags)
        client.t.send_json = parked_request
        spec = client.ensure_engine(SOURCE, SOURCE_BYTES, frame_skip=4, build_timeout=30)
        if spec.output_nelem != 18452: raise RuntimeError('Unexpected output shape')
        # Deterministic synthetic image; features/desires are queued by the server.
        warped = np.arange(spec.warped_nbytes, dtype=np.uint8).reshape(spec.warped_shape)
        packed = np.zeros(spec.packed_nelem,np.float32)
        for name,(at,_) in spec.packed_layout.items():
            if name == 'traffic_convention': packed[at] = [1,0]
            if name == 'action_t': packed[at] = [0.25,0.35]
        due = time.monotonic()
        for i in range(a.frames+20):
            parked()
            time.sleep(max(0,due-time.monotonic()))
            parked()
            start = time.monotonic()
            out = client.infer(warped,packed,frame_id=i,reset=(i==0))
            elapsed=(time.monotonic()-start)*1000
            if not np.isfinite(out).all(): raise RuntimeError('Non-finite output')
            if i>=20: rows.append([elapsed]+[v/1000 for v in client.last_timings])
            due=max(due+0.05,time.monotonic())
            if i and i%200==0: print(f'{len(rows)} measured frames; latest exchange {elapsed:.2f} ms',flush=True)
    except Exception as e:
        report['failures'].append(str(e))
    finally:
        signal.alarm(0)
        for resource in (client, loan):
            if resource:
                try: resource.close()
                except Exception as e: report['failures'].append(f'Cleanup: {e}')
        report['measured_frames']=len(rows)
        report['protocol_pass']=len(rows)==a.frames and not report['failures']
        if rows:
            data=np.asarray(rows)
            for i,name in enumerate(['round_trip','inference','queues','server_total']):
                v=data[:,i]
                report[name]={'mean_ms':float(v.mean()),'p95_ms':float(np.percentile(v,95)),
                    'p99_ms':float(np.percentile(v,99)),'max_ms':float(v.max()),'over_50ms':int((v>50).sum())}
            report['timing_pass']=report['protocol_pass'] and report['round_trip']['p95_ms']<50 and report['round_trip']['max_ms']<100
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)
        print('USB loan released. Turn off Parked USB Test on the Pixel. Driving remains blocked.',flush=True)
    return 0 if report['protocol_pass'] and report.get('timing_pass') else 1


if __name__=='__main__': raise SystemExit(main())