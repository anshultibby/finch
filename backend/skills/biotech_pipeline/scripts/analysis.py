"""Aggregate analysis: disease landscape and company pipeline mapping."""


def get_disease_landscape(
    condition: str,
    intervention_type: list[str] = None,
    max_trials: int = 500,
) -> dict:
    """
    Map the competitive landscape for a disease by counting active trials across phases.

    Uses ClinicalTrials.gov to answer: How many drugs are being developed for this
    condition? What phase are they in? Who are the sponsors? How big is enrollment?

    Args:
        condition: Disease or condition (e.g., "treatment resistant depression")
        intervention_type: Filter by type, default ["DRUG", "BIOLOGICAL"].
                          Set to None or [] to include all types.
        max_trials: Max trials to fetch with pagination (default 500, capped at 1000)

    Returns:
        {
            "condition": str,
            "total_active_trials": int,
            "total_enrollment": int,
            "by_phase": {"PHASE1": {"count": int, "trials": [...]}, ...},
            "top_sponsors": [(name, count), ...],
            "active_interventions": [{"name": str, "phase": str, "sponsor": str, ...}],
        }
    """
    from .clinical_trials import search_trials

    if intervention_type is None:
        intervention_type = ["DRUG", "BIOLOGICAL"]

    active_statuses = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING"

    trials = search_trials(
        condition=condition,
        status=active_statuses,
        intervention_type=intervention_type if intervention_type else None,
        max_results=min(max_trials, 1000),
        paginate=True,
    )

    if trials and isinstance(trials[0], dict) and "error" in trials[0]:
        return trials[0]

    by_phase = {"EARLY_PHASE1": [], "PHASE1": [], "PHASE2": [], "PHASE3": [], "PHASE4": [], "NA": []}
    by_sponsor = {}
    total_enrollment = 0
    active_interventions = []

    for t in trials:
        phases = t.get("phase", ["NA"])
        enrollment = t.get("enrollment", 0) or 0
        total_enrollment += enrollment
        sponsor_name = t.get("sponsor", "Unknown")

        by_sponsor[sponsor_name] = by_sponsor.get(sponsor_name, 0) + 1

        drug_names = [i["name"] for i in t.get("interventions", [])
                      if not intervention_type or i.get("type") in intervention_type]

        entry = {
            "nct_id": t.get("nct_id"),
            "title": t.get("title"),
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
                "nct_id": t.get("nct_id"),
            })

    by_phase = {k: v for k, v in by_phase.items() if v}
    top_sponsors = sorted(by_sponsor.items(), key=lambda x: -x[1])

    return {
        "condition": condition,
        "total_active_trials": len(trials),
        "total_enrollment": total_enrollment,
        "by_phase": {k: {"count": len(v), "trials": v} for k, v in by_phase.items()},
        "top_sponsors": top_sponsors[:20],
        "active_interventions": active_interventions,
    }


def get_company_pipeline(
    company: str,
    aliases: list[str] = None,
    include_completed: bool = False,
    max_results: int = 100,
) -> dict:
    """
    Build a full clinical pipeline view for a company.

    Micro-cap biotechs often use different names as sponsors (legal entity vs.
    trading name). Pass aliases to catch them all.

    Args:
        company: Primary company name (e.g., "Achieve Life Sciences")
        aliases: Optional list of alternate sponsor names to also search
        include_completed: Include completed trials (default False — active only)
        max_results: Max trials per search (default 100)

    Returns:
        {
            "company": str,
            "aliases_searched": [str],
            "pipeline_summary": {"PHASE1": int, ...},
            "total_trials": int,
            "drugs": [{"name": str, "conditions": [...], "highest_phase": str, ...}],
        }
    """
    from .clinical_trials import search_trials

    names = [company] + (aliases or [])
    status = None
    if not include_completed:
        status = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING,COMPLETED"

    all_trials = []
    seen_ncts = set()

    for name in names:
        trials = search_trials(
            sponsor=name,
            status=status,
            max_results=min(max_results, 100),
        )
        if trials and isinstance(trials[0], dict) and "error" in trials[0]:
            continue
        for t in trials:
            nct = t.get("nct_id")
            if nct and nct not in seen_ncts:
                seen_ncts.add(nct)
                all_trials.append(t)

    drug_map = {}
    phase_counts = {}

    for t in all_trials:
        phases = t.get("phase", [])
        conditions = t.get("conditions", [])
        drug_names = [
            i["name"] for i in t.get("interventions", [])
            if i.get("type") in ("DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT")
        ]
        if not drug_names:
            drug_names = ["(other/device)"]

        for phase in phases:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        for drug in drug_names:
            if drug not in drug_map:
                drug_map[drug] = {"conditions": set(), "phases": set(), "trials": []}
            drug_map[drug]["conditions"].update(conditions)
            drug_map[drug]["phases"].update(phases)
            drug_map[drug]["trials"].append({
                "nct_id": t.get("nct_id"),
                "title": t.get("title"),
                "phase": phases,
                "status": t.get("status"),
                "enrollment": t.get("enrollment"),
                "conditions": conditions,
            })

    drugs = []
    phase_order = ["PHASE4", "PHASE3", "PHASE2", "PHASE1", "EARLY_PHASE1"]
    for name, info in sorted(drug_map.items(), key=lambda x: -len(x[1]["trials"])):
        highest_phase = "EARLY_PHASE1"
        for p in phase_order:
            if p in info["phases"]:
                highest_phase = p
                break
        drugs.append({
            "name": name,
            "conditions": sorted(info["conditions"]),
            "highest_phase": highest_phase,
            "all_phases": sorted(info["phases"]),
            "trial_count": len(info["trials"]),
            "trials": info["trials"],
        })

    return {
        "company": company,
        "aliases_searched": names,
        "pipeline_summary": phase_counts,
        "total_trials": len(all_trials),
        "drugs": drugs,
    }
