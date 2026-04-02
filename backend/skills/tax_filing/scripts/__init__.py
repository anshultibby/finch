"""Tax filing scripts — form downloading, instruction lookup, PDF filling, and document parsing."""
from .forms import download_form, download_instructions, read_instructions, list_common_forms
from .forms import save_progress, load_progress, save_form_schema, load_form_schema
from .fill_pdf import (
    render_annotated_form,
    save_field_mapping_from_markers,
    save_field_mapping,
    load_field_mapping,
    fill_from_mapping,
    verify_filled,
)
from .parse_document import auto_detect, extract_w2, extract_1099_nec, extract_1099_int
from .parse_document import extract_1099_div, extract_1099_b, list_uploads

__all__ = [
    "download_form",
    "download_instructions",
    "read_instructions",
    "list_common_forms",
    "save_progress",
    "load_progress",
    "save_form_schema",
    "load_form_schema",
    "render_annotated_form",
    "save_field_mapping_from_markers",
    "save_field_mapping",
    "load_field_mapping",
    "fill_from_mapping",
    "verify_filled",
    "auto_detect",
    "extract_w2",
    "extract_1099_nec",
    "extract_1099_int",
    "extract_1099_div",
    "extract_1099_b",
    "list_uploads",
]
