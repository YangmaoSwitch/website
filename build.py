#!/usr/bin/env python3
"""Render the YangmaoSwitch website from catalog.json into ./public.

Usage: python build.py [path-or-url-to-catalog.json]
"""
import html
import json
import pathlib
import shutil
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "public"
CATALOG_URL = "https://raw.githubusercontent.com/YangmaoSwitch/catalog/dist/catalog.json"
REPO = "https://github.com/YangmaoSwitch"

UNIT = {"requests": "次", "tokens": "tokens", "input_tokens": "输入 tokens", "output_tokens": "输出 tokens", "credits": "额度",
        "points": "积分", "neurons": "Neurons", "usd": "美元", "cny": "元"}
PERIOD = {"second": "每秒", "minute": "每分钟", "hour": "每小时", "day": "每天", "week": "每周", "month": "每月", "one-time": "一次性"}
REQUIRES = {"email": "邮箱", "phone": "手机号", "phone_cn": "大陆手机号", "card": "信用卡", "real_name": "实名", "company": "企业认证",
            "github": "GitHub 账号", "google": "Google 账号", "cloud_account": "云账号"}
OVERAGE = {"blocked": "用完即停", "auto_paid": "用完自动转付费", "manual": "需手动开通付费", "unknown": "未知"}
LEVEL = {"L1": "手动添加 Key", "L2": "粘贴 Key 自动识别", "L3": "一键开通"}

e = html.escape


def load_catalog(src: str) -> dict:
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(pathlib.Path(src).read_text(encoding="utf-8"))


def latest_release() -> dict | None:
    try:
        req = urllib.request.Request("https://api.github.com/repos/YangmaoSwitch/app/releases/latest", headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


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


def page(title: str, body: str, desc: str = "", depth: int = 0) -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="{up}style.css"><link rel="icon" href="{up}icon.png">
<link rel="alternate" type="application/feed+json" title="羊毛switch 目录" href="{up}feed.json">
</head><body>
<header><a class="brand" href="{up}index.html">羊毛<span>switch</span></a>
<nav><a href="{up}index.html">免费额度目录</a><a href="{up}download.html">下载</a><a href="{up}providers-join.html">平台入驻</a><a href="{REPO}">GitHub</a></nav></header>
<main>{body}</main>
<footer><p>额度信息以各平台官方公布为准。羊毛switch 是开源项目（MIT），与所列平台无隶属关系。
<a href="{REPO}/catalog/issues/new/choose">报告新额度或纠错</a></p></footer>
<script src="{up}app.js"></script></body></html>"""


def card(p: dict) -> str:
    name = p.get("name_zh") or p["name"]
    tags = [p["region"], "api" if p["api_usable"] else "product", p["onboarding"]["level"], p["overage"]] + p.get("tags", [])
    badges = [f'<span class="badge {e(p["region"])}">{"国内" if p["region"] == "cn" else "海外"}</span>']
    if p["status"] != "verified":
        badges.append('<span class="badge warn">待核实</span>')
    if p["onboarding"]["level"] == "L3":
        badges.append('<span class="badge ok">一键开通</span>')
    quotas = "".join(f'<li><a href="{e(q["evidence"])}" rel="nofollow noopener" target="_blank">{e(quota_text(q))}</a></li>' for q in p["quotas"])
    req = "、".join(REQUIRES.get(r, r) for r in p["signup"].get("requires", [])) or "—"
    over_cls = ' class="danger"' if p["overage"] == "auto_paid" else ""
    search = " ".join([p["name"], p.get("name_zh", ""), p.get("summary", ""), " ".join(p.get("tags", [])), " ".join((p.get("api") or {}).get("free_models", []))])
    return f"""<article class="card" data-tags="{e(' '.join(tags))}" data-search="{e(search.lower())}">
<div class="card-head"><h3><a href="p/{e(p['id'])}.html">{e(name)}</a></h3>{''.join(badges)}</div>
{f'<p>{e(p["summary"])}</p>' if p.get("summary") else ''}
<ul class="quotas">{quotas}</ul>
<p class="meta"><span>注册：{e(req)}</span><span{over_cls}>超额：{OVERAGE[p['overage']]}</span></p>
<p class="actions"><a class="btn" href="{e(p['signup']['url'])}" rel="nofollow noopener" target="_blank">去注册</a>
<a class="btn" href="p/{e(p['id'])}.html">详情</a></p>
<p class="foot">最后核实 {e(p['last_verified'])}</p></article>"""


def detail(p: dict) -> str:
    name = p.get("name_zh") or p["name"]
    api = p.get("api") or {}
    rows = [
        ("平台", f'<a href="{e(p["homepage"])}" target="_blank" rel="noopener">{e(p["name"])}</a>'),
        ("地区", "国内" if p["region"] == "cn" else "海外"),
        ("能否当 API 用", "能" if p["api_usable"] else "不能，只能在平台自己的产品里用"),
        ("接口", f'<code>{e(api["base_url"])}</code>（{e("、".join(api["protocol"]))} 协议）' if api else "—"),
        ("免费模型", e("、".join(api.get("free_models", []))) or e(api.get("free_model_rule", "") or "见平台定价页")),
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
    body = f"""<p><a href="../index.html">← 返回目录</a></p><h1>{e(name)}</h1>
{f'<p class="lead">{e(p["summary"])}</p>' if p.get("summary") else ''}{warn}
<h2>免费额度</h2><ul>{quotas}</ul>
<h2>基本信息</h2><table class="kv">{''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in rows)}</table>
{f'<h2>条款要点</h2><ul>{terms}</ul>' if terms else ''}
<p class="actions">{' '.join(links)}</p>
<p class="muted">用羊毛switch 桌面端添加这个平台的 Key 后，可以在本机按上面的额度记账和限量。<a href="../download.html">下载桌面端</a></p>"""
    return page(f"{name} 免费额度 - 羊毛switch", body, p.get("summary", ""), depth=1)


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else CATALOG_URL
    cat = load_catalog(src)
    providers = sorted(cat["providers"], key=lambda p: (p["status"] != "verified", p["onboarding"]["level"] != "L3", p["name"].lower()))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "p").mkdir(parents=True)
    for f in ("style.css", "app.js", "icon.png"):
        shutil.copy(ROOT / "static" / f, OUT / f)

    api_n = sum(1 for p in providers if p["api_usable"])
    filters = """<div class="toolbar">
<input id="q" placeholder="搜索平台、模型、标签">
<select id="region"><option value="">全部地区</option><option value="cn">国内</option><option value="global">海外</option></select>
<select id="overage"><option value="">超额处理不限</option><option value="blocked">只看用完即停</option></select>
<label><input type="checkbox" id="api" checked> 只看能当 API 用的</label>
<label><input type="checkbox" id="l3"> 只看能一键开通的</label>
<span id="count" class="muted"></span></div>"""
    hero = f"""<section class="hero"><h1>大模型免费额度，一站看全</h1>
<p>收录 {len(providers)} 个平台（其中 {api_n} 个能当 API 用），每条额度都附官方依据。用 <a href="download.html">羊毛switch 桌面端</a> 管理自己的 Key，在本机按免费额度记账和限量。</p>
<p class="muted">目录更新于 {e((cat.get('generated_at') or '')[:10])} · 尽量保持最新、完整，欢迎<a href="providers-join.html">平台方</a>和用户<a href="{REPO}/catalog/issues/new/choose">提交</a>，我们核实后上架。</p></section>"""
    grid = '<section class="grid" id="grid">' + "".join(card(p) for p in providers) + "</section>"
    (OUT / "index.html").write_text(page("羊毛switch - 大模型免费额度目录", hero + filters + grid, "各平台大模型免费 API 额度目录，附官方依据，可一键开通和本地限量。"), encoding="utf-8")

    for p in providers:
        (OUT / "p" / f"{p['id']}.html").write_text(detail(p), encoding="utf-8")

    release = latest_release()
    if release:
        assets = "".join(f'<li><a href="{e(a["browser_download_url"])}">{e(a["name"])}</a>（{a["size"] / 1048576:.1f} MB）</li>'
                         for a in release.get("assets", []) if not a["name"].endswith((".sig", ".json")))
        dl = f'<p>最新版本 <b>{e(release["tag_name"])}</b>，发布于 {e(release["published_at"][:10])}。</p><ul>{assets}</ul>'
    else:
        dl = '<p class="muted">暂无正式版本。可以从源代码构建，正式版本发布后会出现在这里和 GitHub Releases。</p>'
    download = f"""<h1>下载羊毛switch 桌面端</h1>
<p class="lead">一站式查看免费额度、开通账号、在本机管理 Key 和用量。</p>
{dl}
<p class="actions"><a class="btn primary" href="{REPO}/app/releases">GitHub Releases</a> <a class="btn" href="{REPO}/app">源代码</a></p>
<h2>安全说明</h2><ul>
<li>你的 Key 只保存在本机系统钥匙串（Windows 凭据管理器、macOS 钥匙串、Linux Secret Service）。</li>
<li>羊毛switch 的服务器不接触你的 Key，也不转发任何模型调用。</li>
<li>本机入口只监听 127.0.0.1，用你自己的 Key 直接请求平台。</li></ul>
<h2>三步上手</h2><ol>
<li>安装并打开羊毛switch。</li>
<li>在“免费额度目录”里一键开通（如 OpenRouter），或去平台注册后粘贴 Key。</li>
<li>把 Cherry Studio、Cline 等工具的 Base URL 设为 <code>http://127.0.0.1:17890/v1</code>，模型名写成 <code>&lt;账号&gt;/&lt;模型名&gt;</code>。</li></ol>
<p class="muted">本地限量按目录里的额度口径估算，默认使用免费额度的 90%。各平台的额度和计费规则以平台官方为准。</p>"""
    (OUT / "download.html").write_text(page("下载 - 羊毛switch", download, "下载羊毛switch 桌面端"), encoding="utf-8")

    join = f"""<h1>平台入驻</h1>
<p class="lead">欢迎提供免费额度的平台主动接入。接入越深，用户开通越方便。</p>
<table class="kv"><tr><th>级别</th><th>平台需要做的</th><th>用户能得到的</th></tr>
<tr><td>L1 收录</td><td>向目录仓库提 PR，新增一条结构化条目（额度、模型、注册链接、官方依据）</td><td>在官网和桌面端可见；注册链接可带平台自己的渠道码</td></tr>
<tr><td>L2 半自动</td><td>再提供 Key 页链接、Key 前缀、查询剩余额度的接口或响应头</td><td>粘贴 Key 即自动识别；本机按真实剩余额度限量</td></tr>
<tr><td>L3 全自动</td><td>再提供 OAuth 2.0 PKCE 公共客户端，允许回调到 127.0.0.1 任意端口，授权后签发 Key</td><td>桌面端一键开通</td></tr></table>
<p>不收录返利或邀请链接、API 中转站，以及需要虚拟号码、批量注册或多开账号才能获得的额度。</p>
<p class="actions"><a class="btn primary" href="{REPO}/catalog/blob/main/CONTRIBUTING.md">查看接入规范</a> <a class="btn" href="{REPO}/catalog/issues/new/choose">提交一个平台</a></p>"""
    (OUT / "providers-join.html").write_text(page("平台入驻 - 羊毛switch", join, "免费额度平台接入羊毛switch"), encoding="utf-8")

    (OUT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    feed = {"version": "https://jsonfeed.org/version/1.1", "title": "羊毛switch 免费额度目录", "home_page_url": "https://github.com/YangmaoSwitch",
            "items": [{"id": p["id"], "title": p.get("name_zh") or p["name"], "content_text": "；".join(quota_text(q) for q in p["quotas"]),
                       "url": f"p/{p['id']}.html", "date_modified": p["last_verified"]} for p in providers]}
    (OUT / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    llms = ["# 羊毛switch 免费额度目录", "", "各平台大模型免费 API 额度，附官方依据。机器可读数据：catalog.json", ""]
    for p in providers:
        llms.append(f"- {p.get('name_zh') or p['name']}（{'能' if p['api_usable'] else '不能'}当 API 用）：" + "；".join(quota_text(q) for q in p["quotas"]) + f"。注册 {p['signup']['url']}")
    (OUT / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"ok: {len(providers)} providers -> {OUT}")


if __name__ == "__main__":
    main()
