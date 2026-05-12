"""ClinicalTrials.gov v2 API wrapper."""

_BASE = "https://clinicaltrials.gov/api/v2/studies"


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


def _paginated_fetch(params: dict, max_results: int) -> list[dict]:
    """Fetch studies with pagination, hard cap at max_results."""
    from ._http import get_json

    all_studies = []
    while len(all_studies) < max_results:
        params["pageSize"] = min(100, max_results - len(all_studies))
        data = get_json(_BASE, params=params)
        if isinstance(data, dict) and "error" in data:
            if not all_studies:
                return [data]
            break

        studies = data.get("studies", [])
        all_studies.extend(studies)

        next_token = data.get("nextPageToken")
        if not next_token or not studies:
            break
        params["pageToken"] = next_token

    return all_studies


def search_trials(
    condition: str = None,
    intervention: str = None,
    sponsor: str = None,
    phase: str = None,
    status: str = None,
    intervention_type: list[str] = None,
    completion_date_range: tuple[str, str] = None,
    max_results: int = 20,
    paginate: bool = False,
) -> list[dict]:
    """
    Search ClinicalTrials.gov for trials.

    Args:
        condition: Disease or condition (e.g., "non-small cell lung cancer")
        intervention: Drug or therapy name (e.g., "pembrolizumab")
        sponsor: Sponsor company (e.g., "Pfizer")
        phase: "PHASE1", "PHASE2", "PHASE3", or "PHASE4"
        status: "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", etc.
        intervention_type: Filter by type, e.g. ["DRUG", "BIOLOGICAL"]. Applied client-side.
        completion_date_range: Tuple of (start, end) dates as "MM/DD/YYYY" strings.
        max_results: Max trials to return (default 20)
        paginate: If True, follow nextPageToken up to max_results (capped at 1000)

    Returns:
        List of trial dicts with nct_id, title, status, phase, enrollment,
        dates, sponsor, conditions, interventions, summary.
    """
    from ._http import get_json

    if paginate:
        max_results = min(max_results, 1000)

    params = {"pageSize": min(max_results, 100), "format": "json"}
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if sponsor:
        params["query.spons"] = sponsor
    if status:
        params["filter.overallStatus"] = status

    term_parts = []
    if phase:
        term_parts.append(f"AREA[Phase]{phase}")
    if completion_date_range:
        start, end = completion_date_range
        term_parts.append(f"AREA[CompletionDate]RANGE[{start},{end}]")
    if term_parts:
        params["query.term"] = " AND ".join(term_parts)

    if paginate:
        studies = _paginated_fetch(params, max_results)
        if studies and isinstance(studies[0], dict) and "error" in studies[0]:
            return studies
    else:
        data = get_json(_BASE, params=params)
        if isinstance(data, dict) and "error" in data:
            return [data]
        studies = data.get("studies", [])

    results = [_flatten_study(s) for s in studies]

    if intervention_type:
        allowed = set(intervention_type)
        results = [
            r for r in results
            if any(i["type"] in allowed for i in r["interventions"])
        ]

    return results


def get_trial(nct_id: str) -> dict:
    """
    Get full detail and posted results for a single trial by NCT ID.

    Returns dict with: identification, status, design, eligibility,
    endpoints (primary/secondary outcomes), arms, and if results are
    posted: outcome measures with statistical data and adverse events.
    """
    from ._http import get_json

    data = get_json(f"{_BASE}/{nct_id}", params={"format": "json"})
    if isinstance(data, dict) and "error" in data:
        return data

    proto = data.get("protocolSection", {})
    results_section = data.get("resultsSection", {})

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

    # Results
    base["has_results"] = bool(results_section)
    if results_section:
        baseline = results_section.get("baselineCharacteristicsModule", {})
        base["results_enrollment"] = baseline.get("populationDescription")

        # Outcome measures
        outcome_measures = results_section.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
        parsed_outcomes = []
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
            parsed_outcomes.append({
                "title": om.get("title"),
                "type": om.get("type"),
                "time_frame": om.get("timeFrame"),
                "description": om.get("description"),
                "units": om.get("unitOfMeasure"),
                "groups": groups,
                "measurements": measurements,
                "analyses": analyses,
            })
        base["outcomes"] = parsed_outcomes

        # Adverse events
        adverse = results_section.get("adverseEventsModule", {})
        if adverse:
            base["adverse_events"] = {
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

    return base
