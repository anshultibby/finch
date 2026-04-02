"""Fill PDF forms using vision-guided field mapping + pymupdf widget API.

Flow:
1. render_annotated_form() — renders each page with numbered markers on widget boxes,
   returns annotated images to the agent via <<RETURN_IMAGE>>
2. Agent sees images, maps marker numbers to semantic names
3. save_field_mapping() — caches {semantic_name: pdf_field_name}
4. fill_from_mapping() — fills using pymupdf widgets with the cached mapping
"""

import os
import json
from typing import Optional

_BOT_DIR = os.environ.get("FINCH_BOT_DIR", "/home/user")
TAX_DIR = f"{_BOT_DIR}/tax"
FILLED_DIR = f"{TAX_DIR}/filled"
SCHEMAS_DIR = f"{TAX_DIR}/schemas"
PREVIEWS_DIR = f"{TAX_DIR}/previews"


def _ensure_dirs():
    os.makedirs(FILLED_DIR, exist_ok=True)
    os.makedirs(SCHEMAS_DIR, exist_ok=True)
    os.makedirs(PREVIEWS_DIR, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Render annotated form preview
# ──────────────────────────────────────────────────────────────────────────────

def render_annotated_form(pdf_path: str, max_pages: int = 4) -> str:
    """Render PDF pages with numbered markers on every fillable widget box.

    Each widget gets a small red numbered label drawn on top of it so the
    vision model can see exactly which number corresponds to which visual
    field on the form.

    The annotated images are returned to you via <<RETURN_IMAGE>> markers.
    A numbered legend mapping each marker to its PDF field name is printed.

    After seeing the annotated images, create a mapping from semantic names
    to marker numbers, then call save_field_mapping_from_markers().

    Args:
        pdf_path: Path to the PDF form.
        max_pages: Max pages to render (default 4).

    Returns:
        Numbered legend: marker_number -> pdf_field_name (+ type).
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")

    _ensure_dirs()
    doc = fitz.open(pdf_path)
    num_pages = min(len(doc), max_pages)
    basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # Collect all widgets across pages with their marker numbers
    marker_num = 1
    legend = []  # (marker_num, field_name, field_type, page_num)

    for page_idx in range(num_pages):
        page = doc[page_idx]
        widgets = list(page.widgets())

        for widget in widgets:
            field_name = widget.field_name
            field_type = widget.field_type_string
            rect = widget.rect  # fitz.Rect(x0, y0, x1, y1) in PDF coords

            # Draw a red numbered label at the top-left corner of the widget
            label = str(marker_num)
            font_size = 7
            label_width = len(label) * font_size * 0.6 + 4
            label_height = font_size + 4

            # Position label at top-left of widget box
            label_rect = fitz.Rect(
                rect.x0, rect.y0 - label_height,
                rect.x0 + label_width, rect.y0
            )

            # Red background rectangle
            page.draw_rect(label_rect, color=(1, 0, 0), fill=(1, 0, 0))
            # White text
            page.insert_text(
                (label_rect.x0 + 2, label_rect.y1 - 3),
                label,
                fontsize=font_size,
                color=(1, 1, 1),
                fontname="helv",
            )

            # Light red border around the widget itself
            page.draw_rect(rect, color=(1, 0, 0), width=0.5)

            legend.append((marker_num, field_name, field_type, page_idx + 1))
            marker_num += 1

    # Open the original form in the PDF side panel so user sees it
    print(f"<<OPEN_FILE:{pdf_path}>>")

    # Render annotated pages to images
    for page_idx in range(num_pages):
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_path = f"{PREVIEWS_DIR}/{basename}_annotated_p{page_idx+1}.png"
        pix.save(img_path)
        print(f"<<RETURN_IMAGE:{img_path}>>")

    doc.close()

    # Build compact legend — NO field names (agent doesn't need them, saves tokens)
    # Just marker number + type so agent knows if it's a text field or checkbox
    lines = [f"{num_pages} pages, {len(legend)} fields marked.\n"]
    # Group by page for readability
    by_page: dict[int, list[tuple[int, str]]] = {}
    for num, _name, ftype, pg in legend:
        by_page.setdefault(pg, []).append((num, ftype))
    for pg in sorted(by_page):
        markers = by_page[pg]
        text_markers = [str(n) for n, ft in markers if ft == "Text"]
        check_markers = [str(n) for n, ft in markers if ft != "Text"]
        parts = []
        if text_markers:
            parts.append(f"text: {','.join(text_markers)}")
        if check_markers:
            parts.append(f"checkbox: {','.join(check_markers)}")
        lines.append(f"  Page {pg}: {' | '.join(parts)}")

    lines.append(
        "\nLook at the annotated images. Each red [N] marker sits on a "
        "fillable field. Map marker numbers to semantic names based on "
        "the form labels you see next to them.\n"
        "Call save_field_mapping_from_markers() with {semantic_name: marker_number}."
    )

    return "\n".join(lines)


def save_field_mapping_from_markers(
    form_id: str,
    pdf_path: str,
    marker_mapping: dict[str, int],
    max_pages: int = 4,
) -> str:
    """Save a field mapping using marker numbers from render_annotated_form().

    Translates marker numbers back to actual PDF field names and caches the
    mapping for future fills.

    Args:
        form_id: Short form identifier (e.g. "1040", "schedule-c").
        pdf_path: Path to the PDF form (same one passed to render_annotated_form).
        marker_mapping: Dict of semantic_name -> marker_number.
                        Example: {"first_name": 2, "last_name": 3, "ssn": 4}
        max_pages: Must match the max_pages used in render_annotated_form().

    Returns:
        Path to the saved schema file.
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")

    # Rebuild the marker→field_name lookup (same order as render_annotated_form)
    doc = fitz.open(pdf_path)
    num_pages = min(len(doc), max_pages)
    marker_to_field: dict[int, str] = {}
    marker_num = 1
    for page_idx in range(num_pages):
        page = doc[page_idx]
        for widget in page.widgets():
            marker_to_field[marker_num] = widget.field_name
            marker_num += 1
    doc.close()

    # Translate: semantic_name → marker_number → pdf_field_name
    mapping: dict[str, str] = {}
    errors = []
    for semantic_name, num in marker_mapping.items():
        if num in marker_to_field:
            mapping[semantic_name] = marker_to_field[num]
        else:
            errors.append(f"  Marker [{num}] not found (for '{semantic_name}')")

    if errors:
        print("Warnings:\n" + "\n".join(errors))

    _ensure_dirs()
    path = f"{SCHEMAS_DIR}/{form_id}.json"
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"Saved field mapping for '{form_id}': {len(mapping)} fields -> {path}")

    return path


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Fill using cached mapping + pymupdf widgets
# ──────────────────────────────────────────────────────────────────────────────

def fill_from_mapping(
    form_id: str,
    input_pdf: str,
    output_pdf: str,
    data: dict[str, str],
) -> str:
    """Fill a PDF form using a cached field mapping and pymupdf widgets.

    This is the main fill function. It:
    1. Loads the cached semantic→field_name mapping
    2. Opens the PDF with pymupdf
    3. Sets widget values by matching field names
    4. Saves the result (editable, not flattened)

    Args:
        form_id: Form identifier matching a saved mapping (e.g. "1040").
        input_pdf: Path to blank form PDF.
        output_pdf: Path for filled output PDF.
        data: Dict of semantic_name -> value. Keys must match the mapping.

    Returns:
        Path to the filled PDF.
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")

    mapping = load_field_mapping(form_id)
    if mapping is None:
        raise FileNotFoundError(
            f"No field mapping cached for '{form_id}'. "
            f"Run render_annotated_form() first, then save_field_mapping_from_markers()."
        )

    # Translate semantic keys to PDF field names
    field_values: dict[str, str] = {}
    unmapped = []
    for key, value in data.items():
        if key in mapping:
            field_values[mapping[key]] = str(value)
        else:
            unmapped.append(key)

    if unmapped:
        print(f"Warning: {len(unmapped)} keys not in mapping: {unmapped}")

    _ensure_dirs()

    # Fill using pymupdf widget API
    doc = fitz.open(input_pdf)
    filled_count = 0
    for page in doc:
        for widget in page.widgets():
            if widget.field_name in field_values:
                value = field_values[widget.field_name]
                widget.field_value = value
                widget.update()
                filled_count += 1

    doc.save(output_pdf)
    doc.close()

    print(f"Filled {filled_count}/{len(field_values)} fields -> {output_pdf}")
    # Auto-open in the PDF side panel
    print(f"<<OPEN_FILE:{output_pdf}>>")
    if filled_count < len(field_values):
        missed = set(field_values.keys()) - _get_widget_names(input_pdf)
        if missed:
            print(f"Fields not found in PDF: {missed}")

    return output_pdf


def _get_widget_names(pdf_path: str) -> set[str]:
    """Get all widget field names from a PDF."""
    import fitz
    doc = fitz.open(pdf_path)
    names = set()
    for page in doc:
        for widget in page.widgets():
            names.add(widget.field_name)
    doc.close()
    return names


# ──────────────────────────────────────────────────────────────────────────────
# Mapping persistence
# ──────────────────────────────────────────────────────────────────────────────

def save_field_mapping(form_id: str, mapping: dict[str, str]) -> str:
    """Directly save a semantic→field_name mapping (if you already know the names).

    Prefer save_field_mapping_from_markers() for vision-guided mapping.

    Args:
        form_id: Short form identifier (e.g. "1040").
        mapping: Dict of semantic_name -> exact_pdf_field_name.
    """
    _ensure_dirs()
    path = f"{SCHEMAS_DIR}/{form_id}.json"
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"Saved field mapping for '{form_id}' ({len(mapping)} fields) -> {path}")
    return path


def load_field_mapping(form_id: str) -> Optional[dict[str, str]]:
    """Load a cached field mapping. Returns None if not cached yet."""
    path = f"{SCHEMAS_DIR}/{form_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


# ──────────────────────────────────────────────────────────────────────────────
# Verification
# ──────────────────────────────────────────────────────────────────────────────

def verify_filled(pdf_path: str) -> str:
    """Render a filled PDF and return the image so you can visually verify it.

    Call this after fill_from_mapping() to confirm values landed in the right spots.
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")

    _ensure_dirs()
    doc = fitz.open(pdf_path)
    basename = os.path.splitext(os.path.basename(pdf_path))[0]

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_path = f"{PREVIEWS_DIR}/{basename}_verify_p{i+1}.png"
        pix.save(img_path)
        print(f"<<RETURN_IMAGE:{img_path}>>")

    num = len(doc)
    doc.close()
    return f"{num} pages rendered. Check images above."
