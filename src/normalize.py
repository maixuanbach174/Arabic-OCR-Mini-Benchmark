"""FR3: Arabic text normalization.

raw:        trim surrounding whitespace only.
normalized: the orthographic variation that OCR references are inconsistent about is removed,
            so the remaining errors are real misrecognitions.
"""
import re
import unicodedata

# Tashkeel U+064B-U+0652 (fathatan .. sukun) plus superscript (dagger) alef U+0670.
DIACRITICS = re.compile("[ً-ْٰ]")
TATWEEL = "ـ"
# Bidi control marks some engines emit: LRM, RLM, ALM, LRE..RLO, LRI..PDI.
BIDI_MARKS = re.compile("[‎‏؜‪-‮⁦-⁩]")
ALEF_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي"})
# Persian-style and dotless (rasm) letter forms used in manuscript transcriptions (HistoryAr):
# Farsi yeh, keheh, dotless feh, noon ghunna (dotless final noon).
VARIANT_MAP = str.maketrans({"ی": "ي", "ک": "ك", "ڡ": "ف", "ں": "ن"})
# Arabic-Indic (U+0660..) and Extended/Persian (U+06F0..) digits -> ASCII.
DIGIT_MAP = str.maketrans({**{chr(0x0660 + d): str(d) for d in range(10)},
                           **{chr(0x06F0 + d): str(d) for d in range(10)}})
SPACES = re.compile(r"\s+")


def normalize_raw(text):
    return (text or "").strip()


def normalize_arabic(text):
    text = text or ""
    # NFKC folds Arabic presentation forms (U+FB50-U+FEFF) back to base letters.
    text = unicodedata.normalize("NFKC", text)
    text = BIDI_MARKS.sub("", text)
    text = DIACRITICS.sub("", text)
    text = text.replace(TATWEEL, "")
    text = text.translate(ALEF_MAP).translate(VARIANT_MAP).translate(DIGIT_MAP)
    return SPACES.sub(" ", text).strip()


NORMALIZERS = {"raw": normalize_raw, "norm": normalize_arabic}
