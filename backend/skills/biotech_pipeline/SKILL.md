---
name: biotech_pipeline
description: "Biotech research toolkit: clinical trials (ClinicalTrials.gov v2), FDA approvals + review doc PDFs + FAERS adverse events + drug labels (openFDA), research papers (PubMed/PMC), disease epidemiology/market sizing, and company pipeline mapping. Use instead of web searches for FDA filings, Phase 1/2/3 trial data, PDUFA prep, safety signals, competitive landscape, and published efficacy results."
metadata:
  emoji: "🧬"
  category: biotech_research
  is_system: true
  auto_on: true
  requires:
    env: []
    bins:
      - pypdf
      - httpx
---

# Biotech Pipeline

Primary data sources for biotech research: clinical trials, FDA filings, and published papers. **Use this instead of web searches** for trial data, FDA review documents, and research paper results.

All APIs are free and keyless.

## Clinical Trials (ClinicalTrials.gov v2)

```python
from skills.biotech_pipeline.scripts.clinical_trials import (
    search_trials,
    get_trial_detail,
    get_trial_results,
)
```

### Search for trials

```python
# Find Phase 3 trials for a drug
trials = search_trials(intervention="cytisinicline", phase="PHASE3")
for t in trials:
    print(f"{t['nct_id']} | {t['status']} | {t['sponsor']} | enrolled={t['enrollment']}")
    print(f"  {t['title']}")
    print(f"  Conditions: {t['conditions']}")

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
```

Phase values: `"PHASE1"`, `"PHASE2"`, `"PHASE3"`, `"PHASE4"`, `"EARLY_PHASE1"`
Status values: `"RECRUITING"`, `"COMPLETED"`, `"ACTIVE_NOT_RECRUITING"`, `"TERMINATED"`, `"WITHDRAWN"`

### Get trial detail (endpoints, design, eligibility)

```python
detail = get_trial_detail("NCT04280705")
print(f"Study type: {detail['study_type']}")
print(f"Allocation: {detail['allocation']}")
print(f"Masking: {detail['masking']}")

# Primary endpoints — what the trial is actually measuring
for ep in detail['primary_outcomes']:
    print(f"  PRIMARY: {ep['measure']} ({ep['time_frame']})")

# Secondary endpoints
for ep in detail['secondary_outcomes']:
    print(f"  SECONDARY: {ep['measure']}")

# Treatment arms
for arm in detail['arms']:
    print(f"  Arm: {arm['label']} ({arm['type']})")
```

### Get posted results (p-values, CIs, effect sizes)

```python
results = get_trial_results("NCT04280705")
if results['has_results']:
    for outcome in results['outcomes']:
        print(f"\n{outcome['type']}: {outcome['title']}")
        print(f"  Units: {outcome['units']}, Time frame: {outcome['time_frame']}")

        # Statistical analyses
        for a in outcome['analyses']:
            print(f"  p={a['p_value']}, CI=[{a['ci_lower']}, {a['ci_upper']}]")
            print(f"  Method: {a['method']}")

        # Group measurements
        for m in outcome['measurements']:
            print(f"  Group {m['group_id']}: {m['value']} ± {m['spread']}")

    # Adverse events
    ae = results.get('adverse_events')
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
    print(f"  Sponsor: {r['sponsor_name']}")
    for sub in r['submissions']:
        print(f"  {sub['submission_type']}-{sub['submission_number']} | {sub['submission_status']} | {sub['submission_status_date']}")
        print(f"    Docs: {len(sub['docs'])}")
```

### Get review documents for an application

```python
# Get all documents (medical review, statistical review, label, etc.)
docs = get_application_docs("NDA214611")
for d in docs:
    print(f"  [{d['type']}] {d['title']}")
    print(f"    URL: {d['url']}")
    print(f"    Submission: {d['submission_type']}-{d['submission_number']} ({d['submission_date']})")
```

### Read an FDA review document (PDF → text)

```python
# Download and extract text from a medical or statistical review PDF
review = fetch_review_document(doc_url, max_chars=50000)
if 'error' not in review:
    print(f"Pages: {review['pages_extracted']}/{review['total_pages']}")
    print(f"Truncated: {review['truncated']}")
    # The full text contains Phase 1/2/3 data, efficacy tables, safety data,
    # and the FDA reviewer's own analysis
    print(review['text'][:2000])
```

This is the key function for getting Phase 1 and Phase 2 data that isn't published anywhere else — the FDA reviewer re-analyzes all sponsor-submitted clinical data.

### Advisory committee documents

```python
adcom = get_adcom_documents("tebipenem")
if adcom['doc_count'] > 0:
    for d in adcom['adcom_docs']:
        print(f"  {d['title']} — {d['url']}")
else:
    # Not all drugs go through AdCom
    print(f"No AdCom docs found. Try: {adcom['fallback_url']}")
```

### Post-market safety signals (FAERS)

```python
# Check adverse event reports for a drug
ae = search_adverse_events("pembrolizumab", serious=True, max_results=10)
print(f"Total FAERS reports: {ae['total_reports']}")

# Top 20 most reported reactions — use for competitive safety comparison
for rx in ae['top_reactions']:
    print(f"  {rx['reaction']}: {rx['count']} reports")

# Individual case reports
for r in ae['reports']:
    print(f"  {r['safety_report_id']} | {r['reactions']} | serious={r['serious']}")
```

Use FAERS to compare safety profiles of competing drugs. If a new entrant has cleaner trial safety data than the incumbent's FAERS profile, that's a competitive advantage.

### Drug labels (prescribing information)

```python
# Get the approved label for competitive analysis
labels = get_drug_label("Keytruda")
for l in labels:
    print(f"Brand: {l['brand_name']}")
    print(f"Indications: {l['indications_and_usage'][:300]}...")
    print(f"Boxed warning: {l['boxed_warning'][:200] if l['boxed_warning'] else 'None'}")
    print(f"Mechanism: {l['mechanism_of_action'][:200]}...")
    # clinical_studies section has pivotal trial summaries
    print(f"Clinical studies: {l['clinical_studies'][:500]}...")
```

Labels contain the FDA-approved indications, contraindications, boxed warnings, adverse reactions, and clinical study summaries. Essential for comparing what's already approved vs. what's in the pipeline.

## PubMed / PMC (Research Papers)

```python
from skills.biotech_pipeline.scripts.pubmed import (
    search_pubmed,
    get_abstract,
    get_full_text,
    search_by_nct,
)
```

### Search for published trial results

```python
papers = search_pubmed("cytisinicline ORCA Phase 3 smoking cessation", max_results=5)
for p in papers:
    print(f"PMID:{p['pmid']} | {p['journal']} | {p['pub_date']}")
    print(f"  {p['title']}")
    print(f"  Full text available: {p['has_full_text']} (PMC: {p['pmc_id']})")
    if p['abstract']:
        print(f"  Abstract: {p['abstract'][:200]}...")
```

### Get a single abstract

```python
article = get_abstract("39012345")
print(article['title'])
print(article['abstract'])  # Structured: **BACKGROUND**: ... **METHODS**: ... **RESULTS**: ...
```

### Get full text (open access via PMC)

```python
# By PMID
paper = get_full_text("39012345", max_chars=80000)
# or by PMC ID directly
paper = get_full_text("PMC10234567")

if 'error' not in paper:
    print(f"PMC ID: {paper['pmc_id']}")
    print(f"Sections: {len(paper['sections'])}")
    for sec in paper['sections']:
        print(f"\n## {sec['heading']}")
        print(sec['text'][:500])
else:
    # Not open access — fall back to abstract
    print(paper['error'])
    print(paper.get('suggestion', ''))
```

### Find papers linked to a clinical trial

```python
# Search by NCT ID — finds published results for a specific trial
papers = search_by_nct("NCT04280705")
for p in papers:
    print(f"PMID:{p['pmid']} | {p['title']}")
```

## Disease Epidemiology & Market Sizing

```python
from skills.biotech_pipeline.scripts.epidemiology import (
    get_disease_landscape,
    search_prevalence,
    estimate_market_from_trials,
)
```

### Map the competitive landscape for a disease

```python
landscape = get_disease_landscape("treatment resistant depression")
print(f"Total active trials: {landscape['total_active_trials']}")
print(f"Total enrollment: {landscape['total_enrollment']}")

# Trials by phase — shows pipeline maturity
for phase, info in landscape['by_phase'].items():
    print(f"\n{phase}: {info['count']} trials")
    for t in info['trials'][:3]:
        print(f"  {t['sponsor']}: {', '.join(t['interventions'])} (n={t['enrollment']})")

# Top sponsors — who's investing most
for sponsor, count in landscape['top_sponsors'][:10]:
    print(f"  {sponsor}: {count} trials")
```

### Find prevalence/epidemiology data

```python
# Search PubMed for review articles on patient population size
papers = search_prevalence("spinal muscular atrophy")
for p in papers:
    print(f"PMID:{p['pmid']} | {p['title']}")
    # Read the abstracts for actual numbers like "prevalence of 1 in 10,000"
    print(f"  {p['abstract'][:300]}...")
```

### Quick market validation from trial signals

```python
market = estimate_market_from_trials("non-obstructive hypertrophic cardiomyopathy")
print(f"Signal: {market['market_signal']}")  # LARGE_VALIDATED, VALIDATED, EMERGING, EARLY_NICHE, NO_ACTIVITY
print(f"Rationale: {market['rationale']}")
print(f"Phase counts: {market['phase_counts']}")
print(f"Unique sponsors: {market['unique_sponsors']}")
```

## Company Pipeline Mapping

```python
from skills.biotech_pipeline.scripts.pipeline import (
    get_company_pipeline,
    get_pdufa_candidates,
)
```

### Build a full pipeline view

```python
# Micro-caps often use different legal names as trial sponsors
pipeline = get_company_pipeline(
    "Achieve Life Sciences",
    aliases=["Achieve Life Sciences, Inc.", "Extab Corporation"],
)
print(f"Total trials: {pipeline['total_trials']}")
print(f"Pipeline: {pipeline['pipeline_summary']}")

for drug in pipeline['drugs']:
    print(f"\n{drug['name']} — {drug['highest_phase']}")
    print(f"  Conditions: {drug['conditions']}")
    print(f"  Trials: {drug['trial_count']}")
    for t in drug['trials']:
        print(f"    {t['nct_id']} | {t['status']} | n={t['enrollment']}")
```

### Find PDUFA candidates (late-stage completed Phase 3)

```python
# For a specific company
candidates = get_pdufa_candidates("Spero Therapeutics")
for c in candidates:
    print(f"{c['nct_id']} | {', '.join(c['drugs'])} | {c['status']}")
    print(f"  Conditions: {c['conditions']}")
    print(f"  Completion: {c['completion_date']} | Results posted: {c['has_results']}")

# Broad scan: recently completed Phase 3 trials across all sponsors
candidates = get_pdufa_candidates()
```

## Compound Workflows

### Pre-NDA drug analysis (PDUFA watchlist use case)

```python
from skills.biotech_pipeline.scripts.clinical_trials import search_trials, get_trial_detail, get_trial_results
from skills.biotech_pipeline.scripts.pubmed import search_by_nct, get_full_text

drug = "cytisinicline"

# 1. Find the pivotal trials
trials = search_trials(intervention=drug, phase="PHASE3", status="COMPLETED")

for t in trials:
    nct = t['nct_id']
    detail = get_trial_detail(nct)

    # 2. Get primary endpoints and statistical design
    print(f"\n=== {nct}: {detail['title']} ===")
    print(f"Enrollment: {detail['enrollment']} | Design: {detail['allocation']}, {detail['masking']}")
    for ep in detail['primary_outcomes']:
        print(f"  Primary: {ep['measure']}")

    # 3. Get posted results (p-values, effect sizes)
    results = get_trial_results(nct)
    if results['has_results']:
        for outcome in results['outcomes']:
            for a in outcome['analyses']:
                print(f"  p={a['p_value']}, method={a['method']}")

    # 4. Find published papers for this trial
    papers = search_by_nct(nct)
    for p in papers:
        print(f"  Paper: {p['title']} ({p['journal']})")
        if p['has_full_text']:
            full = get_full_text(p['pmc_id'])
            # Now you have the actual paper with Methods, Results, Discussion
```

### FDA review deep dive (Phase 1/2 data from filings)

```python
from skills.biotech_pipeline.scripts.fda import search_fda_approvals, get_application_docs, fetch_review_document

# 1. Find the NDA
approvals = search_fda_approvals(drug_name="CARDAMYST")
app_num = approvals[0]['application_number']

# 2. Get review documents
docs = get_application_docs(app_num)

# 3. Read the medical review (contains Phase 1/2/3 data)
medical_reviews = [d for d in docs if 'review' in (d['title'] or '').lower()]
for doc in medical_reviews:
    review = fetch_review_document(doc['url'], max_chars=80000)
    print(f"\n=== {doc['title']} ({review['pages_extracted']} pages) ===")
    # Search for efficacy data, dose-response, Phase 1 PK data, etc.
    text = review['text']
    # The agent can now analyze the actual FDA review
```

### Competitive landscape for a condition

```python
from skills.biotech_pipeline.scripts.clinical_trials import search_trials

# Find all active trials for a condition across phases
for phase in ["PHASE1", "PHASE2", "PHASE3"]:
    trials = search_trials(condition="treatment resistant depression", phase=phase, max_results=50)
    active = [t for t in trials if t['status'] in ('RECRUITING', 'ACTIVE_NOT_RECRUITING')]
    print(f"\n{phase}: {len(active)} active trials")
    for t in active:
        print(f"  {t['sponsor']}: {t['interventions'][0]['name'] if t['interventions'] else '?'} (n={t['enrollment']})")
```

### Full competitive due diligence

```python
from skills.biotech_pipeline.scripts.epidemiology import get_disease_landscape, search_prevalence, estimate_market_from_trials
from skills.biotech_pipeline.scripts.fda import search_adverse_events, get_drug_label
from skills.biotech_pipeline.scripts.clinical_trials import search_trials, get_trial_results

condition = "PSVT"  # paroxysmal supraventricular tachycardia

# 1. Market validation
market = estimate_market_from_trials(condition)
prevalence = search_prevalence(condition)

# 2. Competitive landscape
landscape = get_disease_landscape(condition)

# 3. Safety comparison of existing treatments
for approved_drug in ["adenosine", "verapamil"]:
    ae = search_adverse_events(approved_drug, serious=True)
    label = get_drug_label(approved_drug)
    # Compare safety profiles

# 4. Pipeline company analysis
from skills.biotech_pipeline.scripts.pipeline import get_company_pipeline
pipeline = get_company_pipeline("Milestone Pharmaceuticals")
```

## Data Source Priority

| Drug stage | Best source | Function |
|---|---|---|
| Phase 1/2, no NDA | ClinicalTrials.gov results → PMC papers | `get_trial_results()` → `search_by_nct()` → `get_full_text()` |
| NDA filed, pre-PDUFA | FDA AdCom briefing → ClinicalTrials.gov | `get_adcom_documents()` → `get_trial_results()` |
| Post-approval | FDA review package (has everything) | `get_application_docs()` → `fetch_review_document()` |
| Published trial | PubMed full text | `search_pubmed()` → `get_full_text()` |
| Safety comparison | FAERS + labels | `search_adverse_events()` → `get_drug_label()` |
| Market sizing | Epi papers + trial landscape | `search_prevalence()` → `get_disease_landscape()` |
| Company pipeline | ClinicalTrials.gov by sponsor | `get_company_pipeline()` → `get_pdufa_candidates()` |

## When to Use

- Analyzing drugs before PDUFA dates (get actual trial data, not blog summaries)
- Evaluating clinical trial statistical rigor (endpoints, p-values, enrollment)
- Reading FDA review documents for Phase 1/2 data not published elsewhere
- Mapping competitive landscape by condition (how many trials, who's ahead)
- Finding published efficacy data for a specific trial (via NCT ID)
- Market sizing by seeing how many active trials target a condition
- Comparing safety profiles of competing drugs (FAERS + labels)
- Building full company pipeline views from trial data
- Finding late-stage PDUFA candidates

## When NOT to Use

- Stock fundamentals or financials (use financial_modeling_prep)
- Real-time market data (use polygon_io)
- General biotech news (use web search)
- Non-pharma clinical research
