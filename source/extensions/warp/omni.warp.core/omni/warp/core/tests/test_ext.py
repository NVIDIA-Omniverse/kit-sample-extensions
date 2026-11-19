"""Tests for the Warp Core extension.

The library is already thoroughly tested in its dedicated repository,
so these tests only check whether it's correctly exposed to Kit.
"""

import numpy as np
import omni.kit.test
import warp as wp


def array_are_equal(
    a: np.ndarray | wp.array,
    b: np.ndarray | wp.array,
) -> None:
    """Checks whether two arrays are equal."""
    if isinstance(a, wp.array):
        a = a.numpy()

    if isinstance(b, wp.array):
        b = b.numpy()

    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        assert a.shape == b.shape
        assert a.dtype == b.dtype
    else:
        assert len(a) == len(b)

    np.testing.assert_equal(a, b)


@wp.kernel
def double_kernel(arr: wp.array(dtype=int)):
    tid = wp.tid()
    arr[tid] *= 2


class TestWarpCore(omni.kit.test.AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        cls.devices = ()

        if wp.is_cpu_available():
            cls.devices += (wp.get_device("cpu"),)

        if wp.is_cuda_available():
            cls.devices += (wp.get_device("cuda"),)

    async def test_launch_kernel(self):
        for device in self.devices:
            arr = wp.array((1, 2, 3), dtype=int, device=device)
            wp.launch(double_kernel, dim=3, inputs=(arr,), device=device)
            array_are_equal(arr, (2, 4, 6))
