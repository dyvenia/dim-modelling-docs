// Make the whole label of a collapsible (draft) sidebar section toggle the
// fold — not just the chevron. The chevron keeps mdBook's native handler; this
// only adds click-to-toggle on the section title text.
// Loaded via book.toml `additional-js`.
(function () {
  "use strict";

  document.addEventListener("click", function (e) {
    var wrapper = e.target.closest(".chapter-link-wrapper");
    if (!wrapper) return;

    // Ignore clicks on real links and on the chevron (both are <a>), so we don't
    // double-toggle or block navigation.
    if (e.target.closest("a")) return;

    // Only act on collapsible parents — those that actually have a fold chevron.
    if (!wrapper.querySelector(".chapter-fold-toggle")) return;

    var li = wrapper.closest("li.chapter-item");
    if (li) li.classList.toggle("expanded");
  });
})();
