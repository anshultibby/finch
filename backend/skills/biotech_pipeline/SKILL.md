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

### Search for trials

```python
# Find Phase 3 trials for a drug
trials = search_trials(intervention="cytisinicline", phase="PHASE3")
for t in trials:
    print(f"{t['nct_id']} | {t['status']} | {t['sponsor']} | enrolled={t['enrollment']}")

# Find all recruiting trials for a disease
trials = search_trials(condition="spinal muscular atrophy", status="RECRUITING")

# Find trials by sponsor
trials = search_trials(sponsor="Achieve Life Sciences", phase="PHASE3")

# Combine filters
trials = search_trials(
    condition="non-small cell lung cancer",
    intervention="pembrolizumab",
    phase="PHASE3",
    status="COMPLETED",
    max_results=10,
)

# Filter by intervention type (exclude devices/behavioral)
trials = search_trials(
    condition="depression",
    intervention_type=["DRUG", "BIOLOGICAL"],
    max_results=50,
)

# Search by completion date range (MM/DD/YYYY format)
trials = search_trials(
    phase="PHASE3",
    status="COMPLETED",
    completion_date_range=("01/01/2025", "12/31/2025"),
)

# Paginated search (follows nextPageToken, capped at 1000)
trials = search_trials(
    condition="breast cancer",
    paginate=True,
    max_results=500,
)
```

Phase values: `"PHASE1"`, `"PHASE2"`, `"PHASE3"`, `"PHASE4"`, `"EARLY_PHASE1"`
Status values: `"RECRUITING"`, `"COMPLETED"`, `"ACTIVE_NOT_RECRUITING"`, `"TERMINATED"`, `"WITHDRAWN"`

### Get trial detail + results (single call)

```python
# One call gets design, eligibility, endpoints, arms, AND posted results
trial = get_trial("NCT04280705")
print(f"Study type: {trial['study_type']}")
print(f"Design: {trial['allocation']}, {trial['masking']}")

# Primary endpoints
for ep in trial['primary_outcomes']:
    print(f"  PRIMARY: {ep['measure']} ({ep['time_frame']})")

# Arms
for arm in trial['arms']:
    print(f"  Arm: {arm['label']} ({arm['type']})")

# Posted results (p-values, CIs, effect sizes)
if trial['has_results']:
    for outcome in trial['outcomes']:
        print(f"\n{outcome['type']}: {outcome['title']}")
        print(f"  Units: {outcome['units']}, Time frame: {outcome['time_frame']}")
        for a in outcome['analyses']:
            print(f"  p={a['p_value']}, CI=[{a['ci_lower']}, {a['ci_upper']}]")
        for m in outcome['measurements']:
            print(f"  Group {m['group_id']}: {m['value']} ± {m['spread']}")

    # Adverse events
    ae = trial.get('adverse_events')
    if ae:
        print(f"\nSerious AEs: {ae['serious_count']}, Other AEs: {ae['other_count']}")
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

### Search approved drugs

```python
results = search_fda_approvals(drug_name="cytisinicline")
# or by company
results = search_fda_approvals(company="Achieve Life Sciences")

for r in results:
    print(f"{r['application_number']} | {r['brand_name']} | {r['generic_name']}")
    for sub in r['submissions']:
        print(f"  {sub['submission_type']}-{sub['submission_number']} | {sub['submission_status']}")
```

### Get review documents for an application

```python
docs = get_application_docs("NDA214611")
for d in docs:
    print(f"  [{d['type']}] {d['title']} — {d['url']}")
```

### Read an FDA review document (PDF → text + tables)

```python
review = fetch_review_document(doc_url, max_chars=50000)
if 'error' not in review:
    print(f"Pages: {review['pages_extracted']}/{review['total_pages']}")
    print(review['text'][:2000])

    # Extracted tables (efficacy data, demographics, endpoints)
    for table in review['tables']:
        print(f"\nTable on page {table['page']}:")
        for row in table['data'][:3]:
            print(f"  {row}")
```

This is the key function for getting Phase 1 and Phase 2 data that isn't published anywhere else — the FDA reviewer re-analyzes all sponsor-submitted clinical data. Tables contain structured efficacy and safety data.

### Advisory committee documents

```python
adcom = get_adcom_documents("tebipenem")
if adcom['doc_count'] > 0:
    for d in adcom['adcom_docs']:
        print(f"  {d['title']} — {d['url']}")
else:
    print(f"No AdCom docs. Try: {adcom['fallback_url']}")
```

### Post-market safety signals (FAERS)

```python
ae = search_adverse_events("pembrolizumab", serious=True, max_results=10)
print(f"Total FAERS reports: {ae['total_reports']}")
for rx in ae['top_reactions']:
    print(f"  {rx['reaction']}: {rx['count']} reports")
```

### Drug labels (prescribing information)

```python
labels = get_drug_label("Keytruda")
for l in labels:
    print(f"Indications: {l['indications_and_usage'][:300]}...")
    print(f"Clinical studies: {l['clinical_studies'][:500]}...")
```

## PubMed / PMC (Research Papers)

```python
from skills.biotech_pipeline.scripts.pubmed import search_pubmed, get_full_text
```

### Search for published trial results

```python
papers = search_pubmed("cytisinicline ORCA Phase 3 smoking cessation", max_results=5)
for p in papers:
    print(f"PMID:{p['pmid']} | {p['journal']} | {p['pub_date']}")
    print(f"  {p['title']}")
    if p['abstract']:
        print(f"  {p['abstract'][:200]}...")

# Find papers for a specific trial (use NCT ID as search term)
papers = search_pubmed("NCT04280705[si]", max_results=5)

# Get a single abstract (use PMID as search term)
papers = search_pubmed("39012345[pmid]", max_results=1)
```

### Get full text (open access via PMC)

```python
paper = get_full_text("39012345", max_chars=80000)
# or by PMC ID
paper = get_full_text("PMC10234567")

if 'error' not in paper:
    for sec in paper['sections']:
        print(f"\n## {sec['heading']}")
        print(sec['text'][:500])
```

## Analysis (Disease Landscape + Company Pipeline)

```python
from skills.biotech_pipeline.scripts.analysis import get_disease_landscape, get_company_pipeline
```

### Map the competitive landscape for a disease

```python
# Paginated, filtered to DRUG+BIOLOGICAL by default
landscape = get_disease_landscape("treatment resistant depression")
print(f"Total active trials: {landscape['total_active_trials']}")
print(f"Total enrollment: {landscape['total_enrollment']}")

for phase, info in landscape['by_phase'].items():
    print(f"\n{phase}: {info['count']} trials")
    for t in info['trials'][:3]:
        print(f"  {t['sponsor']}: {', '.join(t['interventions'])} (n={t['enrollment']})")

for sponsor, count in landscape['top_sponsors'][:10]:
    print(f"  {sponsor}: {count} trials")

# Include all intervention types
landscape = get_disease_landscape("depression", intervention_type=[])
```

### Build a full company pipeline view

```python
pipeline = get_company_pipeline(
    "Achieve Life Sciences",
    aliases=["Achieve Life Sciences, Inc.", "Extab Corporation"],
)
print(f"Total trials: {pipeline['total_trials']}")
for drug in pipeline['drugs']:
    print(f"\n{drug['name']} — {drug['highest_phase']}")
    print(f"  Conditions: {drug['conditions']}")
    for t in drug['trials']:
        print(f"    {t['nct_id']} | {t['status']} | n={t['enrollment']}")
```

## Compound Workflows

### Pre-NDA drug analysis

```python
from skills.biotech_pipeline.scripts.clinical_trials import search_trials, get_trial
from skills.biotech_pipeline.scripts.pubmed import search_pubmed, get_full_text

drug = "cytisinicline"

# 1. Find pivotal trials
trials = search_trials(intervention=drug, phase="PHASE3", status="COMPLETED")

for t in trials:
    # 2. Get detail + results in one call
    full = get_trial(t['nct_id'])
    print(f"\n=== {full['nct_id']}: {full['title']} ===")
    print(f"Enrollment: {full['enrollment']} | Design: {full['allocation']}, {full['masking']}")

    if full['has_results']:
        for outcome in full['outcomes']:
            for a in outcome['analyses']:
                print(f"  p={a['p_value']}, method={a['method']}")

    # 3. Find published papers
    papers = search_pubmed(f"{t['nct_id']}[si]")
    for p in papers:
        if p.get('has_full_text'):
            text = get_full_text(p['pmc_id'])
```

### FDA review deep dive

```python
from skills.biotech_pipeline.scripts.fda import search_fda_approvals, get_application_docs, fetch_review_document

approvals = search_fda_approvals(drug_name="CARDAMYST")
app_num = approvals[0]['application_number']
docs = get_application_docs(app_num)
medical_reviews = [d for d in docs if 'review' in (d['title'] or '').lower()]
for doc in medical_reviews:
    review = fetch_review_document(doc['url'], max_chars=80000)
    # review['text'] has Phase 1/2/3 data
    # review['tables'] has structured efficacy/safety tables
```

### Find PDUFA candidates (replaces get_pdufa_candidates)

```python
from skills.biotech_pipeline.scripts.clinical_trials import search_trials

# Phase 3 completed in the last year — likely near NDA/PDUFA
candidates = search_trials(
    sponsor="Spero Therapeutics",
    phase="PHASE3",
    status="COMPLETED",
    completion_date_range=("01/01/2025", "12/31/2025"),
)
```

## Data Source Priority

| Drug stage | Best source | Function |
|---|---|---|
| Phase 1/2, no NDA | ClinicalTrials.gov results → PMC papers | `get_trial()` → `search_pubmed("NCT...[si]")` → `get_full_text()` |
| NDA filed, pre-PDUFA | FDA AdCom → ClinicalTrials.gov | `get_adcom_documents()` → `get_trial()` |
| Post-approval | FDA review package (has everything) | `get_application_docs()` → `fetch_review_document()` |
| Published trial | PubMed full text | `search_pubmed()` → `get_full_text()` |
| Safety comparison | FAERS + labels | `search_adverse_events()` → `get_drug_label()` |
| Market sizing | Trial landscape | `get_disease_landscape()` |
| Company pipeline | ClinicalTrials.gov by sponsor | `get_company_pipeline()` |
| PDUFA candidates | Phase 3 completed recently | `search_trials(phase="PHASE3", status="COMPLETED", completion_date_range=(...))` |

## When to Use

- Analyzing drugs before PDUFA dates (get actual trial data, not blog summaries)
- Evaluating clinical trial statistical rigor (endpoints, p-values, enrollment)
- Reading FDA review documents for Phase 1/2 data not published elsewhere
- Mapping competitive landscape by condition (how many trials, who's ahead)
- Finding published efficacy data for a specific trial (via NCT ID)
- Market sizing by seeing how many active trials target a condition
- Comparing safety profiles of competing drugs (FAERS + labels)
- Building full company pipeline views from trial data

## When NOT to Use

- Stock fundamentals or financials (use financial_modeling_prep)
- Real-time market data (use polygon_io)
- General biotech news (use web search)
- Non-pharma clinical research
