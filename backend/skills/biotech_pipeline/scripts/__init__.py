"""
Biotech Pipeline - Clinical Trials, FDA, PubMed, and Analysis

CAPABILITIES:
- Search ClinicalTrials.gov for trials by condition, drug, sponsor, phase, date range
- Get full trial detail + posted results (p-values, CIs) in one call
- Search FDA approvals and fetch review documents with table extraction
- Query FAERS adverse event database for post-market safety signals
- Get FDA drug labels (prescribing info) for competitive analysis
- Search PubMed for research papers, get full text from PMC
- Map disease landscapes with pagination and intervention type filtering
- Build full company pipelines from clinical trial data

KEY MODULES:
- clinical_trials: ClinicalTrials.gov v2 API (search + detail/results)
- fda: openFDA (approvals, review docs with tables, FAERS, drug labels)
- pubmed: PubMed/PMC (search, full text)
- analysis: Disease landscape, company pipeline mapping

All APIs are free and keyless. Returns structured dicts. Errors return {"error": "..."}.
"""

from .clinical_trials import search_trials, get_trial
from .fda import (
    search_fda_approvals, get_application_docs, fetch_review_document,
    get_adcom_documents, search_adverse_events, get_drug_label,
)
from .pubmed import search_pubmed, get_full_text
from .analysis import get_disease_landscape, get_company_pipeline

__all__ = [
    # Clinical trials
    "search_trials", "get_trial",
    # FDA
    "search_fda_approvals", "get_application_docs", "fetch_review_document",
    "get_adcom_documents", "search_adverse_events", "get_drug_label",
    # PubMed
    "search_pubmed", "get_full_text",
    # Analysis
    "get_disease_landscape", "get_company_pipeline",
]
