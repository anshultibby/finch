"""
Biotech Pipeline - Clinical Trials, FDA, PubMed, Epidemiology, and Pipeline Mapping

CAPABILITIES:
- Search ClinicalTrials.gov for trials by condition, drug, sponsor, phase
- Get detailed trial info including endpoints, eligibility, posted results (p-values, CIs)
- Search FDA approvals and fetch full review documents (medical/statistical review PDFs)
- Query FAERS adverse event database for post-market safety signals
- Get FDA drug labels (prescribing info) for competitive analysis
- Search PubMed for research papers, get abstracts and PMC full text
- Link clinical trials to published papers via NCT ID
- Map disease landscapes: trial counts by phase, sponsors, total enrollment
- Search PubMed for prevalence/epidemiology data
- Build full company pipelines from clinical trial data
- Find PDUFA candidates by identifying late-stage completed trials

KEY MODULES:
- clinical_trials: ClinicalTrials.gov v2 API (trial search, detail, results)
- fda: openFDA (approvals, review docs, FAERS adverse events, drug labels)
- pubmed: PubMed/PMC (search, abstracts, full text)
- epidemiology: Disease landscape, prevalence search, market validation
- pipeline: Company pipeline mapping, PDUFA candidate detection

All APIs are free and keyless. Returns structured dicts. Errors return {"error": "..."}.
"""

from .clinical_trials import search_trials, get_trial_detail, get_trial_results
from .fda import (
    search_fda_approvals, get_application_docs, fetch_review_document,
    get_adcom_documents, search_adverse_events, get_drug_label,
)
from .pubmed import search_pubmed, get_abstract, get_full_text, search_by_nct
from .epidemiology import get_disease_landscape, search_prevalence, estimate_market_from_trials
from .pipeline import get_company_pipeline, get_pdufa_candidates

__all__ = [
    # Clinical trials
    "search_trials", "get_trial_detail", "get_trial_results",
    # FDA
    "search_fda_approvals", "get_application_docs", "fetch_review_document",
    "get_adcom_documents", "search_adverse_events", "get_drug_label",
    # PubMed
    "search_pubmed", "get_abstract", "get_full_text", "search_by_nct",
    # Epidemiology
    "get_disease_landscape", "search_prevalence", "estimate_market_from_trials",
    # Pipeline
    "get_company_pipeline", "get_pdufa_candidates",
]
