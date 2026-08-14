"""
PDF export of a finalized delivery run, for drivers.

ReportLab is chosen over WeasyPrint specifically because the primary dev
environment is native Windows: ReportLab is pure-Python with prebuilt wheels
and no native system dependency, whereas WeasyPrint needs GTK/Pango
installed system-wide -- real setup friction for a coursework build. Worth
revisiting for a future Linux/Docker deployment.
"""

import io

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import DeliveryRun
from .export_csv import COLUMNS, build_run_rows


def export_run_pdf(run: DeliveryRun) -> HttpResponse:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Delivery run {run.pk}")
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Delivery Run #{run.pk} — {run.run_date}", styles["Title"]))
    elements.append(Paragraph(f"Van: {run.van} &nbsp;&nbsp; Driver: {run.driver or 'Unassigned'}", styles["Normal"]))
    if run.total_duration_min:
        elements.append(Paragraph(f"Estimated total duration: {run.total_duration_min:.0f} min", styles["Normal"]))
    elements.append(Spacer(1, 10 * mm))

    rows = build_run_rows(run)
    table_data = [COLUMNS] + [[str(cell) for cell in row] for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3d2b1f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf7f2")]),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="delivery_run_{run.pk}_{run.run_date}.pdf"'
    return response
