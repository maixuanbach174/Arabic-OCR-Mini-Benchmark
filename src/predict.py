"""Run one system over every subset, caching each prediction as it is made.

Invoked as its own process per system (see run.py) so peak memory is measured in isolation.
"""
import argparse
import json
import resource
import sys
from pathlib import Path

from .common import append_jsonl, load_config, read_jsonl
from .runners import build_runner


def peak_rss_gb():
    # ru_maxrss is bytes on macOS, kilobytes on Linux. Children covers the tesseract subprocesses.
    unit = 1 if sys.platform == "darwin" else 1024
    own = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    child = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return max(own, child) * unit / 1e9


def run_system(cfg, system, limit=None):
    sys_cfg = cfg["systems"][system]
    out_dir = Path(cfg["paths"]["preds"]) / system
    runner = None
    for subset in cfg["subsets"]:
        manifest = read_jsonl(Path(cfg["paths"]["data"]) / subset / "manifest.jsonl")[:limit]
        pred_path = out_dir / f"{subset}.jsonl"
        done = {r["id"] for r in read_jsonl(pred_path)}
        todo = [r for r in manifest if r["id"] not in done]
        print(f"[{system}] {subset}: {len(done)} cached, {len(todo)} to run", flush=True)
        for i, rec in enumerate(todo, 1):
            runner = runner or build_runner(sys_cfg, cfg)
            pred = runner.predict(rec["image_path"])
            append_jsonl(pred_path, {"id": rec["id"], **pred})
            if i % 10 == 0 or i == len(todo):
                print(f"[{system}] {subset}: {i}/{len(todo)}  last {pred['latency_s']:.2f}s", flush=True)

    if runner is not None:  # only overwrite memory stats when something actually ran
        meta_path = out_dir / "_meta.json"
        old = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        meta = {"peak_rss_gb": max(peak_rss_gb(), old.get("peak_rss_gb") or 0)}
        if hasattr(runner, "peak_accelerator_gb"):
            meta["peak_mlx_gb"] = max(runner.peak_accelerator_gb(), old.get("peak_mlx_gb") or 0)
        meta_path.write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--system", required=True)
    ap.add_argument("--limit", type=int, default=None, help="only the first N samples per subset (smoke test)")
    args = ap.parse_args()
    run_system(load_config(args.config), args.system, args.limit)
