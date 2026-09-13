#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies active partial resume from a text trigger into iterator.
# File Name: F11.20_active_iterator_resume_from_text_trigger.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-15
# -----------------------------------------------------------------------------

"""F11.20 - Active resume from a text trigger into Iterator.

The graph is `list -> iterator.list` plus `text -> iterator.trigger`.
After a normal active run, recomputing from the text trigger must replay the
text seed and trigger one iterator step with the reused list payload.
"""

# Test cases:
# - FB2 - Verify any data message on Iterator trigger input is accepted during active partial resume.
# - FB3 - Verify the resumed Iterator publishes item/index/done/next outputs from the text trigger.

import json

from ui_smoke_common import (
    create_run_api,
    data_edge,
    display_node,
    expect,
    graph_payload,
    isolated_server,
    resume_from_node_api,
    text_node,
    wait_for_run_terminal,
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
            {
                "id": 1,
                "name": "liste",
                "title": "Liste",
                "multiplicity": "many",
                "accepts": ["application/json", "message/*"],
                "required": True,
            },
            {
                "id": 2,
                "name": "trigger",
                "title": "Trigger",
                "multiplicity": "many",
                "accepts": ["control/trigger", "message/*"],
                "required": True,
            },
        ],
        "outputs": [
            {"id": 1, "name": "item", "title": "Item", "multiplicity": "many", "emits": ["message/*"]},
            {"id": 2, "name": "index", "title": "Index", "multiplicity": "many", "emits": ["message/*"]},
            {"id": 3, "name": "done", "title": "Done", "multiplicity": "many", "emits": ["message/*"]},
            {
                "id": 4,
                "name": "next",
                "title": "Next",
                "multiplicity": "many",
                "emits": ["control/trigger", "message/*"],
            },
        ],
        "config": {},
    }


def document() -> dict:
    return graph_payload(
        "F11 active iterator resume from text trigger",
        [
            list_node(),
            text_node("text-1", "Text Source", "go", 220, 460),
            iterator_node(),
            display_node("display-item", "Iterator item", 1310, 80),
            display_node("display-index", "Iterator index", 1310, 230),
            display_node("display-done", "Iterator done", 1310, 380),
            display_node("display-next", "Iterator next", 1170, 510),
        ],
        [
            data_edge("edge-list-iterator", "list-1", 1, "iterator-1", 1),
            data_edge("edge-text-trigger", "text-1", 1, "iterator-1", 2),
            data_edge("edge-iterator-item", "iterator-1", 1, "display-item", 1),
            data_edge("edge-iterator-index", "iterator-1", 2, "display-index", 1),
            data_edge("edge-iterator-done", "iterator-1", 3, "display-done", 1),
            data_edge("edge-iterator-next", "iterator-1", 4, "display-next", 1),
        ],
    )


def main() -> None:
    with isolated_server() as server:
        created = create_run_api(server, document(), runtime_mode="zeromq_active")
        source_run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=20)
        expect(source_run.get("status") == "success", "Le run actif initial doit reussir.")
        expect(source_run.get("iterator_cursors", {}).get("iterator-1") == 1, "Le run initial doit declencher un item.")

        resumed_created = resume_from_node_api(
            server,
            str(source_run.get("run_id") or ""),
            "text-1",
            document=document(),
        )
        resumed = wait_for_run_terminal(server, str(resumed_created.get("run_id") or ""), timeout_sec=20)
        logs = "\n".join(resumed.get("logs", []))
        item = resumed.get("output_values", {}).get("iterator-1:1", {})

        expect(resumed.get("status") == "success", "La reprise depuis le trigger texte doit reussir.")
        expect(resumed.get("runtime_mode") == "zeromq_active", "La reprise doit rester en runtime actif.")
        expect(resumed.get("iterator_cursors", {}).get("iterator-1") == 1, "Iterator doit avancer d'un pas en reprise.")
        expect(json.loads(str(item.get("value") or "{}")) == {"item": list_node()["config"]["items"][0]}, "Le premier item doit etre republie.")
        expect("trigger batch 1" in logs, "Iterator doit traiter le texte comme trigger en reprise.")
        expect("trigger(s) ignore" not in logs, "Le trigger texte ne doit pas etre ignore.")
    print("[ok] F11.20_active_iterator_resume_from_text_trigger")


if __name__ == "__main__":
    main()
