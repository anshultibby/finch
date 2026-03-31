"""Fill IRS PDF forms — either via native form fields or text overlay."""

import os
import json
from typing import Any, Optional

TAX_DIR = "/home/user/tax"
FILLED_DIR = f"{TAX_DIR}/filled"


def _ensure_dirs():
    os.makedirs(FILLED_DIR, exist_ok=True)


def list_fields(pdf_path: str) -> dict[str, dict]:
    """List all fillable fields in a PDF form.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dict mapping field name -> {type, value, options} for each field.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        return {"_note": "No fillable form fields found. Use overlay_text() instead."}

    result = {}
    for name, field in fields.items():
        info: dict[str, Any] = {"type": str(field.get("/FT", "unknown"))}
        if "/V" in field:
            info["current_value"] = str(field["/V"])
        if "/Opt" in field:
            info["options"] = [str(o) for o in field["/Opt"]]
        result[name] = info
    return result


def fill_form(
    input_pdf: str,
    output_pdf: str,
    field_values: dict[str, str],
) -> str:
    """Fill a PDF form's native fields and save the result.

    Args:
        input_pdf: Path to the blank form PDF.
        output_pdf: Path for the filled output PDF.
        field_values: Dict mapping field name -> value to fill.

    Returns:
        Path to the filled PDF.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    _ensure_dirs()

    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    writer.append(reader)

    # Fill fields across all pages
    for page_num in range(len(writer.pages)):
        try:
            writer.update_page_form_field_values(writer.pages[page_num], field_values)
        except Exception:
            # Some pages may not have form fields
            pass

    with open(output_pdf, "wb") as f:
        writer.write(f)

    return output_pdf


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
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        return {"_note": "No form fields found in this PDF."}

    result = {}
    for name, field in fields.items():
        val = field.get("/V")
        if val is not None:
            result[name] = str(val)
    return result
