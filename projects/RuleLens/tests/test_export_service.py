"""导出服务单元测试。"""

from __future__ import annotations

from rulelens.models import AnalysisBundle, CitationStatus
from rulelens.services.export_service import (
    build_export_filename,
    safe_filename,
    to_json,
    to_markdown,
)


def test_json_reparseable(analysis_service, sample_bytes, sample_name):
    bundle = analysis_service.analyze_document(sample_name, sample_bytes)
    js = to_json(bundle)
    again = AnalysisBundle.model_validate_json(js)
    assert again.file_name == bundle.file_name
    assert len(again.rule_result.rules) == len(bundle.rule_result.rules)


def test_markdown_contains_sections(analysis_service, sample_bytes, sample_name):
    bundle = analysis_service.analyze_document(sample_name, sample_bytes)
    md = to_markdown(bundle)
    assert "规则地图" in md
    assert "情景闯关" in md
    assert "歧义" in md
    assert "免责声明" in md
    # 引用核验状态出现在报告中
    assert "原文已核验" in md


def test_safe_filename_no_traversal():
    # 去除路径分隔与目录，取基础文件名并净化
    assert safe_filename("../../etc/passwd") == "passwd"
    assert ".." not in safe_filename("../../x.md")
    assert ".." not in build_export_filename("../../x.md", "md")


def test_export_filename_format():
    name = build_export_filename("demo.md", "json")
    assert name.startswith("rulelens_demo")
    assert name.endswith(".json")


def test_no_api_key_in_export(analysis_service, sample_bytes, sample_name):
    bundle = analysis_service.analyze_document(sample_name, sample_bytes)
    # 确保导出内容不含密钥形状（模型名等均为占位，无 sk- 前缀）
    js = to_json(bundle)
    assert "sk-" not in js
    assert "Authorization" not in js


def test_citation_status_present(analysis_service, sample_bytes, sample_name):
    bundle = analysis_service.analyze_document(sample_name, sample_bytes)
    bundle.rule_result.rules[0].citations[0].status = CitationStatus.VERIFIED
    md = to_markdown(bundle)
    assert "VERIFIED" in md
