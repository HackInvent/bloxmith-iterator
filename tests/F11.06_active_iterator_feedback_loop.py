#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies active iterator consumes feedback transport edges.
# File Name: F11.06_active_iterator_feedback_loop.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-03-01
# -----------------------------------------------------------------------------

"""F11.06 - Feedback actif minimal en ZeroMQ active.

Le test lance `list + trigger -> iterator -> display` avec
`iterator.next --feedback--> iterator.trigger`. Il vérifie que le worker
iterator reste actif, consomme son propre feedback borné et avance jusqu'au
dernier item sans fallback centralisé.
"""

# Test cases:
# - FB2/FB3/FB5 - Verify feedback next -> trigger edge drives a bounded active iterator loop.

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
        "config": {"items": ["alpha", "beta", "gamma"]},
    }


def iterator_node() -> dict:
    return {
        "id": "iterator-1",
        "kind": "iterator",
        "title": "Iterator feedback visuel",
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
            "F11 active iterator feedback",
            [
                list_node(),
                text_node("trigger-1", "Trigger", "go", 80, 260),
                iterator_node(),
                display_node("display-1", "Affichage", 720, 140),
            ],
            [
                data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
                data_edge("edge-trigger-iterator", "trigger-1", 1, "iterator-1", 2),
                feedback_edge(
                    "edge-iterator-next",
                    "iterator-1",
                    4,
                    "iterator-1",
                    2,
                ),
                data_edge("edge-iterator-display", "iterator-1", 1, "display-1", 1),
            ],
        )
        created = create_run_api(server, document, runtime_mode="zeromq_active")
        run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=20)

        expect(run.get("status") == "success", "Le run iterator avec feedback visuel doit réussir.")
        expect(run.get("iterator_cursors", {}).get("iterator-1") == 3, "Le curseur iterator attendu est 3 après boucle feedback bornée.")
        expect("feedback_iterations" not in run, "Le run ne doit plus exposer de compteur feedback.")
        item = run.get("output_values", {}).get("iterator-1:1", {})
        expect(json.loads(str(item.get("value") or "{}")) == {"item": "gamma"}, "Le dernier item émis doit être gamma.")
        logs = "\n".join(run.get("node_logs", {}).get("iterator-1", []))
        expect("policy on_trigger" in logs, "La policy on_trigger doit être loggée.")
        expect(logs.count("trigger batch") >= 3, "Le feedback doit déclencher les batches iterator successifs.")
        expect("fallback centralized" not in "\n".join(run.get("logs", [])), "Le run ne doit pas fallback centralisé.")
    print("[ok] F11.06_active_iterator_feedback_loop")


if __name__ == "__main__":
    main()
