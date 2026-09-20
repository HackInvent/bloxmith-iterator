#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies iterator one by one behavior for the iterator block.
# File Name: F5.02_iterator_one_by_one.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-05-14
# -----------------------------------------------------------------------------

"""F5.02 - Item-by-item Iterator with a trigger.

The test wires `list -> iterator`, adds an initial trigger, then loops
`iterator.next -> iterator.trigger` back as feedback. It checks that the
feedback really carries the trigger, that the cursor advances item by item
during the run and that the last wrapper item is published.
"""

# Test cases:
# - FB1/FB2/FB3/FB4/FB5 - Verify feedback transports Iterator next triggers in centralized runtime.
# - FB3/FB5 - Verify the iterator advances item by item and publishes item/index/done/next outputs.

import json

from ui_smoke_common import (
    create_run_api,
    data_edge,
    display_node,
    expect,
    feedback_edge,
    graph_payload,
    isolated_server,
    text_node,
    wait_for_run_terminal,
)


def list_node(items: list[str]) -> dict:
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
                "emits": ["application/json", "message/*"],
                "multiplicity": "many",
            }
        ],
        "config": {"items": items},
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
            "F5 Iterator",
            [
                list_node(["alpha", "beta", "gamma"]),
                text_node("trigger-1", "Trigger initial", "go", 80, 260),
                iterator_node(),
                display_node("display-1", "Affichage", 680, 120),
            ],
            [
                data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
                data_edge("edge-trigger-iterator", "trigger-1", 1, "iterator-1", 2),
                data_edge("edge-iterator-display", "iterator-1", 1, "display-1", 1),
                feedback_edge("edge-iterator-next", "iterator-1", 4, "iterator-1", 2),
            ],
        )
        created = create_run_api(server, document)
        run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=20)
        expect(run.get("status") == "success", "The iterator run must succeed.")
        expect(run.get("iterator_cursors", {}).get("iterator-1") == 3, "The iterator cursor must reach 3 after the feedback triggers.")
        expect("feedback_iterations" not in run, "The run must no longer expose a feedback counter.")
        iterator_item = run.get("output_values", {}).get("iterator-1:1", {})
        expect(
            json.loads(str(iterator_item.get("value") or "{}")) == {"item": "gamma"},
            "The expected last wrapper item is {\"item\":\"gamma\"}.",
        )
        expect(iterator_item.get("content_type") == "application/json", "The wrapper item must be application/json.")
        expect(run.get("output_values", {}).get("iterator-1:2", {}).get("value") == "2", "L'index final attendu est 2.")

        logs = "\n".join(str(line) for line in run.get("logs", []))
        expect("item 1/3 emis" in logs and "item 2/3 emis" in logs and "item 3/3 emis" in logs, "The feedback must trigger the following items.")
        display_value = str(run.get("worker_rows", {}).get("display-1", {}).get("received") or "")
        expect("alpha" in display_value and "beta" in display_value and "gamma" in display_value, "Display must receive the three items.")
    print("[ok] F5.02_iterator_one_by_one")


if __name__ == "__main__":
    main()
