"""Company pipeline mapping: sponsor → all trials, with phase/status breakdown."""


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
            "pipeline_summary": {"PHASE1": int, "PHASE2": int, "PHASE3": int, ...},
            "drugs": [{"name": str, "conditions": [...], "phase": str, "trials": [...]}],
            "total_trials": int,
        }
    """
    from ._http import get_json

    base = "https://clinicaltrials.gov/api/v2/studies"
    names = [company] + (aliases or [])

    all_studies = []
    seen_ncts = set()

    for name in names:
        params = {
            "query.spons": name,
            "pageSize": min(max_results, 100),
            "format": "json",
        }
        if not include_completed:
            params["filter.overallStatus"] = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING,COMPLETED"

        data = get_json(base, params=params)
        if isinstance(data, dict) and "error" in data:
            continue

        for s in data.get("studies", []):
            nct = s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
            if nct and nct not in seen_ncts:
                seen_ncts.add(nct)
                all_studies.append(s)

    # Group by drug
    drug_map = {}  # drug_name -> {conditions, phases, trials}
    phase_counts = {}

    for s in all_studies:
        proto = s.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        design = proto.get("designModule", {})
        status_mod = proto.get("statusModule", {})
        conditions_mod = proto.get("conditionsModule", {})
        arms = proto.get("armsInterventionsModule", {})

        nct_id = ident.get("nctId")
        title = ident.get("briefTitle")
        phases = design.get("phases", [])
        status = status_mod.get("overallStatus")
        conditions = conditions_mod.get("conditions", [])
        enrollment = design.get("enrollmentInfo", {}).get("count")

        interventions = arms.get("interventions", [])
        drug_names = [
            i.get("name") for i in interventions
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
                "nct_id": nct_id,
                "title": title,
                "phase": phases,
                "status": status,
                "enrollment": enrollment,
                "conditions": conditions,
            })

    drugs = []
    for name, info in sorted(drug_map.items(), key=lambda x: -len(x[1]["trials"])):
        highest_phase = "EARLY_PHASE1"
        phase_order = ["PHASE4", "PHASE3", "PHASE2", "PHASE1", "EARLY_PHASE1"]
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
        "total_trials": len(all_studies),
        "drugs": drugs,
    }


def get_pdufa_candidates(
    company: str = None,
    aliases: list[str] = None,
) -> list[dict]:
    """
    Find drugs likely near PDUFA/NDA stage for a company.

    Heuristic: Phase 3 trials that are COMPLETED or ACTIVE_NOT_RECRUITING
    suggest the sponsor may be preparing or has filed an NDA.

    For broader PDUFA calendar, use web search — FDA doesn't expose a structured API.

    Returns list of candidate drugs with their late-stage trial data.
    """
    from ._http import get_json

    base = "https://clinicaltrials.gov/api/v2/studies"
    names = [company] + (aliases or []) if company else []

    if not names:
        # Broad search: all Phase 3 completed recently
        params = {
            "filter.phase": "PHASE3",
            "filter.overallStatus": "COMPLETED",
            "pageSize": 50,
            "format": "json",
            "sort": "LastUpdatePostDate:desc",
        }
        data = get_json(base, params=params)
        studies = data.get("studies", []) if not (isinstance(data, dict) and "error" in data) else []
    else:
        studies = []
        seen = set()
        for name in names:
            params = {
                "query.spons": name,
                "filter.phase": "PHASE3",
                "filter.overallStatus": "COMPLETED,ACTIVE_NOT_RECRUITING",
                "pageSize": 50,
                "format": "json",
            }
            data = get_json(base, params=params)
            if isinstance(data, dict) and "error" in data:
                continue
            for s in data.get("studies", []):
                nct = s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
                if nct and nct not in seen:
                    seen.add(nct)
                    studies.append(s)

    candidates = []
    for s in studies:
        proto = s.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        conditions_mod = proto.get("conditionsModule", {})
        arms = proto.get("armsInterventionsModule", {})

        interventions = arms.get("interventions", [])
        drug_names = [i.get("name") for i in interventions if i.get("type") in ("DRUG", "BIOLOGICAL")]

        completion = status_mod.get("completionDateStruct", {})
        primary_completion = status_mod.get("primaryCompletionDateStruct", {})

        candidates.append({
            "nct_id": ident.get("nctId"),
            "title": ident.get("briefTitle"),
            "sponsor": sponsor_mod.get("leadSponsor", {}).get("name"),
            "status": status_mod.get("overallStatus"),
            "drugs": drug_names,
            "conditions": conditions_mod.get("conditions", []),
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "primary_completion_date": completion.get("date") if primary_completion else None,
            "completion_date": completion.get("date"),
            "has_results": bool(s.get("hasResults")),
        })

    candidates.sort(key=lambda x: x.get("completion_date") or "9999", reverse=True)
    return candidates
