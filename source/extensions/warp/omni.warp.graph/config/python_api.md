# Public API for module omni.warp.graph:

## Functions

- def device_get_cuda_compute() -> wp.Device
- def from_omni_graph(value: Union[np.ndarray, og.DataWrapper, og.AttributeData, og.DynamicAttributeAccess], dtype: Optional[type] = None, shape: Optional[Sequence[int]] = None, device: Optional[wp.Device] = None) -> wp.array
- def from_omni_graph_ptr(ptr, shape, dtype = None, device = None)
