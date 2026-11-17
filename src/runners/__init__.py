"""FR2: every runner exposes predict(image_path) -> {"text": str, "latency_s": float}."""
import importlib


def build_runner(sys_cfg, cfg):
    module = importlib.import_module(f"src.runners.{sys_cfg['runner']}")
    return module.Runner(sys_cfg, cfg)
