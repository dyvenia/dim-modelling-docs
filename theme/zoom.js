// Adds a zoom button to every content image and rendered Mermaid diagram, and
// opens a full-screen lightbox with scroll-to-zoom and drag-to-pan.
// Dependency-free. Loaded via book.toml `additional-js`.
(function () {
  "use strict";

  var MAGNIFIER =
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
    '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'd="M10 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zM14.5 14.5L20 20M10 7v6M7 10h6"/></svg>';

  function makeZoomButton(onClick) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "zoom-btn";
    btn.title = "Zoom";
    btn.setAttribute("aria-label", "Zoom");
    btn.innerHTML = MAGNIFIER;
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      onClick();
    });
    return btn;
  }

  // Wrap a target element so we can position a zoom button over it.
  function attach(el) {
    if (el.dataset.zoomReady === "1") return;
    el.dataset.zoomReady = "1";

    var wrap = document.createElement("span");
    wrap.className = "zoomable-wrap";
    // Diagrams are block-level and should fill the content column.
    if (el.classList && el.classList.contains("mermaid")) {
      wrap.classList.add("zoomable-wrap--block");
    }
    el.parentNode.insertBefore(wrap, el);
    wrap.appendChild(el);
    wrap.appendChild(makeZoomButton(function () { openLightbox(el); }));
  }

  // Size the cloned element to ~fill the viewport. Mermaid puts an inline
  // `max-width:<px>` on its <svg>, so we must override it with !important and set
  // an explicit width/height (derived from the viewBox) for the lightbox.
  function fitToViewport(node) {
    var vw = window.innerWidth * 0.92;
    var vh = window.innerHeight * 0.92;
    var svg = node.tagName && node.tagName.toLowerCase() === "svg"
      ? node
      : node.querySelector && node.querySelector("svg");

    if (svg) {
      var ar = 0;
      var vb = svg.viewBox && svg.viewBox.baseVal;
      if (vb && vb.width && vb.height) ar = vb.width / vb.height;
      if (!ar) {
        var r = svg.getBoundingClientRect();
        if (r.width && r.height) ar = r.width / r.height;
      }
      if (!ar) ar = 1;
      var w = vw, h = vw / ar;
      if (h > vh) { h = vh; w = vh * ar; }
      svg.style.setProperty("max-width", "none", "important");
      svg.style.setProperty("width", w + "px", "important");
      svg.style.setProperty("height", h + "px", "important");
    } else if (node.tagName && node.tagName.toLowerCase() === "img") {
      node.style.maxWidth = "92vw";
      node.style.maxHeight = "92vh";
    }
  }

  function openLightbox(srcEl) {
    var overlay = document.createElement("div");
    overlay.className = "zoom-overlay";

    var stage = document.createElement("div");
    stage.className = "zoom-stage";

    var node = srcEl.cloneNode(true);
    node.removeAttribute("data-zoom-ready");
    node.className = (node.className || "").replace("zoomable", "").trim();
    node.classList.add("zoom-content");
    stage.appendChild(node);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "zoom-close";
    close.title = "Close (Esc)";
    close.setAttribute("aria-label", "Close");
    close.innerHTML = "&times;";

    var hint = document.createElement("div");
    hint.className = "zoom-hint";
    hint.textContent = "scroll to zoom · drag to pan · Esc to close";

    overlay.appendChild(stage);
    overlay.appendChild(close);
    overlay.appendChild(hint);
    document.body.appendChild(overlay);
    document.documentElement.classList.add("zoom-open");
    fitToViewport(node); // size to viewport now that it's measurable in the DOM

    // Pan / zoom state.
    var scale = 1, tx = 0, ty = 0, dragging = false, ox = 0, oy = 0;
    function apply() {
      node.style.transform =
        "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
    }

    stage.addEventListener(
      "wheel",
      function (e) {
        e.preventDefault();
        var factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        scale = Math.min(10, Math.max(0.4, scale * factor));
        apply();
      },
      { passive: false }
    );

    node.addEventListener("mousedown", function (e) {
      dragging = true;
      ox = e.clientX - tx;
      oy = e.clientY - ty;
      stage.classList.add("grabbing");
      e.preventDefault();
    });
    function onMove(e) {
      if (!dragging) return;
      tx = e.clientX - ox;
      ty = e.clientY - oy;
      apply();
    }
    function onUp() {
      dragging = false;
      stage.classList.remove("grabbing");
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);

    function destroy() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.removeEventListener("keydown", onKey);
      overlay.remove();
      document.documentElement.classList.remove("zoom-open");
    }
    function onKey(e) {
      if (e.key === "Escape") destroy();
    }
    document.addEventListener("keydown", onKey);
    close.addEventListener("click", destroy);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay || e.target === stage) destroy();
    });
  }

  function scan() {
    var content = document.querySelector(".content") || document.body;

    // Content images (skip tiny inline icons / already-wrapped).
    content.querySelectorAll("img").forEach(function (img) {
      if (img.closest(".zoomable-wrap")) return;
      if (img.naturalWidth && img.naturalWidth < 48) return;
      attach(img);
    });

    // Mermaid diagrams, once rendered into an <svg>.
    content.querySelectorAll("pre.mermaid").forEach(function (pre) {
      if (pre.querySelector("svg")) attach(pre);
    });
  }

  function init() {
    scan();
    // Mermaid renders asynchronously, so re-scan when SVGs appear.
    var content = document.querySelector(".content");
    if (content && "MutationObserver" in window) {
      var pending = false;
      new MutationObserver(function () {
        if (pending) return;
        pending = true;
        requestAnimationFrame(function () {
          pending = false;
          scan();
        });
      }).observe(content, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
