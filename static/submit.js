(function () {
  var root = document.getElementById("submit-app");
  if (!root) return;
  var API = root.dataset.api, T = JSON.parse(root.dataset.text), LANG = root.dataset.lang;
  var $ = function (id) { return document.getElementById(id); };
  var KEY = "ym_token";

  if (!API) { $("s-unavailable").hidden = false; return; }

  // GitHub sign-in returns the token in the URL fragment; keep it and clean the address bar
  var m = /[#&]token=([^&]+)/.exec(location.hash);
  if (m) {
    localStorage.setItem(KEY, decodeURIComponent(m[1]));
    history.replaceState(null, "", location.pathname + location.search);
  }

  function errText(e) {
    var code = e && e.code;
    return T.errors[code] || (code === "validation" ? T.errors.invalid : (e && e.message) || T.errors.network);
  }

  function call(method, path, body) {
    var h = { "Content-Type": "application/json" };
    var tok = localStorage.getItem(KEY);
    if (tok) h.Authorization = "Bearer " + tok;
    return fetch(API + path, { method: method, headers: h, body: body ? JSON.stringify(body) : undefined })
      .catch(function () { throw { code: "network" }; })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (r.ok) return j;
          if (r.status === 401) localStorage.removeItem(KEY);
          if (r.status === 422) throw { code: "validation" };
          throw (j && j.detail) || { code: "network" };
        });
      });
  }

  function msg(el, text, ok) {
    el.textContent = text || "";
    el.className = "form-msg" + (text ? (ok ? " ok" : " bad") : "");
  }

  // ---- signed out
  function showLogin() {
    $("s-main").hidden = true;
    $("s-login").hidden = false;
    call("GET", "/api/health").then(function (h) {
      if (h.github) { $("s-gh").hidden = false; $("s-gh-or").hidden = false; }
    }).catch(function () {});
  }

  var timer = null;
  $("s-send").addEventListener("click", function () {
    var btn = this, email = $("s-email").value.trim();
    if (!$("s-email").checkValidity() || !email) { msg($("s-login-msg"), T.errors.bad_email); $("s-email").focus(); return; }
    btn.disabled = true;
    call("POST", "/api/auth/email/send", { email: email, lang: LANG }).then(function (r) {
      msg($("s-login-msg"), "");
      var n = r.resend_after || 60;
      $("s-code").focus();
      timer = setInterval(function () {
        n -= 1;
        btn.textContent = n > 0 ? T.resend.replace("{n}", n) : T.send;
        if (n <= 0) { clearInterval(timer); btn.disabled = false; }
      }, 1000);
    }).catch(function (e) { btn.disabled = false; msg($("s-login-msg"), errText(e)); });
  });

  $("s-login").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var code = $("s-code").value.trim();
    if (!/^\d{6}$/.test(code)) { msg($("s-login-msg"), T.errors.code_wrong); $("s-code").focus(); return; }
    call("POST", "/api/auth/email/verify", { email: $("s-email").value.trim(), code: code, client: "web" }).then(function (r) {
      localStorage.setItem(KEY, r.token);
      showMain(r.user);
    }).catch(function (e) { msg($("s-login-msg"), errText(e)); });
  });

  $("s-gh").addEventListener("click", function () {
    location.href = API + "/api/auth/github/start?client=web&redirect=" + encodeURIComponent(location.origin + location.pathname);
  });

  // ---- signed in
  function showMain(user) {
    $("s-login").hidden = true;
    $("s-main").hidden = false;
    $("s-who").textContent = T.signed_in.replace("{who}", user.email || user.github_login || "");
    loadMine();
  }

  $("s-logout").addEventListener("click", function () {
    call("POST", "/api/auth/logout").catch(function () {}).then(function () { localStorage.removeItem(KEY); showLogin(); });
  });

  function loadMine() {
    call("GET", "/api/submissions/mine").then(function (list) {
      var ul = $("s-mine");
      ul.textContent = "";
      if (!list.length) { var li = document.createElement("li"); li.className = "muted"; li.textContent = T.none; ul.appendChild(li); return; }
      list.forEach(function (s) {
        var li = document.createElement("li");
        var head = document.createElement("div");
        var b = document.createElement("b"); b.textContent = s.title;
        var st = document.createElement("span"); st.className = "mtag " + (s.status === "done" || s.status === "accepted" ? "ok" : s.status === "open" ? "blue" : ""); st.textContent = T.status[s.status] || s.status;
        var when = document.createElement("span"); when.className = "muted small"; when.textContent = new Intl.DateTimeFormat(LANG === "zh" ? "zh-CN" : "en", { dateStyle: "medium" }).format(new Date(s.created_at * 1000));
        head.appendChild(b); head.appendChild(st); head.appendChild(when);
        li.appendChild(head);
        if (s.admin_note) { var n = document.createElement("p"); n.className = "small"; n.textContent = T.note + s.admin_note; li.appendChild(n); }
        ul.appendChild(li);
      });
    }).catch(function () {});
  }

  // prefill from the page that linked here
  var q = new URLSearchParams(location.search);
  if (q.get("kind") && T.kinds[q.get("kind")]) $("s-kind").value = q.get("kind");
  if (q.get("target")) $("s-target").value = q.get("target");
  var pageUrl = q.get("page") ? new URL(q.get("page"), location.href).href : null;

  $("s-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var f = this, btn = f.querySelector("button[type=submit]");
    if (!f.checkValidity()) { f.reportValidity(); return; }
    btn.disabled = true;
    call("POST", "/api/submissions", {
      kind: $("s-kind").value, target: $("s-target").value.trim() || null, title: $("s-title").value.trim(),
      body: $("s-body").value.trim(), evidence_url: $("s-evidence").value.trim() || null, page_url: pageUrl, lang: LANG
    }).then(function () {
      msg($("s-msg"), T.sent_ok, true);
      $("s-title").value = ""; $("s-body").value = ""; $("s-evidence").value = "";
      loadMine();
    }).catch(function (e) {
      if (e && e.code === "not_signed_in") showLogin();
      msg($("s-msg"), errText(e));
    }).then(function () { btn.disabled = false; });
  });

  if (localStorage.getItem(KEY)) call("GET", "/api/me").then(showMain).catch(showLogin);
  else showLogin();
})();
