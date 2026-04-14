from __future__ import annotations

import io
from typing import BinaryIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from proposal_agent.services.proposal import Proposal

_BRAND_COLOR = colors.HexColor("#2B6CB0")
_LIGHT_BG = colors.HexColor("#EBF4FF")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ProposalTitle",
            parent=base["Title"],
            fontSize=22,
            textColor=_BRAND_COLOR,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ProposalSubtitle",
            parent=base["Normal"],
            fontSize=12,
            textColor=colors.grey,
            spaceAfter=18,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=14,
            textColor=_BRAND_COLOR,
            spaceBefore=16,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ProposalBody",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "ProposalBullet",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=20,
            spaceAfter=4,
        ),
    }


def generate_pdf(proposal: Proposal) -> bytes:
    """Render a :class:`Proposal` to PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    s = _styles()
    story: list = []

    # --- Header ---
    story.append(Paragraph(proposal.project_title, s["title"]))
    story.append(
        Paragraph(
            f"Prepared for {proposal.client_name} &bull; {proposal.date}",
            s["subtitle"],
        )
    )
    story.append(
        HRFlowable(
            width="100%", thickness=1, color=_BRAND_COLOR, spaceAfter=12
        )
    )

    # --- Executive Summary ---
    story.append(Paragraph("Executive Summary", s["heading"]))
    for para in proposal.executive_summary.split("\n\n"):
        story.append(Paragraph(para.strip(), s["body"]))

    # --- Scope of Work ---
    story.append(Paragraph("Scope of Work", s["heading"]))
    for item in proposal.scope_of_work:
        story.append(Paragraph(f"&bull; {item}", s["bullet"]))

    # --- Deliverables ---
    story.append(Paragraph("Deliverables", s["heading"]))
    for item in proposal.deliverables:
        story.append(Paragraph(f"&bull; {item}", s["bullet"]))

    # --- Timeline ---
    story.append(Paragraph("Timeline", s["heading"]))
    timeline_data = [["Phase", "Duration", "Description"]]
    for phase in proposal.timeline:
        timeline_data.append([phase.name, phase.duration, phase.description])
    t = Table(timeline_data, colWidths=[1.8 * inch, 1.2 * inch, 3.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_BG]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(Spacer(1, 4))
    story.append(t)

    # --- Pricing ---
    story.append(Paragraph("Pricing", s["heading"]))
    pricing_data = [["Item", "Amount"]]
    for item in proposal.pricing:
        pricing_data.append([item.description, item.formatted_amount()])
    pricing_data.append(["Total", proposal.formatted_total])

    p = Table(pricing_data, colWidths=[4.5 * inch, 2.0 * inch])
    p.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, _LIGHT_BG]),
                ("BACKGROUND", (0, -1), (-1, -1), _LIGHT_BG),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(Spacer(1, 4))
    story.append(p)

    # --- Terms ---
    if proposal.terms_and_conditions:
        story.append(Paragraph("Terms & Conditions", s["heading"]))
        for para in proposal.terms_and_conditions.split("\n\n"):
            story.append(Paragraph(para.strip(), s["body"]))

    # --- Notes ---
    if proposal.notes:
        story.append(Paragraph("Notes", s["heading"]))
        story.append(Paragraph(proposal.notes, s["body"]))

    doc.build(story)
    return buf.getvalue()
