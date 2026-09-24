"""Parser for Fly-in map files."""

from __future__ import annotations

import re
from pathlib import Path

from models import Connection, Network, Zone, ZoneType


class MapParseError(ValueError):
    """A map input error with a line number."""


class MapParser:
    """Read and validate a text map into a Network."""

    _ZONE = re.compile(
        r"^(start_hub|end_hub|hub):\s+(\S+)\s+(-?\d+)\s+(-?\d+)"
        r"(?:\s+\[([^\]]*)\])?$"
    )
    _CONNECTION = re.compile(
        r"^connection:\s+(\S+)-(\S+)(?:\s+\[([^\]]*)\])?$"
    )

    def parse_file(self, path: str | Path) -> Network:
        """Parse a map file, translating file errors into map errors."""
        try:
            with Path(path).open(encoding="utf-8") as source:
                return self.parse_lines(source.readlines())
        except OSError as error:
            raise MapParseError(f"Unable to read map: {error}") from error

    def parse_lines(self, lines: list[str]) -> Network:
        """Parse lines from a map file."""
        network: Network | None = None
        seen_connections: set[frozenset[str]] = set()
        for number, raw_line in enumerate(lines, start=1):
            line = raw_line.split("#", maxsplit=1)[0].strip()
            if not line:
                continue
            if line.startswith("nb_drones:"):
                if network is not None:
                    self._error(number, "duplicate drone count")
                value = line.removeprefix("nb_drones:").strip()
                if not value.isdigit() or int(value) <= 0:
                    self._error(
                        number, "drone count must be a positive integer"
                    )
                network = Network(drones_count=int(value))
                continue
            if network is None:
                self._error(number, "first definition must be nb_drones")
            assert network is not None
            zone_match = self._ZONE.match(line)
            if zone_match is not None:
                self._parse_zone(network, zone_match, number)
                continue
            connection_match = self._CONNECTION.match(line)
            if connection_match is not None:
                self._parse_connection(
                    network, connection_match, seen_connections, number
                )
                continue
            self._error(number, "invalid syntax")
        if network is None:
            raise MapParseError("Line 1: missing drone count")
        if network.start is None or network.end is None:
            raise MapParseError(
                "Map must define exactly one start_hub and one end_hub"
            )
        return network

    def _parse_zone(
        self, network: Network, match: re.Match[str], line: int
    ) -> None:
        kind, name, x_text, y_text, metadata_text = match.groups()
        if "-" in name:
            self._error(line, "zone names cannot contain dashes")
        if name in network.zones:
            self._error(line, f"duplicate zone '{name}'")
        if kind == "start_hub" and network.start is not None:
            self._error(line, "duplicate start_hub")
        if kind == "end_hub" and network.end is not None:
            self._error(line, "duplicate end_hub")
        metadata = self._metadata(
            metadata_text, {"zone", "color", "max_drones"}, line
        )
        zone_name = metadata.get("zone", "normal")
        try:
            zone_type = ZoneType(zone_name)
        except ValueError as error:
            self._error(line, f"invalid zone type '{zone_name}'")
            raise error
        unlimited = kind in {"start_hub", "end_hub"}
        capacity = 1 if unlimited else self._positive(
            metadata.get("max_drones", "1"), line, "max_drones"
        )
        network.add_zone(
            Zone(
                name, int(x_text), int(y_text), zone_type,
                metadata.get("color"), capacity, unlimited,
            ),
            kind == "start_hub", kind == "end_hub",
        )

    def _parse_connection(
        self,
        network: Network,
        match: re.Match[str],
        seen: set[frozenset[str]],
        line: int,
    ) -> None:
        first, second, metadata_text = match.groups()
        if first not in network.zones or second not in network.zones:
            self._error(line, "connections must use previously defined zones")
        if first == second:
            self._error(line, "a connection cannot join a zone to itself")
        key = frozenset((first, second))
        if key in seen:
            self._error(line, "duplicate connection")
        metadata = self._metadata(metadata_text, {"max_link_capacity"}, line)
        capacity = self._positive(
            metadata.get("max_link_capacity", "1"),
            line,
            "max_link_capacity",
        )
        network.add_connection(Connection(first, second, capacity))
        seen.add(key)

    def _metadata(
        self, text: str | None, allowed: set[str], line: int
    ) -> dict[str, str]:
        if text is None:
            return {}
        result: dict[str, str] = {}
        for item in text.split():
            if "=" not in item:
                self._error(line, "metadata must use key=value")
            key, value = item.split("=", maxsplit=1)
            if not key or not value or key not in allowed or key in result:
                self._error(line, f"invalid metadata '{item}'")
            result[key] = value
        return result

    def _positive(self, text: str, line: int, label: str) -> int:
        if not text.isdigit() or int(text) <= 0:
            self._error(line, f"{label} must be a positive integer")
        return int(text)

    def _error(self, line: int, message: str) -> None:
        raise MapParseError(f"Line {line}: {message}")