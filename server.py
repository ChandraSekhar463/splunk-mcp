"""MCP tools for searching Splunk or the local demo events."""

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load project settings before importing the client that reads them.
load_dotenv(Path(__file__).resolve().parent / ".env")

from splunk_client import list_indexes as get_indexes
from splunk_client import search_splunk as run_search


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)
mcp = FastMCP("splunk")


@mcp.tool()
def list_indexes() -> str:
    """List the indexes available in Splunk or in the local demo dataset."""
    try:
        return json.dumps(get_indexes())
    except Exception as exc:
        logger.exception("Could not list Splunk indexes")
        return f"Error listing indexes: {exc}"


@mcp.tool()
def search_splunk(query: str, earliest: str = "-1h", latest: str = "now", max_results: int = 50) -> str:
    """Run a read-only search; use index=wineventlog_test for the uploaded sample, index=windows for live Windows events, or index=wineventlog in demo mode.

    Check list_indexes first if the expected index is not returning events.
    """
    try:
        results = run_search(query, earliest, latest, max_results)
        return json.dumps(results, indent=2, default=str)
    except Exception as exc:
        logger.exception("Splunk search failed")
        return f"Error searching Splunk: {exc}"


if __name__ == "__main__":
    mcp.run()
