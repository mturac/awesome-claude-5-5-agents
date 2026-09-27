(function () {
  var root = document.documentElement;
  var body = document.body;
  var input = document.getElementById("q");
  var count = document.getElementById("count");
  var empty = document.getElementById("empty");
  var themeButton = document.getElementById("theme");
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-entry]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("[data-section]"));
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".nav a"));
  var total = cards.length;

  function themeName() {
    return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function applyTheme(theme, persist) {
    root.setAttribute("data-theme", theme);
    themeButton.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    if (persist) {
      try {
        localStorage.setItem("theme", theme);
      } catch (err) {}
    }
  }

  themeButton.addEventListener("click", function () {
    applyTheme(themeName() === "dark" ? "light" : "dark", true);
  });

  function applyFilter() {
    var query = input.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var hay = card.getAttribute("data-entry") || "";
      var match = !query || hay.indexOf(query) !== -1;
      card.hidden = !match;
      if (match) {
        shown += 1;
      }
    });
    sections.forEach(function (section) {
      var kind = section.getAttribute("data-section");
      if (kind === "entries") {
        section.hidden = !section.querySelector("[data-entry]:not([hidden])");
        return;
      }
      if (!query) {
        section.hidden = false;
        return;
      }
      var text = section.getAttribute("data-text") || "";
      section.hidden = text.indexOf(query) === -1;
    });
    navLinks.forEach(function (link) {
      var id = (link.getAttribute("href") || "").slice(1);
      var section = document.getElementById(id);
      link.hidden = !!(section && section.hidden);
    });
    empty.hidden = shown !== 0;
    count.textContent = query ? shown + " of " + total : total + " entries";
    body.classList.toggle("is-filtering", query.length > 0);
  }

  var params = new URLSearchParams(location.search);
  var requested = params.get("theme");
  if (requested === "dark" || requested === "light") {
    applyTheme(requested, true);
  } else {
    applyTheme(themeName(), false);
  }
  if (params.get("q")) {
    input.value = params.get("q");
  }
  input.addEventListener("input", applyFilter);
  applyFilter();
})();
