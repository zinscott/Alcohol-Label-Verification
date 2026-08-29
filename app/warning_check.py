"""
Deterministic, zero-tolerance validator for the government warning statement.

The vision model only OBSERVES the warning (transcribes it, reports caps/bold).
This module makes the PASS/FAIL decision in plain Python so the strict check is
never subject to LLM leniency.
"""
import re
from typing import TYPE_CHECKING
from app.config import GOVERNMENT_WARNING_PREFIX, GOVERNMENT_WARNING_TEXT
from app.models import WarningResult

if TYPE_CHECKING:  # avoid importing vision.py (constructs the Gemini client) at runtime
    from app.vision import WarningObs

# Checks that must all pass, in the order we report the first failure.
_REQUIRED = ("exact_wording", "prefix_all_caps", "prefix_bold")


def _normalize(text: str) -> str:
    #Collapse all whitespace to single spaces and strip ends.
    return re.sub(r"\s+", " ", text).strip()


def _wording_reason(got: str, want: str) -> str:
    #Point the reviewer at the first place the transcription diverges.
    i = next(
        (n for n, (a, b) in enumerate(zip(got, want)) if a != b),
        min(len(got), len(want)),
    )
    lo, hi = max(0, i - 25), i + 25
    return (
        f'wording differs near "...{got[lo:hi]}..." '
        f'(expected "...{want[lo:hi]}...")'
    )


def validate(obs: "WarningObs") -> WarningResult:
    """
    Turn the vision model's observations into a strict WarningResult.

    Fails on: no warning found, any wording difference (after whitespace
    normalization), a non-all-caps prefix, or a non-bold prefix. Whether the
    warning is a separate paragraph is recorded but is not on its own a failure.
    """
    checks: dict[str, bool] = {}

    checks["found"] = bool(obs.found and obs.verbatim_text)
    if not checks["found"]:
        return WarningResult(
            match=False,
            reason="no government warning statement found on the label",
            label_text=obs.verbatim_text,
            checks=checks,
        )

    got = _normalize(obs.verbatim_text or "")
    want = _normalize(GOVERNMENT_WARNING_TEXT)

    checks["exact_wording"] = got == want
    checks["prefix_all_caps"] = bool(obs.prefix_is_all_caps)
    checks["prefix_bold"] = bool(obs.prefix_is_bold)
    checks["separate_paragraph"] = bool(obs.is_separate_paragraph)

    failed = [name for name in _REQUIRED if not checks[name]]
    if not failed:
        return WarningResult(
            match=True,
            reason="warning statement is compliant",
            label_text=obs.verbatim_text,
            checks=checks,
        )

    first = failed[0]
    if first == "prefix_all_caps":
        reason = f'"{GOVERNMENT_WARNING_PREFIX}" is not in all capital letters'
    elif first == "prefix_bold":
        reason = f'"{GOVERNMENT_WARNING_PREFIX}" is not bold'
    else:
        reason = _wording_reason(got, want)

    return WarningResult(
        match=False,
        reason=reason,
        label_text=obs.verbatim_text,
        checks=checks,
    )
