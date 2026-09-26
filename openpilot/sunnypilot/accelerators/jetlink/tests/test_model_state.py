"""The older split small model can feed the current Jetlink inference protocol."""
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from openpilot.sunnypilot.accelerators.jetlink.model_state import JetlinkModelState


class SmallBundleCompatibilityTest(unittest.TestCase):
  def setUp(self):
    self.client = mock.Mock(last_timings=(0, 0, 0))
    self.client.t.last_receive = {}
    self.client.infer_end.return_value = np.arange(4, dtype=np.float32)
    spec = SimpleNamespace(input_shapes={'img': (1, 12, 128, 256), 'big_img': (1, 12, 128, 256)},
                           output_slices={'hidden_state': slice(0, 4)}, frame_skip=5,
                           packed_nelem=16, packed_sizes=[8, 2, 2, 4],
                           packed_shapes={'desire': (1, 8), 'traffic_convention': (1, 2),
                                          'action_t': (1, 2), 'prev_feat': (1, 4)})
    # A split model has no combined input_shapes. Its camera geometry is
    # independent of the Jetlink warp, which is already prepared for the spec.
    self.model = JetlinkModelState(1928, 1208, self.client, spec, small=SimpleNamespace(), warp=object())
    self.model.parser = mock.Mock()
    self.model.parser.parse_outputs.return_value = {'parsed': True}

  def test_desire_input_names_and_pulses(self):
    bufs = {key: np.zeros(8, dtype=np.uint8) for key in ('img', 'big_img')}
    transforms = {key: np.eye(3, dtype=np.float32) for key in bufs}
    warped = mock.Mock()
    warped.data.return_value = b'warped-frame'
    for name in ('desire', 'desire_pulse'):
      self.model.prev_desire.fill(0)
      inputs = {name: np.array([1, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
                'traffic_convention': np.array([1, 0], dtype=np.float32),
                'action_t': np.array([0.2, 0.4], dtype=np.float32)}
      with self.subTest(name=name), \
           mock.patch('openpilot.sunnypilot.accelerators.jetlink.model_state.Tensor.from_blob'), \
           mock.patch('openpilot.sunnypilot.accelerators.jetlink.model_state.warp_cache.call_warp', return_value=warped):
        self.assertEqual(self.model.run(bufs, transforms, inputs), {'parsed': True})
        np.testing.assert_array_equal(self.model.npy['desire'], [[0, 1, 0, 0, 0, 0, 0, 0]])
        np.testing.assert_array_equal(self.model.npy['action_t'], [inputs['action_t']])
        self.model.run(bufs, transforms, inputs)
        np.testing.assert_array_equal(self.model.npy['desire'], 0)

  def test_large_model_exposes_its_own_action_function(self):
    from openpilot.selfdrive.modeld.modeld import get_action_from_model, LONG_SMOOTH_SECONDS
    self.assertIs(self.model.get_action_from_model, get_action_from_model)
    self.assertEqual(self.model.LONG_SMOOTH_SECONDS, LONG_SMOOTH_SECONDS)
    self.assertEqual(self.model.constants.DESIRE_LEN, 8)
