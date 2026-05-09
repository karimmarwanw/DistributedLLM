import os
import platform
import re
import subprocess
import threading
import time


GPU_METRICS_MODE = os.getenv("GPU_METRICS_MODE", "auto").lower()
GPU_METRICS_CACHE_SECONDS = float(os.getenv("GPU_METRICS_CACHE_SECONDS", "1.0"))
GPU_METRICS_COMMAND_TIMEOUT = float(os.getenv("GPU_METRICS_COMMAND_TIMEOUT", "0.75"))

DEVICE_UTILIZATION_PATTERN = re.compile(
    r'"Device Utilization %"\s*=\s*([0-9]+(?:\.[0-9]+)?)'
)
RENDERER_UTILIZATION_PATTERN = re.compile(
    r'"Renderer Utilization %"\s*=\s*([0-9]+(?:\.[0-9]+)?)'
)
TILER_UTILIZATION_PATTERN = re.compile(
    r'"Tiler Utilization %"\s*=\s*([0-9]+(?:\.[0-9]+)?)'
)
GPU_MODEL_PATTERN = re.compile(r'"model"\s*=\s*"([^"]+)"')
GPU_CORE_COUNT_PATTERN = re.compile(r'"gpu-core-count"\s*=\s*([0-9]+)')

metrics_lock = threading.Lock()
cached_metrics = None
cached_at = 0.0


def clamp_percent(value):
    return round(max(0.0, min(100.0, float(value))), 2)


def parse_ioreg_gpu_metrics(output):
    device_values = [
        clamp_percent(value)
        for value in DEVICE_UTILIZATION_PATTERN.findall(output)
    ]
    renderer_values = [
        clamp_percent(value)
        for value in RENDERER_UTILIZATION_PATTERN.findall(output)
    ]
    tiler_values = [
        clamp_percent(value)
        for value in TILER_UTILIZATION_PATTERN.findall(output)
    ]

    if not device_values and not renderer_values and not tiler_values:
        return None

    model_match = GPU_MODEL_PATTERN.search(output)
    core_count_match = GPU_CORE_COUNT_PATTERN.search(output)

    utilization_values = device_values or renderer_values + tiler_values

    return {
        "gpu_utilization_percent": max(utilization_values),
        "gpu_utilization_source": "macos_ioreg",
        "gpu_model": model_match.group(1) if model_match else None,
        "gpu_core_count": int(core_count_match.group(1)) if core_count_match else None
    }


def sample_macos_ioreg_gpu_metrics():
    result = subprocess.run(
        ["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"],
        capture_output=True,
        text=True,
        timeout=GPU_METRICS_COMMAND_TIMEOUT,
        check=False
    )

    if result.returncode != 0:
        return None

    return parse_ioreg_gpu_metrics(result.stdout)


def sample_real_gpu_metrics():
    if GPU_METRICS_MODE in {"disabled", "off", "none"}:
        return None

    if GPU_METRICS_MODE in {"auto", "macos_ioreg"}:
        if platform.system() == "Darwin":
            return sample_macos_ioreg_gpu_metrics()

        if GPU_METRICS_MODE == "macos_ioreg":
            return None

    return None


def simulated_gpu_metrics(fallback_percent, fallback_source):
    if fallback_percent is None:
        return {
            "gpu_utilization_percent": None,
            "gpu_utilization_source": "unavailable",
            "gpu_model": None,
            "gpu_core_count": None
        }

    return {
        "gpu_utilization_percent": clamp_percent(fallback_percent),
        "gpu_utilization_source": fallback_source,
        "gpu_model": None,
        "gpu_core_count": None
    }


def get_gpu_metrics(fallback_percent=None, fallback_source="simulated"):
    if GPU_METRICS_MODE == "simulated":
        return simulated_gpu_metrics(fallback_percent, fallback_source)

    now = time.time()

    with metrics_lock:
        global cached_metrics, cached_at

        if cached_metrics and now - cached_at < GPU_METRICS_CACHE_SECONDS:
            return dict(cached_metrics)

        try:
            metrics = sample_real_gpu_metrics()
        except Exception:
            metrics = None

        if metrics is None:
            metrics = simulated_gpu_metrics(fallback_percent, fallback_source)

        cached_metrics = metrics
        cached_at = now

        return dict(metrics)
