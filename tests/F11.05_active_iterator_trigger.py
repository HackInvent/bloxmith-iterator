#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies active iterator trigger behavior for the iterator block.
# File Name: F11.05_active_iterator_trigger.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-01-24
# -----------------------------------------------------------------------------

"""F11.05 - Iterator actif sur plusieurs triggers.

Le test lance `list + 2 triggers -> iterator -> display` en `zeromq_active`.
L'iterator doit rester une instance active, avancer deux fois son curseur et
publier le dernier item.
"""

# Test cases:
# - FB1/FB2/FB3/FB4 - Run Iterator in active runtime with multiple trigger messages.
# - FB2/FB3 - Verify the active iterator advances its cursor and publishes the latest item.

import json

from ui_smoke_common import (
    create_run_api,
    data_edge,
    display_node,
    expect,
    graph_payload,
    isolated_server,
    text_node,
    wait_for_run_terminal,
)


def list_node() -> dict:
    return {
        "id": "list-1",
        "kind": "list",
        "title": "Liste active",
        "position": {"x": 80, "y": 80},
        "inputs": [],
        "outputs": [
            {
                "id": 1,
                "name": "liste",
                "title": "Liste",
                "emits": ["application/json", "message/*"],
                "multiplicity": "many",
            }
        ],
        "config": {"items": ["alpha", "beta"]},
    }


def iterator_node() -> dict:
    return {
        "id": "iterator-1",
        "kind": "iterator",
        "title": "Iterator actif",
        "position": {"x": 380, "y": 140},
        "inputs": [
            {"id": 1, "name": "liste", "title": "Liste", "accepts": ["application/json", "message/*"], "multiplicity": "many"},
            {"id": 2, "name": "trigger", "title": "Trigger", "accepts": ["control/trigger", "message/*"], "multiplicity": "many"},
        ],
        "outputs": [
            {"id": 1, "name": "item", "title": "Item", "emits": ["message/*"], "multiplicity": "many"},
            {"id": 2, "name": "index", "title": "Index", "emits": ["message/*"], "multiplicity": "many"},
            {"id": 3, "name": "done", "title": "Done", "emits": ["message/*"], "multiplicity": "many"},
            {"id": 4, "name": "next", "title": "Next", "emits": ["control/trigger", "message/*"], "multiplicity": "many"},
        ],
        "config": {},
    }


def main() -> None:
    with isolated_server() as server:
        document = graph_payload(
            "F11 active iterator",
            [
                list_node(),
                text_node("trigger-a", "Trigger A", "go-1", 80, 240),
                text_node("trigger-b", "Trigger B", "go-2", 80, 360),
                iterator_node(),
                display_node("display-1", "Affichage", 720, 140),
            ],
            [
                data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
                data_edge("edge-trigger-a", "trigger-a", 1, "iterator-1", 2),
                data_edge("edge-trigger-b", "trigger-b", 1, "iterator-1", 2),
                data_edge("edge-iterator-display", "iterator-1", 1, "display-1", 1),
            ],
        )
        created = create_run_api(server, document, runtime_mode="zeromq_active")
        run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=20)

        expect(run.get("status") == "success", "The active iterator run must succeed.")
        expect(run.get("iterator_cursors", {}).get("iterator-1") == 2, "The expected iterator cursor is 2.")
        item = run.get("output_values", {}).get("iterator-1:1", {})
        expect(json.loads(str(item.get("value") or "{}")) == {"item": "beta"}, "The last item must be beta.")
        expect(run.get("output_values", {}).get("iterator-1:2", {}).get("value") == "1", "The last index must be 1.")
        logs = "\n".join(run.get("node_logs", {}).get("iterator-1", []))
        expect("policy on_trigger" in logs, "La policy on_trigger doit être loggée.")
        expect("trigger batch 1" in logs and "trigger batch 2" in logs, "Iterator doit traiter deux triggers.")
        expect(logs.count("[active-worker] iterator-1: instance ") == 1, "Iterator doit rester une seule instance.")
    print("[ok] F11.05_active_iterator_trigger")


if __name__ == "__main__":
    main()
