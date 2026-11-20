#!/usr/bin/env python3
"""Render the YangmaoSwitch website into ./public.

Data comes from the catalog repo's `dist` branch:
* catalog.json – platforms and their free quotas (with official evidence);
* models.json  – every platform's model list (free / covered by the free quota / paid, list prices)
                 and the merged model square.

Usage: python build.py [catalog.json] [models.json]   (paths or URLs; default: the published files)
"""
import hashlib
import html
import json
import pathlib
import re
import shutil
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "public"
DIST = "https://raw.githubusercontent.com/YangmaoSwitch/catalog/dist"
REPO = "https://github.com/YangmaoSwitch"

UNIT = {"requests": "次", "tokens": "tokens", "input_tokens": "输入 tokens", "output_tokens": "输出 tokens", "credits": "额度",
        "points": "积分", "neurons": "Neurons", "usd": "美元", "cny": "元"}
PERIOD = {"second": "每秒", "minute": "每分钟", "hour": "每小时", "day": "每天", "week": "每周", "month": "每月", "one-time": "一次性"}
REQUIRES = {"email": "邮箱", "phone": "手机号", "phone_cn": "大陆手机号", "card": "信用卡", "real_name": "实名", "company": "企业认证",
            "github": "GitHub 账号", "google": "Google 账号", "cloud_account": "云账号"}
OVERAGE = {"blocked": "用完即停", "auto_paid": "用完自动转付费", "manual": "需手动开通付费", "unknown": "未知"}
LEVEL = {"L1": "手动添加 Key", "L2": "粘贴 Key 自动识别", "L3": "一键开通"}
ACCESS = {"free": ("免费模型", "ok"), "quota": ("用免费额度", "blue"), "paid": ("付费", "")}
MODAL = {"text": "文本", "image": "图片", "video": "视频", "audio": "音频", "file": "文件"}
RANK = {"free": 0, "quota": 1, "paid": 2}
COLORS = ["#c2410c", "#1d4ed8", "#047857", "#6d28d9", "#b91c1c", "#0369a1", "#a16207", "#0f766e", "#be185d", "#4338ca"]

e = html.escape


def load(src: str) -> dict:
    if src.startswith("http"):
        with urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": "YangmaoSwitch-website"}), timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(pathlib.Path(src).read_text(encoding="utf-8"))


def latest_release() -> dict | None:
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/YangmaoSwitch/app/releases/latest", headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def avatar(name: str, seed: str, cls: str = "av") -> str:
    color = COLORS[sum(map(ord, seed)) % len(COLORS)]
    letters = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", name)[:2] or "?"
    letters = letters[0] if re.match(r"[\u4e00-\u9fff]", letters) else letters[:1].upper() + letters[1:2].lower()
    return f'<span class="{cls}" style="--c:{color}">{e(letters)}</span>'


def quota_text(q: dict) -> str:
    if q.get("amount") is None:
        parts = [f"{PERIOD.get(q['period'], q['period'])}有上限（按{UNIT.get(q['unit'], q['unit'])}计，数值见平台页面）"]
    else:
        amount = f"{q['amount']:,.0f}" if float(q["amount"]).is_integer() else str(q["amount"])
        parts = [f"{PERIOD.get(q['period'], q['period'])} {amount} {UNIT.get(q['unit'], q['unit'])}"]
    for k in ("models", "condition"):
        if q.get(k):
            parts.append(q[k])
    if q.get("reset") and q["reset"] != "rolling":
        parts.append(f"{q['reset']} 重置")
    if q.get("expires_days"):
        parts.append(f"{q['expires_days']} 天有效")
    return " · ".join(parts)


def pick_quota(p: dict, access: str) -> dict:
    """The quota that applies: free models use the model-specific limit, others the general quota or credits."""
    qs = p["quotas"]
    if access == "quota":
        return next((q for q in qs if not q.get("models")), qs[0])
    return next((q for q in qs if q.get("models")), qs[0])


def price_text(p: dict | None) -> str:
    if not p or (p["input"] == 0 and p["output"] == 0):
        return ""
    f = lambda x: f"{x:.3f}".rstrip("0").rstrip(".")
    return f"${f(p['input'])} / ${f(p['output'])}"


def ctx_text(n) -> str:
    if not n:
        return ""
    return f"{n / 1048576:.1f}".rstrip("0").rstrip(".") + "M" if n >= 1e6 else f"{round(n / 1024)}K"


def page(title: str, body: str, desc: str = "", depth: int = 0, nav: str = "") -> str:
    up = "../" * depth
    links = [("models", "index.html", "模型广场"), ("providers", "providers.html", "Providers"), ("download", "download.html", "下载"),
             ("join", "providers-join.html", "平台入驻")]
    navs = "".join(f'<a href="{up}{h}"{" aria-current=page" if k == nav else ""}>{t}</a>' for k, h, t in links)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="{up}style.css"><link rel="icon" href="{up}icon.png">
<link rel="alternate" type="application/feed+json" title="羊毛switch Providers" href="{up}feed.json">
</head><body>
<header><div class="bar"><a class="brand" href="{up}index.html"><img src="{up}icon.png" alt="" width="26" height="26">羊毛<span>switch</span></a>
<nav>{navs}<a href="{REPO}" class="gh">GitHub</a></nav>
<a class="btn primary small" href="{up}download.html">下载桌面端</a></div></header>
<main>{body}</main>
<footer><p>额度和价格以各平台官方公布为准。羊毛switch 是开源项目（MIT），与所列平台无隶属关系。
<a href="{REPO}/catalog/issues/new/choose">提交新平台或纠错</a> · 联系 <a href="mailto:kangletian@hotmail.com">kangletian@hotmail.com</a></p></footer>
<script src="{up}app.js"></script></body></html>"""


def tags(m: dict) -> list[tuple[str, str]]:
    t = []
    mods = m.get("input_modalities") or ["text"]
    if "image" in mods:
        t.append(("视觉", ""))
    if "video" in mods:
        t.append(("视频理解", ""))
    if "audio" in mods:
        t.append(("音频", ""))
    if m.get("tools"):
        t.append(("Tools", ""))
    if m.get("reasoning"):
        t.append(("推理模型", ""))
    if m.get("open_weights") or m.get("hugging_face_id"):
        t.append(("开源权重", ""))
    c = ctx_text(m.get("context_length"))
    if c:
        t.append((c, ""))
    return t


def model_card(m: dict, pname) -> str:
    offers = m["offers"]
    best = offers[0]["access"]
    plats = "、".join(pname(o["provider"]) for o in offers[:2]) + (f" 等 {len(offers)} 个平台" if len(offers) > 2 else "")
    caps = []
    mods = m.get("input_modalities") or []
    if "image" in mods:
        caps.append("vision")
    if m.get("tools"):
        caps.append("tools")
    if m.get("reasoning"):
        caps.append("reasoning")
    title = f"{m['vendor']} / {m['name']}" if m.get("vendor") else m["name"]
    search = " ".join([m["name"], m.get("vendor") or "", m["id"], (m.get("description") or "")[:200]] + [o["model"] for o in offers])
    badge = ACCESS[best]
    tag_html = f'<span class="mtag {badge[1]}">{badge[0]}</span>' + "".join(f'<span class="mtag">{e(x)}</span>' for x, _ in tags(m))
    return f"""<a class="mcard" href="m/{e(m['slug'])}.html" data-search="{e(search.lower())}" data-caps="{' '.join(caps)}" data-providers=" {' '.join(o['provider'] for o in offers)} " data-access="{best}">
<div class="mcard-head">{avatar(m.get('vendor') or m['name'], m.get('vendor') or offers[0]['provider'])}<div><b>{e(title)}</b><span>{e(plats)}</span></div></div>
<p class="mdesc">{e(m.get('description') or '暂无介绍。')}</p>
<div class="mtags">{tag_html}</div></a>"""


def model_page(m: dict, pname, provs: dict) -> str:
    rows = []
    for o in m["offers"]:
        p = provs.get(o["provider"])
        q = quota_text(pick_quota(p, o["access"])) if p and p.get("quotas") and o["access"] != "paid" else ""
        lab, tone = ACCESS[o["access"]]
        rows.append(f"""<tr><td><a class="plat" href="../p/{e(o['provider'])}.html">{avatar(pname(o['provider']), o['provider'], 'av sm')}{e(pname(o['provider']))}</a></td>
<td><code>{e(o['model'])}</code></td><td><span class="mtag {tone}">{lab}</span></td><td>{e(q) or '—'}</td><td class="num">{e(price_text(o.get('price'))) or '—'}</td></tr>""")
    facts = []
    if m.get("context_length"):
        facts.append(("上下文", f"{m['context_length']:,} tokens"))
    facts.append(("输入", "、".join(MODAL.get(x, x) for x in (m.get("input_modalities") or ["text"]))))
    if m.get("created"):
        facts.append(("上线时间", e(m["created"])))
    if m.get("hugging_face_id"):
        facts.append(("开源权重", f'<a href="https://huggingface.co/{e(m["hugging_face_id"])}" target="_blank" rel="noopener">{e(m["hugging_face_id"])}</a>'))
    title = f"{m['vendor']} / {m['name']}" if m.get("vendor") else m["name"]
    desc = m.get("description") or ""
    src = f'<span class="muted">（简介来自 {e(m["description_source"])}）</span>' if m.get("description_source") and desc else ""
    tag_html = "".join(f'<span class="mtag">{e(x)}</span>' for x, _ in tags(m))
    body = f"""<p class="crumb"><a href="../index.html">模型广场</a> / {e(m['name'])}</p>
<div class="mhead">{avatar(m.get('vendor') or m['name'], m.get('vendor') or m['offers'][0]['provider'], 'av lg')}<div><h1>{e(m['name'])}</h1><p class="muted">{e(m.get('vendor') or '')}</p></div></div>
{f'<p class="lead">{e(desc)}{src}</p>' if desc else ''}
<div class="mtags">{tag_html}</div>
<table class="kv">{''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in facts)}</table>
<h2>提供这个模型的平台 <span class="muted">{len(m['offers'])}</span></h2>
<div class="table-wrap"><table class="list"><thead><tr><th>平台</th><th>模型名</th><th>方式</th><th>免费额度</th><th>标价（每百万输入 / 输出 tokens）</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="muted small">“用免费额度”指调用会消耗平台送的免费额度或代金券。标价为平台公开的美元价格，仅供参考。</p>
<p class="cta">用 <a href="../download.html">羊毛switch 桌面端</a> 添加这些平台的 Key 后，本机入口会按模型名自动选用有额度的账号。</p>"""
    return page(f"{m['name']} 在哪些平台可以免费调用 - 羊毛switch", body, f"{title}：{len(m['offers'])} 个平台的调用方式、免费额度和标价。", depth=1, nav="models")


def provider_card(p: dict, pm: dict | None) -> str:
    name = p.get("name_zh") or p["name"]
    tg = [p["region"], "api" if p["api_usable"] else "product", p["onboarding"]["level"], p["overage"]] + p.get("tags", [])
    badges = [f'<span class="badge {e(p["region"])}">{"国内" if p["region"] == "cn" else "海外"}</span>']
    if p["status"] != "verified":
        badges.append('<span class="badge warn">待核实</span>')
    if p["onboarding"]["level"] == "L3":
        badges.append('<span class="badge ok">一键开通</span>')
    quotas = "".join(f'<li><a href="{e(q["evidence"])}" rel="nofollow noopener" target="_blank">{e(quota_text(q))}</a></li>' for q in p["quotas"])
    req = "、".join(REQUIRES.get(r, r) for r in p["signup"].get("requires", [])) or "—"
    over_cls = ' class="danger"' if p["overage"] == "auto_paid" else ""
    mc = f'<span>模型 {pm["total"]} 个（免费 {pm["free"]} · 用免费额度 {pm["quota"]}）</span>' if pm and pm["total"] else ""
    search = " ".join([p["name"], p.get("name_zh", ""), p.get("summary", ""), " ".join(p.get("tags", []))])
    return f"""<article class="card" data-tags="{e(' '.join(tg))}" data-search="{e(search.lower())}">
<div class="card-head">{avatar(name, p['id'])}<h3><a href="p/{e(p['id'])}.html">{e(name)}</a></h3>{''.join(badges)}</div>
{f'<p>{e(p["summary"])}</p>' if p.get("summary") else ''}
<ul class="quotas">{quotas}</ul>
<p class="meta"><span>注册：{e(req)}</span><span{over_cls}>超额：{OVERAGE[p['overage']]}</span>{mc}</p>
<p class="actions"><a class="btn" href="{e(p['signup']['url'])}" rel="nofollow noopener" target="_blank">去注册</a>
<a class="btn" href="p/{e(p['id'])}.html">详情</a></p>
<p class="foot">最后核实 {e(p['last_verified'])}</p></article>"""


def provider_page(p: dict, pm: dict | None, slug_of: dict) -> str:
    name = p.get("name_zh") or p["name"]
    api = p.get("api") or {}
    rows = [
        ("平台", f'<a href="{e(p["homepage"])}" target="_blank" rel="noopener">{e(p["name"])}</a>'),
        ("地区", "国内" if p["region"] == "cn" else "海外"),
        ("能否当 API 用", "能" if p["api_usable"] else "不能，只能在平台自己的产品里用"),
        ("接口", f'<code>{e(api["base_url"])}</code>（{e("、".join(api["protocol"]))} 协议）' if api else "—"),
        ("注册要求", e("、".join(REQUIRES.get(r, r) for r in p["signup"].get("requires", [])) or "—")),
        ("不支持地区", e("、".join(p["signup"].get("regions_blocked", []))) or "—"),
        ("额度用完后", OVERAGE[p["overage"]]),
        ("开通方式", LEVEL[p["onboarding"]["level"]]),
        ("最后核实", e(p["last_verified"])),
    ]
    if p["signup"].get("notes"):
        rows.append(("说明", e(p["signup"]["notes"])))
    quotas = "".join(f'<li>{e(quota_text(q))}{f"（{e(q["note"])}）" if q.get("note") else ""} — <a href="{e(q["evidence"])}" target="_blank" rel="nofollow noopener">官方依据</a></li>' for q in p["quotas"])
    terms = "".join(f'<li><a href="{e(t["url"])}" target="_blank" rel="nofollow noopener">{e(t["point"])}</a></li>' for t in p.get("terms", []))
    links = [f'<a class="btn primary" href="{e(p["signup"]["url"])}" target="_blank" rel="nofollow noopener">去注册</a>']
    if p["onboarding"].get("key_page"):
        links.append(f'<a class="btn" href="{e(p["onboarding"]["key_page"])}" target="_blank" rel="nofollow noopener">创建 Key</a>')
    warn = '<p class="alert">注意：这个平台的免费额度用完后会自动转为付费。请先在平台控制台开启“用完即停”之类的保护设置。</p>' if p["overage"] == "auto_paid" else ""

    models = '<p class="muted">暂无模型列表，欢迎<a href="' + REPO + '/catalog/issues/new/choose">提交</a>。</p>'
    if pm and pm["total"]:
        groups = []
        for acc in ("free", "quota", "paid"):
            lst = [x for x in pm["models"] if x["access"] == acc]
            if not lst:
                continue
            def cell(x):
                code = f'<code>{e(x["model"])}</code>'
                return f'<a href="../m/{e(slug_of[x["model"]])}.html">{code}</a>' if x["model"] in slug_of else code
            li = "".join(f'<tr><td>{cell(x)}</td><td class="num">{e(price_text(x.get("price"))) or "—"}</td></tr>' for x in lst)
            lab = ACCESS[acc][0]
            groups.append(f'<details{" open" if acc != "paid" else ""}><summary>{lab} <span class="muted">{len(lst)}</span></summary>'
                          f'<table class="list"><thead><tr><th>模型名</th><th>标价（每百万输入 / 输出 tokens）</th></tr></thead><tbody>{li}</tbody></table></details>')
        models = f'<p class="muted">共 {pm["total"]} 个：免费 {pm["free"]} · 用免费额度 {pm["quota"]} · 付费 {pm["paid"]}。</p>' + "".join(groups)
    body = f"""<p class="crumb"><a href="../providers.html">Providers</a> / {e(name)}</p>
<div class="mhead">{avatar(name, p['id'], 'av lg')}<div><h1>{e(name)}</h1><p class="muted">{e(p['name'])}</p></div></div>
{f'<p class="lead">{e(p["summary"])}</p>' if p.get("summary") else ''}{warn}
<h2>免费额度</h2><ul>{quotas}</ul>
<h2>模型</h2>{models}
<h2>基本信息</h2><table class="kv">{''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in rows)}</table>
{f'<h2>条款要点</h2><ul>{terms}</ul>' if terms else ''}
<p class="actions">{' '.join(links)}</p>
<p class="cta">用 <a href="../download.html">羊毛switch 桌面端</a> 添加这个平台的 Key 后，可以在本机按上面的额度记账和限量。</p>"""
    return page(f"{name} 免费额度与模型 - 羊毛switch", body, p.get("summary", ""), depth=1, nav="providers")


def main() -> None:
    cat = load(sys.argv[1] if len(sys.argv) > 1 else f"{DIST}/catalog.json")
    sq = load(sys.argv[2] if len(sys.argv) > 2 else f"{DIST}/models.json")
    providers = sorted(cat["providers"], key=lambda p: (p["status"] != "verified", p["onboarding"]["level"] != "L3", p["name"].lower()))
    provs = {p["id"]: p for p in providers}
    pname = lambda pid: (provs[pid].get("name_zh") or provs[pid]["name"]) if pid in provs else pid
    pmodels = sq.get("providers") or {}
    models = sq["models"]
    seen: set[str] = set()
    slug_of: dict[str, str] = {}
    for m in models:
        s = slug(m["id"]) or "model"
        while s in seen:
            s += "-2"
        seen.add(s)
        m["slug"] = s
        for o in m["offers"]:
            slug_of.setdefault(o["model"], s)

    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ("p", "m", "download"):
        (OUT / d).mkdir(parents=True)
    for f in ("style.css", "app.js", "icon.png"):
        shutil.copy(ROOT / "static" / f, OUT / f)

    # model square (home)
    used = sorted({o["provider"] for m in models for o in m["offers"]}, key=lambda x: pname(x))
    multi = sum(len(m["offers"]) > 1 for m in models)
    hero = f"""<section class="hero"><h1>模型广场</h1>
<p class="lead">收录 <b>{len(models)}</b> 个可以免费调用的模型，以及提供它们的 <b>{len(used)}</b> 个平台；其中 {multi} 个模型在多个平台都能用。点开模型可以看到每个平台的调用方式、免费额度和标价。</p>
<p class="muted">羊毛switch 是开源的 Key 管理和用量管理桌面应用：在本机保存各平台的 Key，按免费额度记账和限量。
数据更新于 {e((sq.get('generated_at') or '')[:10])}，尽量保持最新且完整，欢迎用户和平台方<a href="{REPO}/catalog/issues/new/choose">提交</a>，我们核实后上架。</p></section>"""
    filters = f"""<div class="toolbar" id="mfilters">
<input id="mq" placeholder="搜索模型名称">
<div class="seg" id="mcap"><button data-v="" aria-pressed="true">全部</button><button data-v="vision">视觉</button><button data-v="tools">Tools</button><button data-v="reasoning">推理</button></div>
<select id="macc"><option value="">全部方式</option><option value="free">只看免费模型</option><option value="quota">免费或用免费额度</option></select>
<select id="mprov"><option value="">全部平台</option>{''.join(f'<option value="{e(x)}">{e(pname(x))}</option>' for x in used)}</select>
<span id="mcount" class="muted"></span></div>"""
    grid = '<section class="mgrid" id="mgrid">' + "".join(model_card(m, pname) for m in models) + "</section>"
    (OUT / "index.html").write_text(page("羊毛switch - 模型广场：哪些大模型可以免费调用", hero + filters + grid,
                                         "汇总各平台可以免费调用的大模型，列出每个平台的调用方式、免费额度和标价。开源的 Key 与用量管理桌面应用。", nav="models"), encoding="utf-8")
    for m in models:
        (OUT / "m" / f"{m['slug']}.html").write_text(model_page(m, pname, provs), encoding="utf-8")

    # providers
    api_n = sum(1 for p in providers if p["api_usable"])
    phero = f"""<section class="hero"><h1>Providers</h1>
<p class="lead">收录 {len(providers)} 个提供免费额度的平台（其中 {api_n} 个能当 API 用），每条额度都附官方依据。</p>
<p class="muted">目录更新于 {e((cat.get('generated_at') or '')[:10])} · 欢迎<a href="providers-join.html">平台方</a>和用户<a href="{REPO}/catalog/issues/new/choose">提交</a>，我们核实后上架。</p></section>"""
    pfilters = """<div class="toolbar">
<input id="q" placeholder="搜索平台、标签">
<select id="region"><option value="">全部地区</option><option value="cn">国内</option><option value="global">海外</option></select>
<select id="overage"><option value="">超额处理不限</option><option value="blocked">只看用完即停</option></select>
<label><input type="checkbox" id="api" checked> 只看能当 API 用的</label>
<label><input type="checkbox" id="l3"> 只看能一键开通的</label>
<span id="count" class="muted"></span></div>"""
    pgrid = '<section class="grid" id="grid">' + "".join(provider_card(p, pmodels.get(p["id"])) for p in providers) + "</section>"
    (OUT / "providers.html").write_text(page("Providers - 羊毛switch", phero + pfilters + pgrid, "各平台大模型免费 API 额度，附官方依据。", nav="providers"), encoding="utf-8")
    for p in providers:
        (OUT / "p" / f"{p['id']}.html").write_text(provider_page(p, pmodels.get(p["id"]), slug_of), encoding="utf-8")

    # download
    release = latest_release()
    files = sorted((ROOT / "static" / "download").glob("*.exe")) if (ROOT / "static" / "download").exists() else []
    if release and release.get("assets"):
        assets = "".join(f'<li><a href="{e(a["browser_download_url"])}">{e(a["name"])}</a>（{a["size"] / 1048576:.1f} MB）</li>'
                         for a in release["assets"] if not a["name"].endswith((".sig", ".json")))
        dl = f'<p>最新版本 <b>{e(release["tag_name"])}</b>，发布于 {e(release["published_at"][:10])}。</p><ul class="files">{assets}</ul>'
    elif files:
        items = []
        for f in files:
            shutil.copy(f, OUT / "download" / f.name)
            sha = hashlib.sha256(f.read_bytes()).hexdigest()
            items.append(f'<li><a class="btn primary" href="download/{e(f.name)}">下载 Windows 版（{f.stat().st_size / 1048576:.1f} MB）</a>'
                         f'<span class="muted small">{e(f.name)} · SHA-256 <code>{sha}</code></span></li>')
        dl = f'<ul class="files">{"".join(items)}</ul><p class="muted small">目前只提供 Windows 10/11 x64 版本；macOS 和 Linux 版本之后提供。安装包暂未做代码签名，Windows 可能提示“未知发布者”，可在提示里选择“仍要运行”。</p>'
    else:
        dl = '<p class="muted">暂无正式版本。可以从源代码构建。</p>'
    download = f"""<h1>下载羊毛switch 桌面端</h1>
<p class="lead">在本机管理各平台的 Key 和用量：查看哪些模型可以免费调用、开通账号、按免费额度记账和限量。</p>
{dl}
<p class="actions"><a class="btn" href="{REPO}/app">源代码</a> <a class="btn" href="{REPO}/app/issues">反馈问题</a></p>
<h2>安全说明</h2><ul>
<li>你的 Key 只保存在本机系统钥匙串（Windows 凭据管理器）。</li>
<li>羊毛switch 的服务器只提供公开的平台和模型目录，不接触你的 Key，也不转发任何模型调用。</li>
<li>本机入口只监听 127.0.0.1，并且需要本机密钥才能调用；请求用你自己的 Key 直接发往平台。</li>
<li>卸载时可以勾选“删除应用数据”，一并删除保存的 Key 和用量记录。</li></ul>
<h2>三步上手</h2><ol>
<li>安装并打开羊毛switch。</li>
<li>在“模型广场”或“Providers”里找到平台，一键开通（如 OpenRouter），或去平台注册后粘贴 Key。</li>
<li>打开“接入工具”页，按页面上的地址和本机密钥配置 Cherry Studio、Cline、Claude Code 等工具。OpenAI 兼容工具的 Base URL 一般是 <code>http://127.0.0.1:17890/v1</code>，模型名直接写平台上的模型名。</li></ol>
<p class="muted">本地限量按目录里的额度口径估算，默认使用免费额度的 90%。各平台的额度和计费规则以平台官方为准。</p>"""
    (OUT / "download.html").write_text(page("下载 - 羊毛switch", download, "下载羊毛switch 桌面端（Windows）", nav="download"), encoding="utf-8")

    join = f"""<h1>平台入驻</h1>
<p class="lead">欢迎提供免费额度的平台主动接入。接入越深，用户开通越方便。</p>
<table class="kv"><tr><th>级别</th><th>平台需要做的</th><th>用户能得到的</th></tr>
<tr><td>L1 收录</td><td>向目录仓库提 PR，新增一条结构化条目（额度、模型、注册链接、官方依据）</td><td>在官网和桌面端可见；注册链接可带平台自己的渠道码</td></tr>
<tr><td>L2 半自动</td><td>再提供 Key 页链接、Key 前缀、查询剩余额度的接口或响应头</td><td>粘贴 Key 即自动识别；本机按真实剩余额度限量</td></tr>
<tr><td>L3 全自动</td><td>再提供 OAuth 2.0 PKCE 公共客户端，允许回调到 127.0.0.1 任意端口，授权后签发 Key</td><td>桌面端一键开通</td></tr></table>
<p>也欢迎提供公开的模型列表接口（无需 Key 的 OpenAI 格式 <code>/models</code>），以及每个模型是免费、用免费额度还是付费，方便模型广场保持完整。</p>
<p>不收录返利或邀请链接、API 中转站，以及需要虚拟号码、批量注册或多开账号才能获得的额度。</p>
<p class="actions"><a class="btn primary" href="{REPO}/catalog/blob/main/CONTRIBUTING.md">查看接入规范</a> <a class="btn" href="{REPO}/catalog/issues/new/choose">提交一个平台</a> <a class="btn" href="mailto:kangletian@hotmail.com">邮件联系</a></p>"""
    (OUT / "providers-join.html").write_text(page("平台入驻 - 羊毛switch", join, "提供免费额度的平台接入羊毛switch", nav="join"), encoding="utf-8")

    (OUT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    (OUT / "models.json").write_text(json.dumps(sq, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    feed = {"version": "https://jsonfeed.org/version/1.1", "title": "羊毛switch Providers", "home_page_url": "https://yangmaoswitch.github.io/website/",
            "items": [{"id": p["id"], "title": p.get("name_zh") or p["name"], "content_text": "；".join(quota_text(q) for q in p["quotas"]),
                       "url": f"https://yangmaoswitch.github.io/website/p/{p['id']}.html", "date_modified": p["last_verified"]} for p in providers]}
    (OUT / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    llms = ["# 羊毛switch", "", "开源的大模型 Key 与用量管理桌面应用。本站汇总各平台的免费额度和可以免费调用的模型。",
            "机器可读数据：catalog.json（平台与额度）、models.json（各平台模型列表：免费 / 用免费额度 / 付费，标价）", "", "## Providers", ""]
    for p in providers:
        llms.append(f"- {p.get('name_zh') or p['name']}（{'能' if p['api_usable'] else '不能'}当 API 用）：" + "；".join(quota_text(q) for q in p["quotas"]) + f"。注册 {p['signup']['url']}")
    llms += ["", "## 免费模型（免费模型 / 用免费额度的平台）", ""]
    for m in models:
        ok = [o for o in m["offers"] if o["access"] != "paid"]
        llms.append(f"- {m['name']}：" + "、".join(f"{pname(o['provider'])}（{ACCESS[o['access']][0]}，{o['model']}）" for o in ok))
    (OUT / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"ok: {len(models)} models, {len(providers)} providers -> {OUT}")


if __name__ == "__main__":
    main()
