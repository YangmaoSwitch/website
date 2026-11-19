(function () {
  var grid = document.getElementById("grid");
  if (!grid) return;
  var q = document.getElementById("q"), region = document.getElementById("region"), overage = document.getElementById("overage"),
    apiOnly = document.getElementById("api"), l3 = document.getElementById("l3"), count = document.getElementById("count");
  var cards = Array.prototype.slice.call(grid.querySelectorAll(".card"));
  function apply() {
    var text = q.value.trim().toLowerCase(), shown = 0;
    cards.forEach(function (c) {
      var tags = " " + c.dataset.tags + " ";
      var ok = (!text || c.dataset.search.indexOf(text) >= 0) &&
        (!region.value || tags.indexOf(" " + region.value + " ") >= 0) &&
        (!overage.value || tags.indexOf(" " + overage.value + " ") >= 0) &&
        (!apiOnly.checked || tags.indexOf(" api ") >= 0) &&
        (!l3.checked || tags.indexOf(" L3 ") >= 0);
      c.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = "显示 " + shown + " 个";
  }
  [q, region, overage, apiOnly, l3].forEach(function (el) { el.addEventListener("input", apply); });
  apply();
})();
