"""Download IRS forms and instructions, and read instruction text."""

import os
import json
import urllib.request
import urllib.error
from typing import Optional

TAX_DIR = "/home/user/tax"
FORMS_DIR = f"{TAX_DIR}/forms"
INSTRUCTIONS_DIR = f"{TAX_DIR}/instructions"
DATA_DIR = f"{TAX_DIR}/data"
FILLED_DIR = f"{TAX_DIR}/filled"

# Maps friendly form names to IRS PDF filenames
FORM_CATALOG = {
    # Main return
    "1040":         {"form": "f1040",    "inst": "i1040"},
    # Schedules
    "schedule-1":   {"form": "f1040s1",  "inst": "i1040s1"},
    "schedule-2":   {"form": "f1040s2",  "inst": "i1040s2"},
    "schedule-3":   {"form": "f1040s3",  "inst": "i1040s3"},
    "schedule-a":   {"form": "f1040sa",  "inst": "i1040sa"},
    "schedule-b":   {"form": "f1040sb",  "inst": "i1040sb"},
    "schedule-c":   {"form": "f1040sc",  "inst": "i1040sc"},
    "schedule-d":   {"form": "f1040sd",  "inst": "i1040sd"},
    "schedule-e":   {"form": "f1040se",  "inst": "i1040se"},
    "schedule-se":  {"form": "f1040sse", "inst": "i1040sse"},
    # Other common forms
    "8949":         {"form": "f8949",    "inst": "i8949"},
    "8995":         {"form": "f8995",    "inst": "i8995"},
    "w-4":          {"form": "fw4",      "inst": None},
    "1099-nec":     {"form": "f1099nec", "inst": None},
    "8889":         {"form": "f8889",    "inst": "i8889"},
    "8829":         {"form": "f8829",    "inst": "i8829"},
    "2441":         {"form": "f2441",    "inst": "i2441"},
    "8863":         {"form": "f8863",    "inst": "i8863"},
    "8962":         {"form": "f8962",    "inst": "i8962"},
}


def _ensure_dirs():
    """Create the tax directory structure."""
    for d in [FORMS_DIR, INSTRUCTIONS_DIR, DATA_DIR, FILLED_DIR]:
        os.makedirs(d, exist_ok=True)


def _irs_url(filename: str, tax_year: int) -> str:
    """Build the IRS download URL for a given form/instruction PDF.

    IRS hosts prior-year forms at /pub/irs-prior/ and current-year at /pub/irs-pdf/.
    We try the prior-year path first for explicit years, current for latest.
    """
    # IRS uses /pub/irs-prior/ for prior-year revisions and /pub/irs-pdf/ for current
    return f"https://www.irs.gov/pub/irs-pdf/{filename}.pdf"


def _download(url: str, dest: str) -> str:
    """Download a file from url to dest. Returns dest path."""
    if os.path.exists(dest):
        return dest
    _ensure_dirs()
    req = urllib.request.Request(url, headers={"User-Agent": "FinchTaxSkill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return dest
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Failed to download {url}: HTTP {e.code} — "
            f"check that the form name and tax year are correct."
        )


def list_common_forms() -> list[dict]:
    """Return a list of commonly-used IRS forms with descriptions."""
    descriptions = {
        "1040":        "U.S. Individual Income Tax Return (everyone files this)",
        "schedule-1":  "Additional Income and Adjustments to Income",
        "schedule-2":  "Additional Taxes",
        "schedule-3":  "Additional Credits and Payments",
        "schedule-a":  "Itemized Deductions",
        "schedule-b":  "Interest and Ordinary Dividends (>$1,500)",
        "schedule-c":  "Profit or Loss from Business (self-employment)",
        "schedule-d":  "Capital Gains and Losses",
        "schedule-e":  "Supplemental Income (rental, royalty, S-corp, partnerships)",
        "schedule-se": "Self-Employment Tax",
        "8949":        "Sales and Dispositions of Capital Assets",
        "8995":        "Qualified Business Income Deduction",
        "8889":        "Health Savings Accounts (HSA)",
        "8829":        "Expenses for Business Use of Your Home",
        "2441":        "Child and Dependent Care Expenses",
        "8863":        "Education Credits (AOTC / Lifetime Learning)",
        "8962":        "Premium Tax Credit (ACA marketplace)",
    }
    return [
        {"form": name, "description": descriptions.get(name, ""), "irs_filename": info["form"]}
        for name, info in FORM_CATALOG.items()
        if name in descriptions
    ]


def download_form(form_name: str, tax_year: int = 2025) -> str:
    """Download a blank IRS form PDF.

    Args:
        form_name: Friendly name like "1040", "schedule-c", "8949"
        tax_year: Tax year (default 2025)

    Returns:
        Path to the downloaded PDF.
    """
    key = form_name.lower().strip()
    if key not in FORM_CATALOG:
        available = ", ".join(sorted(FORM_CATALOG.keys()))
        raise ValueError(f"Unknown form '{form_name}'. Available: {available}")

    filename = FORM_CATALOG[key]["form"]
    url = _irs_url(filename, tax_year)
    dest = f"{FORMS_DIR}/{filename}.pdf"
    return _download(url, dest)


def download_instructions(form_name: str, tax_year: int = 2025) -> str:
    """Download the IRS instructions PDF for a form.

    Args:
        form_name: Friendly name like "1040", "schedule-c"
        tax_year: Tax year (default 2025)

    Returns:
        Path to the downloaded instructions PDF.
    """
    key = form_name.lower().strip()
    if key not in FORM_CATALOG:
        available = ", ".join(sorted(FORM_CATALOG.keys()))
        raise ValueError(f"Unknown form '{form_name}'. Available: {available}")

    inst_filename = FORM_CATALOG[key].get("inst")
    if not inst_filename:
        raise ValueError(f"No instructions PDF available for '{form_name}'.")

    url = _irs_url(inst_filename, tax_year)
    dest = f"{INSTRUCTIONS_DIR}/{inst_filename}.pdf"
    return _download(url, dest)


def read_instructions(form_name: str, pages: str = "1-5") -> str:
    """Read text from a downloaded instructions PDF.

    The instructions PDF must already be downloaded via download_instructions().

    Args:
        form_name: Friendly name like "1040", "schedule-c"
        pages: Page range string, e.g. "1-5", "30-32", "10"

    Returns:
        Extracted text from the specified pages.
    """
    key = form_name.lower().strip()
    if key not in FORM_CATALOG:
        raise ValueError(f"Unknown form '{form_name}'.")

    inst_filename = FORM_CATALOG[key].get("inst")
    if not inst_filename:
        raise ValueError(f"No instructions PDF for '{form_name}'.")

    pdf_path = f"{INSTRUCTIONS_DIR}/{inst_filename}.pdf"
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"Instructions not downloaded yet. Run: download_instructions('{form_name}')"
        )

    # Parse page range
    start, end = _parse_page_range(pages)

    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    end = min(end, total - 1)

    text_parts = []
    for i in range(start, end + 1):
        page_text = reader.pages[i].extract_text() or ""
        text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

    return "\n\n".join(text_parts)


def _parse_page_range(pages: str) -> tuple[int, int]:
    """Parse a page range string like '1-5' or '10' into 0-based (start, end)."""
    pages = pages.strip()
    if "-" in pages:
        parts = pages.split("-", 1)
        start = int(parts[0].strip()) - 1
        end = int(parts[1].strip()) - 1
    else:
        start = int(pages) - 1
        end = start
    return max(0, start), max(0, end)


# --- Progress / data persistence ---

def save_progress(data: dict, filename: str = "progress.json") -> str:
    """Save interview progress to a JSON file.

    Args:
        data: Dict with collected tax data so far.
        filename: Output filename (default: progress.json)

    Returns:
        Path to the saved file.
    """
    _ensure_dirs()
    path = f"{DATA_DIR}/{filename}"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_progress(filename: str = "progress.json") -> Optional[dict]:
    """Load previously saved interview progress.

    Returns:
        The saved dict, or None if no progress file exists.
    """
    path = f"{DATA_DIR}/{filename}"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_form_schema(schema: dict) -> str:
    """Save a form schema definition that the interactive panel will render.

    The schema defines sections, fields, and calculations. See SKILL.md for format.

    Args:
        schema: Dict with keys: name, subtitle, year, sections.

    Returns:
        Path to the saved schema file.
    """
    _ensure_dirs()
    path = f"{DATA_DIR}/form_schema.json"
    with open(path, "w") as f:
        json.dump(schema, f, indent=2)
    return path


def load_form_schema() -> Optional[dict]:
    """Load the current form schema.

    Returns:
        The schema dict, or None if not defined yet.
    """
    path = f"{DATA_DIR}/form_schema.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)
