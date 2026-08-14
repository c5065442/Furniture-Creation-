"""
Select which candidate orders fit into a given van's load, using a greedy
best-fit-decreasing heuristic on volume then weight -- not full 3D bin
packing, which would be far more complex than this problem warrants for a
handful of large furniture items per run.

Orders that don't fit this run are deferred to the next one, never silently
dropped. An order that alone exceeds the van's capacity is flagged as an
exception for staff to handle manually (e.g. a dedicated one-item run).
"""

from dataclasses import dataclass

from apps.orders.models import Order


@dataclass
class OrderLoad:
    order_id: int
    volume_m3: float
    weight_kg: float


@dataclass
class CapacityResult:
    selected: list[OrderLoad]
    deferred: list[OrderLoad]
    exceptions: list[OrderLoad]  # single order alone exceeds van capacity


def compute_order_load(order: Order) -> OrderLoad:
    volume_m3 = 0.0
    weight_kg = 0.0
    for item in order.items.filter(requires_van=True):
        item_volume_m3 = (item.width_mm * item.height_mm * item.depth_mm) / 1_000_000_000
        volume_m3 += item_volume_m3 * item.quantity
        weight_kg += float(item.weight_kg) * item.quantity
    return OrderLoad(order_id=order.id, volume_m3=volume_m3, weight_kg=weight_kg)


def select_orders_for_van(loads: list[OrderLoad], van, safety_factor: float) -> CapacityResult:
    max_volume = van.load_volume_m3 * safety_factor
    max_weight = float(van.max_weight_kg) * safety_factor

    selected: list[OrderLoad] = []
    deferred: list[OrderLoad] = []
    exceptions: list[OrderLoad] = []

    used_volume = 0.0
    used_weight = 0.0

    # Best-fit-decreasing: place the largest items first for better packing.
    for load in sorted(loads, key=lambda item: (item.volume_m3, item.weight_kg), reverse=True):
        if load.volume_m3 > max_volume or load.weight_kg > max_weight:
            exceptions.append(load)
            continue
        if used_volume + load.volume_m3 <= max_volume and used_weight + load.weight_kg <= max_weight:
            selected.append(load)
            used_volume += load.volume_m3
            used_weight += load.weight_kg
        else:
            deferred.append(load)

    return CapacityResult(selected=selected, deferred=deferred, exceptions=exceptions)
