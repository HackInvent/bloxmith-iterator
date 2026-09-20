# -----------------------------------------------------------------------------
# Role: Implements the iterator block runtime and UI contract.
# File Name: block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2024-12-18
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from bloxsmith_app.block_api import (
    APPLICATION_JSON,
    BlockDefinition,
    BlockRuntimeContext,
    BlockRuntimeOutput,
    BlockRuntimeResult,
    CONTROL_TRIGGER,
    render_inspector_template,
    render_node_card_template,
    TEXT_PLAIN,
)


# Functional behavior:
# FB1 - Parse an input JSON list or line-based fallback list.
# FB2 - Keep an iterator cursor in runtime state and emit one item per trigger.
# FB3 - Emit item, index, done, and next outputs with correct emitted flags/content types.
# FB4 - Support wrapper items {"item": value} while preserving JSON/plain-text output types.
# FB5 - Emit a normal next trigger output that can drive feedback transport loops.
class IteratorBlock(BlockDefinition):
    """Autonomous block implementation for `IteratorBlock`."""
    kind = "iterator"

    def render_node_card(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the Iterator canvas card body from the block-owned template.

        Args:
            node: Serialized iterator node being rendered.
            payload: Optional UI payload, currently unused for iterator cards.

        Returns:
            Block UI payload used by the generic canvas shell.
        """

        return render_node_card_template(
            block=self,
            node=node,
            node_classes=["iterator-node"],
            replacements={
                "title": node.get("title") or self.default_title(),
                "summary": "List -> one item per trigger",
                "ports": "item, index, done, next",
            },
        )

    def render_inspector_panel(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the iterator inspector panel from its block-owned template.

        Args:
            node: Serialized iterator node being inspected.
            payload: Optional server/UI rendering payload.

        Returns:
            Inspector HTML plus context for the frontend shell.
        """

        template = (self.directory / "inspector_panel.html").read_text(encoding="utf-8")
        html = render_inspector_template(
            template=template,
            node={**node, "type": self.kind, "kind": self.kind},
            payload=payload,
        )
        return {"html": html, "context": {"node_id": str(node.get("id") or ""), "full_panel": True}}

    def execute_runtime(self, context: BlockRuntimeContext) -> BlockRuntimeResult:
        """Emit one list item and update the iterator cursor for a runtime tick.

        Args:
            context: Runtime inputs, output ports, and mutable iterator state.

        Returns:
            Runtime outputs for item/index/done/next and metadata containing the next cursor.
        """

        trigger_input_has_value = context.input_attribute("trigger", "2") is not None
        trigger_events = tuple(
            event
            for event in getattr(context, "input_events", ())
            if int(event.input_port_id or 0) == 2 or str(event.input_port_name or "").strip().lower() == "trigger"
        )
        has_trigger = bool(trigger_events) or trigger_input_has_value
        items = self.parse_items(context.input_value("liste", "1") or context.input_message)
        reset_requested = bool(context.state.get("iterator_reset_cursor"))
        cursor = 0 if reset_requested else max(0, int(context.state.get("iterator_cursor") or 0))
        exhausted = cursor >= len(items)
        has_next = not exhausted and cursor + 1 < len(items)
        next_cursor = cursor if exhausted else cursor + 1
        item_value, item_content_type = ("", TEXT_PLAIN) if exhausted else self.serialize_item(items[cursor])
        values_by_name = {
            "item": (item_value, item_content_type, not exhausted),
            "index": ("" if exhausted else str(cursor), TEXT_PLAIN, not exhausted),
            "done": ("true" if exhausted else "false", TEXT_PLAIN, True),
            "next": ("true" if has_next else "", CONTROL_TRIGGER, has_next),
        }

        outputs: list[BlockRuntimeOutput] = []
        for port in context.output_ports:
            name = str(getattr(port, "name", "") or "").strip().lower()
            if not name:
                port_id = int(getattr(port, "id", 0) or 0)
                name = {1: "item", 2: "index", 3: "done", 4: "next"}.get(port_id, "")
            if name not in values_by_name:
                continue
            value, content_type, emitted = values_by_name[name]
            outputs.append(
                BlockRuntimeOutput(
                    port_id=int(getattr(port, "id", 0) or 0),
                    port_name=str(getattr(port, "name", "") or ""),
                    value=value,
                    content_type=content_type,
                    emitted=emitted,
                )
            )

        logs = []
        if reset_requested:
            logs.append(f"[iterator] {context.node_id}: nouvelle liste recue, curseur reinitialise.")
        if not has_trigger:
            logs.append("[iterator-warn] No trigger received; one pass still runs to stay compatible.")
        if exhausted:
            logs.append(f"[iterator] {context.node_id}: liste terminee ({len(items)} item(s)).")
        else:
            logs.append(f"[iterator] {context.node_id}: item {cursor + 1}/{len(items)} emis.")
            if has_next:
                logs.append(f"[iterator] {context.node_id}: next emis, item suivant disponible.")
        logs.append(
            f"[done] Iterator {context.node_id}: {len(items)} item(s), "
            f"curseur={next_cursor}, item courant={cursor if not exhausted else 'termine'}."
        )
        return BlockRuntimeResult(
            status="success",
            outputs=outputs,
            logs=logs,
            last_message=item_value or ("true" if exhausted else "false"),
            worker_received=item_value or ("true" if exhausted else "false") or "-",
            metadata={"iterator_cursor": next_cursor, "item_count": len(items)},
        )

    def parse_items(self, raw_value: Any) -> list[Any]:
        """Parse an iterator input payload into a Python list of item values.

        Args:
            raw_value: JSON list, JSON object with list-like keys, plain list, or line-based text.

        Returns:
            Normalized item values ready to be emitted one by one.
        """

        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            return [self.parse_item_value(item) for item in raw_value]
        text = str(raw_value or "").strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [self.parse_item_value(item) for item in parsed]
        if isinstance(parsed, dict):
            for key in ("items", "liste", "list", "values"):
                values = parsed.get(key)
                if isinstance(values, list):
                    return [self.parse_item_value(item) for item in values]
        return [self.parse_item_value(line.strip()) for line in text.splitlines() if line.strip()]

    def parse_item_value(self, item: Any) -> Any:
        """Decode one string item as JSON when possible while preserving plain text.

        Args:
            item: Raw item value from a list or text line.

        Returns:
            JSON-decoded value, original text, or the non-string value unchanged.
        """

        if not isinstance(item, str):
            return item
        text = item.strip()
        if not text:
            return ""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return item

    def serialize_item(self, item: Any) -> tuple[str, str]:
        """Serialize one item and report its content type.

        Args:
            item: Current iterator item value.

        Returns:
            Tuple of output value and content type.
        """

        if isinstance(item, str):
            return item, TEXT_PLAIN
        return json.dumps(item, ensure_ascii=False), APPLICATION_JSON
