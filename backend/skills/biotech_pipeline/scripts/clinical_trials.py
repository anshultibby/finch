"""ClinicalTrials.gov v2 API wrapper."""

_BASE = "https://clinicaltrials.gov/api/v2/studies"

_SEARCH_FIELDS = (
    "NCTId,BriefTitle,OfficialTitle,OverallStatus,Phase,"
    "EnrollmentInfo,StartDateStruct,PrimaryCompletionDateStruct,"
    "CompletionDateStruct,LeadSponsorName,Condition,InterventionName,"
    "BriefSummary"
)


def _safe_date(date_struct: dict | None) -> str | None:
    if not date_struct or not isinstance(date_struct, dict):
        return None
    return date_struct.get("date")


def _flatten_study(study: dict) -> dict:
    proto = study.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    design = proto.get("designModule", {})
    sponsor = proto.get("sponsorCollaboratorsModule", {})
    conditions = proto.get("conditionsModule", {})
    interventions = proto.get("armsInterventionsModule", {})
    desc = proto.get("descriptionModule", {})

    enrollment_info = design.get("enrollmentInfo", {})
    lead = sponsor.get("leadSponsor", {})
    intervention_list = interventions.get("interventions", [])

    return {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "status": status.get("overallStatus"),
        "phase": design.get("phases", []),
        "enrollment": enrollment_info.get("count"),
        "enrollment_type": enrollment_info.get("type"),
        "start_date": _safe_date(status.get("startDateStruct")),
        "primary_completion": _safe_date(status.get("primaryCompletionDateStruct")),
        "completion_date": _safe_date(status.get("completionDateStruct")),
        "sponsor": lead.get("name"),
        "conditions": conditions.get("conditions", []),
        "interventions": [
            {"name": i.get("name"), "type": i.get("type")}
            for i in intervention_list
        ],
        "summary": desc.get("briefSummary"),
    }


def search_trials(
    condition: str = None,
    intervention: str = None,
    sponsor: str = None,
    phase: str = None,
    status: str = None,
    max_results: int = 20,
) -> list[dict]:
    """
    Search ClinicalTrials.gov for trials.

    Args:
        condition: Disease or condition (e.g., "non-small cell lung cancer")
        intervention: Drug or therapy name (e.g., "pembrolizumab")
        sponsor: Sponsor company (e.g., "Pfizer")
        phase: "PHASE1", "PHASE2", "PHASE3", or "PHASE4"
        status: "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", etc.
        max_results: Max trials to return (default 20)

    Returns:
        List of trial dicts with nct_id, title, status, phase, enrollment,
        dates, sponsor, conditions, interventions, summary.
    """
    from ._http import get_json

    params = {"pageSize": min(max_results, 100), "format": "json"}
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if sponsor:
        params["query.spons"] = sponsor
    if phase:
        params["filter.phase"] = phase
    if status:
        params["filter.overallStatus"] = status

    data = get_json(_BASE, params=params)
    if isinstance(data, dict) and "error" in data:
        return [data]

    studies = data.get("studies", [])
    return [_flatten_study(s) for s in studies]


def get_trial_detail(nct_id: str) -> dict:
    """
    Get full detail for a single trial by NCT ID.

    Returns dict with: identification, status, design, eligibility,
    endpoints (primary/secondary outcomes), arms, and results summary if posted.
    """
    from ._http import get_json

    data = get_json(f"{_BASE}/{nct_id}", params={"format": "json"})
    if isinstance(data, dict) and "error" in data:
        return data

    proto = data.get("protocolSection", {})
    results = data.get("resultsSection", {})

    base = _flatten_study(data)

    # Design details
    design = proto.get("designModule", {})
    base["study_type"] = design.get("studyType")
    design_info = design.get("designInfo", {})
    base["allocation"] = design_info.get("allocation")
    base["intervention_model"] = design_info.get("interventionModel")
    base["masking"] = design_info.get("maskingInfo", {}).get("masking")

    # Eligibility
    elig = proto.get("eligibilityModule", {})
    base["eligibility"] = {
        "criteria": elig.get("eligibilityCriteria"),
        "min_age": elig.get("minimumAge"),
        "max_age": elig.get("maximumAge"),
        "sex": elig.get("sex"),
        "healthy_volunteers": elig.get("healthyVolunteers"),
    }

    # Endpoints
    outcomes = proto.get("outcomesModule", {})
    base["primary_outcomes"] = [
        {"measure": o.get("measure"), "time_frame": o.get("timeFrame"), "description": o.get("description")}
        for o in outcomes.get("primaryOutcomes", [])
    ]
    base["secondary_outcomes"] = [
        {"measure": o.get("measure"), "time_frame": o.get("timeFrame"), "description": o.get("description")}
        for o in outcomes.get("secondaryOutcomes", [])
    ]

    # Arms
    arms = proto.get("armsInterventionsModule", {})
    base["arms"] = [
        {"label": a.get("label"), "type": a.get("type"), "description": a.get("description")}
        for a in arms.get("armGroups", [])
    ]

    # Results summary
    base["has_results"] = bool(results)
    if results:
        baseline = results.get("baselineCharacteristicsModule", {})
        base["results_enrollment"] = baseline.get("populationDescription")

    return base


def get_trial_results(nct_id: str) -> dict:
    """
    Get posted results for a trial (outcome measures with statistical data).

    Returns:
        {"nct_id": str, "has_results": bool, "outcomes": [...]} where each
        outcome has title, type, time_frame, groups, and measurements with
        statistical values (p-values, CIs) when available.
    """
    from ._http import get_json

    data = get_json(f"{_BASE}/{nct_id}", params={"format": "json"})
    if isinstance(data, dict) and "error" in data:
        return data

    results = data.get("resultsSection", {})
    if not results:
        return {"nct_id": nct_id, "has_results": False, "outcomes": []}

    outcome_measures = results.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    outcomes = []
    for om in outcome_measures:
        groups = [
            {"id": g.get("id"), "title": g.get("title"), "description": g.get("description")}
            for g in om.get("groups", [])
        ]

        measurements = []
        for cls in om.get("classes", []):
            for cat in cls.get("categories", []):
                for m in cat.get("measurements", []):
                    measurements.append({
                        "group_id": m.get("groupId"),
                        "value": m.get("value"),
                        "spread": m.get("spread"),
                        "lower_limit": m.get("lowerLimit"),
                        "upper_limit": m.get("upperLimit"),
                    })

        analyses = []
        for a in om.get("analyses", []):
            analyses.append({
                "groups": a.get("groupIds", []),
                "method": a.get("statisticalMethod"),
                "p_value": a.get("pValue"),
                "ci_lower": a.get("ciLowerLimit"),
                "ci_upper": a.get("ciUpperLimit"),
                "estimate": a.get("estimateComment"),
            })

        outcomes.append({
            "title": om.get("title"),
            "type": om.get("type"),
            "time_frame": om.get("timeFrame"),
            "description": om.get("description"),
            "units": om.get("unitOfMeasure"),
            "groups": groups,
            "measurements": measurements,
            "analyses": analyses,
        })

    # Adverse events summary
    adverse = results.get("adverseEventsModule", {})
    adverse_summary = None
    if adverse:
        adverse_summary = {
            "frequency_threshold": adverse.get("frequencyThreshold"),
            "time_frame": adverse.get("timeFrame"),
            "description": adverse.get("description"),
            "serious_count": sum(
                int(s.get("numAffected", 0))
                for e in adverse.get("seriousEvents", [])
                for s in e.get("stats", [])
            ),
            "other_count": sum(
                int(s.get("numAffected", 0))
                for e in adverse.get("otherEvents", [])
                for s in e.get("stats", [])
            ),
        }

    return {
        "nct_id": nct_id,
        "has_results": True,
        "outcomes": outcomes,
        "adverse_events": adverse_summary,
    }
