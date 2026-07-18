import hashlib
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REVIEWED_GIF_SHA256 = {
    "cline.gif": "405b10c3321d3229a5c7df6d7faecbc103e6e91233fe99b575ecf5051b7f92c2",
    "trae.gif": "71882360a7db2271122ea0f3c0889ef7ec32ec6a299a46d13e4ff50bb51f092a",
}


def test_demo_gifs_are_real_nonempty_gif_files() -> None:
    for name in ("cline.gif", "trae.gif"):
        path = PACKAGE_ROOT / "docs" / "demos" / name
        data = path.read_bytes()
        assert data[:6] in {b"GIF87a", b"GIF89a"}
        assert len(data) > 10_000


def test_demo_gifs_match_manually_reviewed_assets() -> None:
    for name, expected in REVIEWED_GIF_SHA256.items():
        data = (PACKAGE_ROOT / "docs" / "demos" / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected


def test_demo_notes_do_not_contain_secrets_or_placeholders() -> None:
    text = (PACKAGE_ROOT / "docs" / "demos" / "README.md").read_text(encoding="utf-8")
    assert "sk-or-v1-" not in text
    assert "<NEW_ROTATED_KEY>" not in text
    assert "placeholder" not in text.lower()


def test_demo_notes_record_measured_client_evidence() -> None:
    text = (PACKAGE_ROOT / "docs" / "demos" / "README.md").read_text(encoding="utf-8")
    for expected in (
        "2026-07-11",
        "Cline CLI `3.0.39`",
        "TRAE SOLO CN `0.1.25` / VS Code `1.107.1`",
        "tencent/hy3:free",
        "reasoning_effort=none",
        "hy3_kb_index_documents",
        "hy3_kb_list_sources",
        "hy3_kb_search",
        "hy3_kb_ask",
        "2025-11-18",
        "738b65bbd428/roadmap.md, lines 1\u20138",
        "[recording excerpt](cline.gif)",
        "[recording excerpt](trae.gif)",
    ):
        assert expected in text


def test_package_readmes_link_real_client_evidence() -> None:
    for name in ("README.md", "README_CN.md"):
        text = (PACKAGE_ROOT / name).read_text(encoding="utf-8")
        assert "docs/demos/cline.gif" in text
        assert "docs/demos/trae.gif" in text
        assert "docs/demos/README.md" in text
        assert "Cline CLI `3.0.39`" in text
        assert "TRAE SOLO CN `0.1.25`" in text
