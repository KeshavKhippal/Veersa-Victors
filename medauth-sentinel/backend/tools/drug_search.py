"""
MedAuth Sentinel — Drug Search Tool
When a drug is not found in the alias map (Tier 3 fails),
this tool searches the web for its pharmacological properties
in real time before passing context to the Groq agent.

Uses Tavily API — free tier, built for AI agents.
"""

import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


def search_drug_info(drug_name: str) -> dict:
    """
    Search the web for a drug's pharmacological properties.

    Args:
        drug_name: The drug name to search (e.g. "Ozivy")

    Returns:
        dict with keys:
          found        — bool, whether useful info was found
          drug_name    — the searched drug name
          summary      — plain text summary of findings
          active_ingredient — extracted if found, else None
          mechanism    — extracted if found, else None
          drug_class   — extracted if found, else None
          source_urls  — list of sources
          raw_results  — full Tavily results for debugging
          error        — error message if search failed
    """

    if not TAVILY_API_KEY:
        return {
            "found": False,
            "drug_name": drug_name,
            "summary": "Web search unavailable — TAVILY_API_KEY not set in .env",
            "active_ingredient": None,
            "mechanism": None,
            "drug_class": None,
            "source_urls": [],
            "error": "TAVILY_API_KEY missing"
        }

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)

        # Search query optimized for pharmacological info
        query = (
            f"{drug_name} drug active ingredient mechanism of action "
            f"therapeutic class pharmacology prior authorization"
        )

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,  # Tavily generates a summary answer
        )

        # Extract the AI-generated answer (most useful for agents)
        answer = response.get("answer", "")

        # Extract source URLs
        results = response.get("results", [])
        source_urls = [r.get("url", "") for r in results if r.get("url")]

        # Extract content snippets from top results
        snippets = []
        for r in results[:3]:
            content = r.get("content", "").strip()
            if content:
                snippets.append(content[:500])

        # Build combined summary
        summary_parts = []
        if answer:
            summary_parts.append(f"Summary: {answer}")
        if snippets:
            summary_parts.append("Supporting details:")
            for i, s in enumerate(snippets, 1):
                summary_parts.append(f"  [{i}] {s}")

        full_summary = "\n".join(summary_parts) if summary_parts else ""

        # Try to extract key pharmacological fields from the answer
        active_ingredient = _extract_field(
            answer + " " + " ".join(snippets),
            ["active ingredient", "active substance", "contains",
             "molecule", "generic name", "inn"]
        )
        mechanism = _extract_field(
            answer + " " + " ".join(snippets),
            ["mechanism of action", "works by", "acts by",
             "receptor", "inhibitor", "agonist", "antagonist"]
        )
        drug_class = _extract_field(
            answer + " " + " ".join(snippets),
            ["drug class", "therapeutic class", "classification",
             "belongs to", "type of drug", "category"]
        )

        found = bool(full_summary and len(full_summary) > 50)

        return {
            "found": found,
            "drug_name": drug_name,
            "summary": full_summary,
            "active_ingredient": active_ingredient,
            "mechanism": mechanism,
            "drug_class": drug_class,
            "source_urls": source_urls[:3],
            "raw_results": results,
            "error": None
        }

    except Exception as e:
        return {
            "found": False,
            "drug_name": drug_name,
            "summary": f"Web search failed: {str(e)}",
            "active_ingredient": None,
            "mechanism": None,
            "drug_class": None,
            "source_urls": [],
            "error": str(e)
        }


def _extract_field(text: str, keywords: list) -> str | None:
    """
    Simple keyword-based extraction from text.
    Returns the sentence containing the first keyword found.
    """
    text_lower = text.lower()
    sentences = text.replace("\n", ". ").split(". ")

    for keyword in keywords:
        for sentence in sentences:
            if keyword in sentence.lower() and len(sentence) > 10:
                return sentence.strip()[:200]

    return None


def format_search_result_for_agent(search_result: dict) -> str:
    """
    Formats the search result into a clean string
    for injection into the agent's prompt.
    """
    if not search_result.get("found"):
        error = search_result.get("error", "Unknown error")
        return (
            f"WEB SEARCH FOR '{search_result['drug_name']}': No results found.\n"
            f"Reason: {error}\n"
            f"The agent must rely on training knowledge only."
        )

    lines = [
        f"WEB SEARCH RESULTS FOR '{search_result['drug_name']}':",
        f"(Real-time search conducted — results are current)",
        "",
    ]

    if search_result.get("active_ingredient"):
        lines.append(f"Active Ingredient: {search_result['active_ingredient']}")
    if search_result.get("mechanism"):
        lines.append(f"Mechanism: {search_result['mechanism']}")
    if search_result.get("drug_class"):
        lines.append(f"Drug Class: {search_result['drug_class']}")

    lines.append("")
    lines.append("Full Summary:")
    lines.append(search_result.get("summary", ""))

    if search_result.get("source_urls"):
        lines.append("")
        lines.append("Sources:")
        for url in search_result["source_urls"]:
            lines.append(f"  - {url}")

    return "\n".join(lines)
