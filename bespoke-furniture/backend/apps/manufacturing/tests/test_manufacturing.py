import pytest

from apps.delivery.tests.factories import build_delivery_run_with_stops
from apps.manufacturing.models import ManufacturingList, ManufacturingListItem
from apps.manufacturing.services import ManufacturingListAlreadyExists, generate_manufacturing_list

pytestmark = pytest.mark.django_db


class TestGenerateManufacturingList:
    def test_creates_one_item_per_order_item_on_the_run(self):
        run, stops = build_delivery_run_with_stops(n_stops=3)

        manufacturing_list = generate_manufacturing_list(run)

        expected_order_item_ids = {stop.order.items.get().id for stop in stops}
        actual_order_item_ids = set(manufacturing_list.items.values_list("order_item_id", flat=True))
        assert actual_order_item_ids == expected_order_item_ids
        assert manufacturing_list.items.count() == 3

    def test_snapshot_fields_match_the_order_item_at_generation_time(self):
        run, stops = build_delivery_run_with_stops(n_stops=1)
        order_item = stops[0].order.items.get()

        manufacturing_list = generate_manufacturing_list(run)
        item = manufacturing_list.items.get()

        assert item.quantity == order_item.quantity
        assert item.width_mm == order_item.width_mm
        assert item.height_mm == order_item.height_mm
        assert item.depth_mm == order_item.depth_mm

    def test_double_generation_for_the_same_run_is_rejected(self):
        run, _ = build_delivery_run_with_stops(n_stops=1)
        generate_manufacturing_list(run)

        with pytest.raises(ManufacturingListAlreadyExists):
            generate_manufacturing_list(run)

        assert ManufacturingList.objects.filter(delivery_run=run).count() == 1

    def test_no_stops_produces_an_empty_but_valid_list(self):
        run, _ = build_delivery_run_with_stops(n_stops=0)

        manufacturing_list = generate_manufacturing_list(run)

        assert manufacturing_list.items.count() == 0
        assert ManufacturingListItem.objects.filter(manufacturing_list=manufacturing_list).count() == 0
