#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies iterator block inspector panel API behavior for the iterator block.
# File Name: F8.14_iterator_block_inspector_panel_api.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-06-20
# -----------------------------------------------------------------------------

"""F8.14 - Modular UI of the Iterator inspector panel.

The test starts an isolated server, renders the `iterator` inspector panel from
`block.py`, then checks that its CSS is exposed. No user data is modified
outside the test server.
"""

# Test cases:
# - Iterator UI - Render the Iterator inspector panel through the block API.
# - Iterator UI - Verify the panel explains list/item/next ports and serves its CSS asset.
# - Iterator UI - Verify the modal is autonomous and declares block-owned JS.

from __future__ import annotations

from urllib.parse import quote
from urllib.request import urlopen

from ui_smoke_common import expect, http_json, isolated_server
from block_test_packages import install_test_package, release_key, surface_payload


def main() -> None:
    with isolated_server() as server:
        # Surfaces are release assets: a bundled kind serves none of them.
        model = install_test_package(server, "iterator")
        key = quote(release_key(model), safe="")
        served = lambda payload, suffix: next(
            asset["path"] for asset in payload["assets"] if asset["path"].endswith(suffix))
        node = {"id": "iterator-1", "kind": "iterator", "type": "iterator", "block_version": model["version"], "title": "Iterator"}
        rendered = surface_payload(server, model, node, "inspector_panel")
        html = str(rendered.get("html") or "")
        expect("data-iterator-inspector-root" in html, "The iterator inspector HTML must come from the block.")
        expect("liste" in html and "item" in html, "The iterator panel must keep the user help.")
        assets = rendered.get("assets") or []
        with urlopen(f"{server.base_url}/api/blocks/{key}/assets/{served(rendered, 'assets/css/inspector_panel.css')}", timeout=5) as response:
            body = response.read().decode("utf-8")
        expect("iterator" in body.lower(), "Asset CSS inspecteur iterator non servi.")

        modal = surface_payload(server, model, node, "modal")
        modal_html = str(modal.get("html") or "")
        modal_assets = modal.get("assets") or []
        expect('data-block-runtime-refresh="autonomous"' in modal_html, "The iterator modal must own its runtime refresh.")
        with urlopen(f"{server.base_url}/api/blocks/{key}/assets/{served(modal, 'assets/js/block_modal.js')}", timeout=5) as response:
            modal_js = response.read().decode("utf-8")
        expect("export function mount" in modal_js, "Asset JS modal iterator non servi.")
    print("[ok] F8.14_iterator_block_inspector_panel_api")


if __name__ == "__main__":
    main()
