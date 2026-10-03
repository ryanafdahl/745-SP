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
    def run_harness(self, *, onroad=False, bad_peer=False, bad_output=False, close_error=False):
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
        modules = {
            'openpilot.common.params': types.SimpleNamespace(Params=lambda: types.SimpleNamespace(get_bool=lambda key: not onroad)),
            'jetlink.comma.lending': types.SimpleNamespace(borrow=lambda **kw: loan),
        }
        with patch.dict(sys.modules,modules):
            descriptor=importlib.util.spec_from_file_location('parked_harness',Path(__file__).with_name('parked-test.py'))
            module=importlib.util.module_from_spec(descriptor);descriptor.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d, patch.object(module.JetlinkClient,'open_loan',return_value=client), \
             patch.object(module.signal,'signal'),patch.object(module.signal,'alarm'),patch.object(module.time,'sleep'), \
             patch.object(sys,'argv',['parked-test.py','--frames','20','--output',str(Path(d)/'result.json')]), \
             contextlib.redirect_stdout(io.StringIO()):
            if onroad:
                with self.assertRaisesRegex(RuntimeError,'Ignition'): module.main()
                self.assertFalse(loan.closed)
                return
            status=module.main()
            self.assertTrue(loan.closed)
            self.assertTrue(client.closed)
            self.assertEqual(status,1 if bad_peer or bad_output or close_error else 0)

    def test_ignition_on_refuses_before_borrowing(self): self.run_harness(onroad=True)
    def test_wrong_peer_releases_loan(self): self.run_harness(bad_peer=True)
    def test_nonfinite_output_releases_loan(self): self.run_harness(bad_output=True)
    def test_client_close_failure_still_releases_loan(self): self.run_harness(close_error=True)
    def test_success_releases_loan(self): self.run_harness()


if __name__=='__main__': unittest.main()