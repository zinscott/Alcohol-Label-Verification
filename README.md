# TTB Alcohol Label Verification (Prototype)

Checks whether an alcohol label image matches its COLA application data.

## What it checks

Given a label image + application fields (brand name, class/type, ABV, net contents),
returns a per-field match/mismatch with reasons and an overall PASS/FAIL.

- Brand name, class/type, ABV, net contents — fuzzy/semantic matching
- Government warning statement — strict: exact wording, all-caps + bold prefix
