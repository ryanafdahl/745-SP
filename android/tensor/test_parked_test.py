"""The parked harness must release its loan and refuse onroad operation."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np


class ParkedHarnessTests(unittest.TestCase):
    def run_harness(self, *, onroad=False, bad_peer=False, bad_output=False, close_error=False, legacy=False, release_error=False, open_error=False, connect_error=False):
        loan = types.SimpleNamespace(closed=False)
        loan.close = lambda: setattr(loan, 'closed', True)
        client = types.SimpleNamespace(closed=False)
        def close_client():
            client.closed = True
            if close_error: raise RuntimeError('close failed')
        client.close = close_client
        client.t = types.SimpleNamespace(send_json=lambda *args: None, link_info=lambda: {'kind':'usb','usb_speed':'super-speed'})
        client.hello = lambda **kw: {'validation':'parked_only','device':'wrong' if bad_peer else 'tensor-Tensor_G6'}
        spec = types.SimpleNamespace(output_nelem=18452,warped_nbytes=12,warped_shape=(2,6,1,1),packed_nelem=4,
                                     packed_layout={'traffic_convention':(slice(0,2),None),'action_t':(slice(2,4),None)})
        client.ensure_engine = lambda *a,**kw: spec
        client.last_timings = (100,10,110)
        client.infer = lambda *a,**kw: np.array([np.nan] if bad_output else [0.0],dtype=np.float32)
        changes = []
        state = {'IsOffroad': not onroad, 'JetlinkEnabled': True}
        def put_bool(key, value, **kw):
            changes.append((key, value))
            state[key] = value
        modules = {
            'openpilot.common.params': types.SimpleNamespace(Params=lambda: types.SimpleNamespace(get_bool=lambda key: state[key], put_bool=put_bool)),
            'jetlink.comma.lending': types.SimpleNamespace(borrow=lambda **kw: loan),
        }
        with patch.dict(sys.modules,modules):
            descriptor=importlib.util.spec_from_file_location('parked_harness',Path(__file__).with_name('parked-test.py'))
            module=importlib.util.module_from_spec(descriptor);descriptor.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d, patch.object(module.JetlinkClient,'open_loan',return_value=client), \
             patch.object(module.JetlinkClient,'open_ffs',return_value=client,side_effect=RuntimeError('open failed') if open_error else None), \
             patch.object(module,'wait_legacy_release',side_effect=RuntimeError('release failed') if release_error else None), \
             patch.object(module,'wait_usb_host',side_effect=RuntimeError('connect timed out') if connect_error else None), \
             patch.object(module.signal,'signal'),patch.object(module.signal,'alarm'),patch.object(module.time,'sleep'), \
             patch.object(sys,'argv',['parked-test.py','--frames','20','--output',str(Path(d)/'result.json')]+(['--legacy-owner'] if legacy else [])), \
             contextlib.redirect_stdout(io.StringIO()):
            if onroad:
                with self.assertRaisesRegex(RuntimeError,'Ignition'): module.main()
                self.assertFalse(loan.closed)
                self.assertEqual(changes, [])
                return
            status=module.main()
            self.assertEqual(loan.closed, not legacy)
            self.assertEqual(client.closed, not release_error and not open_error)
            self.assertEqual(changes, [('JetlinkEnabled', False), ('JetlinkEnabled', True)] if legacy else [])
            self.assertTrue(state['JetlinkEnabled'])
            self.assertEqual(status,1 if bad_peer or bad_output or close_error or release_error or open_error or connect_error else 0)

    def test_ignition_on_refuses_before_borrowing(self): self.run_harness(onroad=True)
    def test_wrong_peer_releases_loan(self): self.run_harness(bad_peer=True)
    def test_nonfinite_output_releases_loan(self): self.run_harness(bad_output=True)
    def test_client_close_failure_still_releases_loan(self): self.run_harness(close_error=True)
    def test_success_releases_loan(self): self.run_harness()
    def test_legacy_success_restores_enable(self): self.run_harness(legacy=True)
    def test_legacy_wrong_peer_restores_enable(self): self.run_harness(legacy=True,bad_peer=True)
    def test_legacy_release_failure_restores_enable(self): self.run_harness(legacy=True,release_error=True)
    def test_legacy_open_failure_restores_enable(self): self.run_harness(legacy=True,open_error=True)
    def test_legacy_close_failure_restores_enable(self): self.run_harness(legacy=True,close_error=True)
    def test_legacy_connect_timeout_restores_enable(self): self.run_harness(legacy=True,connect_error=True)
    def test_legacy_ignition_on_refuses_before_disabling(self): self.run_harness(legacy=True,onroad=True)


class ConnectionWaitTests(unittest.TestCase):
    def setUp(self):
        modules={'openpilot.common.params': types.SimpleNamespace(Params=lambda: None),
                 'jetlink.comma.lending': types.SimpleNamespace(borrow=lambda **kw: None)}
        with patch.dict(sys.modules,modules):
            descriptor=importlib.util.spec_from_file_location('parked_connection_wait',Path(__file__).with_name('parked-test.py'))
            self.module=importlib.util.module_from_spec(descriptor);descriptor.loader.exec_module(self.module)
        self.client=types.SimpleNamespace(t=types.SimpleNamespace(bound_udc='fake-udc',link_info=lambda: {'kind':'usb'}))

    def test_waits_for_configuration_without_opening_endpoint_files(self):
        parked=unittest.mock.Mock()
        with patch.object(Path,'read_text',side_effect=['not attached','addressed','configured']), \
             patch.object(self.module.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
            self.module.wait_usb_host(self.client,parked,60)
        self.assertEqual(parked.call_count,3)

    def test_ignition_change_aborts_while_waiting(self):
        def onroad(): raise RuntimeError('Ignition on')
        with self.assertRaisesRegex(RuntimeError,'Ignition'), contextlib.redirect_stdout(io.StringIO()):
            self.module.wait_usb_host(self.client,onroad,60)

    def test_network_loan_is_not_reported_as_direct_usb(self):
        self.client.t.link_info=lambda: {'kind':'tcp'}
        with self.assertRaisesRegex(RuntimeError,'direct USB'):
            self.module.wait_usb_host(self.client,lambda: None,60)

    def test_missing_host_times_out(self):
        with patch.object(self.module.time,'monotonic',side_effect=[0,61]), \
             self.assertRaisesRegex(RuntimeError,'connection window'), contextlib.redirect_stdout(io.StringIO()):
            self.module.wait_usb_host(self.client,lambda: None,60)


if __name__=='__main__': unittest.main()