import pytest
from pathlib import Path
from app.executor.report_handler import ReportHandler


def test_parse_html_report_with_valid_file():
    """测试正常 HTML 报告解析"""
    handler = ReportHandler()
    html_path = Path("tests/fixtures/sample_fail_report.html")

    result = handler.parse_html_report(html_path)

    assert result["caseFailStep"] == "步骤1：登录系统, 步骤2：提交表单"
    assert result["failReason"] == "AssertionError: 预期值与实际值不符"
    assert "测试执行失败" in result["caseFailLog"]


def test_parse_html_report_file_not_exists():
    """测试 HTML 文件不存在"""
    handler = ReportHandler()
    html_path = Path("tests/fixtures/not_exists.html")

    result = handler.parse_html_report(html_path)

    assert result["caseFailStep"] == ""
    assert result["caseFailLog"] == ""
    assert result["failReason"] == "HTML日志不存在"


def test_parse_html_report_empty_elements():
    """测试 HTML 中无失败信息"""
    handler = ReportHandler()
    html_path = Path("tests/fixtures/empty_report.html")

    # 创建空报告 fixture
    empty_html = "<html><body></body></html>"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(empty_html, encoding='utf-8')

    result = handler.parse_html_report(html_path)

    assert result["caseFailStep"] == ""
    assert result["failReason"] == ""
    assert result["caseFailLog"] == ""