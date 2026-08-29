"""
The government warning wording is fixed by 27 CFR 16.21. Do not reformat these strings.
"""
import os
from dotenv import load_dotenv

load_dotenv()

VISION_MODEL = os.environ.get("VISION_MODEL", "gemini-3.6-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 27 CFR 16.21 — the Health Warning Statement, exact required wording.
GOVERNMENT_WARNING_TEXT = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth "
    "defects. (2) Consumption of alcoholic beverages impairs your ability to "
    "drive a car or operate machinery, and may cause health problems."
)

# The prefix that must be all-caps AND bold per TTB guidance.
GOVERNMENT_WARNING_PREFIX = "GOVERNMENT WARNING:"

# Fields that get fuzzy/semantic matching via the vision model.
FUZZY_FIELDS = ("brand_name", "class_type", "alcohol_content", "net_contents")
