# TTB Alcohol Label Verification (Prototype)

A standalone proof-of-concept that checks whether an alcohol label image matches the
data an agent has on file for that application — automating the routine "does the number
on the label match the number on the form" work so agents can spend their time on the
calls that need judgment.

**Live demo:** <https://labelverification-five.vercel.app/>

---

## What it does

The agent uploads a label image and enters the application details. In one screen they
get back an overall **PASS / FAIL / NEEDS REVIEW** plus a per-field breakdown with a
plain-language reason for every result.

| Field | How it's checked |
|---|---|
| Brand name | Fuzzy / semantic — `STONE'S THROW` and `Stone's Throw` are the same thing |
| Class / type designation | Fuzzy / semantic |
| Alcohol content | Fuzzy / semantic — `45% Alc./Vol. (90 Proof)` matches `45` |
| Net contents | Fuzzy / semantic — `750 ML` matches `750 mL` |
| Government warning statement | **Strict, zero-tolerance** — exact mandatory wording, and `GOVERNMENT WARNING:` must be all-caps and bold |

If the image is too poor to read a field confidently, the tool returns **NEEDS REVIEW**
rather than guessing.

---

## Approach

The core design decision is to use **two different matching engines**, because the two
kinds of check have opposite requirements:

**1. The four ordinary fields → one vision-LLM call.** Brand name, class/type, ABV, and
net contents need *semantic* judgment — "STONE'S THROW" vs "Stone's Throw" is a match, a
different proof is not. That's exactly what a vision model is good at, and doing it in a
single round trip keeps latency low. The label image and the four application values go
to Google Gemini together; it returns, per field, the value it read off the label plus a
match/no-match verdict and a one-sentence reason. Structured output (a response schema)
guarantees the shape of what comes back.

**2. The government warning → deterministic Python.** This check is zero-tolerance: exact
wording, all-caps, bold. Leaving that to an LLM's discretion is the wrong call — it might
decide a near-miss is "close enough." So the vision model only *observes* the warning
(transcribes it character-for-character, reports whether the prefix looks all-caps and
bold); a plain validator in [`app/warning_check.py`](app/warning_check.py) makes the
actual PASS/FAIL decision by exact string comparison against the
[27 CFR 16.21](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16)
text. Whitespace and line breaks are normalized (a label wraps the warning across lines —
that's layout, not wording); everything else is significant. The same input always
produces the same verdict, and the failure reason points at the exact word that diverges.

---

## Tech choices

| Piece | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python) | Small, typed, fast to build; Pydantic models double as the API contract |
| Vision | Google Gemini (`gemini-3.6-flash`) | Vision-capable, structured output, free tier for a prototype; the client is isolated in one file for an easy swap |
| Frontend | One static HTML file, vanilla JS | No build step, no framework. Upload → result, large type, high contrast — built for the stated user base (half the team is 50+, "something my mother could figure out") |
| Image handling | Client-side canvas downscale before upload | Keeps requests small and fast, and under serverless body limits |
| Deploy | Vercel | Zero-config Python serverless + static hosting |
| Package manager | `uv` | Fast, reproducible |

---

## Setup

Requires Python 3.11+ and a [Google AI Studio API key](https://aistudio.google.com/apikey).

```bash
# 1. install dependencies
uv venv && uv pip install -r requirements.txt
#   (or: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)

# 2. add your key
#    edit .env and set GEMINI_API_KEY=...

# 3. run
uv run uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>.

### Tests

```bash
uv run pytest
```

The suite (`tests/test_warning_check.py`) covers the strict warning validator — the piece
with the least tolerance for error — across compliant text, whitespace/line-break
handling, missing and altered wording, non-caps and non-bold prefixes, and a missing
warning.

---

## Deployment

Deployed on Vercel — <https://labelverification-five.vercel.app/>. `api/index.py` exposes
the FastAPI app as a serverless function; `vercel.json` routes `/api/*` and `/` to it and
bundles `app/` and `public/`. `GEMINI_API_KEY` is set as a Vercel environment variable.

---

## Assumptions & trade-offs

**Fields checked.** The prototype checks the five fields on the sample label (brand,
class/type, ABV, net contents, government warning). TTB also requires bottler name/address
and, for imports, country of origin; those follow the same fuzzy-field pattern and would
be a small addition, but they aren't in the sample so they're out of scope here.

**Input is manual entry, not a data-source lookup.** The agent types the four application
values. Integrating with COLA is explicitly out of scope for this prototype (per Marcus),
and there's no application data source to look them up from, so manual entry is the
workflow.

**The ~5-second bar is not reliably met on the free tier.** Median latency is ~3–4s, but
the Gemini free tier throttles unpredictably and individual calls have been observed to
spike to 15–30s. This is a free-tier quota issue, not a design one — a paid tier or a
latency-optimized provider (e.g. Groq) resolves it, and the provider client is isolated
in [`app/vision.py`](app/vision.py) so swapping it touches ~15 lines. For a production
build this would need a provisioned endpoint with a latency SLA.

**External API dependency / TTB's firewall.** The prototype depends on an outbound call
to the Gemini API. TTB's network blocks a lot of outbound traffic (this broke the prior
scanning-vendor pilot). Acceptable here because the prototype runs on public
infrastructure and touches no TTB systems or real data — but a production version would
need the model endpoint allowlisted, or an in-network / self-hosted model.

**"Bold" detection.** A string comparison can't see font weight, so whether
`GOVERNMENT WARNING:` is bold is the one part of the strict check that relies on the
vision model's visual observation. The *decision* still lives in deterministic code; only
the observation is delegated.

**Poor-quality photos are not corrected.** Angle, glare, and lighting aren't handled
(Jenny flagged this as likely out of scope). If a field can't be read confidently the
result is NEEDS REVIEW, matching the current manual practice of rejecting and asking for a
better image.

**No auth, persistence, or PII handling.** Prototype scope, per Marcus — nothing
sensitive is stored.

**Batch upload is not implemented.** It's a clear want (peak-season importers submit
200–300 applications at once) and the single-label logic would loop cleanly, but the core
single-label flow was the priority for a time-boxed prototype.

---

## Project structure

```
app/
  main.py           FastAPI app — POST /api/verify ties the pieces together
  vision.py         one Gemini call: fuzzy field matching + warning transcription
  warning_check.py  deterministic strict validator for the government warning
  models.py         Pydantic request/response schemas
  config.py         model id + the 27 CFR 16.21 warning constants
api/index.py        Vercel serverless entrypoint
public/index.html   the entire frontend
tests/              warning-validator test suite + a sample label image
```
