/**
 * Role: Mounts the Iterator block modal frontend.
 * File Name: block_modal.js
 * Author: Alexandre EL
 * Email: alex@hackinvent.com
 * Created Date: 2026-06-10
 */

(function () {
  "use strict";

  const registry = (window.CWBlockUiBlocks = window.CWBlockUiBlocks || {});

  registry.iterator = {
    /**
     * Mark the Iterator modal as block-owned while generic fields, ports,
     * runtime state, and Apply stay handled by the framework modal API.
     *
     * @param {HTMLElement} root - Mounted Iterator modal root.
     */
    mount(root) {
      if (root instanceof HTMLElement) {
        root.dataset.iteratorModalMounted = "true";
      }
    },
  };
})();
