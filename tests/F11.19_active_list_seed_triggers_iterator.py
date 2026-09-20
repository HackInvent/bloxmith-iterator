#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies active list seed triggers iterator behavior for the iterator block.
# File Name: F11.19_active_list_seed_triggers_iterator.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-04-07
# -----------------------------------------------------------------------------

"""F11.19 - Targeted publication of a List to an active Iterator.

The test prepares a `zeromq_active` run with no global trigger, publishes the `list`
seed only, then checks that the'iterator reçoit la liste et émet le premier item.
Il utilise un serveur isolé et ne modifie pas les données utilisateur.
"""

# Test cases:
# - FB1/FB2/FB3 - Prepare an active runtime without a global trigger and publish one List seed manually.
# - FB2 - Verify the subscribed Iterator receives the list and emits the first item.

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
            {
                "id": 1,
                "name": "liste",
                "title": "Liste",
                "accepts": ["application/json", "message/*"],
                "multiplicity": "many",
            },
            {
                "id": 2,
                "name": "trigger",
                "title": "Trigger",
                "accepts": ["control/trigger", "message/*"],
                "multiplicity": "many",
            },
        ],
        "outputs": [
            {"id": 1, "name": "item", "title": "Item", "emits": ["message/*"], "multiplicity": "many"},
            {"id": 2, "name": "index", "title": "Index", "emits": ["message/*"], "multiplicity": "many"},
            {"id": 3, "name": "done", "title": "Done", "emits": ["message/*"], "multiplicity": "many"},
            {
                "id": 4,
                "name": "next",
                "title": "Next",
                "emits": ["control/trigger", "message/*"],
                "multiplicity": "many",
            },
        ],
        "config": {},
    }


def main() -> None:
    with isolated_server() as server:
        document = graph_payload(
            "F11 active list seed iterator",
            [
                list_node(),
                iterator_node(),
                display_node("display-1", "Affichage", 720, 140),
            ],
            [
                data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
                data_edge("edge-iterator-display", "iterator-1", 1, "display-1", 1),
            ],
        )
        prepared = prepare_run_api(server, document, runtime_mode="zeromq_active")
        run_id = str(prepared.get("run_id") or "")
        expect(run_id, "prepare doit retourner un run_id.")

        active_control(server, run_id, "publish_seed", "list-1")
        state = wait_for_run_predicate(
            server,
            run_id,
            lambda item: "iterator-1:1" in (item.get("output_values") or {}),
            "The active iterator published no item after the list was published.",
            timeout_sec=5,
        )
        expect(state.get("status") == "prepared", "The active runtime must stay loaded after a targeted publication.")
        stop_run_api(server, run_id)
        final_state = wait_for_run_terminal(server, run_id, timeout_sec=10)
        state = get_run_api(server, run_id) or final_state

        item = state.get("output_values", {}).get("iterator-1:1", {})
        expect(json.loads(str(item.get("value") or "{}")) == {"item": "alpha"}, "The iterator must emit the first item.")
        expect(state.get("output_values", {}).get("iterator-1:2", {}).get("value") == "0", "L'index attendu est 0.")
        logs = "\n".join(state.get("node_logs", {}).get("iterator-1", []))
        expect("declenchement initial" in logs, "Le déclenchement initial par liste doit être loggé.")
    print("[ok] F11.19_active_list_seed_triggers_iterator")


if __name__ == "__main__":
    main()
