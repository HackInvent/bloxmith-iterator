#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies active text seed control triggers iterator.
# File Name: F11.21_active_iterator_text_seed_control.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-15
# -----------------------------------------------------------------------------

"""F11.21 - Active control publication of a text trigger into Iterator.

The runtime is prepared without a global trigger. Publishing only the Text seed connected
to the Iterator trigger must also provide the Iterator's list-side input, then
treat the text payload as the trigger message and emit one item.
"""

# Test cases:
# - FB2 - Verify a manually published text seed triggers Iterator in a prepared active runtime.
# - FB2 - Verify trigger publication also publishes required non-trigger sibling inputs.
# - FB3 - Verify Iterator publishes item/index/done/next after the text trigger control action.

import json

from ui_smoke_common import (
    data_edge,
    display_node,
    expect,
    get_run_api,
    graph_payload,
    http_json,
    isolated_server,
    prepare_run_api,
    stop_run_api,
    text_node,
    wait_for_run_predicate,
    wait_for_run_terminal,
)


def active_control(server, run_id: str, action: str, node_id: str) -> dict:
    return http_json(
        server.base_url,
        f"/api/runs/{run_id}/active/control",
        method="POST",
        payload={"action": action, "node_id": node_id},
    )


def list_node() -> dict:
    return {
        "id": "list-1",
        "kind": "list",
        "title": "Needs copy",
        "position": {"x": 150, "y": 250},
        "inputs": [],
        "outputs": [
            {
                "id": 1,
                "name": "liste",
                "title": "Liste",
                "multiplicity": "many",
                "emits": ["application/json", "message/*"],
            }
        ],
        "config": {
            "items": [
                "Les couleurs des blocs doit changer lorsqu'ils sont en cours de run, et retourner a leur couleur initiale apres",
                "Creation d'un mode de visualisation d'un texte pour mettre en evidence les premiers blocs et liens connectes au bloc selectionne",
            ]
        },
    }


def iterator_node() -> dict:
    return {
        "id": "iterator-1",
        "kind": "iterator",
        "title": "Iterator 1",
        "position": {"x": 710, "y": 240},
        "inputs": [
            {"id": 1, "name": "liste", "title": "Liste", "multiplicity": "many", "accepts": ["application/json", "message/*"]},
            {"id": 2, "name": "trigger", "title": "Trigger", "multiplicity": "many", "accepts": ["control/trigger", "message/*"]},
        ],
        "outputs": [
            {"id": 1, "name": "item", "title": "Item", "multiplicity": "many", "emits": ["message/*"]},
            {"id": 2, "name": "index", "title": "Index", "multiplicity": "many", "emits": ["message/*"]},
            {"id": 3, "name": "done", "title": "Done", "multiplicity": "many", "emits": ["message/*"]},
            {"id": 4, "name": "next", "title": "Next", "multiplicity": "many", "emits": ["control/trigger", "message/*"]},
        ],
        "config": {},
    }


def document() -> dict:
    return graph_payload(
        "F11 active iterator text seed control",
        [
            list_node(),
            text_node("text-1", "Text Source", "go", 220, 460),
            iterator_node(),
            display_node("display-item", "Iterator item", 1310, 80),
        ],
        [
            data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
            data_edge("edge-text-trigger", "text-1", 1, "iterator-1", 2),
            data_edge("edge-iterator-item", "iterator-1", 1, "display-item", 1),
        ],
    )


def main() -> None:
    with isolated_server() as server:
        prepared = prepare_run_api(server, document(), runtime_mode="zeromq_active")
        run_id = str(prepared.get("run_id") or "")
        expect(run_id, "prepare doit retourner un run_id.")
        prepared_nodes = prepared.get("graph", {}).get("nodes", [])
        text_id = next(str(node.get("id") or "") for node in prepared_nodes if node.get("kind") == "text")
        iterator_id = next(str(node.get("id") or "") for node in prepared_nodes if node.get("kind") == "iterator")

        active_control(server, run_id, "publish_seed", text_id)
        state = wait_for_run_predicate(
            server,
            run_id,
            lambda item: f"{iterator_id}:1" in (item.get("output_values") or {}),
            "L'iterator actif n'a pas publie d'item apres publication du trigger texte.",
            timeout_sec=5,
        )
        expect(state.get("status") == "prepared", "Le runtime actif doit rester charge apres publication ciblee.")
        item = state.get("output_values", {}).get(f"{iterator_id}:1", {})
        expect(json.loads(str(item.get("value") or "{}")) == {"item": list_node()["config"]["items"][0]}, "Le premier item doit etre emis.")
        logs = "\n".join(state.get("node_logs", {}).get(iterator_id, []))
        expect("item 1/2 emis" in logs, f"Iterator doit traiter le texte comme trigger actif. Logs: {logs}")

        stop_run_api(server, run_id)
        wait_for_run_terminal(server, run_id, timeout_sec=10)
        get_run_api(server, run_id)
    print("[ok] F11.21_active_iterator_text_seed_control")


if __name__ == "__main__":
    main()
