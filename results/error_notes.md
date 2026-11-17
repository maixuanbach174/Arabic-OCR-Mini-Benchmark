The 15 worst predictions per system (appendix) are dominated by total failures: empty output for the classic engines and runaway generations for Qwen. They say *that* a system failed, not *how* it misreads Arabic. So the analysis has two parts:

1. **Catastrophic failure modes**, counted automatically over all 300 predictions per system (`src/errors.py: failure_flags`).
2. **Arabic-specific error types**, hand-labelled on 15 randomly sampled partial errors per system (5% < normalized CER ≤ 60%). The labels and a one-line note per sample are in `results/error_labels.csv`.

## Findings

**The VLM and the classic engines fail in different ways.**

- **Qwen2.5-VL-3B makes word-level errors.** In 12 of its 15 sampled errors it writes a *real, fluent Arabic word that is not in the image* (ابتدات→البدلات, المريخ→المرجح, الكلمات→الاتصالات). On KHATT's nonsense test words (مشمش، غيظ، بث) it substitutes real words (مشهدة، عيال، بنت). The output reads well, so these errors are hard to catch downstream.
- **Its language prior surfaces in two other ways.** It completes formulae that are cut off in the image (adds وسلم after صلى الله عليه, pats_0279). On illegible manuscript lines it falls back on religious phrases (الله لا إله إلا هو, الحمد لله) that are not on the page: 12 of the 100 HistoryAr outputs, 4 of which then loop until they hit the 256-token cap. In total, 7 of 300 Qwen outputs hit that cap. On HistoryAr, 10% of outputs run past 1.5× the reference length, which is why its mean CER there is 157% while the median is 39%.
- **It also adds diacritics that are not in the image.** 67 of 100 KHATT outputs carry tashkeel, but only 6 KHATT references do. That is why normalization cuts Qwen's median CER by 23 points on KHATT and 27 on HistoryAr, but cuts the classic engines' by only 0–11.
- **It produced 2 non-Arabic outputs.** One PATS line came back mostly in Chinese (pats_0116), and one historical line came back as a LaTeX fraction.

- **Tesseract makes character-level errors.** Its errors are letter-shape confusions (13 of 15) and dotted-letter confusions (9 of 15): ت→ن, ف→ق, ه→ة, ي→ب. These are exactly the pairs that share a skeleton (rasm) and differ only in dots. When it cannot read a line at all, it returns **nothing**: 80 of 300 lines (51% of HistoryAr, 23% of KHATT, and even 6% of clean PATS lines) come back empty. On a line I probed, grayscaling, contrast stretching and halving the resolution all still gave empty output, which points to a recognition failure rather than a preprocessing bug.

- **EasyOCR makes segmentation errors.** 9 of its 15 errors merge or split words (وبيلانالجزءالثالت = four words glued together). It also injects Latin digits and symbols (`7`, `=`, `_`) into Arabic text, and its CRAFT detector misses short historical fragments (9% empty on HistoryAr).

**Dotted-letter confusion is common to all three** (Qwen 5 of 15, Tesseract 9, EasyOCR 8). It is the one Arabic-specific error no system has solved, but for the VLM it is not the dominant one.

**Reference noise.** Some HistoryAr references are page numbers (٧٢), marginal notes (صح) or contain stray brackets (`ا[؟`). Several use dotless manuscript letters (ٮ, ٯ, ڡ, ں). `ڡ`/`ں` are mapped in normalized mode; dotless `ٮ` is left as is because it can stand for ب, ت, ث, ن or ي.
