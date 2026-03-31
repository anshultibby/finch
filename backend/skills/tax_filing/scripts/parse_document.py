"""Extract structured data from uploaded tax document PDFs (W-2, 1099, etc.)."""

import re
import os
from typing import Optional

_BOT_DIR = os.environ.get("FINCH_BOT_DIR", "/home/user")
UPLOADS_DIR = f"{_BOT_DIR}/tax/uploads"


def _read_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    reader = PdfReader(pdf_path)
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n".join(parts)


def _find(pattern: str, text: str, group: int = 1) -> Optional[str]:
    """Find a regex match and return the captured group, or None."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(group).strip() if m else None


def _find_amount(pattern: str, text: str) -> Optional[str]:
    """Find a dollar amount matching a pattern."""
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip().replace(",", "").replace("$", "")
    return raw if raw else None


# ─────────────────────────────────────────────────────────────────────────────
# Form-specific extractors
# ─────────────────────────────────────────────────────────────────────────────

def extract_w2(pdf_path: str) -> dict:
    """Extract data from a W-2 (Wage and Tax Statement) PDF.

    Returns dict with keys: employer_name, employer_ein, employee_name, employee_ssn,
    wages, federal_withholding, ss_wages, ss_tax, medicare_wages, medicare_tax,
    state, state_wages, state_tax, etc.
    """
    text = _read_pdf_text(pdf_path)

    data = {"form_type": "W-2", "source_file": pdf_path, "raw_text": text}

    # EIN (box b)
    data["employer_ein"] = _find(r"(?:employer.?s?\s*(?:identification|ID|EIN)\s*(?:number|no\.?)?|b\s+Employer)\s*[:\-]?\s*([\d\-]+)", text)

    # Employer name/address (box c)
    data["employer_name"] = _find(r"(?:employer.?s?\s*name|c\s+Employer)\s*[:\-]?\s*(.+?)(?:\n|$)", text)

    # Employee SSN (box a)
    data["employee_ssn"] = _find(r"(?:employee.?s?\s*(?:social|SSN)|a\s+Employee)\s*[:\-]?\s*([\d\-]+)", text)

    # Employee name (box e)
    data["employee_name"] = _find(r"(?:employee.?s?\s*(?:first\s*name|name)|e\s+Employee)\s*[:\-]?\s*(.+?)(?:\n|$)", text)

    # Box 1: Wages, tips, other compensation
    data["wages"] = _find_amount(r"(?:wages.*?tips.*?other\s*comp|box\s*1)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # Box 2: Federal income tax withheld
    data["federal_withholding"] = _find_amount(r"(?:federal\s*income\s*tax\s*withheld|box\s*2)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # Box 3: Social security wages
    data["ss_wages"] = _find_amount(r"(?:social\s*security\s*wages|box\s*3)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # Box 4: Social security tax withheld
    data["ss_tax"] = _find_amount(r"(?:social\s*security\s*tax\s*withheld|box\s*4)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # Box 5: Medicare wages and tips
    data["medicare_wages"] = _find_amount(r"(?:medicare\s*wages|box\s*5)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # Box 6: Medicare tax withheld
    data["medicare_tax"] = _find_amount(r"(?:medicare\s*tax\s*withheld|box\s*6)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # State (box 15)
    data["state"] = _find(r"(?:state\b|box\s*15)\s*[:\-]?\s*([A-Z]{2})", text)

    # State wages (box 16)
    data["state_wages"] = _find_amount(r"(?:state\s*wages|box\s*16)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # State income tax (box 17)
    data["state_tax"] = _find_amount(r"(?:state\s*income\s*tax|box\s*17)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text)

    # Clean out None values for readability
    return {k: v for k, v in data.items() if v is not None}


def extract_1099_nec(pdf_path: str) -> dict:
    """Extract data from a 1099-NEC (Nonemployee Compensation) PDF."""
    text = _read_pdf_text(pdf_path)
    data = {"form_type": "1099-NEC", "source_file": pdf_path, "raw_text": text}

    data["payer_name"] = _find(r"(?:payer.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)
    data["payer_tin"] = _find(r"(?:payer.?s?\s*TIN)\s*[:\-]?\s*([\d\-]+)", text)
    data["recipient_name"] = _find(r"(?:recipient.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)
    data["recipient_tin"] = _find(r"(?:recipient.?s?\s*TIN)\s*[:\-]?\s*([\d\-]+)", text)

    # Box 1: Nonemployee compensation
    data["nonemployee_compensation"] = _find_amount(
        r"(?:nonemployee\s*compensation|box\s*1)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Box 4: Federal income tax withheld
    data["federal_withholding"] = _find_amount(
        r"(?:federal\s*income\s*tax\s*withheld|box\s*4)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    return {k: v for k, v in data.items() if v is not None}


def extract_1099_int(pdf_path: str) -> dict:
    """Extract data from a 1099-INT (Interest Income) PDF."""
    text = _read_pdf_text(pdf_path)
    data = {"form_type": "1099-INT", "source_file": pdf_path, "raw_text": text}

    data["payer_name"] = _find(r"(?:payer.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)
    data["recipient_name"] = _find(r"(?:recipient.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)

    # Box 1: Interest income
    data["interest_income"] = _find_amount(
        r"(?:interest\s*income|box\s*1)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Box 3: Interest on US savings bonds
    data["us_savings_bond_interest"] = _find_amount(
        r"(?:interest\s*on.*?(?:U\.?S\.?\s*)?savings\s*bonds|box\s*3)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Box 4: Federal income tax withheld
    data["federal_withholding"] = _find_amount(
        r"(?:federal\s*income\s*tax\s*withheld|box\s*4)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    return {k: v for k, v in data.items() if v is not None}


def extract_1099_div(pdf_path: str) -> dict:
    """Extract data from a 1099-DIV (Dividends and Distributions) PDF."""
    text = _read_pdf_text(pdf_path)
    data = {"form_type": "1099-DIV", "source_file": pdf_path, "raw_text": text}

    data["payer_name"] = _find(r"(?:payer.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)
    data["recipient_name"] = _find(r"(?:recipient.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)

    # Box 1a: Total ordinary dividends
    data["ordinary_dividends"] = _find_amount(
        r"(?:total\s*ordinary\s*dividends|box\s*1a)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Box 1b: Qualified dividends
    data["qualified_dividends"] = _find_amount(
        r"(?:qualified\s*dividends|box\s*1b)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Box 2a: Total capital gain distributions
    data["capital_gain_distributions"] = _find_amount(
        r"(?:total\s*capital\s*gain\s*dist|box\s*2a)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Box 4: Federal income tax withheld
    data["federal_withholding"] = _find_amount(
        r"(?:federal\s*income\s*tax\s*withheld|box\s*4)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    return {k: v for k, v in data.items() if v is not None}


def extract_1099_b(pdf_path: str) -> dict:
    """Extract data from a 1099-B (Proceeds from Broker Transactions) PDF."""
    text = _read_pdf_text(pdf_path)
    data = {"form_type": "1099-B", "source_file": pdf_path, "raw_text": text}

    data["payer_name"] = _find(r"(?:payer.?s?\s*name|broker)\s*[:\-]?\s*(.+?)(?:\n|$)", text)
    data["recipient_name"] = _find(r"(?:recipient.?s?\s*name)\s*[:\-]?\s*(.+?)(?:\n|$)", text)

    # Try to find summary totals
    data["total_proceeds"] = _find_amount(
        r"(?:total\s*proceeds|gross\s*proceeds)\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )
    data["total_cost_basis"] = _find_amount(
        r"(?:total\s*cost\s*(?:basis|or other))\s*[:\-]?\s*\$?([\d,]+\.?\d*)", text
    )

    # Note: 1099-B often has many individual transactions.
    # The raw_text is included so the agent can parse individual rows if needed.
    return {k: v for k, v in data.items() if v is not None}


# ─────────────────────────────────────────────────────────────────────────────
# Auto-detection
# ─────────────────────────────────────────────────────────────────────────────

_FORM_PATTERNS = [
    (r"W[\-\s]?2\b|Wage\s+and\s+Tax\s+Statement", "W-2", extract_w2),
    (r"1099[\-\s]?NEC|Nonemployee\s+Compensation", "1099-NEC", extract_1099_nec),
    (r"1099[\-\s]?INT|Interest\s+Income", "1099-INT", extract_1099_int),
    (r"1099[\-\s]?DIV|Dividends\s+and\s+Distributions", "1099-DIV", extract_1099_div),
    (r"1099[\-\s]?B\b|Proceeds\s+From\s+Broker", "1099-B", extract_1099_b),
]


def auto_detect(pdf_path: str) -> dict:
    """Detect the form type of a tax document PDF and extract its data.

    Reads the PDF text, identifies which form it is, and calls the appropriate
    extractor. If the form type can't be determined, returns the raw text so
    the agent can parse it manually.

    Args:
        pdf_path: Path to the uploaded PDF.

    Returns:
        Dict with at least {form_type, source_file} and extracted fields.
    """
    text = _read_pdf_text(pdf_path)

    for pattern, form_name, extractor in _FORM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return extractor(pdf_path)

    return {
        "form_type": "unknown",
        "source_file": pdf_path,
        "raw_text": text,
        "note": "Could not auto-detect form type. Use a specific extractor or parse the raw_text manually.",
    }


def list_uploads() -> list[str]:
    """List all uploaded files in the tax uploads directory."""
    if not os.path.exists(UPLOADS_DIR):
        return []
    return [f for f in os.listdir(UPLOADS_DIR) if not f.startswith(".")]
