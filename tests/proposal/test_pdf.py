from __future__ import annotations

import io

import pytest

from proposal_agent.services.pdf import generate_pdf
from proposal_agent.services.proposal import Proposal, PricingLineItem, TimelinePhase


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract readable text from PDF content streams.

    ReportLab uses ASCII85Decode + FlateDecode by default.  We decode
    both layers, then pull text from PDF text-showing operators like
    ``Tj`` and ``TJ``.
    """
    import base64
    import re
    import struct
    import zlib

    def _ascii85_decode(data: bytes) -> bytes:
        """Decode an ASCII85 (btoa) stream ending with ``~>``."""
        # Strip whitespace and the ~> terminator
        text = data.replace(b"\n", b"").replace(b"\r", b"").strip()
        if text.endswith(b"~>"):
            text = text[:-2]

        result = bytearray()
        i = 0
        while i < len(text):
            if text[i:i + 1] == b"z":
                result.extend(b"\x00\x00\x00\x00")
                i += 1
                continue
            chunk = text[i:i + 5]
            i += len(chunk)
            padding = 5 - len(chunk)
            chunk = chunk + b"u" * padding

            acc = 0
            for c in chunk:
                acc = acc * 85 + (c - 33)
            try:
                word = struct.pack(">I", acc)
            except struct.error:
                break
            if padding:
                result.extend(word[: 4 - padding])
            else:
                result.extend(word)
        return bytes(result)

    text_parts: list[str] = []
    raw = pdf_bytes
    idx = 0

    while True:
        start = raw.find(b"stream\n", idx)
        if start == -1:
            start = raw.find(b"stream\r\n", idx)
        if start == -1:
            break
        start = raw.index(b"\n", start) + 1
        end = raw.find(b"endstream", start)
        if end == -1:
            break
        chunk = raw[start:end].strip()
        idx = end + 1

        try:
            decoded = _ascii85_decode(chunk)
            decompressed = zlib.decompress(decoded)
        except Exception:
            try:
                decompressed = zlib.decompress(chunk)
            except Exception:
                continue

        content = decompressed.decode("latin-1", errors="ignore")
        # Extract text from Tj and TJ operators
        for m in re.finditer(r"\(([^)]*)\)\s*Tj", content):
            text_parts.append(m.group(1))
        for m in re.finditer(r"\[(.*?)\]\s*TJ", content):
            for inner in re.finditer(r"\(([^)]*)\)", m.group(1)):
                text_parts.append(inner.group(1))

    return " ".join(text_parts)


class TestGeneratePdf:
    def test_returns_bytes(self, sample_proposal):
        result = generate_pdf(sample_proposal)
        assert isinstance(result, bytes)

    def test_pdf_header_magic(self, sample_proposal):
        result = generate_pdf(sample_proposal)
        assert result[:5] == b"%PDF-"

    def test_pdf_is_nonempty(self, sample_proposal):
        result = generate_pdf(sample_proposal)
        assert len(result) > 500

    def test_pdf_contains_title(self, sample_proposal):
        result = generate_pdf(sample_proposal)
        text = _extract_pdf_text(result)
        assert "E-commerce Dashboard" in text

    def test_pdf_contains_client(self, sample_proposal):
        result = generate_pdf(sample_proposal)
        text = _extract_pdf_text(result)
        assert "Acme Corp" in text

    def test_pdf_contains_pricing_items(self, sample_proposal):
        result = generate_pdf(sample_proposal)
        text = _extract_pdf_text(result)
        assert "Frontend Development" in text
        assert "Backend/API" in text

    def test_minimal_proposal(self):
        p = Proposal(
            client_name="Min",
            project_title="Minimal",
            executive_summary="Short.",
            scope_of_work=["One thing"],
            deliverables=["Deliverable"],
            timeline=[TimelinePhase("P1", "1w", "Do it")],
            pricing=[PricingLineItem("Work", 500)],
            terms_and_conditions="",
        )
        result = generate_pdf(p)
        assert result[:5] == b"%PDF-"

    def test_empty_optional_sections(self):
        p = Proposal(
            client_name="X",
            project_title="Y",
            executive_summary="Z",
            scope_of_work=[],
            deliverables=[],
            timeline=[],
            pricing=[],
            terms_and_conditions="",
            notes="",
        )
        result = generate_pdf(p)
        assert result[:5] == b"%PDF-"
