"""FDA drug data: openFDA approvals, review documents, adverse events, and drug labels."""

import io

_OPENFDA_BASE = "https://api.fda.gov/drug/drugsfda.json"
_FAERS_BASE = "https://api.fda.gov/drug/event.json"
_LABEL_BASE = "https://api.fda.gov/drug/label.json"


def search_fda_approvals(
    drug_name: str = None,
    company: str = None,
    max_results: int = 10,
) -> list[dict]:
    """
    Search FDA-approved drugs by brand/generic name or manufacturer.

    Returns list of dicts with: application_number, brand_name, generic_name,
    manufacturer, submissions (with approval dates and doc URLs).
    """
    from ._http import get_json

    parts = []
    if drug_name:
        parts.append(f'(openfda.brand_name:"{drug_name}"+openfda.generic_name:"{drug_name}")')
    if company:
        parts.append(f'openfda.manufacturer_name:"{company}"')

    if not parts:
        return [{"error": "Provide drug_name or company"}]

    search = "+AND+".join(parts)
    data = get_json(_OPENFDA_BASE, params={"search": search, "limit": max_results})

    if isinstance(data, dict) and "error" in data:
        # openFDA returns {"error": {"code": ..., "message": ...}} for no results
        err = data.get("error", data)
        if isinstance(err, dict):
            return [{"error": err.get("message", str(err))}]
        return [{"error": str(err)}]

    results = data.get("results", [])
    out = []
    for r in results:
        openfda = r.get("openfda", {})
        submissions = []
        for sub in r.get("submissions", []):
            docs = []
            for doc in sub.get("application_docs", []):
                docs.append({
                    "id": doc.get("id"),
                    "url": doc.get("url"),
                    "title": doc.get("title"),
                    "type": doc.get("type"),
                })
            submissions.append({
                "submission_type": sub.get("submission_type"),
                "submission_number": sub.get("submission_number"),
                "submission_status": sub.get("submission_status"),
                "submission_status_date": sub.get("submission_status_date"),
                "review_priority": sub.get("review_priority"),
                "docs": docs,
            })

        out.append({
            "application_number": r.get("application_number"),
            "sponsor_name": r.get("sponsor_name"),
            "brand_name": openfda.get("brand_name", []),
            "generic_name": openfda.get("generic_name", []),
            "manufacturer": openfda.get("manufacturer_name", []),
            "route": openfda.get("route", []),
            "substance_name": openfda.get("substance_name", []),
            "product_type": openfda.get("product_type", []),
            "submissions": submissions,
        })

    return out


def get_application_docs(application_number: str) -> list[dict]:
    """
    Get all review documents for an FDA application number (e.g., "NDA214611").

    Returns list of docs with url, title, type, submission date.
    """
    from ._http import get_json

    clean = application_number.upper().strip()
    data = get_json(_OPENFDA_BASE, params={
        "search": f'application_number:"{clean}"',
        "limit": 1,
    })

    if isinstance(data, dict) and "error" in data:
        err = data.get("error", data)
        if isinstance(err, dict):
            return [{"error": err.get("message", str(err))}]
        return [{"error": str(err)}]

    results = data.get("results", [])
    if not results:
        return [{"error": f"No application found for {clean}"}]

    docs = []
    for sub in results[0].get("submissions", []):
        sub_date = sub.get("submission_status_date")
        sub_type = sub.get("submission_type")
        sub_num = sub.get("submission_number")
        for doc in sub.get("application_docs", []):
            docs.append({
                "url": doc.get("url"),
                "title": doc.get("title"),
                "type": doc.get("type"),
                "doc_id": doc.get("id"),
                "submission_type": sub_type,
                "submission_number": sub_num,
                "submission_date": sub_date,
            })

    return docs


def fetch_review_document(url: str, max_chars: int = 50000, max_pages: int = 80) -> dict:
    """
    Download an FDA review document PDF and extract text.

    Args:
        url: Direct URL to the PDF
        max_chars: Truncate extracted text to this length (default 50K)
        max_pages: Max pages to extract (default 80)

    Returns:
        {"url": str, "text": str, "pages_extracted": int, "total_pages": int, "truncated": bool}
    """
    from ._http import get_bytes

    pdf_bytes = get_bytes(url, timeout=90)
    if pdf_bytes is None:
        return {"error": f"Failed to download PDF from {url}"}

    try:
        from pypdf import PdfReader
    except ImportError:
        return {"error": "pypdf not installed — run: pip install pypdf"}

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        return {"error": f"Failed to parse PDF: {e}"}

    total_pages = len(reader.pages)
    pages_to_read = min(total_pages, max_pages)
    parts = []
    chars = 0
    pages_extracted = 0

    for i in range(pages_to_read):
        text = reader.pages[i].extract_text() or ""
        if chars + len(text) > max_chars:
            remaining = max_chars - chars
            if remaining > 0:
                parts.append(text[:remaining])
                pages_extracted = i + 1
            break
        parts.append(text)
        chars += len(text)
        pages_extracted = i + 1

    full_text = "\n".join(parts)
    return {
        "url": url,
        "text": full_text,
        "pages_extracted": pages_extracted,
        "total_pages": total_pages,
        "truncated": pages_extracted < total_pages or len(full_text) >= max_chars,
    }


def get_adcom_documents(drug_name: str) -> dict:
    """
    Look for FDA advisory committee (AdCom) briefing documents for a drug.

    Searches the drug's FDA application submissions for advisory committee entries.
    AdCom docs contain the FDA's independent statistical review of clinical data.

    Note: coverage is incomplete — not all drugs go through AdCom, and docs may
    not always be linked in the openFDA API. Falls back to a search URL.
    """
    from ._http import get_json

    data = get_json(_OPENFDA_BASE, params={
        "search": f'(openfda.brand_name:"{drug_name}"+openfda.generic_name:"{drug_name}")',
        "limit": 3,
    })

    if isinstance(data, dict) and "error" in data:
        err = data.get("error", data)
        if isinstance(err, dict):
            return {"error": err.get("message", str(err)),
                    "fallback_url": f"https://www.fda.gov/advisory-committees/advisory-committee-calendar?search={drug_name}"}
        return {"error": str(err)}

    results = data.get("results", [])
    adcom_docs = []
    app_numbers = []

    for r in results:
        app_num = r.get("application_number", "")
        app_numbers.append(app_num)
        for sub in r.get("submissions", []):
            for doc in sub.get("application_docs", []):
                title = (doc.get("title") or "").lower()
                doc_type = (doc.get("type") or "").lower()
                if any(kw in title or kw in doc_type for kw in
                       ["advisory", "adcom", "committee", "briefing"]):
                    adcom_docs.append({
                        "url": doc.get("url"),
                        "title": doc.get("title"),
                        "type": doc.get("type"),
                        "submission_date": sub.get("submission_status_date"),
                    })

    return {
        "drug_name": drug_name,
        "application_numbers": app_numbers,
        "adcom_docs": adcom_docs,
        "doc_count": len(adcom_docs),
        "fallback_url": f"https://www.fda.gov/advisory-committees/advisory-committee-calendar?search={drug_name}",
        "note": "If no docs found, the drug may not have had an AdCom meeting, or docs may not be linked in openFDA. Use the fallback URL or web search.",
    }


def search_adverse_events(
    drug_name: str,
    serious: bool = None,
    max_results: int = 20,
) -> dict:
    """
    Search FDA Adverse Event Reporting System (FAERS) for post-market safety signals.

    Args:
        drug_name: Brand or generic drug name
        serious: If True, only serious events. If False, only non-serious. None = all.
        max_results: Max individual reports to return (default 20)

    Returns dict with:
        - total_reports: Total matching reports in FAERS
        - reports: List of individual adverse event reports
        - top_reactions: Aggregated count of most common reactions (top 20)
    """
    from ._http import get_json

    # Get aggregated reaction counts first
    count_search = f'patient.drug.medicinalproduct:"{drug_name}"'
    if serious is True:
        count_search += "+AND+serious:1"
    elif serious is False:
        count_search += "+AND+serious:2"

    agg_data = get_json(_FAERS_BASE, params={
        "search": count_search,
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": 20,
    })

    top_reactions = []
    if isinstance(agg_data, dict) and "results" in agg_data:
        top_reactions = [
            {"reaction": r.get("term"), "count": r.get("count")}
            for r in agg_data["results"]
        ]

    # Get individual reports
    report_data = get_json(_FAERS_BASE, params={
        "search": count_search,
        "limit": max_results,
    })

    if isinstance(report_data, dict) and "error" in report_data:
        err = report_data.get("error", report_data)
        if isinstance(err, dict):
            return {"error": err.get("message", str(err)), "top_reactions": top_reactions}
        return {"error": str(err), "top_reactions": top_reactions}

    total = report_data.get("meta", {}).get("results", {}).get("total", 0)
    reports = []
    for r in report_data.get("results", []):
        patient = r.get("patient", {})
        drugs = [
            {
                "name": d.get("medicinalproduct"),
                "indication": d.get("drugindication"),
                "role": d.get("drugcharacterization"),  # 1=suspect, 2=concomitant, 3=interacting
            }
            for d in patient.get("drug", [])
        ]
        reactions = [
            rx.get("reactionmeddrapt")
            for rx in patient.get("reaction", [])
        ]
        reports.append({
            "safety_report_id": r.get("safetyreportid"),
            "receive_date": r.get("receivedate"),
            "serious": r.get("serious"),
            "patient_sex": patient.get("patientsex"),
            "patient_age": patient.get("patientonsetage"),
            "patient_age_unit": patient.get("patientonsetageunit"),
            "reactions": reactions,
            "drugs": drugs,
            "outcome": r.get("patientdeath"),
        })

    return {
        "drug_name": drug_name,
        "total_reports": total,
        "top_reactions": top_reactions,
        "reports": reports,
    }


def get_drug_label(
    drug_name: str,
    max_results: int = 3,
) -> list[dict]:
    """
    Get FDA drug labeling (prescribing information) for approved drugs.

    Returns structured label sections: indications, contraindications, warnings,
    dosage, adverse reactions, clinical studies, etc.

    Useful for competitive analysis — compare what's approved vs. pipeline drugs.
    """
    from ._http import get_json

    search = f'(openfda.brand_name:"{drug_name}"+openfda.generic_name:"{drug_name}")'
    data = get_json(_LABEL_BASE, params={"search": search, "limit": max_results})

    if isinstance(data, dict) and "error" in data:
        err = data.get("error", data)
        if isinstance(err, dict):
            return [{"error": err.get("message", str(err))}]
        return [{"error": str(err)}]

    results = data.get("results", [])
    out = []
    for r in results:
        openfda = r.get("openfda", {})

        def _first(field):
            val = r.get(field, [])
            return val[0] if isinstance(val, list) and val else val if isinstance(val, str) else None

        out.append({
            "brand_name": openfda.get("brand_name", []),
            "generic_name": openfda.get("generic_name", []),
            "manufacturer": openfda.get("manufacturer_name", []),
            "application_number": openfda.get("application_number", []),
            "product_type": openfda.get("product_type", []),
            "route": openfda.get("route", []),
            "indications_and_usage": _first("indications_and_usage"),
            "contraindications": _first("contraindications"),
            "warnings_and_cautions": _first("warnings_and_cautions"),
            "boxed_warning": _first("boxed_warning"),
            "adverse_reactions": _first("adverse_reactions"),
            "drug_interactions": _first("drug_interactions"),
            "dosage_and_administration": _first("dosage_and_administration"),
            "clinical_studies": _first("clinical_studies"),
            "mechanism_of_action": _first("mechanism_of_action"),
            "clinical_pharmacology": _first("clinical_pharmacology"),
        })

    return out
