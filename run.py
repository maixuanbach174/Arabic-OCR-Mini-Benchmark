"""One command, end to end: python run.py --config config.yaml"""
import argparse
import subprocess
import sys

from src.common import load_config
from src.data import prepare_all
from src.report import build_report

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--limit", type=int, default=None, help="smoke test: first N samples per subset")
    ap.add_argument("--skip-predict", action="store_true", help="only rescore cached predictions")
    args = ap.parse_args()

    cfg = load_config(args.config)
    prepare_all(cfg)
    if not args.skip_predict:
        for system in cfg["systems"]:
            # A fresh process per system keeps peak-memory numbers from bleeding into each other.
            cmd = [sys.executable, "-m", "src.predict", "--config", args.config, "--system", system]
            if args.limit:
                cmd += ["--limit", str(args.limit)]
            subprocess.run(cmd, check=True)
    build_report(cfg)
