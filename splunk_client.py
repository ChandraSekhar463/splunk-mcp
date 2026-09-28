"""Small read-only client for demo data and the Splunk REST API."""

import json
import os
import re
from pathlib import Path

import requests


BLOCKED_COMMANDS = {
    "delete",
    "outputlookup",
    "outputcsv",
    "collect",
    "mcollect",
    "meventcollect",
    "sendemail",
    "sendalert",
    "script",
    "run",
    "map",
    "rest",
    "dbxquery",
    "tscollect",
    "crawl",
}
SEARCH_KEYWORDS = {"error", "critical", "fail", "failed", "failure"}
SAMPLE_FILE = Path(__file__).resolve().parent / "sample_data" / "windows_events.json"


def is_mock():
    """Return whether local demo data should be used (the default)."""
    return os.getenv("SPLUNK_MOCK", "true").strip().lower() in {"1", "true", "yes", "on"}


def check_read_only(query):
    """Add the search command and reject known commands that can change data."""
    query = query.strip()
    if not query:
        raise ValueError("Search query cannot be empty.")

    # Splunk searches begin with a command; bare filters need the search command.
    if not query.lower().startswith("search"):
        query = "search " + query

    for segment in query.split("|"):
        words = segment.strip().split()
        if words and words[0].lower() in BLOCKED_COMMANDS:
            raise ValueError(f"Search command is not allowed: {words[0]}")
    return query


def _clamp_max_results(max_results):
    try:
        value = int(max_results)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_results must be an integer.") from exc
    return max(1, min(value, 200))


def _demo_search(query, max_results):
    with SAMPLE_FILE.open(encoding="utf-8") as sample_file:
        events = json.load(sample_file)

    index_match = re.search(r"\bindex\s*=\s*([^\s|]+)", query, flags=re.IGNORECASE)
    requested_index = index_match.group(1).strip("\"'") if index_match else None
    query_text = re.sub(r"\bindex\s*=\s*[^\s|]+", " ", query, flags=re.IGNORECASE)
    tokens = [token.lower() for token in re.findall(r"[a-zA-Z0-9_.-]+", query_text)]
    tokens = [token for token in tokens if token != "search"]
    keywords = [token for token in tokens if token in SEARCH_KEYWORDS]
    free_text = [token for token in tokens if token not in SEARCH_KEYWORDS]

    matches = []
    for event in events:
        if requested_index and event.get("index", "").lower() != requested_index.lower():
            continue

        searchable = " ".join(str(value) for value in event.values()).lower()
        if keywords:
            # An "error" search also includes critical events; failure searches match messages.
            keyword_match = any(
                (keyword == "error" and event.get("level", "").lower() in {"error", "critical"})
                or (keyword == "critical" and event.get("level", "").lower() == "critical")
                or (keyword in {"fail", "failed", "failure"} and "fail" in searchable)
                for keyword in keywords
            )
            if not keyword_match:
                continue
        if free_text and not all(term in searchable for term in free_text):
            continue
        matches.append(event)

    return matches[:max_results]


def _splunk_config():
    host = os.getenv("SPLUNK_HOST", "").strip().rstrip("/")
    port = os.getenv("SPLUNK_PORT", "8089").strip()
    token = os.getenv("SPLUNK_TOKEN", "").strip()
    if not host or not token:
        raise ValueError("Set SPLUNK_HOST and SPLUNK_TOKEN to use real Splunk mode.")
    return host, port, token


def search_splunk(query, earliest="-1h", latest="now", max_results=50):
    """Search local sample events or run a bounded, read-only Splunk search."""
    safe_query = check_read_only(query)
    result_limit = _clamp_max_results(max_results)

    if is_mock():
        return _demo_search(safe_query, result_limit)

    host, port, token = _splunk_config()
    response = requests.post(
        f"https://{host}:{port}/services/search/jobs",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "search": safe_query,
            "earliest_time": earliest,
            "latest_time": latest,
            "count": result_limit,
            "exec_mode": "oneshot",
            "output_mode": "json",
        },
        timeout=60,
        verify=True,
    )
    response.raise_for_status()
    return response.json()


def list_indexes():
    """Return available index names from demo data or Splunk."""
    if is_mock():
        return ["main", "wineventlog"]

    host, port, token = _splunk_config()
    response = requests.get(
        f"https://{host}:{port}/services/data/indexes",
        headers={"Authorization": f"Bearer {token}"},
        params={"output_mode": "json"},
        timeout=60,
        verify=True,
    )
    response.raise_for_status()
    entries = response.json().get("entry", [])
    return [entry["name"] for entry in entries if "name" in entry]
