#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies iterator block inspector panel API behavior for the iterator block.
# File Name: F8.14_iterator_block_inspector_panel_api.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-06-20
# -----------------------------------------------------------------------------

"""F8.14 - UI modulaire du panneau inspecteur Iterator.

Le test démarre un serveur isolé, demande le rendu du panneau inspecteur
`iterator` depuis `block.py`, puis vérifie que son CSS est exposé. Aucune
donnée utilisateur n'est modifiée hors du serveur de test.
"""

# Test cases:
# - Iterator UI - Render the Iterator inspector panel through the block API.
# - Iterator UI - Verify the panel explains list/item/next ports and serves its CSS asset.
# - Iterator UI - Verify the modal is autonomous and declares block-owned JS.

from __future__ import annotations

from urllib.request import urlopen

from ui_smoke_common import expect, http_json, isolated_server


def main() -> None:
    with isolated_server() as server:
        node = {"id": "iterator-1", "kind": "iterator", "type": "iterator", "title": "Iterator"}
        rendered = http_json(server.base_url, "/api/blocks/iterator/inspector-panel", method="POST", payload={"node": node})
        html = str(rendered.get("html") or "")
        expect("data-iterator-inspector-root" in html, "Le HTML inspecteur iterator doit venir du bloc.")
        expect("liste" in html and "item" in html, "Le panneau iterator doit conserver l'aide utilisateur.")
        assets = rendered.get("assets") or []
        expect({"kind": "css", "path": "assets/css/inspector_panel.css"} in assets, "CSS iterator manquant.")
        with urlopen(f"{server.base_url}/api/blocks/iterator/assets/assets/css/inspector_panel.css", timeout=5) as response:
            body = response.read().decode("utf-8")
        expect("iterator" in body.lower(), "Asset CSS inspecteur iterator non servi.")

        modal = http_json(server.base_url, "/api/blocks/iterator/modal", method="POST", payload={"node": node})
        modal_html = str(modal.get("html") or "")
        modal_assets = modal.get("assets") or []
        expect('data-block-runtime-refresh="autonomous"' in modal_html, "Le modal iterator doit gerer son refresh runtime.")
        expect({"kind": "js", "path": "assets/js/block_modal.js"} in modal_assets, "JS modal iterator manquant.")
        with urlopen(f"{server.base_url}/api/blocks/iterator/assets/assets/js/block_modal.js", timeout=5) as response:
            modal_js = response.read().decode("utf-8")
        expect("registry.iterator" in modal_js, "Asset JS modal iterator non servi.")
    print("[ok] F8.14_iterator_block_inspector_panel_api")


if __name__ == "__main__":
    main()
