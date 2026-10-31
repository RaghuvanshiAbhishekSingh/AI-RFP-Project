from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def leaderboard_csv(results: list[dict[str, Any]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["rank", "supplier", "absolute_score", "ppi", "submission_date", "experience_rating"])
    writer.writeheader()
    for item in results:
        writer.writerow({
            "rank": item["final_rank"], "supplier": item["supplier_name"], "absolute_score": item["absolute_score"],
            "ppi": item["ppi"], "submission_date": item["submission_date"], "experience_rating": item["experience_rating"],
        })
    return output.getvalue()


def report_pdf(run: dict[str, Any], results: list[dict[str, Any]]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, title="RFP Evaluation Report")
    styles = getSampleStyleSheet()
    story = [Paragraph("RFP Evaluation Report", styles["Title"]), Spacer(1, 10)]
    story.append(Paragraph(f"Run ID: {run['rfp_run_id']}<br/>Created: {run['created_at']}", styles["BodyText"]))
    story.append(Spacer(1, 12))
    data = [["Rank", "Supplier", "Absolute", "PPI", "Date", "Experience"]]
    for item in results:
        data.append([
            str(item["final_rank"]), item["supplier_name"], f"{float(item['absolute_score']):.2f}",
            f"{float(item['ppi']):.2f}", item["submission_date"], str(item["experience_rating"]),
        ])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([table, Spacer(1, 16)])
    for supplier in results:
        story.append(Paragraph(f"#{supplier['final_rank']} — {supplier['supplier_name']}", styles["Heading2"]))
        story.append(Paragraph(supplier.get("overall_summary") or "No overall summary supplied.", styles["BodyText"]))
        story.append(Spacer(1, 8))
    document.build(story)
    return buffer.getvalue()
