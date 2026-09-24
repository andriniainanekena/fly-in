"""Models for the Fly-in drone simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ZoneType(str, Enum):
    """Zones supported by a map."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def movement_cost(self) -> int:
        """Return the number of turns needed to enter this zone."""
        return 2 if self is ZoneType.RESTRICTED else 1


@dataclass(frozen=True)
class Zone:
    """A named place in the network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = None
    max_drones: int = 1
    unlimited: bool = False


@dataclass(frozen=True)
class Connection:
    """A bidirectional link between two zones."""

    first: str
    second: str
    max_capacity: int = 1

    def other(self, name: str) -> str:
        """Return the endpoint opposite ``name``."""
        return self.second if name == self.first else self.first

    @property
    def label(self) -> str:
        """Return the stable display name for this connection."""
        return f"{self.first}-{self.second}"

    def label_from(self, origin: str) -> str:
        """Return the display label oriented from origin to its target."""
        return f"{origin}-{self.other(origin)}"


@dataclass
class Network:
    """A manually maintained adjacency-list graph."""

    drones_count: int
    zones: dict[str, Zone] = field(default_factory=dict)
    adjacency: dict[str, list[Connection]] = field(default_factory=dict)
    start: Optional[str] = None
    end: Optional[str] = None

    def add_zone(self, zone: Zone, is_start: bool, is_end: bool) -> None:
        """Add a zone and optionally register it as the start or end."""
        self.zones[zone.name] = zone
        self.adjacency[zone.name] = []
        if is_start:
            self.start = zone.name
        if is_end:
            self.end = zone.name

    def add_connection(self, connection: Connection) -> None:
        """Add one undirected connection to both adjacency lists."""
        self.adjacency[connection.first].append(connection)
        self.adjacency[connection.second].append(connection)

    def connection_between(self, first: str, second: str) -> Connection:
        """Find the connection joining two adjacent zones."""
        for connection in self.adjacency[first]:
            if connection.other(first) == second:
                return connection
        raise ValueError(f"No connection between {first} and {second}")


@dataclass
class Drone:
    """Mutable simulation state for a single drone."""

    identifier: int
    route: list[str]
    position: str
    route_index: int = 0
    in_flight_to: Optional[str] = None
    flight_connection: Optional[Connection] = None
    delivered: bool = False

    def next_zone(self) -> Optional[str]:
        """Return this drone's next planned zone, if any."""
        next_index = self.route_index + 1
        return self.route[next_index] if next_index < len(self.route) else None
