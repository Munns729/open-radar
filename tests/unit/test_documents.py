"""Unit tests for document ingestion: text extraction and prompts."""
import tempfile
from pathlib import Path

import pytest

from src.documents.prompts import build_extraction_prompt, EXTRACT_PROMPT_VERSION
from src.documents.service import extract_text_from_file


def test_extract_text_from_file_txt():
    """Plain text file is read and page_count is 0."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello world.\nSecond line.")
        path = f.name
    try:
        text, page_count = extract_text_from_file(path)
        assert "Hello world" in text
        assert "Second line" in text
        assert page_count == 0
    finally:
        Path(path).unlink(missing_ok=True)


def test_extract_text_from_file_missing_raises():
    """Missing file raises ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        extract_text_from_file("/nonexistent/path/file.txt")


def test_build_extraction_prompt_truncates():
    """Long raw_text is truncated to max_text_chars."""
    long_text = "x" * 100000
    out = build_extraction_prompt(
        company_name="Acme",
        document_type="cim",
        raw_text=long_text,
        current_thesis=None,
        current_moat_scores={},
        open_questions=None,
        max_text_chars=500,
    )
    assert "--- DOCUMENT ---" in out
    doc_section = out.split("--- DOCUMENT ---")[1].split("--- END ---")[0]
    assert len(doc_section.strip()) <= 500


def test_build_extraction_prompt_includes_context():
    """Prompt includes company name, type, thesis, moat scores, open questions."""
    out = build_extraction_prompt(
        company_name="Test Co",
        document_type="mgmt_call",
        raw_text="Short doc.",
        current_thesis="Strong moat.",
        current_moat_scores={"technology": 70},
        open_questions=["Q1"],
    )
    assert "Test Co" in out
    assert "mgmt_call" in out
    assert "Strong moat" in out
    assert "technology" in out
    assert "70" in out
    assert "Q1" in out
