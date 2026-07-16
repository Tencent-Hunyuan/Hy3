from hy3_client import Hy3Client


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    try:
        Hy3Client()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "HY3_API_KEY" in str(e)
