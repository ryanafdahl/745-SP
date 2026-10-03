"""Read-only vehicle guards for a pre-armed, stationary ignition-on USB test.

No CAN messages, model outputs, engagement commands, or process signals are
published here. Startup isolation depends on the pinned deployment: the test
must disable Accelerator Link while offroad, before any model process starts.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time

LIMITS = {'pandaStates':1.5, 'deviceState':1.5, 'carState':0.5,
          'selfdriveState':0.5, 'carControl':0.5, 'modelV2':0.5}
MODELS = {b'openpilot.selfdrive.modeld.modeld', b'openpilot.sunnypilot.modeld_v2.modeld', b'modeld', b'modeld_v2', b'./camerad', b'camerad'}


def audit_deployment(root=Path('/data/openpilot'), manifest=None):
    manifest = manifest or json.loads(Path(__file__).with_name('ignition-on-manifest.json').read_text())
    head = subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True,timeout=5).strip()
    if head != manifest['deployment_commit']:
        raise RuntimeError('Comma deployment changed; ignition-on isolation must be reviewed again')
    for name, expected in manifest['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Unaudited startup code: {name}')
    return head


def assert_no_model_processes(proc=Path('/proc')):
    for entry in proc.glob('[0-9]*/cmdline'):
        try: argv=entry.read_bytes().split(b'\0')
        except FileNotFoundError: continue
        if any(v in MODELS or Path(v.decode(errors='replace')).name in ('modeld','modeld_v2','camerad') for v in argv):
            raise RuntimeError('Arm with ignition off and camera/model processes stopped')


def assert_usb_unowned(proc=Path('/proc'), own_pid=None):
    """Reject another process with an accessible FunctionFS descriptor.

    The pinned startup gate and small-model messages are the other isolation
    checks. Unrelated root processes may hide their descriptors from comma.
    """
    own_pid = os.getpid() if own_pid is None else own_pid
    for entry in proc.glob('[0-9]*/fd'):
        if int(entry.parent.name) == own_pid: continue
        try:
            for fd in entry.iterdir():
                try: target=os.readlink(fd)
                except (FileNotFoundError, PermissionError): continue
                if target.startswith('/dev/ffs-jetlink/'):
                    raise RuntimeError('Another process still owns the JetLink USB endpoints')
        except (FileNotFoundError, PermissionError): continue


def fresh(snapshot, service, now):
    meta=snapshot.get('services',{}).get(service,{})
    sent=meta.get('sent',float('-inf'))
    return (meta.get('seen') is True and meta.get('alive') is True and meta.get('valid') is True
            and math.isfinite(sent) and 0 <= now-sent < LIMITS[service])


def motion_problem(snapshot):
    if snapshot.get('gear') != 'park': return 'Transmission is not in Park'
    if snapshot.get('parking_brake') is not True: return 'Parking brake is not set'
    if snapshot.get('standstill') is not True: return 'Vehicle is not at standstill'
    speeds=snapshot.get('speeds',[])
    if len(speeds)!=6 or any(not math.isfinite(v) or abs(v)>0.01 for v in speeds):
        return 'Vehicle speed is not zero'
    return None


def startup_problem(snapshot, now):
    # Missing publishers are expected during startup. An explicit unsafe
    # reading is never excused just because another publisher is missing.
    if fresh(snapshot,'carState',now):
        # Allow incomplete startup state while waiting, but never motion or
        # a known non-Park gear. No frames run until every strict gate passes.
        if snapshot.get('gear') not in ('unknown','park'):
            return 'Transmission is not in Park'
        speeds=snapshot.get('speeds',[])
        if len(speeds)!=6 or any(not math.isfinite(v) or abs(v)>0.01 for v in speeds):
            return 'Vehicle speed is not zero'
    if fresh(snapshot,'selfdriveState',now) and snapshot.get('enabled') is not False:
        return 'Selfdrive is enabled'
    if fresh(snapshot,'carControl',now) and (snapshot.get('lat_active') is not False or snapshot.get('long_active') is not False):
        return 'Lateral or longitudinal control is active'
    if fresh(snapshot,'pandaStates',now) and snapshot.get('panda_controls') is not False:
        return 'Panda permits vehicle control'
    if fresh(snapshot,'modelV2',now) and snapshot.get('big_model') is not False:
        return 'The normal model pipeline is using a large model'
    return None


def stationary_problem(snapshot, now):
    missing=[s for s in LIMITS if not fresh(snapshot,s,now)]
    if missing: return 'Missing, invalid or stale vehicle data: '+', '.join(missing)
    if snapshot.get('started') is not True or snapshot.get('ignition') is not True:
        return 'Ignition must remain on for this stationary test'
    return motion_problem(snapshot) or startup_problem(snapshot,now)


def offroad_problem(snapshot, now):
    if not all(fresh(snapshot,s,now) for s in ('pandaStates','deviceState')):
        return 'Fresh raw ignition data is unavailable'
    if snapshot.get('ignition') is not False or snapshot.get('started') is not False:
        return 'Ignition must be off before arming USB isolation'
    return None


class IgnitionGuard:
    def __init__(self, params, clock=time.monotonic):
        self.params=params
        self.clock=clock
        self.lock=threading.Lock()
        self.stop=threading.Event()
        self.phase='preflight'
        self.disabled=False
        self.failure=None
        self.latest={}
        self.samples=[]
        self.next_sample=0.0
        self.started=clock()
        self.thread=threading.Thread(target=self._watch,daemon=True,name='stationary-vehicle-guard')
        self.thread.start()

    def _watch(self):
        try:
            from openpilot.cereal import messaging
            sm=messaging.SubMaster(list(LIMITS))
            while not self.stop.is_set():
                sm.update(50)
                now=self.clock()
                cs,ctrl=sm['carState'],sm['carControl']
                pandas=list(sm['pandaStates'])
                snap={'services':{s:{'seen':bool(sm.seen[s]),'alive':bool(sm.alive[s]),'valid':bool(sm.valid[s]),
                                     'sent':sm.logMonoTime[s]/1e9} for s in LIMITS},
                      'captured_at':now,'ignition':any(x.ignitionLine or x.ignitionCan for x in pandas) if pandas else None,
                      'panda_controls':any(x.controlsAllowed or x.controlsAllowedLateral or x.controlsAllowedLongitudinal for x in pandas) if pandas else None,
                      'started':bool(sm['deviceState'].started),'gear':str(cs.gearShifter),
                      'parking_brake':bool(cs.parkingBrake),'standstill':bool(cs.standstill),
                      'speeds':[float(cs.vEgo),float(cs.vEgoRaw),float(cs.wheelSpeeds.fl),float(cs.wheelSpeeds.fr),float(cs.wheelSpeeds.rl),float(cs.wheelSpeeds.rr)],
                      'enabled':bool(sm['selfdriveState'].enabled),'lat_active':bool(ctrl.latActive),
                      'long_active':bool(ctrl.longActive),'big_model':bool(sm['modelV2'].big)}
                self.ingest(snap,now)
        except Exception as e:
            with self.lock: self.failure=f'Vehicle monitor failed: {e}'

    def ingest(self,snapshot,now):
        with self.lock:
            self.latest=snapshot
            reason=None
            if self.disabled and self.params.get_bool('JetlinkEnabled'):
                reason='Accelerator Link was re-enabled during the test'
            elif self.phase=='offroad': reason=offroad_problem(snapshot,now)
            elif self.phase=='waiting': reason=startup_problem(snapshot,now)
            elif self.phase=='active': reason=stationary_problem(snapshot,now)
            if reason and self.failure is None: self.failure=reason
            if self.phase=='active' and now>=self.next_sample:
                self.samples.append({k:v for k,v in snapshot.items() if k not in ('services','captured_at')}
                                    | {'elapsed_s':round(now-self.started,3)})
                self.next_sample=now+1

    def prepare(self):
        self.deployment=audit_deployment()
        end=self.clock()+3
        while True:
            with self.lock:
                snap=dict(self.latest); failure=self.failure
            if failure: raise RuntimeError(failure)
            if not offroad_problem(snap,self.clock()): break
            if self.clock()>=end: raise RuntimeError(offroad_problem(snap,self.clock()))
            time.sleep(0.05)
        if not self.params.get_bool('IsOffroad'): raise RuntimeError('Comma is not offroad')
        assert_no_model_processes()
        with self.lock: self.phase='offroad'
        self.check()
        return {'deployment':self.deployment,'raw_ignition_off':True,'camera_model_processes_absent':True}

    def require_disabled(self):
        from openpilot.sunnypilot import accelerators
        with self.lock: self.disabled=True
        if self.params.get_bool('JetlinkEnabled') or accelerators.enabled():
            raise RuntimeError('Model startup did not observe Accelerator Link disabled')
        self.check()
        assert_no_model_processes()
        assert_usb_unowned()

    def wait_until_ready(self,timeout):
        with self.lock: self.phase='waiting'
        print('USB ISOLATED. You may turn the car on for A/C. Stay in Park, set the parking brake, and leave controls disengaged.',flush=True)
        end=self.clock()+timeout
        stable=None
        reason='No stationary sample'
        while self.clock()<end:
            with self.lock: snap=dict(self.latest); failure=self.failure
            if failure: raise RuntimeError(failure)
            now=self.clock()
            reason=stationary_problem(snap,now)
            if reason: stable=None
            elif stable is None: stable=now
            elif now-stable>=2:
                assert_usb_unowned()
                with self.lock: self.phase='active'
                self.check()
                print('Live vehicle checks passed for two seconds. Ready for the Pixel USB connection.',flush=True)
                return
            time.sleep(0.05)
        raise RuntimeError('Stationary ignition-on readiness timed out: '+(reason or 'not stable'))

    def check(self):
        with self.lock: snapshot=dict(self.latest); failure=self.failure; phase=self.phase
        if failure: raise RuntimeError(failure)
        now=self.clock()
        if now-snapshot.get('captured_at',float('-inf'))>=0.25:
            raise RuntimeError('Vehicle monitor stopped updating')
        if self.disabled and self.params.get_bool('JetlinkEnabled'):
            raise RuntimeError('Accelerator Link must remain disabled while the test owns USB')
        reason=stationary_problem(snapshot,now) if phase=='active' else offroad_problem(snapshot,now)
        if reason: raise RuntimeError(reason)

    def summary(self):
        with self.lock:
            return {'phase':self.phase,'failure':self.failure,'samples':list(self.samples),
                    'deployment':getattr(self,'deployment',None),'startup_link_disabled':self.disabled,
                    'max_fast_message_age_s':0.5,'max_ignition_message_age_s':1.5,
                    'poll_ms':50,'speed_tolerance_m_s':0.01}

    def close(self):
        self.stop.set()
        self.thread.join(1)


if __name__=='__main__':
    import sys
    sys.path.insert(0,'/data/openpilot')
    from openpilot.common.params import Params
    guard=IgnitionGuard(Params())
    try: print(json.dumps(guard.prepare(),indent=2))
    finally: guard.close()
