"""
report.py
---------
Renders the "Export PDF Reconstruction Report" button's payload (a full
world_model dict, as sent by IncidentExplanationPanel.jsx) into an actual
PDF using reportlab.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def build_report_pdf(world_model: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=18)
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story = []
    story.append(Paragraph("Automated 3D Post-Incident Reconstruction Report", title_style))
    story.append(Paragraph("Orchestrated Multi-Agent World Models &mdash; nuScenes Mini", styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    sample_token = world_model.get("sample_token", "unknown")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sim = world_model.get("simulation")
    meta_rows = [
        ["Sample Token", sample_token],
        ["Generated", generated_at],
        ["Scenario", sim["scenario_name"] if sim else "Ground Truth (no counterfactual)"],
    ]
    meta_table = Table(meta_rows, colWidths=[1.8 * inch, 4.5 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.2 * inch))

    explanation = world_model.get("incident_explanation", {})
    story.append(Paragraph(f"Risk Assessment: {explanation.get('risk_level', 'LOW')}", h2))
    story.append(Paragraph(explanation.get("title", ""), styles["Heading3"]))
    story.append(Paragraph(explanation.get("narrative", "No narrative generated."), body))
    story.append(Spacer(1, 0.15 * inch))

    metrics = world_model.get("prediction_metrics", {})
    story.append(Paragraph("Trajectory Forecast Accuracy", h2))
    story.append(
        Paragraph(
            f"Average Displacement Error (ADE): {metrics.get('ade_meters', 'n/a')} m &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Final Displacement Error (FDE): {metrics.get('fde_meters', 'n/a')} m",
            body,
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    breakdown = explanation.get("causality_breakdown", [])
    if breakdown:
        story.append(Paragraph("Causality Risk Breakdown", h2))
        rows = [["Factor", "Value", "Impact"]] + [
            [b.get("factor", ""), str(b.get("value", "")), b.get("impact", "")] for b in breakdown
        ]
        table = Table(rows, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.15 * inch))

    interactions = world_model.get("interactions", [])
    story.append(Paragraph(f"Elevated-Risk Interactions ({len(interactions)})", h2))
    if interactions:
        rows = [["Category", "Risk", "Closest Approach (m)"]] + [
            [i.get("category", ""), i.get("risk_level", ""), str(i.get("closest_approach_m", ""))]
            for i in interactions
        ]
        table = Table(rows, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No elevated-risk interactions detected in this sample.", body))

    story.append(Spacer(1, 0.2 * inch))
    agent_telemetry = world_model.get("agent_telemetry", [])
    if agent_telemetry:
        story.append(Paragraph("Multi-Agent Pipeline Execution", h2))
        rows = [["Agent", "Status", "Time (ms)"]] + [
            [a.get("agent_name", ""), a.get("status", ""), str(a.get("execution_time_ms", ""))]
            for a in agent_telemetry
        ]
        table = Table(rows, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return buf.getvalue()
