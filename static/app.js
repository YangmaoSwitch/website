(function () {
  // model square filters
  var mgrid = document.getElementById("mgrid");
  if (mgrid) {
    var mq = document.getElementById("mq"), macc = document.getElementById("macc"), mprov = document.getElementById("mprov"),
      mcount = document.getElementById("mcount"), seg = document.getElementById("mcap"), cap = "";
    var mcards = Array.prototype.slice.call(mgrid.querySelectorAll(".mcard"));
    var mapply = function () {
      var text = mq.value.trim().toLowerCase(), shown = 0;
      mcards.forEach(function (c) {
        var acc = c.dataset.access;
        var ok = (!text || c.dataset.search.indexOf(text) >= 0) &&
          (!cap || (" " + c.dataset.caps + " ").indexOf(" " + cap + " ") >= 0) &&
          (!mprov.value || c.dataset.providers.indexOf(" " + mprov.value + " ") >= 0) &&
          (!macc.value || (macc.value === "free" ? acc === "free" : acc !== "paid"));
        c.hidden = !ok;
        if (ok) shown++;
      });
      mcount.textContent = "显示 " + shown + " 个";
    };
    seg.addEventListener("click", function (ev) {
      var b = ev.target.closest("button");
      if (!b) return;
      cap = b.dataset.v;
      seg.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      mapply();
    });
    [mq, macc, mprov].forEach(function (el) { el.addEventListener("input", mapply); });
    mapply();
  }

  // providers filters
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
