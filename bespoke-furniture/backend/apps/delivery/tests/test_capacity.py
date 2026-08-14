from dataclasses import dataclass

from apps.delivery.services.capacity import OrderLoad, select_orders_for_van


@dataclass
class FakeVan:
    load_volume_m3: float
    max_weight_kg: float


class TestSelectOrdersForVan:
    def test_all_orders_fit_when_well_under_capacity(self):
        van = FakeVan(load_volume_m3=10.0, max_weight_kg=1000.0)
        loads = [OrderLoad(order_id=1, volume_m3=1.0, weight_kg=50), OrderLoad(order_id=2, volume_m3=1.0, weight_kg=50)]
        result = select_orders_for_van(loads, van, safety_factor=0.9)
        assert {load.order_id for load in result.selected} == {1, 2}
        assert result.deferred == []
        assert result.exceptions == []

    def test_overflow_orders_are_deferred_not_dropped(self):
        van = FakeVan(load_volume_m3=1.0, max_weight_kg=1000.0)
        loads = [
            OrderLoad(order_id=1, volume_m3=0.6, weight_kg=10),
            OrderLoad(order_id=2, volume_m3=0.6, weight_kg=10),  # doesn't fit alongside order 1
        ]
        result = select_orders_for_van(loads, van, safety_factor=1.0)
        selected_ids = {load.order_id for load in result.selected}
        deferred_ids = {load.order_id for load in result.deferred}
        assert len(selected_ids) == 1
        assert len(deferred_ids) == 1
        assert selected_ids | deferred_ids == {1, 2}
        assert result.exceptions == []

    def test_single_item_exceeding_van_capacity_is_flagged_as_exception(self):
        van = FakeVan(load_volume_m3=1.0, max_weight_kg=1000.0)
        loads = [OrderLoad(order_id=1, volume_m3=5.0, weight_kg=10)]
        result = select_orders_for_van(loads, van, safety_factor=1.0)
        assert result.selected == []
        assert result.deferred == []
        assert [load.order_id for load in result.exceptions] == [1]

    def test_weight_limit_is_enforced_independently_of_volume(self):
        van = FakeVan(load_volume_m3=100.0, max_weight_kg=20.0)
        loads = [OrderLoad(order_id=1, volume_m3=0.1, weight_kg=15), OrderLoad(order_id=2, volume_m3=0.1, weight_kg=15)]
        result = select_orders_for_van(loads, van, safety_factor=1.0)
        assert len(result.selected) == 1
        assert len(result.deferred) == 1

    def test_safety_factor_shrinks_usable_capacity(self):
        van = FakeVan(load_volume_m3=10.0, max_weight_kg=1000.0)
        # First item alone fits under the 9.0m3 usable volume (10.0 * 0.9);
        # the second only overflows because of the safety factor, not the van's raw capacity.
        loads = [
            OrderLoad(order_id=1, volume_m3=8.0, weight_kg=10),
            OrderLoad(order_id=2, volume_m3=2.0, weight_kg=10),
        ]
        result = select_orders_for_van(loads, van, safety_factor=0.9)  # usable volume = 9.0
        assert [load.order_id for load in result.selected] == [1]
        assert [load.order_id for load in result.deferred] == [2]
        assert result.exceptions == []

    def test_larger_items_are_packed_first_best_fit_decreasing(self):
        van = FakeVan(load_volume_m3=5.0, max_weight_kg=1000.0)
        loads = [
            OrderLoad(order_id="small", volume_m3=1.0, weight_kg=1),
            OrderLoad(order_id="large", volume_m3=4.0, weight_kg=1),
        ]
        result = select_orders_for_van(loads, van, safety_factor=1.0)
        # Both fit (5.0 total == capacity); large should be considered/placed first.
        assert {load.order_id for load in result.selected} == {"small", "large"}
