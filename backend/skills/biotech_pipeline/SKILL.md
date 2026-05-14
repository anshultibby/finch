---
name: biotech_pipeline
description: "Biotech research toolkit: clinical trials (ClinicalTrials.gov v2), FDA approvals + review doc PDFs with table extraction + FAERS adverse events + drug labels (openFDA), research papers (PubMed/PMC), disease landscape mapping, and company pipeline analysis. Use instead of web searches for FDA filings, Phase 1/2/3 trial data, PDUFA prep, safety signals, competitive landscape, and published efficacy results."
metadata:
  emoji: "🧬"
  category: biotech_research
  is_system: true
  auto_on: true
  requires:
    env: []
    bins:
      - pdfplumber
      - httpx
---

# Biotech Pipeline

Primary data sources for biotech research: clinical trials, FDA filings, and published papers. **Use this instead of web searches** for trial data, FDA review documents, and research paper results.

All APIs are free and keyless. 10 functions across 4 modules.

## Clinical Trials (ClinicalTrials.gov v2)

```python
from skills.biotech_pipeline.scripts.clinical_trials import search_trials, get_trial
```

### search_trials

```python
trials = search_trials(
    condition="non-small cell lung cancer",
    intervention="pembrolizumab",
    phase="PHASE3",              # PHASE1, PHASE2, PHASE3, PHASE4, EARLY_PHASE1
    status="COMPLETED",          # RECRUITING, COMPLETED, ACTIVE_NOT_RECRUITING, TERMINATED, WITHDRAWN
    sponsor="Merck",
    intervention_type=["DRUG", "BIOLOGICAL"],
    completion_date_range=("01/01/2025", "12/31/2025"),  # MM/DD/YYYY
    paginate=True,
    max_results=500,
)
# Returns list of: nct_id, title, status, sponsor, enrollment, interventions, phases
```

### get_trial — detail + results in one call

```python
trial = get_trial("NCT04280705")
# Returns: study_type, allocation, masking, enrollment, primary_outcomes, arms
# If trial['has_results']: outcomes[] with analyses (p_value, ci_lower, ci_upper) and measurements
# Also: adverse_events with serious_count, other_count
```

## FDA Data (openFDA + Review Document PDFs)

```python
from skills.biotech_pipeline.scripts.fda import (
    search_fda_approvals,
    get_application_docs,
    fetch_review_document,
    get_adcom_documents,
    search_adverse_events,
    get_drug_label,
)
```

```python
results = search_fda_approvals(drug_name="cytisinicline")  # or company="Achieve Life Sciences"
# Returns: application_number, brand_name, generic_name, submissions[]

docs = get_application_docs("NDA214611")
# Returns list of: type, title, url

review = fetch_review_document(doc_url, max_chars=50000)
# Returns: text, tables[] (page, data rows), pages_extracted, total_pages
# KEY: This is how to get Phase 1/2 data not published elsewhere — FDA reviewer re-analyzes all clinical data

adcom = get_adcom_documents("tebipenem")
# Returns: adcom_docs[] (title, url), doc_count, fallback_url

ae = search_adverse_events("pembrolizumab", serious=True, max_results=10)
# Returns: total_reports, top_reactions[] (reaction, count)

labels = get_drug_label("Keytruda")
# Returns list with: indications_and_usage, clinical_studies, warnings, dosage_and_administration
```

## PubMed / PMC (Research Papers)

```python
from skills.biotech_pipeline.scripts.pubmed import search_pubmed, get_full_text

papers = search_pubmed("cytisinicline ORCA Phase 3", max_results=5)
# Returns: pmid, title, journal, pub_date, abstract, has_full_text, pmc_id
# Tip: search "NCT04280705[si]" to find papers for a specific trial

paper = get_full_text("39012345", max_chars=80000)  # or "PMC10234567"
# Returns: sections[] (heading, text)
```

## Analysis (Disease Landscape + Company Pipeline)

```python
from skills.biotech_pipeline.scripts.analysis import get_disease_landscape, get_company_pipeline

landscape = get_disease_landscape("treatment resistant depression")
# Returns: total_active_trials, total_enrollment, by_phase (count + trials), top_sponsors
# Filtered to DRUG+BIOLOGICAL by default; pass intervention_type=[] for all

pipeline = get_company_pipeline(
    "Achieve Life Sciences",
    aliases=["Achieve Life Sciences, Inc.", "Extab Corporation"],
)
# Returns: total_trials, drugs[] (name, highest_phase, conditions, trials[])
```

## Data Source Priority

| Drug stage | Best source | Function chain |
|---|---|---|
| Phase 1/2, no NDA | ClinicalTrials.gov → PMC | `get_trial()` → `search_pubmed("NCT...[si]")` → `get_full_text()` |
| NDA filed, pre-PDUFA | FDA AdCom → ClinicalTrials.gov | `get_adcom_documents()` → `get_trial()` |
| Post-approval | FDA review package | `get_application_docs()` → `fetch_review_document()` |
| Published trial | PubMed full text | `search_pubmed()` → `get_full_text()` |
| Safety comparison | FAERS + labels | `search_adverse_events()` → `get_drug_label()` |
| Market sizing | Trial landscape | `get_disease_landscape()` |
| Company pipeline | ClinicalTrials.gov by sponsor | `get_company_pipeline()` |
| PDUFA candidates | Phase 3 completed recently | `search_trials(phase="PHASE3", status="COMPLETED", completion_date_range=(...))` |

## When to Use

- Analyzing drugs before PDUFA dates (get actual trial data, not blog summaries)
- Evaluating clinical trial statistical rigor (endpoints, p-values, enrollment)
- Reading FDA review documents for Phase 1/2 data not published elsewhere
- Mapping competitive landscape by condition
- Finding published efficacy data for a specific trial (via NCT ID)
- Comparing safety profiles of competing drugs (FAERS + labels)
- Building full company pipeline views from trial data

## When NOT to Use

- Stock fundamentals or financials (use financial_modeling_prep)
- Real-time market data (use polygon_io)
- General biotech news (use web search)
