# Splunk MCP Learning Project

This project connects GitHub Copilot Chat to Splunk using a small Python MCP server. MCP (Model Context Protocol) lets an AI client call tools provided by another program. Here, Copilot can ask the server to list indexes or run a read-only Splunk search.

You can run the project in **demo mode** with local sample data or **live mode** with a Splunk REST API connection. These modes are separate: uploading a CSV to Splunk does not change the local demo data, and local tests do not connect to Splunk Cloud.

## Project Files

| File or folder | What it does |
| --- | --- |
| `server.py` | Starts the MCP server and defines the `list_indexes` and `search_splunk` tools that Copilot can call. It loads settings from the project-root `.env` file. |
| `splunk_client.py` | Contains the search logic. It reads local JSON in demo mode or calls Splunk's REST API in live mode. It adds the `search` command when needed, blocks a list of known write commands, and limits results to 1-200. |
| `.vscode/mcp.json` | Tells VS Code how to launch this server: which Python executable to use, which script to run, and environment variables to pass to it. Its `SPLUNK_MOCK` value selects demo (`true`) or live (`false`) mode for the MCP process. |
| `.env.example` | A safe template showing the settings the application understands. It contains no real host or token. |
| `.env` | Your private, local settings such as the Splunk host and token. This file is ignored by Git. Never commit or paste a real token; prefer a Codespaces secret where possible. |
| `requirements.txt` | Lists Python packages: `mcp` for the server, `requests` for REST calls, `python-dotenv` for reading `.env`, and `pytest` for tests. |
| `sample_data/windows_events.json` | Local demo events used by `splunk_client.py` when demo mode is enabled. It contains 30 Windows events and one separate event labeled `main`. |
| `sample_data/windows_events.csv` | The same 31 sample events in CSV format, for uploading through Splunk Web. |
| `tests/test_splunk_client.py` | Automated checks for read-only command blocking, demo searches, and maximum-result handling. These tests use a fake HTTP response; they do not contact Splunk. |
| `README.md` | This guide. |

The `.venv/`, `__pycache__/`, and `.pytest_cache/` folders are generated locally. They are not application source files and are ignored by Git.

## Set Up Python

Run these commands from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

The virtual environment keeps this project's Python packages separate from other projects. Use `.venv/bin/python` for the commands below. The `.env` file is optional for demo mode, but is needed for live mode.

## Choose a Mode

The MCP server mode is selected in `.vscode/mcp.json`:

```json
"SPLUNK_MOCK": "true"
```

Use `true` for demo mode. The server reads `sample_data/windows_events.json`; it does not need a Splunk account or network access.

Use `false` for live mode. The server reads `SPLUNK_HOST`, `SPLUNK_PORT`, and `SPLUNK_TOKEN` from `.env` (or from the process environment). The MCP setting takes precedence over `SPLUNK_MOCK` in `.env`. Restart the MCP server after changing settings.

For live mode, the host must be a hostname only, without `https://` or a trailing slash. The client constructs an HTTPS URL from the host and port. Use the REST API host and port provided for your Splunk Cloud stack; do not assume the URL or port used by the Splunk Web page is the REST API endpoint. Port `8089` is the default shown in `.env.example`, but Cloud access depends on the stack and network policy. A token alone does not enable REST API access. Some Splunk Cloud trial stacks may not provide external REST API access.

Keep `SPLUNK_TOKEN` private. Do not put it in `.vscode/mcp.json`, commit it, or paste it into chat. If it is exposed, revoke it and create a replacement. A search-only role is appropriate for this project.

## Sample Data

The CSV and JSON contain matching events. Thirty are Windows events with hosts, log names, event codes, severity levels, messages, and UTC timestamps. One additional event is labeled `main`. The `index` column in these files is sample metadata; it does not create or select the destination index during upload.

To check that the two sample files match and contain 31 rows:

```bash
.venv/bin/python -c 'import csv,json; events=json.load(open("sample_data/windows_events.json")); rows=list(csv.DictReader(open("sample_data/windows_events.csv", newline=""))); assert len(events)==len(rows)==31; assert [{k:str(e[k]) for k in rows[0]} for e in events]==rows; print("31 matching events")'
```

### Upload to Splunk Cloud

In Splunk Web:

1. Open **Add Data** and choose **Upload**.
2. Select `sample_data/windows_events.csv`.
3. Confirm the file is parsed as CSV and that the first row contains field names.
4. Choose an Events index as the destination. For example, create or select `wineventlog_test` if your role allows it.
5. Select `_time` as the event timestamp field, then finish the upload.

The uploaded sample is expected to contain 31 events. Verify it in Splunk Search with **All time** selected:

```spl
index=wineventlog_test | stats count
```

The expected count is `31`. Splunk indexes can exist with no events; an empty search result is different from a REST API connection error.

## Connect Copilot Chat

`.vscode/mcp.json` configures a local **stdio** server. Stdio means VS Code starts `server.py` as a process and communicates with it through standard input and output; it is not a web server with a URL.

1. Open the Command Palette in VS Code and run **MCP: List Servers**.
2. Select **splunk**, then choose **Start Server**. Review and trust the server if prompted.
3. Open Copilot Chat in agent mode. Ask it to list indexes or search an index.

The server exposes two tools:

- `list_indexes` returns index names visible in Splunk, or the demo index names when demo mode is enabled.
- `search_splunk` runs a query. Its default time range is the last hour and its default maximum is 50 results; the maximum is capped at 200.

For the uploaded sample, ask Copilot to search `index=wineventlog_test | stats count` with `earliest` set to `-30d`. The sample timestamps may fall outside the default last-hour range. Use the exact index name shown in Splunk; `wineventlog_test` is the upload destination, while `wineventlog` is the local demo-data label.

## Search Examples

Run these in Splunk Search or ask Copilot to pass them to `search_splunk`:

```spl
index=wineventlog_test EventCode=4625
index=wineventlog_test (level=Error OR level=Critical)
index=wineventlog_test | stats count by host
```

For real Windows data, replace `wineventlog_test` with the index that contains those events, for example:

```spl
index=windows EventCode=4625
```

The local demo data has index names `wineventlog` and `main`. The demo search implementation is intentionally simple and is not a complete Splunk Search Processing Language (SPL) engine. Live mode sends searches to Splunk. The client blocks several known write commands, but this is not a substitute for using a search-only Splunk role.

## Run Tests

From the repository root:

```bash
.venv/bin/python -m pytest -q
```

The tests do not need network access or a real Splunk token. They temporarily set demo/live settings and mock the HTTP request where needed.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `Set SPLUNK_HOST and SPLUNK_TOKEN` | Live mode is selected, but the process cannot find one or both settings. Check `.env` or the environment used to launch the MCP server. Never print the token when debugging. |
| Hostname error mentioning `https` | `SPLUNK_HOST` probably includes `https://`. Set it to the hostname only; the client adds HTTPS. |
| Connection timeout on the REST port | The server process may be fine, but the workspace cannot reach the Splunk REST API. Check that the stack supports API access, the REST host and port are correct, and network or IP allow-list rules permit the connection. A trial may not include this access. |
| HTTP 401 or 403 | The endpoint is reachable, but the token may be invalid, expired, or missing permission for the requested operation or index. |
| HTTP 404 | The host is responding, but the configured REST path may not be available at that host/port. Confirm the REST API endpoint for the stack; the Splunk Web URL is not necessarily the REST endpoint. |
| Search returns no events | Confirm the destination index name, select a suitable time range such as `-30d`, and verify the upload count in Splunk Web. |
| MCP server does not appear in VS Code | Check that `.venv` exists, dependencies installed successfully, `.vscode/mcp.json` points to `server.py`, and the server is trusted and started from **MCP: List Servers**. |

Splunk Web access and REST API access are separate. If the CSV search works in Splunk Web but the MCP search times out, the data is present; investigate REST API access from the development environment.
