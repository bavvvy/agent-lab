from __future__ import annotations

from typing import Any, Dict, Protocol


class ScientistInterface(Protocol):
    """Defined interface boundary for Node -> Scientist communication.

    Node should only hand off structured payloads and receive structured results.
    """

    def process_allocation_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...
