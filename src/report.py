"""FR5 + FR6: summary CSV/Markdown, figures, and error-analysis files."""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from PIL import Image

from .common import read_jsonl
from .errors import CATEGORIES, FAILURES, dotted_examples, failure_flags, label_errors
from .metrics import per_sample, summarize

# Categorical slots 1-3 of the validated reference palette (blue, orange, aqua), fixed per system.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SUBSET_LABEL = {"pats": "Printed (PATS)", "khatt": "Handwritten (KHATT)", "historyar": "Historical (HistoryAr)"}
SYSTEM_LABEL = {"qwen25vl_3b": "Qwen2.5-VL-3B (MLX)", "qwen25vl_7b_4bit": "Qwen2.5-VL-7B 4-bit (MLX)",
                "tesseract": "Tesseract 5 (ara)", "easyocr": "EasyOCR (ar)"}
# Matplotlib >= 3.11 shapes complex scripts itself (joining + RTL), so raw Arabic strings are drawn as-is.
ARABIC_FONTS = ["/System/Library/Fonts/SFArabic.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"]


def _style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
        "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    })


def _arabic_font():
    """Arabic font first, DejaVu Sans as fallback for the Latin digits/punctuation engines emit."""
    for path in ARABIC_FONTS:
        if Path(path).exists():
            font_manager.fontManager.addfont(path)
            name = font_manager.FontProperties(fname=path).get_name()
            return font_manager.FontProperties(family=[name, "DejaVu Sans"])
    return None


def _label(s):
    return SYSTEM_LABEL.get(s, s)


def _pct(x):
    return "–" if pd.isna(x) else f"{100 * x:.1f}%"


def markdown_tables(summary):
    pivot = summary.pivot(index="system", columns="subset", values="median_cer_norm")
    pivot = pivot.reindex(index=summary["system"].unique(), columns=summary["subset"].unique())
    lines = ["**Median CER (normalized), lower is better**", "",
             "| System | " + " | ".join(SUBSET_LABEL.get(c, c) for c in pivot.columns) + " |",
             "|---|" + "---:|" * len(pivot.columns)]
    for sys_name, row in pivot.iterrows():
        lines.append(f"| {_label(sys_name)} | " + " | ".join(_pct(v) for v in row) + " |")

    lines += ["", "**Full results** (CER/WER as %, n = samples scored)", "",
              "| System | Subset | n | CER raw (median / mean) | CER norm (median / mean) | WER norm (median / mean) "
              "| Halluc. rate | Empty output | Latency s/img (mean) | Peak mem GB |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in summary.iterrows():
        lines.append(
            f"| {_label(r.system)} | {SUBSET_LABEL.get(r.subset, r.subset)} | {r.n} "
            f"| {_pct(r.median_cer_raw)} / {_pct(r.mean_cer_raw)} | {_pct(r.median_cer_norm)} / {_pct(r.mean_cer_norm)} "
            f"| {_pct(r.median_wer_norm)} / {_pct(r.mean_wer_norm)} | {_pct(r.hallucination_rate)} | {_pct(r.empty_rate)} "
            f"| {r.mean_latency_s:.2f} | {r.peak_mem_gb:.2f} |")
    return "\n".join(lines)


def fig_cer_bars(summary, out):
    systems, subsets = list(summary["system"].unique()), list(summary["subset"].unique())
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.8 / len(systems)
    for i, s in enumerate(systems):
        d = summary[summary.system == s].set_index("subset").reindex(subsets)
        xs = [j + (i - (len(systems) - 1) / 2) * width for j in range(len(subsets))]
        bars = ax.bar(xs, d["median_cer_norm"] * 100, width=width - 0.02, color=SERIES[i], label=_label(s),
                      edgecolor=SURFACE, linewidth=2)
        ax.bar_label(bars, fmt="%.0f", padding=2, fontsize=8, color=INK_2)
    ax.set_xticks(range(len(subsets)), [SUBSET_LABEL.get(s, s) for s in subsets])
    ax.set_ylabel("Median CER, normalized (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Character error rate by system and subset")
    ax.legend(frameon=False, ncol=len(systems), loc="upper left", bbox_to_anchor=(0, -0.1))
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def fig_cost_scatter(summary, out):
    systems, subsets = list(summary["system"].unique()), list(summary["subset"].unique())
    markers = ["o", "s", "^"]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for i, s in enumerate(systems):
        for k, sub in enumerate(subsets):
            r = summary[(summary.system == s) & (summary.subset == sub)]
            if r.empty:
                continue
            ax.scatter(r.mean_latency_s, r.median_cer_norm * 100, s=70, color=SERIES[i], marker=markers[k % 3],
                       edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_xscale("log")
    ax.set_xlabel("Mean latency per image (s, log scale)")
    ax.set_ylabel("Median CER, normalized (%)")
    ax.set_title("Accuracy vs. cost on an M4 laptop")
    sys_handles = [plt.Line2D([], [], color=SERIES[i], marker="o", ls="", ms=8, label=_label(s)) for i, s in enumerate(systems)]
    sub_handles = [plt.Line2D([], [], color=INK_2, marker=markers[k % 3], ls="", ms=8, label=SUBSET_LABEL.get(sub, sub))
                   for k, sub in enumerate(subsets)]
    ax.legend(handles=sys_handles + sub_handles, frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def fig_normalization(summary, out):
    """Dumbbell: median CER raw (hollow) -> normalized (filled) for every system x subset."""
    systems, subsets = list(summary["system"].unique()), list(summary["subset"].unique())
    fig, axes = plt.subplots(1, len(subsets), figsize=(10, 3.2), sharex=True)
    for ax, sub in zip(axes, subsets):
        for i, s in enumerate(systems):
            r = summary[(summary.system == s) & (summary.subset == sub)]
            if r.empty:
                continue
            raw, norm = r.median_cer_raw.iloc[0] * 100, r.median_cer_norm.iloc[0] * 100
            y = len(systems) - 1 - i
            ax.plot([raw, norm], [y, y], color=SERIES[i], lw=2, zorder=2)
            ax.scatter([raw], [y], s=60, facecolor=SURFACE, edgecolor=SERIES[i], linewidth=2, zorder=3)
            ax.scatter([norm], [y], s=60, color=SERIES[i], edgecolor=SURFACE, linewidth=2, zorder=3)
            if raw - norm >= 5:
                ax.annotate(f"−{raw - norm:.0f}", ((raw + norm) / 2, y), textcoords="offset points", xytext=(0, 6),
                            ha="center", fontsize=8, color=INK_2)
        ax.set_yticks(range(len(systems)), [_label(s) for s in reversed(systems)] if ax is axes[0] else [])
        ax.set_ylim(-0.6, len(systems) - 0.4)
        ax.set_title(SUBSET_LABEL.get(sub, sub), fontsize=10)
        ax.grid(axis="y", visible=False)
    axes[1].set_xlabel("Median CER (%)")
    handles = [plt.Line2D([], [], marker="o", ls="", ms=7, markerfacecolor=SURFACE, markeredgecolor=INK_2, label="raw"),
               plt.Line2D([], [], marker="o", ls="", ms=7, color=INK_2, label="normalized")]
    fig.legend(handles=handles, frameon=False, ncol=2, loc="upper right", fontsize=8)
    fig.suptitle("Effect of Arabic normalization", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def pick_examples(df):
    """One representative sample per subset: the one whose mean CER across systems is closest to the subset median."""
    systems = df["system"].nunique()
    full = df.groupby("id").filter(lambda g: len(g) == systems)
    per_id = full.groupby(["subset", "id"])["cer_norm"].mean().reset_index()
    picks = {}
    for sub, g in per_id.groupby("subset", sort=False):
        picks[sub] = g.iloc[(g["cer_norm"] - g["cer_norm"].median()).abs().argsort().iloc[0]]["id"]
    return {sub: picks[sub] for sub in df["subset"].unique() if sub in picks}


def fig_examples(df, manifest_paths, out):
    font = _arabic_font()
    picks = pick_examples(df)
    systems = list(df["system"].unique())
    fig = plt.figure(figsize=(10, 3.4 * len(picks)))
    for row, (sub, sid) in enumerate(picks.items()):
        g = df[df.id == sid].set_index("system")
        ax_img = fig.add_axes([0.03, 1 - (row + 0.42) / len(picks), 0.94, 0.36 / len(picks)])
        ax_img.imshow(Image.open(manifest_paths[sid]))
        ax_img.axis("off")
        ax_img.set_title(f"{SUBSET_LABEL.get(sub, sub)} — {sid}", fontsize=10)
        ax_txt = fig.add_axes([0.03, 1 - (row + 0.98) / len(picks), 0.94, 0.54 / len(picks)])
        ax_txt.axis("off")
        entries = [("Ground truth", g.iloc[0].gt_text, INK)] + [
            (f"{_label(s)}  (CER {100 * g.loc[s].cer_norm:.0f}%)", g.loc[s].pred_text, SERIES[i]) for i, s in enumerate(systems)]
        for k, (name, text, color) in enumerate(entries):
            y = 0.92 - k * 0.92 / len(entries)
            text = " ".join(str(text).split())
            text = text if len(text) <= 110 else text[:110] + "…"
            ax_txt.text(0.0, y, name, fontsize=9, color=color, fontweight="bold", va="top")
            if text:
                ax_txt.text(1.0, y, text, fontsize=11, ha="right", va="top", fontproperties=font, color=INK)
            else:
                ax_txt.text(1.0, y, "(empty output)", fontsize=9, ha="right", va="top", color=INK_2, style="italic")
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return picks


def failure_table(df, cfg):
    ratio = cfg["metrics"]["hallucination_ratio"]
    flags = pd.DataFrame([failure_flags(r.gt_text, str(r.pred_text), ratio) for r in df.itertuples()], index=df.index)
    counts = pd.concat([df[["system"]], flags], axis=1).groupby("system", sort=False).sum()
    n = df.groupby("system", sort=False).size()
    lines = [f"Counted over all {n.iloc[0]} predictions per system.", "",
             "| Failure mode | " + " | ".join(_label(s) for s in counts.index) + " |",
             "|---|" + "---:|" * len(counts.index)]
    for key, desc in FAILURES.items():
        lines.append(f"| {desc} | " + " | ".join(str(int(counts.loc[s, key])) for s in counts.index) + " |")
    return "\n".join(lines)


def error_files(df, cfg, results):
    """Worst-k per system (catastrophic cases) + a seeded sample of partial errors for hand labelling.

    Reviewed labels for the partial-error sample live in results/error_labels.csv.
    """
    m = cfg["metrics"]
    ratio, k = m["hallucination_ratio"], m["error_sample_k"]
    lo, hi = m["error_band"]

    def rows_for(frame):
        return [{"system": r.system, "id": r.id, "subset": r.subset, "cer_norm": round(r.cer_norm, 3),
                 "auto_labels": ";".join(label_errors(r.gt_text, str(r.pred_text), ratio)),
                 "dotted_pairs": " ".join(dotted_examples(r.gt_text, str(r.pred_text))),
                 "gt_text": " ".join(r.gt_text.split()), "pred_text": " ".join(str(r.pred_text).split())}
                for r in frame.itertuples()]

    worst = pd.concat([g.sort_values("cer_norm", ascending=False).head(m["worst_k"])
                       for _, g in df.groupby("system", sort=False)])
    pd.DataFrame(rows_for(worst)).to_csv(results / "worst_predictions.csv", index=False)

    band = df[(df.cer_norm > lo) & (df.cer_norm <= hi)]
    sample = pd.concat([g.sample(min(k, len(g)), random_state=cfg["seed"]).sort_values("id")
                        for _, g in band.groupby("system", sort=False)])
    sample = pd.DataFrame(rows_for(sample))
    sample.to_csv(results / "error_sample.csv", index=False)

    reviewed_path = results / "error_labels.csv"
    if reviewed_path.exists():
        reviewed = pd.read_csv(reviewed_path, keep_default_na=False)
        labels = sample.drop(columns=["auto_labels"]).merge(reviewed[["system", "id", "labels", "note"]],
                                                           on=["system", "id"], how="left").fillna("")
        source = "hand-reviewed labels (`results/error_labels.csv`)"
    else:
        labels = sample.rename(columns={"auto_labels": "labels"}).assign(note="")
        source = "heuristic labels from `src/errors.py` (not yet reviewed)"

    counts = {s: {c: 0 for c in CATEGORIES} for s in labels["system"].unique()}
    for _, r in labels.iterrows():
        for lab in filter(None, str(r["labels"]).split(";")):
            counts[r["system"]][lab] += 1
    count_df = pd.DataFrame(counts).rename(index=CATEGORIES)

    lines = [f"{k} randomly sampled predictions per system (seed {cfg['seed']}) with {100 * lo:.0f}% < CER ≤ {100 * hi:.0f}%, "
             f"i.e. partial misreadings rather than total failures; {source}. A sample can carry several labels.", "",
             "| Error type | " + " | ".join(_label(s) for s in count_df.columns) + " |",
             "|---|" + "---:|" * len(count_df.columns)]
    for cat, r in count_df.iterrows():
        lines.append(f"| {cat} | " + " | ".join(str(v) for v in r) + " |")
    table = "\n".join(lines)

    detail = []
    for s, g in labels.groupby("system", sort=False):
        detail += [f"\n### {_label(s)}\n", "| id | CER | labels | ground truth | prediction | note |", "|---|---:|---|---|---|---|"]
        for _, r in g.iterrows():
            pred = r.pred_text if len(r.pred_text) <= 160 else r.pred_text[:160] + "…"
            detail.append(f"| {r.id} | {100 * r.cer_norm:.0f}% | {r['labels'].replace(';', ', ')} | {r.gt_text} | {pred} | {r.note} |")

    worst_lines = []
    for s, g in worst.groupby("system", sort=False):
        worst_lines += [f"\n### {_label(s)}\n", "| id | CER | ground truth | prediction |", "|---|---:|---|---|"]
        for r in g.itertuples():
            pred = " ".join(str(r.pred_text).split()) or "*(empty)*"
            pred = pred if len(pred) <= 120 else pred[:120] + "…"
            worst_lines.append(f"| {r.id} | {100 * r.cer_norm:.0f}% | {' '.join(r.gt_text.split())} | {pred} |")
    return table, "\n".join(detail), "\n".join(worst_lines)


def inject(readme, marker, content):
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    pattern = re.compile(rf"(<!-- {marker}:START -->).*?(<!-- {marker}:END -->)", re.S)
    if pattern.search(text):
        readme.write_text(pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", text), encoding="utf-8")


def build_report(cfg):
    _style()
    results = Path(cfg["paths"]["results"])
    (results / "figures").mkdir(parents=True, exist_ok=True)

    df = per_sample(cfg)
    df.to_csv(results / "per_sample.csv", index=False)
    summary = summarize(df, cfg)
    summary["peak_mem_gb"] = summary[["peak_rss_gb", "peak_mlx_gb"]].max(axis=1)
    summary.to_csv(results / "summary.csv", index=False)

    tables = markdown_tables(summary)
    (results / "summary.md").write_text(tables + "\n", encoding="utf-8")

    fig_cer_bars(summary, results / "figures" / "cer_by_subset.png")
    fig_cost_scatter(summary, results / "figures" / "cer_vs_latency.png")
    fig_normalization(summary, results / "figures" / "normalization.png")
    manifest_paths = {}
    for sub in cfg["subsets"]:
        manifest_paths.update({r["id"]: r["image_path"] for r in read_jsonl(Path(cfg["paths"]["data"]) / sub / "manifest.jsonl")})
    fig_examples(df, manifest_paths, results / "figures" / "examples.png")

    fail_table = failure_table(df, cfg)
    err_table, err_detail, worst_detail = error_files(df, cfg, results)
    notes_path = results / "error_notes.md"  # hand-written findings, kept across reruns
    notes = notes_path.read_text(encoding="utf-8") + "\n\n" if notes_path.exists() else ""
    (results / "error_analysis.md").write_text(
        "# Error analysis\n\n" + notes
        + "## 1. Catastrophic failure modes\n\n" + fail_table
        + "\n\n## 2. Arabic-specific error types\n\n" + err_table
        + "\n\n## Labeled samples\n" + err_detail
        + f"\n\n## Appendix: worst {cfg['metrics']['worst_k']} predictions per system\n" + worst_detail + "\n",
        encoding="utf-8")

    readme = Path("README.md")
    inject(readme, "RESULTS", tables)
    inject(readme, "FAILURES", fail_table)
    inject(readme, "ERRORS", err_table)
    print(tables)
    print("\n" + fail_table)
    print("\n" + err_table)
    return summary
