"""Fail-closed stationary gates; fixtures contain no vehicle identity or route data."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import stationary as S


def safe_snapshot(now=10.0):
    return {'services':{s:{'seen':True,'alive':True,'valid':True,'sent':now} for s in S.LIMITS},
            'captured_at':now,'ignition':True,'started':True,'panda_controls':False,
            'gear':'park','parking_brake':True,'standstill':True,'speeds':[0.0]*6,
            'enabled':False,'lat_active':False,'long_active':False,'big_model':False}


class SnapshotTests(unittest.TestCase):
    def test_all_live_stationary_fields_required(self):
        self.assertIsNone(S.stationary_problem(safe_snapshot(),10.0))
        for field,value in [('gear','drive'),('parking_brake',False),('standstill',False),
                            ('enabled',True),('lat_active',True),('long_active',True),
                            ('panda_controls',True),('big_model',True),('ignition',False),('started',False)]:
            with self.subTest(field=field):
                snap=safe_snapshot();snap[field]=value
                self.assertIsNotNone(S.stationary_problem(snap,10.0))

    def test_each_speed_and_nonfinite_value_refuses(self):
        for index in range(6):
            for speed in [0.011,-0.011,float('nan'),float('inf')]:
                with self.subTest(index=index,speed=speed):
                    snap=safe_snapshot();snap['speeds'][index]=speed
                    self.assertIn('speed',S.stationary_problem(snap,10.0))
        snap=safe_snapshot();snap['speeds']=[]
        self.assertIn('speed',S.stationary_problem(snap,10.0))

    def test_each_publisher_must_be_seen_alive_valid_and_fresh(self):
        for service,limit in S.LIMITS.items():
            for field,value in [('seen',False),('alive',False),('valid',False),
                                ('sent',10.0-limit),('sent',10.001),('sent',float('nan'))]:
                with self.subTest(service=service,field=field):
                    snap=safe_snapshot();snap['services'][service][field]=value
                    self.assertIn(service,S.stationary_problem(snap,10.0))
            snap=safe_snapshot();del snap['services'][service]
            self.assertIn(service,S.stationary_problem(snap,10.0))

    def test_startup_waits_for_initialization_but_refuses_known_motion(self):
        snap=safe_snapshot();snap['services']['modelV2']['seen']=False
        snap['gear']='unknown';snap['parking_brake']=False
        self.assertIsNone(S.startup_problem(snap,10.0))
        self.assertIsNotNone(S.stationary_problem(snap,10.0))
        for field,value in [('gear','reverse'),('speeds',[0,0,0,0,0,0.1]),('lat_active',True)]:
            bad=copy.deepcopy(snap);bad[field]=value
            self.assertIsNotNone(S.startup_problem(bad,10.0))

    def test_offroad_requires_fresh_raw_ignition_and_device_data(self):
        snap=safe_snapshot();snap.update(ignition=False,started=False)
        self.assertIsNone(S.offroad_problem(snap,10.0))
        snap['ignition']=True
        self.assertIn('off before',S.offroad_problem(snap,10.0))
        snap['ignition']=False;snap['services']['pandaStates']['valid']=False
        self.assertIn('unavailable',S.offroad_problem(snap,10.0))


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.now=10.0
        self.values={'JetlinkEnabled':False,'IsOffroad':True}
        params=types.SimpleNamespace(get_bool=lambda k:self.values[k])
        with patch.object(S.threading,'Thread'):
            self.guard=S.IgnitionGuard(params,clock=lambda:self.now)
        self.guard.phase='active';self.guard.disabled=True
        self.guard.ingest(safe_snapshot(),self.now)

    def tearDown(self): self.guard.close()

    def test_transient_motion_stays_latched_after_recovery(self):
        bad=safe_snapshot();bad['speeds'][2]=0.02
        self.guard.ingest(bad,self.now)
        self.guard.ingest(safe_snapshot(),self.now)
        with self.assertRaisesRegex(RuntimeError,'speed'): self.guard.check()
        self.assertIn('speed',self.guard.summary()['failure'])

    def test_lost_publisher_latches_before_next_inference(self):
        bad=safe_snapshot();bad['services']['carState']['sent']=9.4
        self.guard.ingest(bad,self.now)
        with self.assertRaisesRegex(RuntimeError,'stale'): self.guard.check()

    def test_monitor_heartbeat_stall_refuses(self):
        self.now+=0.25
        with self.assertRaisesRegex(RuntimeError,'stopped updating'): self.guard.check()

    def test_reenabled_link_refuses_even_without_new_sample(self):
        self.values['JetlinkEnabled']=True
        with self.assertRaisesRegex(RuntimeError,'remain disabled'): self.guard.check()
        self.guard.ingest(safe_snapshot(),self.now)
        self.values['JetlinkEnabled']=False
        with self.assertRaisesRegex(RuntimeError,'re-enabled'): self.guard.check()

    def test_ignition_on_before_usb_isolation_latches(self):
        self.guard.phase='offroad'
        self.guard.ingest(safe_snapshot(),self.now)
        with self.assertRaisesRegex(RuntimeError,'off before'): self.guard.check()

    def test_model_startup_flag_is_checked_independently(self):
        fake=types.SimpleNamespace(accelerators=types.SimpleNamespace(enabled=lambda:True))
        with patch.dict('sys.modules',{'openpilot.sunnypilot':fake}):
            with self.assertRaisesRegex(RuntimeError,'startup'): self.guard.require_disabled()

    def test_wait_requires_two_continuous_seconds_and_checks_foreign_usb_owner(self):
        self.guard.phase='offroad'
        def tick(_):
            self.now+=0.05
            snap=safe_snapshot(self.now)
            # Interrupt readiness once, without creating an unsafe moving state.
            if self.now<11: snap['parking_brake']=False
            self.guard.ingest(snap,self.now)
        with patch.object(S.time,'sleep',side_effect=tick), patch.object(S,'assert_usb_unowned') as owner, patch('builtins.print'):
            self.guard.wait_until_ready(5)
        self.assertGreaterEqual(self.now,13)
        owner.assert_called_once()
        self.assertEqual(self.guard.phase,'active')
        self.guard.check()

    def test_wait_aborts_known_unsafe_state_before_active(self):
        def tick(_):
            self.now+=0.05
            bad=safe_snapshot(self.now);bad['gear']='drive'
            self.guard.ingest(bad,self.now)
        with patch.object(S.time,'sleep',side_effect=tick), patch('builtins.print'):
            with self.assertRaisesRegex(RuntimeError,'Park'): self.guard.wait_until_ready(5)
        self.assertNotEqual(self.guard.phase,'active')

    def test_prepare_read_only_preflight_and_active_process_refusal(self):
        self.guard.phase='preflight';self.guard.disabled=False
        off=safe_snapshot();off.update(ignition=False,started=False)
        self.guard.ingest(off,self.now)
        with patch.object(S,'audit_deployment',return_value='audited'), patch.object(S,'assert_no_model_processes'):
            result=self.guard.prepare()
        self.assertTrue(result['raw_ignition_off'])
        self.assertEqual(self.guard.phase,'offroad')
        with patch.object(S,'audit_deployment',return_value='audited'), patch.object(S,'assert_no_model_processes',side_effect=RuntimeError('model active')):
            with self.assertRaisesRegex(RuntimeError,'model active'): self.guard.prepare()


class IsolationTests(unittest.TestCase):
    def test_exact_deployment_and_file_content_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'model.py').write_bytes(b'audited')
            manifest={'deployment_commit':'expected','files':{'model.py':hashlib.sha256(b'audited').hexdigest()}}
            with patch.object(S.subprocess,'check_output',return_value='expected\n'):
                self.assertEqual(S.audit_deployment(root,manifest),'expected')
                (root/'model.py').write_bytes(b'changed')
                with self.assertRaisesRegex(RuntimeError,'Unaudited'): S.audit_deployment(root,manifest)
            with patch.object(S.subprocess,'check_output',return_value='other\n'):
                with self.assertRaisesRegex(RuntimeError,'deployment changed'): S.audit_deployment(root,manifest)

    def test_existing_model_or_camera_process_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'123/cmdline';path.parent.mkdir();path.write_bytes(b'python\0unrelated.py\0')
            S.assert_no_model_processes(Path(d))
            for token in (b'openpilot.selfdrive.modeld.modeld',b'openpilot.sunnypilot.modeld_v2.modeld',b'/data/openpilot/camerad'):
                path.write_bytes(b'python\0'+token+b'\0')
                with self.assertRaisesRegex(RuntimeError,'processes stopped'): S.assert_no_model_processes(Path(d))

    def test_foreign_endpoint_owner_refuses_but_self_is_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            fd=Path(d)/'123/fd/5';fd.parent.mkdir(parents=True);fd.symlink_to('/dev/ffs-jetlink/ep1')
            S.assert_usb_unowned(Path(d),own_pid=123)
            with self.assertRaisesRegex(RuntimeError,'owns'): S.assert_usb_unowned(Path(d),own_pid=456)


if __name__=='__main__': unittest.main()
