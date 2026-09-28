# Splunk MCP Learning Project

A small Python MCP server that lets GitHub Copilot Chat search Splunk data. MCP (Model Context Protocol) is a standard that lets an AI client call tools exposed by a server. Splunk is a platform for searching and analyzing machine-generated data such as Windows event logs.

The project defaults to demo mode and reads local sample data, so you can explore without connecting to Splunk.

## Setup

From the repository root, create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you want to keep local configuration in a file. The default mode is demo mode; do not put credentials in committed files.

## Sample Data

`sample_data/windows_events.json` contains 30 Windows events across three hosts and one separate event for the `main` index. The matching CSV is provided for importing the Windows sample into a Splunk test index.

To upload the CSV in Splunk Web:

1. Open **Add Data** and choose **Upload**.
2. Select `sample_data/windows_events.csv`.
3. In the preview, choose CSV and confirm the first row contains the field names.
4. Set the destination index to `wineventlog_test` (create the index if prompted).
5. Review the time field and choose `_time`, then finish the upload.

The upload destination is the actual Splunk index; the CSV's `index` column records the sample's original label (`wineventlog` or `main`).

Verify the sample files parse and match row-for-row:

```bash
.venv/bin/python -c 'import csv,json; events=json.load(open("sample_data/windows_events.json")); rows=list(csv.DictReader(open("sample_data/windows_events.csv", newline=""))); assert len(events)==len(rows)==31; assert [{k:str(e[k]) for k in rows[0]} for e in events]==rows; print("31 matching events")'
```

## Connect Copilot Chat

The `.vscode/mcp.json` file configures a local stdio server, which communicates with Copilot through the process's standard input and output. In VS Code, open the Command Palette, run **MCP: List Servers**, select **splunk**, and choose **Start Server**. When prompted, review and trust the server so Copilot Chat can use its tools. Use Copilot Chat in agent mode to call `list_indexes` or `search_splunk`.

## Searching Windows Events

Ask Copilot to call `list_indexes` first to confirm the index name visible to your Splunk account. For live Windows events in an index named `windows`, a failed-logon search is `index=windows EventCode=4625`; for errors and critical events, try `index=windows (level=Error OR level=Critical)`. The tool adds Splunk's `search` command when it is omitted. Demo mode uses `wineventlog` instead of `windows`.

## Tests

Run the client tests from the repository root:

```bash
.venv/bin/python -m pytest -q
```

## Real Splunk Mode

Real mode is off by default and requires a Splunk deployment with REST API access; Splunk Cloud free trials do not provide that access, and creating a token does not by itself guarantee API access. For your host, configure these settings in the ignored local `.env` file:

```dotenv
SPLUNK_HOST=prd-p-wqbot.splunkcloud.com
SPLUNK_PORT=8089
SPLUNK_MOCK=false
```

Also change the `SPLUNK_MOCK` value in `.vscode/mcp.json` from `true` to `false` so the MCP process is not forced into demo mode. Store `SPLUNK_TOKEN` as a Codespaces secret, never in a committed file or checked-in `.env`, then restart the MCP server. A bearer token is a credential sent with API requests and should be protected like a password. A search-only role lets the token search permitted data without write or administrative capabilities.
