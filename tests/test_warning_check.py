"""
Tests for the deterministic government-warning validator.

These never touch the vision model. Each test builds a fake observation object
(the shape of app.vision.WarningObs) with SimpleNamespace and checks that
validate() makes the right strict PASS/FAIL call.
"""
from types import SimpleNamespace
from app.config import GOVERNMENT_WARNING_PREFIX, GOVERNMENT_WARNING_TEXT
from app.warning_check import validate


def obs(
    *,
    found=True,
    verbatim_text=GOVERNMENT_WARNING_TEXT,
    prefix_is_all_caps=True,
    prefix_is_bold=True,
    is_separate_paragraph=True,
):
    # Build a WarningObs-shaped object; kwargs override the compliant default.
    return SimpleNamespace(
        found=found,
        verbatim_text=verbatim_text,
        prefix_is_all_caps=prefix_is_all_caps,
        prefix_is_bold=prefix_is_bold,
        is_separate_paragraph=is_separate_paragraph,
    )


def test_compliant_warning_passes():
    result = validate(obs())
    assert result.match is True
    assert result.checks["exact_wording"] is True
    assert result.checks["prefix_all_caps"] is True
    assert result.checks["prefix_bold"] is True


def test_line_breaks_do_not_fail_wording():
    # A real label wraps the warning across lines; that is not a wording change.
    wrapped = GOVERNMENT_WARNING_TEXT.replace(" ", "\n", 3)
    result = validate(obs(verbatim_text=wrapped))
    assert result.match is True
    assert result.checks["exact_wording"] is True


def test_extra_internal_whitespace_is_ignored():
    spaced = GOVERNMENT_WARNING_TEXT.replace(" ", "   ")
    result = validate(obs(verbatim_text=spaced))
    assert result.match is True


def test_missing_word_fails():
    text = GOVERNMENT_WARNING_TEXT.replace(
        ", and may cause health problems", ""
    )
    result = validate(obs(verbatim_text=text))
    assert result.match is False
    assert result.checks["exact_wording"] is False
    assert "wording differs" in result.reason


def test_altered_wording_fails():
    text = GOVERNMENT_WARNING_TEXT.replace("Surgeon General", "Surgeon-General")
    result = validate(obs(verbatim_text=text))
    assert result.match is False
    assert result.checks["exact_wording"] is False


def test_prefix_not_all_caps_fails():
    result = validate(obs(prefix_is_all_caps=False))
    assert result.match is False
    assert result.checks["prefix_all_caps"] is False
    assert "capital letters" in result.reason


def test_prefix_not_bold_fails():
    result = validate(obs(prefix_is_bold=False))
    assert result.match is False
    assert result.checks["prefix_bold"] is False
    assert "not bold" in result.reason


def test_no_warning_found_fails():
    result = validate(obs(found=False, verbatim_text=None))
    assert result.match is False
    assert result.checks["found"] is False
    assert "no government warning" in result.reason


def test_found_true_but_empty_text_fails():
    result = validate(obs(verbatim_text=""))
    assert result.match is False
    assert result.checks["found"] is False


def test_wording_failure_reported_before_formatting_failure():
    # When several checks fail at once, wording is the reason surfaced first.
    result = validate(
        obs(verbatim_text="GOVERNMENT WARNING: wrong text", prefix_is_bold=False)
    )
    assert result.match is False
    assert "wording differs" in result.reason


def test_separate_paragraph_false_does_not_fail_on_its_own():
    result = validate(obs(is_separate_paragraph=False))
    assert result.match is True
    assert result.checks["separate_paragraph"] is False


def test_label_text_is_passed_through():
    result = validate(obs(verbatim_text="GOVERNMENT WARNING: something off"))
    assert result.label_text == "GOVERNMENT WARNING: something off"


def test_prefix_constant_matches_canonical_text_start():
    # Guard: the prefix constant must stay a literal substring of the full text.
    assert GOVERNMENT_WARNING_TEXT.startswith(GOVERNMENT_WARNING_PREFIX)
