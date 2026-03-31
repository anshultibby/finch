"""Fill IRS PDF forms — either via native form fields or text overlay."""

import os
import json
import subprocess
import shutil
from typing import Any, Optional

_BOT_DIR = os.environ.get("FINCH_BOT_DIR", "/home/user")
TAX_DIR = f"{_BOT_DIR}/tax"
FILLED_DIR = f"{TAX_DIR}/filled"


def _ensure_dirs():
    os.makedirs(FILLED_DIR, exist_ok=True)


def _ensure_pdftk():
    """Install pdftk if not present."""
    if shutil.which("pdftk"):
        return
    subprocess.run(
        ["sudo", "apt-get", "update", "-qq"],
        capture_output=True, timeout=60,
    )
    result = subprocess.run(
        ["sudo", "apt-get", "install", "-y", "-qq", "pdftk-java"],
        capture_output=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to install pdftk: {result.stderr.decode()}")


def list_fields(pdf_path: str) -> str:
    """List all fillable fields in a PDF form using pdftk.

    Returns a formatted string showing each field's name, type, and current value.
    Use these EXACT field names when calling fill_form().
    """
    _ensure_pdftk()
    result = subprocess.run(
        ["pdftk", pdf_path, "dump_data_fields_utf8"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftk failed: {result.stderr}")

    # Parse pdftk output into structured format
    fields = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line == "---":
            if current:
                fields.append(current)
            current = {}
        elif ": " in line:
            key, _, val = line.partition(": ")
            current[key] = val
    if current:
        fields.append(current)

    # Format as readable output
    lines = []
    for f in fields:
        name = f.get("FieldName", "?")
        ftype = f.get("FieldType", "?")
        val = f.get("FieldValue", "")
        tooltip = f.get("FieldNameAlt", "")
        desc = f" ({tooltip})" if tooltip else ""
        lines.append(f"  {name}  [{ftype}]{desc}  = {val!r}" if val else f"  {name}  [{ftype}]{desc}")
    return f"{len(fields)} fields found:\n" + "\n".join(lines)


def fill_form(
    input_pdf: str,
    output_pdf: str,
    field_values: dict[str, str],
) -> str:
    """Fill a PDF form using pdftk — the most reliable method for IRS forms.

    Use EXACT field names from list_fields() output. pdftk generates proper
    field appearances so values display correctly in all PDF viewers.

    Args:
        input_pdf: Path to the blank form PDF.
        output_pdf: Path for the filled output PDF.
        field_values: Dict mapping exact field name -> value.

    Returns:
        Path to the filled PDF.
    """
    _ensure_pdftk()
    _ensure_dirs()

    # Generate XFDF (XML Forms Data Format) — pdftk's preferred input
    xfdf_path = output_pdf.replace(".pdf", ".xfdf")
    xfdf = _generate_xfdf(input_pdf, field_values)
    with open(xfdf_path, "w", encoding="utf-8") as f:
        f.write(xfdf)

    # Run pdftk to fill the form
    result = subprocess.run(
        ["pdftk", input_pdf, "fill_form", xfdf_path, "output", output_pdf, "flatten"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftk fill_form failed: {result.stderr}")

    # Clean up XFDF
    try:
        os.remove(xfdf_path)
    except OSError:
        pass

    print(f"Filled {len(field_values)} fields -> {output_pdf}")
    return output_pdf


def fill_form_editable(
    input_pdf: str,
    output_pdf: str,
    field_values: dict[str, str],
) -> str:
    """Fill a PDF form but keep fields editable (not flattened).

    Same as fill_form() but the output PDF still has fillable fields,
    so the user can continue editing in the PDF viewer.
    """
    _ensure_pdftk()
    _ensure_dirs()

    xfdf_path = output_pdf.replace(".pdf", ".xfdf")
    xfdf = _generate_xfdf(input_pdf, field_values)
    with open(xfdf_path, "w", encoding="utf-8") as f:
        f.write(xfdf)

    result = subprocess.run(
        ["pdftk", input_pdf, "fill_form", xfdf_path, "output", output_pdf],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftk fill_form failed: {result.stderr}")

    try:
        os.remove(xfdf_path)
    except OSError:
        pass

    print(f"Filled {len(field_values)} fields (editable) -> {output_pdf}")
    return output_pdf


def _generate_xfdf(pdf_path: str, field_values: dict[str, str]) -> str:
    """Generate an XFDF file from field name/value pairs."""
    from xml.sax.saxutils import escape
    fields_xml = ""
    for name, value in field_values.items():
        fields_xml += f'    <field name="{escape(name)}"><value>{escape(str(value))}</value></field>\n'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xfdf xmlns="http://ns.adobe.com/xfdf/" xml:space="preserve">
  <f href="{escape(pdf_path)}"/>
  <fields>
{fields_xml}  </fields>
</xfdf>"""


def overlay_text(
    input_pdf: str,
    output_pdf: str,
    placements: list[dict],
) -> str:
    """Overlay text onto a PDF at exact coordinates (for non-fillable forms).

    Each placement dict should have:
        - page: 0-based page number
        - x: x coordinate (points from left)
        - y: y coordinate (points from bottom)
        - text: the text to place
        - size: font size (default 10)

    Args:
        input_pdf: Path to the source PDF.
        output_pdf: Path for the output PDF.
        placements: List of placement dicts.

    Returns:
        Path to the output PDF.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        raise RuntimeError("reportlab not installed. Run: pip install reportlab")

    import io

    _ensure_dirs()

    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Group placements by page
    by_page: dict[int, list[dict]] = {}
    for p in placements:
        by_page.setdefault(p["page"], []).append(p)

    for page_num, page in enumerate(reader.pages):
        if page_num in by_page:
            # Create an overlay PDF in memory
            page_box = page.mediabox
            width = float(page_box.width)
            height = float(page_box.height)

            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(width, height))
            for p in by_page[page_num]:
                font_size = p.get("size", 10)
                c.setFont("Helvetica", font_size)
                c.drawString(float(p["x"]), float(p["y"]), str(p["text"]))
            c.save()
            packet.seek(0)

            overlay_reader = PdfReader(packet)
            page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)

    return output_pdf


def preview_filled(pdf_path: str) -> dict:
    """Read back all filled field values from a PDF for verification.

    Args:
        pdf_path: Path to a filled PDF.

    Returns:
        Dict mapping field name -> current value.
    """
    _ensure_pdftk()
    result_proc = subprocess.run(
        ["pdftk", pdf_path, "dump_data_fields_utf8"],
        capture_output=True, text=True, timeout=30,
    )
    if result_proc.returncode != 0:
        return {"_error": result_proc.stderr}

    result = {}
    current_name = None
    for line in result_proc.stdout.splitlines():
        if line.startswith("FieldName: "):
            current_name = line[11:]
        elif line.startswith("FieldValue: ") and current_name:
            val = line[12:]
            if val:
                result[current_name] = val
    return result
