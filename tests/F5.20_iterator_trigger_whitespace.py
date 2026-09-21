#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Validates iterator trigger handling for messages that are not empty in a
# trimmed-text sense.
# File Name: F5.20_iterator_trigger_whitespace.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-15
# -----------------------------------------------------------------------------

"""F5.20 - Whitespace text messages still trigger Iterator.

This test sends a trigger message made only of spaces. The Iterator must treat
the input event itself as the trigger, even when the textual payload becomes
empty after trimming.
"""

# Test cases:
# - FB1/FB2 - Verify Iterator advances when a whitespace text event reaches the trigger input.
# - FB3 - Verify the missing-trigger warning is not emitted.

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
        "title": "Liste test",
        "position": {"x": 80, "y": 80},
        "inputs": [],
        "outputs": [
            {
                "id": 1,
                "name": "liste",
                "title": "Liste",
                "accepts": ["application/json", "message/*"],
                "multiplicity": "many",
                "emits": ["application/json", "message/*"],
            }
        ],
        "config": {"items": ["alpha"]},
    }


def iterator_node() -> dict:
    return {
        "id": "iterator-1",
        "kind": "iterator",
        "title": "Iterator test",
        "position": {"x": 360, "y": 120},
        "inputs": [
            {
                "id": 1,
                "name": "liste",
                "title": "Liste",
                "accepts": ["application/json", "message/*"],
                "multiplicity": "many",
                "required": True,
            },
            {
                "id": 2,
                "name": "trigger",
                "title": "Trigger",
                "accepts": ["control/trigger", "message/*"],
                "multiplicity": "many",
                "required": True,
            },
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
            "F5 iterator trigger whitespaces",
            [
                list_node(),
                text_node("trigger-1", "Trigger", "   ", 80, 260),
                iterator_node(),
                display_node("display-1", "Affichage", 680, 120),
            ],
            [
                data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
                data_edge("edge-trigger-iterator", "trigger-1", 1, "iterator-1", 2),
                data_edge("edge-iterator-display", "iterator-1", 1, "display-1", 1),
            ],
        )
        created = create_run_api(server, document)
        run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=20)
        expect(run.get("status") == "success", "Iterator run must succeed.")
        expect(run.get("iterator_cursors", {}).get("iterator-1") == 1, "Iterator cursor must be 1.")
        last_item = run.get("output_values", {}).get("iterator-1:1", {}).get("value") or ""
        expect("alpha" in str(last_item), "Iterator item must be published.")
        logs = "\n".join(str(line) for line in run.get("logs", []))
        expect("No trigger received" not in logs, "Whitespace trigger must not be treated as missing.")
    print("[ok] F5.20_iterator_trigger_whitespace")


if __name__ == "__main__":
    main()
