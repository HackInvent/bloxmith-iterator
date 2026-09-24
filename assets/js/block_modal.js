import { withProperties } from "./properties.js";

/**
 * Role: Mounts the Iterator block modal frontend.
 * File Name: block_modal.js
 * Author: Alexandre EL
 * Email: alex@hackinvent.com
 * Created Date: 2026-06-10
 */

/**
 * Mark the Iterator modal as block-owned while generic fields, ports,
 * runtime state, and Apply stay handled by the framework modal API.
 *
 * @param {HTMLElement} root - Mounted Iterator modal root.
 */
function mountOwned(root) {
  if (root instanceof HTMLElement) {
    root.dataset.iteratorModalMounted = "true";
  }
}

/** Keep the block behavior and add properties-only accessibility. */
export function mount(root, ...args) {
  return withProperties(mountOwned).call(this, root, ...args);
}
