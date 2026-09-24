"""Dijkstra implementation and route alternatives."""

from __future__ import annotations

import heapq
from itertools import count

from models import Network, ZoneType


class PathFinder:
    """Find low-cost routes."""

    def find_candidates(
        self, network: Network, limit: int = 5
    ) -> list[list[str]]:
        """Return the shortest route."""
        best = self.shortest_path(network, set())
        if best is None:
            return []
        paths = [best]
        for first, second in zip(best, best[1:]):
            alternative = self.shortest_path(
                network, {frozenset((first, second))}
            )
            if alternative is not None and alternative not in paths:
                paths.append(alternative)
            if len(paths) >= limit:
                break
        return paths

    def shortest_path(
        self, network: Network, disabled: set[frozenset[str]]
    ) -> list[str] | None:
        """Use Dijkstra with destination-zone movement costs."""
        if network.start is None or network.end is None:
            return None
        distances: dict[str, tuple[int, int]] = {network.start: (0, 0)}
        previous: dict[str, str] = {}
        serial = count()
        queue: list[tuple[int, int, int, str]] = [
            (0, 0, next(serial), network.start)
        ]
        while queue:
            cost, priority_penalty, _, current = heapq.heappop(queue)
            if (cost, priority_penalty) != distances[current]:
                continue
            if current == network.end:
                return self._rebuild(previous, current)
            for connection in network.adjacency[current]:
                neighbor = connection.other(current)
                if frozenset((current, neighbor)) in disabled:
                    continue
                zone = network.zones[neighbor]
                if zone.zone_type is ZoneType.BLOCKED:
                    continue
                new_distance = (
                    cost + zone.zone_type.movement_cost,
                    priority_penalty
                    - int(zone.zone_type is ZoneType.PRIORITY),
                )
                if new_distance < distances.get(neighbor, (10**18, 0)):
                    distances[neighbor] = new_distance
                    previous[neighbor] = current
                    heapq.heappush(
                        queue,
                        (*new_distance, next(serial), neighbor),
                    )
        return None

    def _rebuild(self, previous: dict[str, str], end: str) -> list[str]:
        """Reconstruct a route from Dijkstra predecessor links."""
        path = [end]
        while path[-1] in previous:
            path.append(previous[path[-1]])
        path.reverse()
        return path
