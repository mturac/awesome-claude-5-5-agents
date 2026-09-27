import json

from fetch_github_stars import FetchError, build_request, enrich, normalize


def test_request_sends_bearer_token_and_not_the_url() -> None:
    request = build_request("https://api.github.com/repos/qiwei66/model-bump", "s3cret")
    assert request.get_header("Authorization") == "Bearer s3cret"
    assert "s3cret" not in request.full_url
    assert request.host == "api.github.com"


def test_enrich_reads_stars_without_storing_the_token() -> None:
    calls: list[tuple[str, str]] = []

    def transport(url: str, token: str) -> object:
        calls.append((url, token))
        if url.endswith("/commits?per_page=1"):
            return [{"commit": {"committer": {"date": "2026-09-24T01:02:03Z"}}}]
        return {"stargazers_count": 7, "license": {"spdx_id": "MIT"}}

    found = enrich(["https://github.com/qiwei66/model-bump"], token="test-token", transport=transport)
    assert calls[0][1] == "test-token"
    record = found["qiwei66/model-bump"]
    assert record["stars"] == 7
    assert record["license"] == "MIT"
    assert record["last_commit"] == "2026-09-24"
    assert "test-token" not in json.dumps(found)


def test_missing_token_skips_the_network() -> None:
    def transport(url: str, token: str) -> object:
        raise AssertionError("network should not be called")

    assert enrich(["https://github.com/qiwei66/model-bump"], token="", transport=transport) == {}


def test_api_failure_falls_back_by_omitting_the_repo() -> None:
    def transport(url: str, token: str) -> object:
        raise FetchError("HTTP 500 for /repos/qiwei66/model-bump")

    found = enrich(["https://github.com/qiwei66/model-bump"], token="test-token", transport=transport)
    assert found == {}


def test_missing_spdx_becomes_no_license() -> None:
    record = normalize({"stargazers_count": 0, "license": None}, [])
    assert record["license"] == "no license"
    assert record["last_commit"] is None
