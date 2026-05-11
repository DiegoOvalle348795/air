import time
import numpy as np


def cupy_disponible():
    try:
        import cupy as cp  # noqa: F401
        n = cp.cuda.runtime.getDeviceCount()
        if n <= 0:
            return False, "CuPy instalado, pero no se detectó GPU CUDA."
        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)
        name = props.get("name", b"GPU CUDA")
        if isinstance(name, bytes):
            name = name.decode(errors="ignore")
        return True, f"CuPy activo en {name}"
    except Exception as e:
        return False, f"CuPy/CUDA no disponible: {e}"


def metricas_numericas_aceleradas(df_pred, df_flights):
    """Calcula métricas con CuPy/CUDA si está disponible; si no, usa NumPy.

    Esto permite que el proyecto no se rompa en computadoras sin GPU NVIDIA.
    """
    riesgos = df_pred.get("riesgo", []).to_numpy(dtype=np.float64) if not df_pred.empty else np.array([], dtype=np.float64)
    retrasos = df_flights.get("retraso", []).to_numpy(dtype=np.float64) if not df_flights.empty else np.array([], dtype=np.float64)

    disponible, mensaje = cupy_disponible()

    if disponible:
        import cupy as cp
        inicio = time.perf_counter()
        riesgos_gpu = cp.asarray(riesgos)
        retrasos_gpu = cp.asarray(retrasos)
        resultado = {
            "backend": "CuPy / CUDA",
            "gpu_activa": True,
            "mensaje": mensaje,
            "riesgo_promedio": float(cp.mean(riesgos_gpu).get()) if riesgos_gpu.size else 0.0,
            "riesgo_maximo": float(cp.max(riesgos_gpu).get()) if riesgos_gpu.size else 0.0,
            "retraso_promedio": float(cp.mean(retrasos_gpu).get()) if retrasos_gpu.size else 0.0,
            "retraso_std": float(cp.std(retrasos_gpu).get()) if retrasos_gpu.size else 0.0,
        }
        cp.cuda.Stream.null.synchronize()
        resultado["tiempo_ms"] = round((time.perf_counter() - inicio) * 1000, 4)
        return resultado

    inicio = time.perf_counter()
    resultado = {
        "backend": "NumPy CPU fallback",
        "gpu_activa": False,
        "mensaje": mensaje,
        "riesgo_promedio": float(np.mean(riesgos)) if riesgos.size else 0.0,
        "riesgo_maximo": float(np.max(riesgos)) if riesgos.size else 0.0,
        "retraso_promedio": float(np.mean(retrasos)) if retrasos.size else 0.0,
        "retraso_std": float(np.std(retrasos)) if retrasos.size else 0.0,
    }
    resultado["tiempo_ms"] = round((time.perf_counter() - inicio) * 1000, 4)
    return resultado
