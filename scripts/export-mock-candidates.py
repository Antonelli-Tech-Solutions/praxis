#!/usr/bin/env python3
"""Export frontend/mock_data.py to React and integration JSON fixtures.

Canonical source: frontend/mock_data.py
Outputs:
  - frontend-react/public/mock-candidates.json (React mock mode)
  - frontend-react/public/mock-graph.json (React graph view fixtures)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND = _REPO_ROOT / "frontend"
_REACT_CANDIDATES = _REPO_ROOT / "frontend-react" / "public" / "mock-candidates.json"
_REACT_GRAPH = _REPO_ROOT / "frontend-react" / "public" / "mock-graph.json"


def main() -> int:
    sys.path.insert(0, str(_FRONTEND))
    from mock_data import get_mock_candidate_dicts, get_mock_graph_dict  # noqa: PLC0415

    rows = get_mock_candidate_dicts()
    candidates_payload = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    _REACT_CANDIDATES.write_text(candidates_payload, encoding="utf-8")
    print(f"Exported {len(rows)} candidates to {_REACT_CANDIDATES}")

    graph = get_mock_graph_dict()
    graph_payload = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    _REACT_GRAPH.write_text(graph_payload, encoding="utf-8")
    print(
        f"Exported graph ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges) "
        f"to {_REACT_GRAPH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
