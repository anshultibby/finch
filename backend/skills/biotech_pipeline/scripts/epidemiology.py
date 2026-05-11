"""Disease epidemiology and market sizing using ClinicalTrials.gov as a proxy + PubMed prevalence data."""


def get_disease_landscape(condition: str, max_trials: int = 100) -> dict:
    """
    Map the competitive landscape for a disease by counting active trials across phases.

    Uses ClinicalTrials.gov to answer: How many drugs are being developed for this
    condition? What phase are they in? Who are the sponsors? How big is enrollment?

    This is a proxy for market interest — more trials = more validated the target.

    Returns:
        {
            "condition": str,
            "total_trials": int,
            "by_phase": {"PHASE1": [...], "PHASE2": [...], "PHASE3": [...]},
            "by_sponsor": {"Pfizer": 5, ...},
            "total_enrollment": int,
            "active_interventions": [{"name": str, "phase": str, "sponsor": str, "enrollment": int}],
        }
    """
    from ._http import get_json

    base = "https://clinicaltrials.gov/api/v2/studies"
    active_statuses = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING"

    params = {
        "query.cond": condition,
        "filter.overallStatus": active_statuses,
        "pageSize": min(max_trials, 100),
        "format": "json",
    }

    data = get_json(base, params=params)
    if isinstance(data, dict) and "error" in data:
        return data

    studies = data.get("studies", [])
    by_phase = {"EARLY_PHASE1": [], "PHASE1": [], "PHASE2": [], "PHASE3": [], "PHASE4": [], "NA": []}
    by_sponsor = {}
    total_enrollment = 0
    active_interventions = []

    for s in studies:
        proto = s.get("protocolSection", {})
        design = proto.get("designModule", {})
        ident = proto.get("identificationModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        arms = proto.get("armsInterventionsModule", {})

        phases = design.get("phases", ["NA"])
        enrollment = design.get("enrollmentInfo", {}).get("count", 0) or 0
        total_enrollment += enrollment
        sponsor_name = sponsor_mod.get("leadSponsor", {}).get("name", "Unknown")
        nct_id = ident.get("nctId")
        title = ident.get("briefTitle")

        by_sponsor[sponsor_name] = by_sponsor.get(sponsor_name, 0) + 1

        interventions = arms.get("interventions", [])
        drug_names = [i.get("name") for i in interventions if i.get("type") in ("DRUG", "BIOLOGICAL")]

        entry = {
            "nct_id": nct_id,
            "title": title,
            "sponsor": sponsor_name,
            "enrollment": enrollment,
            "interventions": drug_names,
        }

        for phase in phases:
            phase_key = phase if phase in by_phase else "NA"
            by_phase[phase_key].append(entry)

        for drug in drug_names:
            active_interventions.append({
                "name": drug,
                "phase": phases,
                "sponsor": sponsor_name,
                "enrollment": enrollment,
                "nct_id": nct_id,
            })

    # Clean empty phases
    by_phase = {k: v for k, v in by_phase.items() if v}
    # Sort sponsors by count
    top_sponsors = sorted(by_sponsor.items(), key=lambda x: -x[1])

    return {
        "condition": condition,
        "total_active_trials": len(studies),
        "total_enrollment": total_enrollment,
        "by_phase": {k: {"count": len(v), "trials": v} for k, v in by_phase.items()},
        "top_sponsors": top_sponsors[:20],
        "active_interventions": active_interventions,
    }


def search_prevalence(condition: str, max_results: int = 5) -> list[dict]:
    """
    Search PubMed for epidemiology/prevalence studies on a condition.

    Returns papers focused on incidence, prevalence, and disease burden —
    the best structured source for patient population estimates.

    The agent should read the abstracts for actual numbers (e.g., "prevalence of 1 in 10,000"
    or "estimated 500,000 patients in the US").
    """
    from .pubmed import search_pubmed

    query = f'({condition}) AND (prevalence OR incidence OR epidemiology OR "disease burden" OR "patient population") AND (review[pt] OR meta-analysis[pt])'
    return search_pubmed(query, max_results=max_results)


def estimate_market_from_trials(condition: str) -> dict:
    """
    Rough market validation using trial data as signals.

    Logic:
    - Phase 3 trial exists → validated target, likely >$500M TAM
    - Multiple Phase 3 sponsors → large market, competitive
    - Total enrollment across trials → proportional to addressable population
    - Only 1-2 Phase 1/2 → early/niche or novel mechanism

    Returns a structured assessment the agent can combine with prevalence data.
    """
    landscape = get_disease_landscape(condition)
    if "error" in landscape:
        return landscape

    phase_counts = {}
    for phase, info in landscape.get("by_phase", {}).items():
        phase_counts[phase] = info["count"]

    p3 = phase_counts.get("PHASE3", 0)
    p2 = phase_counts.get("PHASE2", 0)
    p1 = phase_counts.get("PHASE1", 0)
    total = landscape["total_active_trials"]
    unique_sponsors = len(landscape["top_sponsors"])

    if p3 >= 3:
        market_signal = "LARGE_VALIDATED"
        rationale = f"{p3} Phase 3 trials from {unique_sponsors} sponsors — well-validated large market"
    elif p3 >= 1:
        market_signal = "VALIDATED"
        rationale = f"{p3} Phase 3 trial(s) — target validated, market established"
    elif p2 >= 3:
        market_signal = "EMERGING"
        rationale = f"{p2} Phase 2 trials, no Phase 3 yet — emerging but unproven market"
    elif total >= 1:
        market_signal = "EARLY_NICHE"
        rationale = f"Only Phase 1/2 trials ({total} total) — early stage or niche indication"
    else:
        market_signal = "NO_ACTIVITY"
        rationale = "No active trials found — either fully addressed or too niche"

    return {
        "condition": condition,
        "market_signal": market_signal,
        "rationale": rationale,
        "phase_counts": phase_counts,
        "total_trials": total,
        "unique_sponsors": unique_sponsors,
        "total_enrollment": landscape["total_enrollment"],
        "top_sponsors": landscape["top_sponsors"][:10],
    }
