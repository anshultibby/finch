"""PubMed and PubMed Central search, abstracts, and full text retrieval."""

import xml.etree.ElementTree as ET

_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_NCBI_PARAMS = {"tool": "finch", "email": "finch@example.com"}


def _parse_article(article_el: ET.Element) -> dict:
    """Parse a single PubMedArticle XML element into a dict."""
    citation = article_el.find(".//MedlineCitation")
    if citation is None:
        return {}

    pmid_el = citation.find("PMID")
    pmid = pmid_el.text if pmid_el is not None else None

    art = citation.find("Article")
    if art is None:
        return {"pmid": pmid}

    title_el = art.find("ArticleTitle")
    title = "".join(title_el.itertext()) if title_el is not None else None

    # Journal
    journal_el = art.find(".//Journal/Title")
    journal = journal_el.text if journal_el is not None else None

    # Date
    pub_date = art.find(".//Journal/JournalIssue/PubDate")
    date_str = None
    if pub_date is not None:
        y = pub_date.findtext("Year", "")
        m = pub_date.findtext("Month", "")
        d = pub_date.findtext("Day", "")
        date_str = f"{y} {m} {d}".strip()

    # Authors
    authors = []
    for author in art.findall(".//AuthorList/Author"):
        last = author.findtext("LastName", "")
        first = author.findtext("ForeName", "")
        if last:
            authors.append(f"{last} {first}".strip())

    # Abstract
    abstract_parts = []
    for abs_text in art.findall(".//Abstract/AbstractText"):
        label = abs_text.get("Label", "")
        text = "".join(abs_text.itertext()) or ""
        if label:
            abstract_parts.append(f"**{label}**: {text}")
        else:
            abstract_parts.append(text)
    abstract = "\n\n".join(abstract_parts)

    # DOI
    doi = None
    for eid in art.findall(".//ELocationID"):
        if eid.get("EIdType") == "doi":
            doi = eid.text

    # PMC ID
    pmc_id = None
    pmd = article_el.find(".//PubmedData")
    if pmd is not None:
        for aid in pmd.findall(".//ArticleId"):
            if aid.get("IdType") == "pmc":
                pmc_id = aid.text

    return {
        "pmid": pmid,
        "title": title,
        "authors": authors,
        "journal": journal,
        "pub_date": date_str,
        "abstract": abstract,
        "doi": doi,
        "pmc_id": pmc_id,
        "has_full_text": pmc_id is not None,
    }


def search_pubmed(query: str, max_results: int = 10) -> list[dict]:
    """
    Search PubMed for articles matching a query.

    Args:
        query: Search string (e.g., "cytisinicline smoking cessation Phase 3")
        max_results: Max articles to return (default 10)

    Returns:
        List of article dicts with pmid, title, authors, journal, pub_date,
        abstract, doi, pmc_id, has_full_text.
    """
    from ._http import get_json, get_xml

    # Step 1: esearch to get PMIDs
    search_params = {
        **_NCBI_PARAMS,
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    search_data = get_json(f"{_EUTILS}/esearch.fcgi", params=search_params)
    if isinstance(search_data, dict) and "error" in search_data:
        return [search_data]

    id_list = search_data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    # Step 2: efetch to get full article metadata
    fetch_params = {
        **_NCBI_PARAMS,
        "db": "pubmed",
        "id": ",".join(id_list),
        "rettype": "abstract",
        "retmode": "xml",
    }
    xml_text = get_xml(f"{_EUTILS}/efetch.fcgi", params=fetch_params)
    if not xml_text:
        return [{"error": "Failed to fetch article details"}]

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [{"error": "Failed to parse PubMed XML"}]

    articles = []
    for article_el in root.findall("PubmedArticle"):
        parsed = _parse_article(article_el)
        if parsed.get("pmid"):
            articles.append(parsed)

    return articles


def get_abstract(pmid: str) -> dict:
    """
    Fetch full metadata and abstract for a single PubMed article.

    Args:
        pmid: PubMed ID (e.g., "39012345")

    Returns:
        Article dict with pmid, title, authors, journal, pub_date, abstract, doi, pmc_id.
    """
    from ._http import get_xml

    params = {
        **_NCBI_PARAMS,
        "db": "pubmed",
        "id": str(pmid),
        "rettype": "abstract",
        "retmode": "xml",
    }
    xml_text = get_xml(f"{_EUTILS}/efetch.fcgi", params=params)
    if not xml_text:
        return {"error": f"Failed to fetch PMID {pmid}"}

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"error": "Failed to parse PubMed XML"}

    article_el = root.find("PubmedArticle")
    if article_el is None:
        return {"error": f"No article found for PMID {pmid}"}

    return _parse_article(article_el)


def get_full_text(pmid_or_pmcid: str, max_chars: int = 80000) -> dict:
    """
    Get full text from PubMed Central (open access only).

    Args:
        pmid_or_pmcid: PubMed ID (numeric) or PMC ID ("PMC1234567")
        max_chars: Truncate text to this length (default 80K)

    Returns:
        {"pmid": str, "pmc_id": str, "sections": [...], "full_text": str}
        Each section has "heading" and "text" keys.
        Returns error if full text is not available in PMC.
    """
    from ._http import get_json, get_xml

    pmcid = None
    pmid = str(pmid_or_pmcid)

    if pmid.upper().startswith("PMC"):
        pmcid = pmid.upper()
    else:
        # Convert PMID to PMCID via elink
        link_params = {
            **_NCBI_PARAMS,
            "dbfrom": "pubmed",
            "db": "pmc",
            "id": pmid,
            "retmode": "json",
        }
        link_data = get_json(f"{_EUTILS}/elink.fcgi", params=link_params)
        if isinstance(link_data, dict) and "error" in link_data:
            return link_data

        linksets = link_data.get("linksets", [])
        for ls in linksets:
            for ldb in ls.get("linksetdbs", []):
                if ldb.get("dbto") == "pmc":
                    links = ldb.get("links", [])
                    if links:
                        pmcid = f"PMC{links[0]}"
                        break

    if not pmcid:
        return {
            "error": "Full text not available in PMC (not open access)",
            "pmid": pmid,
            "suggestion": "Use get_abstract() for the abstract, or check if the paper is available via the DOI.",
        }

    # Fetch full text XML from PMC
    fetch_params = {
        **_NCBI_PARAMS,
        "db": "pmc",
        "id": pmcid.replace("PMC", ""),
        "rettype": "xml",
    }
    xml_text = get_xml(f"{_EUTILS}/efetch.fcgi", params=fetch_params)
    if not xml_text:
        return {"error": f"Failed to fetch full text for {pmcid}"}

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"error": "Failed to parse PMC XML"}

    # Extract sections from JATS XML body
    sections = []
    body = root.find(".//body")
    if body is None:
        # Try alternate structure
        body = root.find(".//article/body")

    if body is not None:
        for sec in body.iter("sec"):
            heading_el = sec.find("title")
            heading = heading_el.text if heading_el is not None else ""
            paragraphs = []
            for p in sec.findall("p"):
                text = "".join(p.itertext()) or ""
                if text.strip():
                    paragraphs.append(text.strip())
            if paragraphs:
                sections.append({"heading": heading or "(untitled)", "text": "\n".join(paragraphs)})

    if not sections:
        # Fallback: extract all text from body
        all_text = "".join(body.itertext()) if body is not None else ""
        if all_text.strip():
            sections.append({"heading": "Full Text", "text": all_text.strip()})

    # Build full text and truncate
    full_text = "\n\n".join(
        f"## {s['heading']}\n{s['text']}" for s in sections
    )
    truncated = len(full_text) > max_chars
    if truncated:
        full_text = full_text[:max_chars] + "\n\n[TRUNCATED]"

    return {
        "pmid": pmid,
        "pmc_id": pmcid,
        "sections": sections if not truncated else sections[:20],
        "full_text": full_text,
        "truncated": truncated,
        "char_count": len(full_text),
    }


def search_by_nct(nct_id: str, max_results: int = 10) -> list[dict]:
    """
    Find PubMed articles linked to a specific clinical trial NCT ID.

    Args:
        nct_id: ClinicalTrials.gov ID (e.g., "NCT04280705")
        max_results: Max articles (default 10)

    Returns:
        List of article dicts (same format as search_pubmed).
    """
    return search_pubmed(f"{nct_id}[si]", max_results=max_results)
