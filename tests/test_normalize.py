from src.metrics import score_sample
from src.normalize import normalize_arabic, normalize_raw


def test_raw_only_trims():
    assert normalize_raw("  أَحْمَد\n") == "أَحْمَد"


def test_removes_diacritics():
    assert normalize_arabic("كَتَبَ الْوَلَدُ") == "كتب الولد"
    assert normalize_arabic("هٰذا") == "هذا"  # dagger alef


def test_removes_tatweel():
    assert normalize_arabic("الســـــلام") == "السلام"


def test_unifies_alef_forms():
    assert normalize_arabic("أحمد إبراهيم آمن ٱلله") == "احمد ابراهيم امن الله"


def test_alef_maqsura_to_yeh():
    assert normalize_arabic("على مستشفى") == "علي مستشفي"


def test_digits():
    assert normalize_arabic("سنة ٢٠٠٥ و ۱۹") == "سنة 2005 و 19"


def test_collapses_spaces_and_bidi_marks():
    assert normalize_arabic("  في‏   البيت \n\t هنا ") == "في البيت هنا"


def test_presentation_forms_fold_to_base_letters():
    assert normalize_arabic("ﻻ") == "لا"  # lam-alef ligature


def test_normalization_removes_spelling_only_error():
    row = score_sample("إِلَى المدرسة", "الي المدرسة", 1.5)
    assert row["cer_raw"] > 0
    assert row["cer_norm"] == 0


def test_hallucination_flag():
    assert score_sample("كتاب", "كتاب كتاب كتاب", 1.5)["hallucination"]
    assert not score_sample("كتاب", "كتب", 1.5)["hallucination"]


def test_empty_prediction_is_full_error():
    row = score_sample("كتاب", "", 1.5)
    assert row["cer_raw"] == 1.0 and row["wer_norm"] == 1.0


def test_empty_flag():
    assert score_sample("كتاب", "  ", 1.5)["empty"]
    assert not score_sample("كتاب", "كتب", 1.5)["empty"]


def test_persian_and_dotless_variants():
    assert normalize_arabic("نصف الںهار ڡی کل") == "نصف النهار في كل"
