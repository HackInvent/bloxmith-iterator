# Iterator Block

<!-- block-metadata:start -->
[![Block version: 0.1.0](https://img.shields.io/badge/block-0.1.0-blue)](model.json)
[![BloxSmith compatibility: 1.0.9](https://img.shields.io/badge/BloxSmith-1.0.9-brightgreen)](compatibility.json)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Verified BloxSmith versions: **1.0.9** (bundled-block tests; see [test evidence](compatibility.json)).
<!-- block-metadata:end -->


## Role

`iterator` consumes a list and emits one item per trigger value. Feedback edges preserve their
visual/editor marker and may transport runtime trigger values to the trigger input.

## Files

- `block.py`: list parsing, iteration state, output emission.
- `model.json`: list and trigger inputs plus item/index/done/next outputs.
- `node_card.html`: canvas card body rendered by the block-owned UI contract.
- `inspector_panel.html`, `assets/`: inspector UI.
- `assets/js/block_modal.js`: modal-owned mount hook used by the framework to keep the modal stable during polling.

## Ports

- Inputs:
  - `liste` (`id: 1`): optional list payload; accepts `application/json` and `message/*`.
    Each new value received on this port starts a new sequence and resets the cursor,
    even when the payload is identical to the previous list.
  - `trigger` (`id: 2`): explicit trigger input; accepts `control/trigger` and `message/*`.
    A trigger is accepted as soon as a message is received on this input,
    regardless of payload type or textual content. It advances the current sequence
    without resetting the cursor.
- Outputs:
  - `item` (`id: 1`): current item.
  - `index` (`id: 2`): zero-based current index.
  - `done` (`id: 3`): completion signal.
  - `next` (`id: 4`): normal trigger signal output for explicit data/control wiring.

## Configuration

No model config is required. Runtime state tracks the current index and parsed items.

## Runtime Behavior

`execute_runtime()` parses the list input as JSON when possible, falls back to
line-based text, then emits the next item for each explicit trigger event. Any received
message on the trigger input (including empty values) is treated as a trigger.

The `liste` and `trigger` ports are declared as not required for execution. This is
intentional: the block owns the iteration state. A list update resets the sequence,
while trigger updates consume the currently remembered list one item at a time.
This reset is event-driven, not value-diff-driven: republishing the same list is
valid and starts a fresh sequence from the first item.

When all items have been emitted, it emits the `done` output and does not re-emit
`item` or `index`. This prevents downstream item processors from receiving an
empty payload during the terminal pass.

The runtime manifest marks `iterator` as a generic executable worker in both
centralized and active modes, with `active_execution_policy="on_trigger"`. The block owns its list parsing, publication
decisions, and cursor state metadata.

## UI Behavior

The canvas card and inspector are both rendered from templates owned by this
block. The inspector summarizes the iterator and keeps the operational behavior
driven by graph wiring and runtime state.

## Modal

`block_modal.html` is owned by this block and rendered by the generic modal contract. It shows block state and lets users edit supported title/config fields through generic bindings.
The modal declares `data-block-runtime-refresh="autonomous"`; it is a lightweight block-owned surface so runtime polling does not replace the open modal or overwrite draft generic fields before **Apply**.

## Maintenance Notes

Iterator behavior is stateful. Any change to `context.state` keys must preserve compatibility with partial resume and active trigger tests.

## Compatibility policy

[compatibility.json](compatibility.json) records HackInvent's verified BloxSmith versions and test evidence. Only the versions listed above have been verified, using the block-owned suites in a **bundled-block test installation**. This is not a certification of managed-package installation, every browser/OS, or live provider availability. Other framework versions are unverified, not necessarily incompatible.

The block-version badge follows `model.json`, not a published Git tag. `unversioned` means that no block release version is declared; no number is inferred from the framework version. The framework still uses `model.json` for its runtime/install contract; the tester-owned JSON does not replace it. Official integration tests run in the private `bloxmith-blocs` workspace. Test helpers and the proprietary framework are not bundled in this public block repository.

## Properties ergonomics

Modal and inspector styles are owned by this package and scoped to its exact
release. Forms adapt to narrow panels, checkboxes stay beside their labels, and
long values do not widen the inspector. Existing labels are associated with
controls; keyboard navigation complements the block’s own tab handlers.
These presentation helpers do not change port bindings, authored settings,
runtime behavior or the block’s original surface cleanup.
