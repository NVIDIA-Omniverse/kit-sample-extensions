import asyncio
import os
import time
from types import ModuleType
from typing import Dict, List, Optional, Tuple

import carb


class BaseSysMonitor:
    # Virtual base class
    def start(self):
        return self

    def stop(self):
        return self

    def gather_stats(self) -> Tuple[int, float, Dict]:
        return (0, 0.0, {})


# SysMonitor uses pynvml to report GPU stats for tasks:
# https://developer.nvidia.com/nvidia-management-library-nvml
pynvml: Optional[ModuleType] = None
try:
    import pynvml as pynvml

except ImportError:

    class SysMonitor(BaseSysMonitor):
        def __init__(self):
            carb.log_warn("GpuMonitor: Missing pynvml, no GPU stats available")

else:

    class SysMonitor(BaseSysMonitor):
        def __init__(self, poll_freq_s: int = 1):
            self._pynvml_ready: bool = False
            self._poll_freq_s: int = poll_freq_s
            self._stop_event = asyncio.Event()
            self._metrics: Dict = {}
            self._start_time: float = 0.0

            global pynvml
            if pynvml is None:
                return

            # Initialize NVML
            try:
                pynvml.nvmlInit()
            except pynvml.nvml.NVMLError as err:
                carb.log_warn(f"GpuMonitor: pynvml failed to initialize ({err}), no GPU stats available")
            else:
                self._pynvml_ready = True

        def __del__(self):
            # Shutdown NVML
            global pynvml
            if pynvml is not None and self._pynvml_ready is True:
                pynvml.nvmlShutdown()
                self._pynvml_ready = False

        def start(self) -> "SysMonitor":
            self._start_time = time.time()
            gpu_indices = self.get_gpu_indices()
            if gpu_indices:
                asyncio.ensure_future(self._monitor_async(gpu_indices))
            return self

        async def _monitor_async(self, gpu_indices: List[int]):
            while not self._stop_event.is_set():
                for gpu_index in gpu_indices:
                    gpu_name = f"GPU{gpu_index}"
                    gpu_utilization, gpu_memory = await self.get_gpu_utilization_async(gpu_index)
                    if gpu_name in self._metrics:
                        self._metrics[gpu_name]["utilization"].append(gpu_utilization)
                        self._metrics[gpu_name]["memory"].append(gpu_memory)
                    else:
                        self._metrics[gpu_name] = {
                            "utilization": [gpu_utilization],
                            "memory": [gpu_memory],
                        }
                await asyncio.sleep(self._poll_freq_s)

        def get_gpu_indices(self) -> List[int]:
            global pynvml
            if pynvml is None or self._pynvml_ready is False:
                return []

            try:
                # Get the number of GPUs
                device_count = pynvml.nvmlDeviceGetCount()
            except pynvml.NVMLError as error:
                carb.log_warn(error)
                return []

            # Find the current process in the list of running processes and get its GPU utilization
            current_pid = os.getpid()

            gpu_indices = []
            # Loop through each GPU
            for i in range(device_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    # Get the list of processes running on the GPU
                    procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                except pynvml.NVMLError as e:
                    carb.log_warn(e)
                    continue

                # Loop through each process to check if it matches the PID of current one
                for p in procs:
                    if p.pid == current_pid:
                        carb.log_info(
                            f"The container is running on GPU {i}, PID: {p.pid}, Process Name: {pynvml.nvmlSystemGetProcessName(p.pid)}"
                        )
                        gpu_indices.append(i)

            return gpu_indices

        async def get_gpu_utilization_async(self, gpu_index: int) -> Tuple[float, float]:
            global pynvml
            if pynvml is None or self._pynvml_ready is False:
                return (0.0, 0.0)

            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

                # Get the GPU utilization
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

                # Get the process info for all processes on the GPU
                processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)

            except pynvml.NVMLError as error:
                carb.log_warn(error)
                return (0.0, 0.0)

            # Find the current process in the list of running processes and get its GPU utilization
            current_pid = os.getpid()
            memory_utilization: float = 0.0
            for process in processes:
                if process.pid == current_pid:
                    try:
                        memory_utilization = process.usedGpuMemory / (1024.0 * 1024.0)  # Convert bytes to megabytes
                    except Exception:
                        pass
                    break

            carb.log_info(f"Total GPU{gpu_index} Utilization: {utilization.gpu}%")
            carb.log_info(f"Current Application GPU{gpu_index} Memory Usage: {memory_utilization} MB")
            return utilization.gpu, memory_utilization

        def stop(self) -> "SysMonitor":
            self._stop_event.set()
            return self

        def gather_stats(self) -> Tuple[int, float, Dict]:
            import statistics

            self.stop()
            stats = {}
            for gpu_name, gpu_metrics in self._metrics.items():
                stats[gpu_name] = {
                    "max_utilization": max(gpu_metrics.get("utilization")),
                    "avg_utilization": statistics.mean(gpu_metrics.get("utilization")),
                    "max_memory": max(gpu_metrics.get("memory")),
                    "avg_memory": statistics.mean(gpu_metrics.get("memory")),
                }
            num_gpus = len(self._metrics)
            duration = time.time() - self._start_time
            return (num_gpus, duration, stats)
