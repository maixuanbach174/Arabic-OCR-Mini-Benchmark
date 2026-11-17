"""FR6: pull the worst predictions per system and pre-label Arabic-specific error types.

The heuristic labels are a first pass; results/error_analysis.md is reviewed by hand.
"""
import re
from difflib import SequenceMatcher

import jiwer

from .normalize import normalize_arabic

# Letters that share a skeleton (rasm) and differ only in dots.
DOTTED_GROUPS = ["بتثني", "جحخ", "دذ", "رز", "سش", "صض", "طظ", "عغ", "فق", "هة"]
SKELETON = {ch: g for g in DOTTED_GROUPS for ch in g}
ARABIC_DIGITS = set("0123456789")

CATEGORIES = {
    "dotted": "Confused dotted letters (ب/ت/ث, ج/ح/خ, ...)",
    "shape": "Other letter-shape confusion (e.g. ع/ه, ر/و, م/ه)",
    "word": "Whole-word substitution (a real but wrong word)",
    "joining": "Letter joining / word segmentation (merged or split words)",
    "digits": "Digit errors",
    "order": "Word order or right-to-left reversal",
    "missing": "Missing words",
    "hallucination": "Hallucinated / repeated text",
    "extra": "Inserted words or punctuation",
}

RELIGIOUS_FORMULAE = ["الله لا اله الا هو", "الحمد لله"]
ARABIC_LETTER = re.compile("[\u0621-\u064A\u0671-\u06D3]")
OTHER_LETTER = re.compile("[^\W\d_\u0621-\u064A\u0671-\u06D3\u064B-\u0652\u0670]")


def failure_flags(gt, pred, halluc_ratio=1.5):
    """Catastrophic failure modes, checked on every prediction (not just the worst)."""
    ref, hyp = normalize_arabic(gt), normalize_arabic(pred)
    words = hyp.split()
    ngrams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
    arabic, other = len(ARABIC_LETTER.findall(hyp)), len(OTHER_LETTER.findall(hyp))
    return {
        "empty": not hyp,
        "runaway": len(hyp) > halluc_ratio * max(len(ref), 1),
        "looping": bool(ngrams) and max(ngrams.count(g) for g in set(ngrams)) >= 3,
        "wrong_script": other > arabic,
        "formula_prior": any(f in hyp and f not in ref for f in RELIGIOUS_FORMULAE),
    }


FAILURES = {
    "empty": "Empty output",
    "runaway": "Output > 1.5x reference length",
    "looping": "Repetition loop (a 3-gram repeated 3+ times)",
    "wrong_script": "Mostly non-Arabic script (e.g. Chinese, Latin)",
    "formula_prior": "Religious formula not in the image (الله لا إله إلا هو / الحمد لله)",
}


def char_substitutions(ref, hyp):
    subs = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if op == "replace" and i2 - i1 == j2 - j1:
            subs += list(zip(ref[i1:i2], hyp[j1:j2]))
    return subs


def label_errors(gt, pred, halluc_ratio=1.5):
    ref, hyp = normalize_arabic(gt), normalize_arabic(pred)
    labels = []
    if len(hyp) > halluc_ratio * max(len(ref), 1):
        labels.append("hallucination")
    if len(hyp.split()) < 0.75 * len(ref.split()):
        labels.append("missing")
    if hyp and ref:
        reversed_hyp = " ".join(hyp.split()[::-1])
        if jiwer.cer(ref, reversed_hyp) + 0.1 < jiwer.cer(ref, hyp) or jiwer.cer(ref, hyp[::-1]) + 0.1 < jiwer.cer(ref, hyp):
            labels.append("order")
    subs = char_substitutions(ref, hyp)
    if sum(1 for a, b in subs if a in SKELETON and SKELETON[a] == SKELETON.get(b)) >= 1:
        labels.append("dotted")
    if {c for c in ref if c in ARABIC_DIGITS} != {c for c in hyp if c in ARABIC_DIGITS}:
        labels.append("digits")
    if ref.replace(" ", "") and SequenceMatcher(None, ref.replace(" ", ""), hyp.replace(" ", ""), autojunk=False).ratio() > 0.9 \
            and ref.split() != hyp.split() and len(ref.split()) != len(hyp.split()):
        labels.append("joining")
    return labels


def dotted_examples(gt, pred):
    ref, hyp = normalize_arabic(gt), normalize_arabic(pred)
    return [f"{a}→{b}" for a, b in char_substitutions(ref, hyp)
            if a in SKELETON and SKELETON[a] == SKELETON.get(b)]
