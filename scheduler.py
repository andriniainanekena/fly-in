"""Deterministic distribution of drones."""

from __future__ import annotations

from models import Network, ZoneType


class RouteScheduler:
    """Assign each drone one route using cost and current route load."""

    def assign(
        self, network: Network, candidates: list[list[str]]
    ) -> list[list[str]]:
        """Return one selected route for every drone."""
        if not candidates:
            raise ValueError("No route exists from start to end")
        loads = [0 for _ in candidates]
        result: list[list[str]] = []
        for _ in range(network.drones_count):
            index = min(
                range(len(candidates)),
                key=lambda item: self._score(
                    network, candidates[item], loads[item], item
                ),
            )
            loads[index] += 1
            result.append(candidates[index])
        return result

    def _cost(self, network: Network, route: list[str]) -> int:
        """Calculate a route's destination-zone movement cost."""
        return sum(
            network.zones[name].zone_type.movement_cost
            for name in route[1:]
        )

    def _score(
        self, network: Network, route: list[str], load: int, index: int
    ) -> tuple[int, int, int]:
        """Prefer lower cost and, on ties, routes with priority zones."""
        priority_count = sum(
            network.zones[name].zone_type is ZoneType.PRIORITY
            for name in route[1:]
        )
        return (self._cost(network, route) + load, -priority_count, index)
