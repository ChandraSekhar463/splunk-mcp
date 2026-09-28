import pytest

import splunk_client


@pytest.mark.parametrize("command", ["delete", "outputlookup"])
def test_check_read_only_blocks_write_commands(command):
    with pytest.raises(ValueError, match="not allowed"):
        splunk_client.check_read_only(f"index=wineventlog | {command}")


def test_demo_search_returns_only_error_and_critical_events(monkeypatch):
    monkeypatch.setenv("SPLUNK_MOCK", "true")

    events = splunk_client.search_splunk("index=wineventlog error")

    assert events
    assert all(event["index"] == "wineventlog" for event in events)
    assert all(event["level"] in {"Error", "Critical"} for event in events)


@pytest.mark.parametrize(("requested", "expected"), [(0, 1), (500, 200)])
def test_search_clamps_max_results(monkeypatch, requested, expected):
    monkeypatch.setenv("SPLUNK_MOCK", "false")
    monkeypatch.setenv("SPLUNK_HOST", "splunk.example.test")
    monkeypatch.setenv("SPLUNK_PORT", "8089")
    monkeypatch.setenv("SPLUNK_TOKEN", "test-token")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(splunk_client.requests, "post", fake_post)
    splunk_client.search_splunk("index=wineventlog error", max_results=requested)

    assert captured["data"]["count"] == expected
