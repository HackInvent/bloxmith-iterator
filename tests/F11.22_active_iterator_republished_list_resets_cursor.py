#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies active iterator cursor reset when a list is republished.
# File Name: F11.22_active_iterator_republished_list_resets_cursor.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-06-10
# -----------------------------------------------------------------------------

"""F11.22 - Active Iterator resets when the list input is republished.

The active runtime keeps Iterator workers alive. Replaying an upstream seed can
publish the exact same list payload again; that must start a fresh iteration
sequence instead of keeping the previous cursor.
"""

# Test cases:
# - FB2 - A trigger advances the Iterator cursor on an existing list.
# - FB2 - Republishing the same list resets the cursor before the next trigger.

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
                "required": False,
                "execution_requirement": "not_required_for_execution",
            },
            {
                "id": 2,
                "name": "trigger",
                "title": "Trigger",
                "accepts": ["control/trigger", "message/*"],
                "multiplicity": "many",
                "required": False,
                "execution_requirement": "not_required_for_execution",
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


def document() -> dict:
    return graph_payload(
        "F11 active iterator republished list reset",
        [
            list_node(),
            text_node("trigger-1", "Trigger", "go", 80, 280),
            iterator_node(),
            display_node("display-1", "Affichage", 720, 140),
        ],
        [
            data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
            data_edge("edge-trigger-iterator", "trigger-1", 1, "iterator-1", 2),
            data_edge("edge-iterator-display", "iterator-1", 1, "display-1", 1),
        ],
    )


def wait_for_iterator_index(server, run_id: str, expected: str, log_marker: str) -> dict:
    return wait_for_run_predicate(
        server,
        run_id,
        lambda item: (
            str((item.get("output_values") or {}).get("iterator-1:2", {}).get("value") or "") == expected
            and log_marker in "\n".join((item.get("node_logs") or {}).get("iterator-1", []))
        ),
        f"Iterator n'a pas atteint l'index attendu {expected}.",
        timeout_sec=8,
    )


def main() -> None:
    with isolated_server() as server:
        prepared = prepare_run_api(server, document(), runtime_mode="zeromq_active")
        run_id = str(prepared.get("run_id") or "")
        expect(run_id, "prepare doit retourner un run_id.")

        active_control(server, run_id, "publish_seed", "list-1")
        active_control(server, run_id, "publish_seed", "trigger-1")
        wait_for_iterator_index(server, run_id, "0", "item 1/2 emis")

        active_control(server, run_id, "publish_seed", "trigger-1")
        wait_for_iterator_index(server, run_id, "1", "item 2/2 emis")

        active_control(server, run_id, "publish_seed", "list-1")
        active_control(server, run_id, "publish_seed", "trigger-1")
        state = wait_for_iterator_index(server, run_id, "0", "nouvelle liste recue, curseur reinitialise")

        item = state.get("output_values", {}).get("iterator-1:1", {})
        expect(json.loads(str(item.get("value") or "{}")) == {"item": "alpha"}, "A republished list must restart from the first item.")
        logs = "\n".join(state.get("node_logs", {}).get("iterator-1", []))
        expect(logs.count("item 1/2 emis") >= 2, "Le premier item doit etre emis avant et apres republication de la liste.")

        stop_run_api(server, run_id)
        wait_for_run_terminal(server, run_id, timeout_sec=10)
        get_run_api(server, run_id)
    print("[ok] F11.22_active_iterator_republished_list_resets_cursor")


if __name__ == "__main__":
    main()
