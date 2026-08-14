import csv
import io

import pytest

from apps.delivery.services.export_csv import export_run_csv
from apps.delivery.services.export_pdf import export_run_pdf
from apps.delivery.tests.factories import build_delivery_run_with_stops

pytestmark = pytest.mark.django_db


class TestExportCsv:
    def test_header_row_matches_expected_columns(self):
        run, _ = build_delivery_run_with_stops(n_stops=2)
        response = export_run_csv(run)

        reader = csv.reader(io.StringIO(response.content.decode()))
        header = next(reader)
        assert header == [
            "Sequence", "Load position", "Order #", "Customer", "Address", "Postcode",
            "Item", "SKU", "Qty", "Dimensions (mm)", "Weight (kg)", "Has design attachment", "Phone",
        ]

    def test_one_row_per_order_item_in_sequence_order(self):
        run, stops = build_delivery_run_with_stops(n_stops=2)
        response = export_run_csv(run)

        reader = csv.reader(io.StringIO(response.content.decode()))
        next(reader)  # header
        rows = list(reader)

        assert len(rows) == 2
        assert [int(row[0]) for row in rows] == [1, 2]  # sequence order
        assert rows[0][2] == stops[0].order.order_number

    def test_response_is_a_csv_attachment(self):
        run, _ = build_delivery_run_with_stops(n_stops=1)
        response = export_run_csv(run)
        assert response["Content-Type"] == "text/csv"
        assert "attachment" in response["Content-Disposition"]


class TestExportPdf:
    def test_response_has_pdf_content_type_and_nonempty_body(self):
        run, _ = build_delivery_run_with_stops(n_stops=2)
        response = export_run_pdf(run)
        assert response["Content-Type"] == "application/pdf"
        assert len(response.content) > 0
        assert response.content.startswith(b"%PDF")
