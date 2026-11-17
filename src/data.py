"""FR1: sample KITAB-Bench subsets and write images + manifest.jsonl to data/<subset>/."""
import json
import random
from pathlib import Path

from datasets import load_dataset


def prepare_subset(name, spec, n, seed, data_dir):
    out_dir = Path(data_dir) / name
    manifest = out_dir / "manifest.jsonl"
    if manifest.exists() and sum(1 for _ in open(manifest, encoding="utf-8")) == n:
        print(f"[data] {name}: {n} samples already on disk")
        return manifest

    ds = load_dataset(spec["hf_id"], split="train")
    n = min(n, len(ds))
    idx = sorted(random.Random(seed).sample(range(len(ds)), n))

    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    with open(manifest, "w", encoding="utf-8") as f:
        for i in idx:
            row = ds[i]
            sid = f"{name}_{i:04d}"
            image_path = out_dir / "images" / f"{sid}.png"
            row["image"].convert("RGB").save(image_path)
            rec = {"id": sid, "subset": name, "image_path": str(image_path),
                   "gt_text": row[spec["text_column"]]}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[data] {name}: wrote {n}/{len(ds)} samples to {out_dir}")
    return manifest


def prepare_all(cfg):
    return {name: prepare_subset(name, spec, cfg["n_per_subset"], cfg["seed"], cfg["paths"]["data"])
            for name, spec in cfg["subsets"].items()}
