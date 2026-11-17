"""FR4: per-sample CER/WER (raw + normalized) and per-(system, subset) aggregates."""
import json
from pathlib import Path

import jiwer
import pandas as pd

from .common import read_jsonl
from .normalize import NORMALIZERS


def _rates(ref, hyp):
    if not ref:
        return None, None
    if not hyp:
        return 1.0, 1.0
    return jiwer.cer(ref, hyp), jiwer.wer(ref, hyp)


def score_sample(gt, pred, halluc_ratio):
    row = {}
    for mode, fn in NORMALIZERS.items():
        ref, hyp = fn(gt), fn(pred)
        row[f"cer_{mode}"], row[f"wer_{mode}"] = _rates(ref, hyp)
    ref_n, hyp_n = NORMALIZERS["norm"](gt), NORMALIZERS["norm"](pred)
    row["len_ratio"] = len(hyp_n) / max(len(ref_n), 1)
    row["hallucination"] = row["len_ratio"] > halluc_ratio
    row["empty"] = not hyp_n
    return row


def per_sample(cfg):
    rows = []
    for name in cfg["subsets"]:
        manifest = {r["id"]: r for r in read_jsonl(Path(cfg["paths"]["data"]) / name / "manifest.jsonl")}
        for system in cfg["systems"]:
            for p in read_jsonl(Path(cfg["paths"]["preds"]) / system / f"{name}.jsonl"):
                if p["id"] not in manifest:
                    continue
                gt = manifest[p["id"]]["gt_text"]
                rows.append({"system": system, "subset": name, "id": p["id"],
                             "gt_text": gt, "pred_text": p["text"], "latency_s": p["latency_s"],
                             **score_sample(gt, p["text"], cfg["metrics"]["hallucination_ratio"])})
    return pd.DataFrame(rows)


def peak_memory_gb(cfg, system):
    meta = Path(cfg["paths"]["preds"]) / system / "_meta.json"
    if not meta.exists():
        return None, None
    m = json.loads(meta.read_text())
    return m.get("peak_rss_gb"), m.get("peak_mlx_gb")


def summarize(df, cfg):
    agg = (df.groupby(["system", "subset"], sort=False)
             .agg(n=("id", "count"),
                  mean_cer_raw=("cer_raw", "mean"), median_cer_raw=("cer_raw", "median"),
                  mean_cer_norm=("cer_norm", "mean"), median_cer_norm=("cer_norm", "median"),
                  mean_wer_raw=("wer_raw", "mean"), median_wer_raw=("wer_raw", "median"),
                  mean_wer_norm=("wer_norm", "mean"), median_wer_norm=("wer_norm", "median"),
                  hallucination_rate=("hallucination", "mean"), empty_rate=("empty", "mean"),
                  mean_latency_s=("latency_s", "mean"), median_latency_s=("latency_s", "median"))
             .reset_index())
    mem = {s: peak_memory_gb(cfg, s) for s in agg["system"].unique()}
    agg["peak_rss_gb"] = agg["system"].map(lambda s: mem[s][0])
    agg["peak_mlx_gb"] = agg["system"].map(lambda s: mem[s][1])
    return agg
