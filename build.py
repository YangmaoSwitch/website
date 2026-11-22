#!/usr/bin/env python3
"""Render the YangmaoSwitch website into ./public, in Chinese (/) and English (/en/).

Data comes from the catalog repo's `dist` branch:
* catalog.json – platforms and their free quotas (with official evidence; English text under `en`);
* models.json  – every platform's model list (free / covered by the free quota / paid, list prices)
                 and the merged model square.

Usage: python build.py [catalog.json] [models.json]   (paths or URLs; default: the published files)
"""
import datetime as dt
import hashlib
import os
import html
import json
import pathlib
import re
import shutil
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "public"
DIST = "https://raw.githubusercontent.com/YangmaoSwitch/catalog/dist"
SITE = "https://yangmaoswitch.github.io/website/"
REPO = "https://github.com/YangmaoSwitch"
EMAIL = os.environ.get("YM_CONTACT_EMAIL", "")  # contact address on the own domain; not shown until set
API_BASE = os.environ.get("YM_API_BASE", "").rstrip("/")  # account service; empty until it is deployed
RANK = {"free": 0, "quota": 1, "paid": 2}
# Header icons (Lucide, ISC licence; GitHub mark)
_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
ICON_LANG = _SVG + '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/></svg>'
ICON_SUBMIT = _SVG + '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M12 7v6"/><path d="M9 10h6"/></svg>'
ICON_DOWNLOAD = _SVG + '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>'
ICON_GITHUB = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.6 18.3 5 18.3 5c.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3"/></svg>')
COLORS = ["#c2410c", "#1d4ed8", "#047857", "#6d28d9", "#b91c1c", "#0369a1", "#a16207", "#0f766e", "#be185d", "#4338ca"]

e = html.escape

# ---------------------------------------------------------------- strings
T = {
    "zh": {
        "brand": '<span class="name">羊毛<span>switch</span></span>', "brand_text": "羊毛switch", "html_lang": "zh-CN", "other": ("en", "English"),
        "nav": {"home": "首页", "models": "模型广场", "providers": "供应商", "blog": "博客", "download": "下载", "join": "供应商入驻"}, "get_app": "下载桌面端", "submit_btn": "提交 / 纠错",
        "home_title": "羊毛switch - 免费大模型 API 目录", "home_h1": "免费大模型 API 目录",
        "home_dl_note": "桌面应用目前只有 Windows 版",
        "home_dl": "下载桌面应用",
        "home_desc": "用 agent 实时检查国内外最新的免费 Token，收录各供应商可以免费调用的大模型，标明免费和付费，每条额度链接到供应商原文。配套开源桌面应用在本机管理密钥和用量。",
        "home_cta": "浏览 {m} 个模型", "home_fresh": "最近一次更新 {d}",
        "home_app": "桌面应用把各供应商的密钥存在系统钥匙串里，给 Cline、Cherry Studio 等工具提供一个本机地址，把请求转给还有额度的账号，用到 90% 就停。",
        "home_submit": "目录尽量保持最新、完整。发现遗漏或错误，欢迎用户和供应商<a href=\"{u}\">提交</a>，我们核实后上架。",
        "tracker_cap": "排名前 {n} 的模型在各供应商的提供方式", "not_offered": "不提供",
        "home_lead": "我们用 agent 实时检查国内外最新的免费 Token，目前收录 <b>{m}</b> 个可以免费调用的模型。每条额度都链接到供应商原文。",
        "sec_hot": "免费好模型", "sec_hot_sub": "先看能否长期免费用，再看下载量、供应商数和发布时间",
        "blog_title": "博客 - 羊毛switch", "blog_h1": "博客", "blog_lead": "目录怎么做、数据从哪来、桌面应用的更新说明。",
        "models_short": "{t} 个（免费 {f} · 付费 {p}）", "new_user": "新用户活动", "refill": {"hour": "每小时", "day": "每日", "week": "每周", "month": "每月"}, "over_refill": "{o}，{r}刷新", "over_once": "{o}，不再补充",
        "sec_prov": "推荐供应商", "sec_prov_sub": "按免费提供的模型排序，长期免费的权重最高",
        "sec_newfree": "新上免费用量", "sec_newfree_sub": "最近 14 天新出现的免费模型或免费额度",
        "sec_newfree_empty": "最近 14 天没有新上的免费用量。",
        "sec_new": "新模型", "sec_new_sub": "最近 45 天上线、可以免费调用的模型",
        "sec_forever": "不限期免费", "sec_forever_sub": "供应商列为免费模型、不消耗额度（通常有限速），以供应商公布为准",
        "sec_more": "查看全部", "since": "{d} 起",
        "sort_lbl": "排序", "sort_heat": "推荐", "sort_new": "最新上线", "sort_platforms": "供应商最多",
        "fix_btn": "纠错",
        "sub": {"title": "提交 / 纠错", "lead": "提交新供应商、新模型，或指出目录里的错误。登录后提交，我们核实后上架或更正，并在“我的提交”里回复处理结果。",
                "not_ready": "账号系统还在准备中，暂时可以在 GitHub 上提交（需要 GitHub 账号）。", "gh": "在 GitHub 上提交",
                "email": "邮箱", "email_ph": "you@example.com", "send": "发送验证码", "resend": "{n} 秒后可重发", "code": "验证码", "code_ph": "6 位数字",
                "login": "登录", "or": "或", "github": "用 GitHub 登录", "signed_in": "已登录：{who}", "logout": "退出登录",
                "kind": "类型", "kinds": {"correction": "纠错", "new_provider": "新供应商", "new_model": "新模型或新额度", "other": "其他"},
                "target": "对象（供应商或模型）", "target_ph": "例如 siliconflow 或 deepseek/deepseek-v4.1-flash", "stitle": "标题", "stitle_ph": "一句话说明",
                "body": "详细说明", "body_ph": "额度、条件、哪里不对……", "evidence": "官方依据链接", "evidence_ph": "https://…", "submit": "提交",
                "sent_ok": "已提交，感谢。处理结果会显示在下方“我的提交”里。", "mine": "我的提交", "none": "还没有提交。",
                "status": {"open": "待处理", "accepted": "已采纳", "rejected": "未采纳", "done": "已上线"}, "note": "回复：",
                "errors": {"bad_email": "邮箱格式不对。", "too_soon": "请稍后再获取验证码。", "rate_limited": "操作太频繁，请稍后再试。", "mail_failed": "邮件发送失败，请稍后再试。",
                           "code_expired": "验证码已失效，请重新获取。", "code_wrong": "验证码不对。", "not_signed_in": "请先登录。", "banned": "这个账号已不能提交。",
                           "network": "连不上服务器，请稍后再试。", "invalid": "请检查填写的内容。"}},
        "footer": "额度和价格以各供应商官方公布为准。羊毛switch 是开源项目（MIT 许可证），与所列供应商无隶属关系。",
        "submit": "提交新供应商或纠错", "contact": "联系",
        "unit": {"requests": "次", "tokens": "Token", "input_tokens": "输入 Token", "output_tokens": "输出 Token", "credits": "额度",
                 "points": "积分", "neurons": "Neurons", "usd": "美元", "cny": "元"},
        "period": {"second": "每秒", "minute": "每分钟", "hour": "每小时", "day": "每天", "week": "每周", "month": "每月", "one-time": "一次性"},
        "requires": {"email": "邮箱", "phone": "手机号", "phone_cn": "大陆手机号", "card": "信用卡", "real_name": "实名", "company": "企业认证",
                     "github": "GitHub 账号", "google": "Google 账号", "cloud_account": "云账号", "qq": "QQ 号"},
        "overage": {"blocked": "用完即停", "auto_paid": "用完自动转付费", "manual": "需手动开通付费", "unknown": "未知"},
        "level": {"L1": "手动添加密钥", "L2": "粘贴密钥自动识别", "L3": "一键开通"},
        "access": {"free": "免费", "quota": "免费", "paid": "付费"},
        "group": {"usable": "免费", "free": "免费模型", "quota": "用免费额度", "paid": "付费"},
        "modal": {"text": "文本", "image": "图片", "video": "视频", "audio": "音频", "file": "文件"},
        "tag": {"vision": "视觉", "video": "视频理解", "audio": "音频", "tools": "工具调用", "reasoning": "推理模型", "open": "开源权重"},
        "tz": {"UTC": "UTC 时间", "Asia/Shanghai": "北京时间", "America/Los_Angeles": "太平洋时间"},
        "proto": {"openai": "OpenAI 兼容", "anthropic": "Anthropic", "gemini": "Gemini", "other": "其他"},
        "limit_unknown": "{period}有上限（按{unit}计，数值见供应商页面）", "reset": "{tz} {t} 重置", "expires": "{n} 天有效", "sep": " · ", "list": "、",
        "more_platforms": "{names} 等 {n} 个供应商", "no_desc": "暂无介绍。", "region": {"cn": "国内", "global": "海外"},
        "to_verify": "待核实", "ended": "已下线", "ended_on": "已于 {d} 下线", "ends_on": "{d} 截止", "ended_alert": "这个免费活动已于 {d} 下线，条目保留供参考。", "one_click": "一键开通", "signup": "注册：", "overage_l": "超额：",
        "models_count": "模型 {t} 个（免费 {f} · 付费 {p}）", "go_signup": "去注册", "details": "详情", "verified": "最后核实 {d}",
        "create_key": "创建密钥", "evidence": "官方依据",
        "auto_paid_warn": "注意：这个供应商的免费额度用完后会自动转为付费。请先在供应商控制台开启“用完即停”之类的保护设置。",
        # model square
        "sq_title": "羊毛switch - 模型广场：哪些大模型可以免费调用",
        "sq_desc": "汇总各供应商可以免费调用的大模型，列出每个供应商的调用方式、免费额度和标价。开源的密钥与用量管理桌面应用。",
        "sq_h1": "模型广场",
        "sq_lead": "收录 <b>{m}</b> 个可以免费调用的模型。点开模型可以看到每个供应商的调用方式、免费额度和标价。",
        "sq_about": "羊毛switch 是开源的密钥管理和用量管理桌面应用：在本机保存各供应商的密钥，按免费额度记账和限量。",
        "updated": "数据更新于 {d}，尽量保持最新且完整，欢迎用户和供应商<a href=\"{u}\">提交</a>，我们核实后上架。",
        "search_model": "搜索模型名称…", "skip": "跳到正文", "lbl_cap": "能力", "lbl_acc": "调用方式", "lbl_prov": "供应商", "lbl_region": "地区", "lbl_over": "超额处理",
        "ex_h": "同一个模型，{n} 个供应商", "ex_more": "查看全部供应商", "lang_label": "切换到英文", "all": "全部", "cap_vision": "视觉", "cap_tools": "工具调用", "cap_reasoning": "推理",
        "acc_all": "全部方式", "acc_free": "只看免费模型", "acc_quota": "只看免费", "all_platforms": "全部供应商", "showing": "显示 {n} 个",
        # model page
        "m_title": "{name} 在哪些供应商可以免费调用 - 羊毛switch", "m_desc": "{name}：{n} 个供应商的调用方式、免费额度和标价。",
        "ctx": "上下文", "input": "输入", "released": "上线时间", "weights": "开源权重", "ctx_tokens": "{n} Token",
        "platforms_h": "提供这个模型的供应商", "th_platform": "供应商", "th_model": "模型名", "th_access": "方式", "th_quota": "免费额度",
        "th_price": "标价（每百万输入 / 输出 Token，美元）",
        "m_note": "“免费”包括完全免费的模型，以及调用会消耗供应商赠送额度或代金券的模型。标价为供应商公开的美元价格，仅供参考；“—”表示没有公开标价。",
        "price_free": "免费",
        "m_cta": "用 <a href=\"{u}\">羊毛switch 桌面端</a> 添加这些供应商的密钥后，本机入口会按模型名自动选用有额度的账号。",
        # generated description
        "gd_vendor": "{v} 的", "gd_open": "开源", "gd_model": "模型。", "gd_ctx": "上下文 {c}", "gd_input": "可输入{m}", "gd_tools": "支持工具调用",
        "gd_reason": "支持推理（思考）模式", "gd_avail": "目前可在 {n} 个供应商调用，其中 {k} 个可以免费调用。", "gd_join": "，", "gd_end": "。",
        # providers
        "p_title": "供应商 - 羊毛switch", "p_desc": "agent 实时检查的国内外大模型免费 API 额度，每条附官方依据。", "p_h1": "供应商",
        "p_lead": "agent 实时检查国内外供应商的免费额度，每条都附官方依据。",
        "p_updated": "目录更新于 {d} · 欢迎用户和供应商<a href=\"{u}\">提交</a>，我们核实后上架。",
        "search_p": "搜索供应商、标签…", "all_regions": "全部地区", "r_cn": "国内", "r_global": "海外", "ov_any": "超额处理不限", "ov_blocked": "只看用完即停",
        "api_only": "只看能当 API 用的", "l3_only": "只看能一键开通的",
        "pp_title": "{name} 免费额度与模型 - 羊毛switch", "quota_h": "免费额度", "models_h": "模型", "basic_h": "基本信息", "terms_h": "条款要点",
        "no_models": "暂无模型列表，欢迎<a href=\"{u}\">提交</a>。", "models_sum": "共 {t} 个：免费 {f} · 付费 {p}。",
        "k_platform": "供应商", "k_region": "地区", "k_api": "能否当 API 用", "k_yes": "能", "k_no": "不能，只能在供应商自己的产品里用", "k_endpoint": "接口",
        "k_protocol": "{p} 协议", "k_requires": "注册要求", "k_blocked": "不支持地区", "k_overage": "额度用完后", "k_level": "开通方式",
        "k_verified": "最后核实", "k_notes": "说明",
        "p_cta": "用 <a href=\"{u}\">羊毛switch 桌面端</a> 添加这个供应商的密钥后，可以在本机按上面的额度记账和限量。",
        # download
        "d_title": "下载 - 羊毛switch", "d_desc": "下载羊毛switch 桌面端（Windows）", "d_h1": "下载羊毛switch 桌面端",
        "d_lead": "在本机管理各供应商的密钥和用量：查看哪些模型可以免费调用、开通账号、按免费额度记账和限量。",
        "d_release": "最新版本 <b>{t}</b>，发布于 {d}。", "d_win": "下载 Windows 版（{s} MB）",
        "d_note": "目前只提供 Windows 10/11 x64 版本；macOS 和 Linux 版本之后提供。安装包暂未做代码签名，Windows 可能提示“未知发布者”，可在提示里选择“仍要运行”。",
        "d_none": "暂无正式版本。可以从源代码构建。", "d_src": "源代码", "d_issues": "反馈问题",
        "d_sec_h": "安全说明", "d_sec": ["你的密钥只保存在本机系统钥匙串（Windows 凭据管理器）。",
                                     "羊毛switch 的服务器只提供公开的供应商和模型目录，不接触你的密钥，也不转发任何模型调用。",
                                     "本机入口只监听 127.0.0.1，并且需要本机密钥才能调用；请求用你自己的密钥直接发往供应商。",
                                     "卸载时可以勾选“删除应用数据”，一并删除保存的密钥和用量记录。"],
        "d_steps_h": "三步上手", "d_steps": ["安装并打开羊毛switch。",
                                         "在“模型广场”或“供应商”里找到供应商，一键开通（如 OpenRouter），或去供应商注册后粘贴密钥。",
                                         "打开“接入工具”页，按页面上的地址和本机密钥配置 Cherry Studio、Cline、Claude Code 等工具。OpenAI 兼容工具的接口地址一般是 <code>http://127.0.0.1:17890/v1</code>，模型名直接写供应商上的模型名。"],
        "d_foot": "本地限量按目录里的额度口径估算，默认使用免费额度的 90%。各供应商的额度和计费规则以供应商官方为准。",
        # join
        "j_title": "供应商入驻 - 羊毛switch", "j_desc": "提供免费额度的供应商接入羊毛switch", "j_h1": "供应商入驻",
        "j_lead": "欢迎提供免费额度的供应商主动接入。接入越深，用户开通越方便。",
        "j_th": ("级别", "供应商需要做的", "用户能得到的"),
        "j_rows": [("L1 收录", "向目录仓库提交拉取请求，新增一条结构化条目（额度、模型、注册链接、官方依据）", "在官网和桌面端可见；注册链接可带供应商自己的渠道码"),
                   ("L2 半自动", "再提供密钥页链接、密钥前缀、查询剩余额度的接口或响应头", "粘贴密钥即自动识别；本机按真实剩余额度限量"),
                   ("L3 全自动", "再提供 OAuth 2.0 PKCE 公共客户端，允许回调到 127.0.0.1 任意端口，授权后签发密钥", "桌面端一键开通")],
        "j_models": "也欢迎提供无需密钥即可访问的公开模型列表接口（OpenAI 格式的 <code>/models</code>），并说明每个模型是免费还是付费，方便模型广场保持完整。",
        "j_no": "官方供应商、聚合平台和 API 中转站的免费额度都可以收录。注册链接一律用供应商官方地址，不放返利或邀请链接；需要虚拟号码、批量注册或多开账号才能拿到的额度不收。",
        "j_spec": "查看接入规范", "j_submit": "提交一个供应商", "j_mail": "邮件联系",
        # llms
        "llms_title": "# 羊毛switch", "llms_intro": "开源的大模型密钥与用量管理桌面应用。本站汇总各供应商的免费额度和可以免费调用的模型。",
        "llms_data": "机器可读数据：catalog.json（供应商与额度）、models.json（各供应商模型列表：免费 / 付费，标价）",
        "llms_p": "## 供应商", "llms_m": "## 免费模型", "llms_api": "（{x}当 API 用）", "llms_can": "能", "llms_cannot": "不能", "llms_reg": "。注册 {u}",
        "feed_title": "羊毛switch 供应商目录",
    },
    "en": {
        "brand": '<span class="name">Yangmao<span>Switch</span></span>', "brand_text": "YangmaoSwitch", "html_lang": "en", "other": ("zh", "中文"),
        "nav": {"home": "Home", "models": "Models", "providers": "Providers", "blog": "Blog", "download": "Download", "join": "For providers"}, "get_app": "Get the app", "submit_btn": "Submit / Report",
        "home_title": "YangmaoSwitch - A directory of free LLM APIs", "home_h1": "A directory of free LLM APIs",
        "home_dl_note": "The desktop app is Windows-only for now",
        "home_dl": "Download the desktop app",
        "home_desc": "Our agents check Chinese and global providers for new free tokens in real time. LLMs you can call for free on each provider, marked free or paid, with every quota linked to the provider’s own terms. The open-source desktop app manages keys and usage locally.",
        "home_cta": "Browse {m} models", "home_fresh": "Last updated {d}",
        "home_app": "The desktop app keeps your keys in the system keychain, gives Cline, Cherry Studio and other tools one local address, and sends each request to an account with quota left. It stops at 90% of each free quota.",
        "home_submit": "We aim to keep the catalog current and complete. Users and providers can <a href=\"{u}\">submit</a> missing or wrong entries, and we verify them before listing.",
        "tracker_cap": "The top {n} models, provider by provider", "not_offered": "Not offered",
        "home_lead": "Our agents check Chinese and global providers for new free tokens in real time. <b>{m}</b> models you can call for free right now, each quota linked to the provider’s own terms.",
        "sec_hot": "Best free models", "sec_hot_sub": "Lasting free access first, then downloads, provider count and release date",
        "blog_title": "Blog - YangmaoSwitch", "blog_h1": "Blog", "blog_lead": "How the catalog is built, where the data comes from, and desktop app release notes.",
        "models_short": "{t} ({f} free · {p} paid)", "new_user": "New users", "refill": {"hour": "hourly", "day": "daily", "week": "weekly", "month": "monthly"}, "over_refill": "{o}; refills {r}", "over_once": "{o}; not refilled",
        "sec_prov": "Recommended providers", "sec_prov_sub": "Ranked by the models they serve for free; lasting free access counts most",
        "sec_newfree": "New free offers", "sec_newfree_sub": "Free models and free quotas that appeared in the last 14 days",
        "sec_newfree_empty": "No new free offers in the last 14 days.",
        "sec_new": "New models", "sec_new_sub": "Released in the last 45 days and callable for free",
        "sec_forever": "Free with no end date", "sec_forever_sub": "Listed as free models by the provider, not counted against a quota (usually rate-limited); per the provider's terms",
        "sec_more": "See all", "since": "since {d}",
        "sort_lbl": "Sort", "sort_heat": "Recommended", "sort_new": "Newest", "sort_platforms": "Most providers",
        "fix_btn": "Report an error",
        "sub": {"title": "Submit / Report", "lead": "Submit a new provider or model, or report an error in the catalog. Sign in to submit; we verify each entry before listing or correcting it, and reply under My submissions.",
                "not_ready": "Accounts are not available yet. Meanwhile you can submit on GitHub (a GitHub account is required).", "gh": "Submit on GitHub",
                "email": "Email", "email_ph": "you@example.com", "send": "Send code", "resend": "Resend in {n}s", "code": "Code", "code_ph": "6 digits",
                "login": "Sign in", "or": "or", "github": "Sign in with GitHub", "signed_in": "Signed in as {who}", "logout": "Sign out",
                "kind": "Type", "kinds": {"correction": "Correction", "new_provider": "New provider", "new_model": "New model or quota", "other": "Other"},
                "target": "Provider or model", "target_ph": "e.g. siliconflow or deepseek/deepseek-v4.1-flash", "stitle": "Title", "stitle_ph": "One line",
                "body": "Details", "body_ph": "Quota, conditions, what is wrong…", "evidence": "Official source", "evidence_ph": "https://…", "submit": "Submit",
                "sent_ok": "Submitted, thank you. The result will show under My submissions below.", "mine": "My submissions", "none": "No submissions yet.",
                "status": {"open": "Open", "accepted": "Accepted", "rejected": "Declined", "done": "Live"}, "note": "Reply: ",
                "errors": {"bad_email": "Check the email address.", "too_soon": "Wait a moment before requesting another code.", "rate_limited": "Too many attempts; try again later.",
                           "mail_failed": "Could not send the email; try again later.", "code_expired": "The code has expired; request a new one.", "code_wrong": "Wrong code.",
                           "not_signed_in": "Sign in first.", "banned": "This account can no longer submit.", "network": "Cannot reach the server; try again later.", "invalid": "Check the fields."}},
        "footer": "Quotas and prices are as published by each provider. YangmaoSwitch is open source (MIT) and not affiliated with the providers listed.",
        "submit": "Submit a provider or a correction", "contact": "Contact",
        "unit": {"requests": "requests", "tokens": "tokens", "input_tokens": "input tokens", "output_tokens": "output tokens", "credits": "credits",
                 "points": "points", "neurons": "Neurons", "usd": "USD", "cny": "CNY"},
        "period": {"second": "per second", "minute": "per minute", "hour": "per hour", "day": "per day", "week": "per week", "month": "per month", "one-time": "one-time"},
        "requires": {"email": "email", "phone": "phone number", "phone_cn": "Chinese mainland phone number", "card": "credit card", "real_name": "real-name verification",
                     "company": "company verification", "github": "GitHub account", "google": "Google account", "cloud_account": "cloud account", "qq": "QQ account"},
        "overage": {"blocked": "Stops when used up", "auto_paid": "Switches to paid when used up", "manual": "Paid use must be enabled manually", "unknown": "Unknown"},
        "level": {"L1": "Add a key manually", "L2": "Paste a key, detected automatically", "L3": "One-click sign-up"},
        "access": {"free": "Free", "quota": "Free", "paid": "Paid"},
        "group": {"usable": "Free", "free": "Free models", "quota": "On free quota", "paid": "Paid"},
        "modal": {"text": "text", "image": "images", "video": "video", "audio": "audio", "file": "files"},
        "tag": {"vision": "Vision", "video": "Video", "audio": "Audio", "tools": "Tools", "reasoning": "Reasoning", "open": "Open weights"},
        "tz": {"UTC": "UTC", "Asia/Shanghai": "Beijing time", "America/Los_Angeles": "Pacific Time"},
        "proto": {"openai": "OpenAI-compatible", "anthropic": "Anthropic", "gemini": "Gemini", "other": "other"},
        "limit_unknown": "Limited {period} (in {unit}; see the provider for the number)", "reset": "resets at {t} {tz}", "expires": "valid for {n} days", "sep": " · ", "list": ", ",
        "more_platforms": "{names} and {k} more", "no_desc": "No description yet.", "region": {"cn": "China", "global": "Global"},
        "to_verify": "Unverified", "ended": "Ended", "ended_on": "ended {d}", "ends_on": "ends {d}", "ended_alert": "This free offer ended on {d}. The entry is kept for reference.", "one_click": "One-click", "signup": "Sign-up: ", "overage_l": "When used up: ",
        "models_count": "{t} models ({f} free · {p} paid)", "go_signup": "Sign up", "details": "Details", "verified": "Last verified {d}",
        "create_key": "Create a key", "evidence": "Source",
        "auto_paid_warn": "Note: on this provider, usage switches to paid once the free quota is used up. Turn on a stop-when-used-up setting in the provider console first.",
        "sq_title": "YangmaoSwitch - Models you can call for free",
        "sq_desc": "Large language models you can call for free, with every provider that serves them: access, free quota and list price. Open-source key and usage manager.",
        "sq_h1": "Models",
        "sq_lead": "<b>{m}</b> models you can call for free. Open a model to see each provider's access, free quota and list price.",
        "sq_about": "YangmaoSwitch is an open-source desktop app for managing your API keys and usage: keys stay on your computer, and calls are metered and capped against each free quota.",
        "updated": "Data updated {d}. We aim to keep it current and complete; users and providers are welcome to <a href=\"{u}\">submit</a> entries, which we verify before listing.",
        "search_model": "Search models…", "skip": "Skip to content", "lbl_cap": "Capability", "lbl_acc": "Access", "lbl_prov": "Provider", "lbl_region": "Region", "lbl_over": "Overage policy",
        "ex_h": "One model, {n} providers", "ex_more": "See all providers", "lang_label": "Switch to Chinese", "all": "All", "cap_vision": "Vision", "cap_tools": "Tools", "cap_reasoning": "Reasoning",
        "acc_all": "Any access", "acc_free": "Free models only", "acc_quota": "Free only", "all_platforms": "All providers", "showing": "Showing {n}",
        "m_title": "Where to call {name} for free - YangmaoSwitch", "m_desc": "{name}: access, free quota and list price on {n} providers.",
        "ctx": "Context", "input": "Input", "released": "Released", "weights": "Weights", "ctx_tokens": "{n} tokens",
        "platforms_h": "Providers serving this model", "th_platform": "Provider", "th_model": "Model ID", "th_access": "Access", "th_quota": "Free quota",
        "th_price": "List price (USD per 1M input / output tokens)",
        "m_note": "“Free” covers fully free models and models whose calls use the provider's free allowance or vouchers. Prices are the providers' published USD prices, for reference only; “—” means no published price.",
        "price_free": "Free",
        "m_cta": "Add these providers' keys to the <a href=\"{u}\">YangmaoSwitch desktop app</a> and its local endpoint picks an account with quota left for each model.",
        "p_title": "Providers - YangmaoSwitch", "p_desc": "Free LLM API quotas from Chinese and global providers, checked by our agents in real time, each with an official source.", "p_h1": "Providers",
        "p_lead": "Free quotas from Chinese and global providers, checked by our agents in real time, each with an official source.",
        "p_updated": "Catalog updated {d} · Users and providers are welcome to <a href=\"{u}\">submit</a> entries, which we verify before listing.",
        "search_p": "Search providers and tags…", "all_regions": "All regions", "r_cn": "China", "r_global": "Global", "ov_any": "Any overage policy", "ov_blocked": "Stops when used up",
        "api_only": "Usable as an API", "l3_only": "One-click sign-up",
        "pp_title": "{name} free quota and models - YangmaoSwitch", "quota_h": "Free quota", "models_h": "Models", "basic_h": "Details", "terms_h": "Terms to note",
        "no_models": "No model list yet; feel free to <a href=\"{u}\">submit</a> one.", "models_sum": "{t} models: {f} free · {p} paid.",
        "k_platform": "Provider", "k_region": "Region", "k_api": "Usable as an API", "k_yes": "Yes", "k_no": "No, only inside the provider's own products",
        "k_endpoint": "Endpoint", "k_protocol": "{p} API", "k_requires": "Sign-up requires", "k_blocked": "Not available in", "k_overage": "When used up",
        "k_level": "Onboarding", "k_verified": "Last verified", "k_notes": "Notes",
        "p_cta": "Add this provider's key to the <a href=\"{u}\">YangmaoSwitch desktop app</a> to meter and cap usage against the quota above on your computer.",
        "d_title": "Download - YangmaoSwitch", "d_desc": "Download the YangmaoSwitch desktop app (Windows)", "d_h1": "Download YangmaoSwitch",
        "d_lead": "Manage your API keys and usage on your own computer: find models you can call for free, sign up, and meter and cap usage against each free quota.",
        "d_release": "Latest version <b>{t}</b>, released {d}.", "d_win": "Download for Windows ({s} MB)",
        "d_note": "Windows 10/11 x64 only for now; macOS and Linux will follow. The installer is not code-signed yet, so Windows may warn about an unknown publisher; choose “Run anyway”.",
        "d_none": "No release yet. You can build it from source.", "d_src": "Source code", "d_issues": "Report an issue",
        "d_sec_h": "Security", "d_sec": ["Your keys are stored only in the system keychain on your computer (Windows Credential Manager).",
                                      "The YangmaoSwitch server only publishes the public provider and model catalog. It never sees your keys or relays model calls.",
                                      "The local endpoint listens on 127.0.0.1 only and requires a local key; requests go straight to the providers with your own keys.",
                                      "When uninstalling, tick “Delete app data” to remove the stored keys and usage records."],
        "d_steps_h": "Get started", "d_steps": ["Install and open YangmaoSwitch.",
                                             "Find a provider under Models or Providers. Sign up with one click (e.g. OpenRouter), or sign up on the provider and paste your key.",
                                             "Open the Connect page and configure Cherry Studio, Cline, Claude Code and other tools with the address and local key shown there. For OpenAI-compatible tools the base URL is usually <code>http://127.0.0.1:17890/v1</code>; use the provider's model ID as the model name."],
        "d_foot": "Local caps are estimated from the catalog's quota definitions and use 90% of each free quota by default. Each provider's own quotas and billing rules apply.",
        "j_title": "For providers - YangmaoSwitch", "j_desc": "List your free quota on YangmaoSwitch", "j_h1": "For providers",
        "j_lead": "Providers that offer free quotas are welcome to integrate. The deeper the integration, the easier it is for users to get started.",
        "j_th": ("Level", "What the provider provides", "What users get"),
        "j_rows": [("L1 Listing", "A pull request to the catalog repository with a structured entry (quota, models, sign-up link, official source)", "Listed on the website and in the app; the sign-up link may carry the provider's own channel code"),
                   ("L2 Assisted", "Also the key page URL, the key prefix, and an endpoint or response headers reporting the remaining quota", "Keys are recognized on paste; usage is capped against the real remaining quota"),
                   ("L3 Automatic", "Also an OAuth 2.0 PKCE public client that allows redirects to any 127.0.0.1 port and issues a key on authorization", "One-click sign-up in the app")],
        "j_models": "A public model list endpoint that needs no key (OpenAI-style <code>/models</code>), with whether each model is free or paid, helps keep the model list complete.",
        "j_no": "Free quotas from official providers, aggregators and API resellers can all be listed. Sign-up links always point to the provider's official address, never to referral or invite links. Quotas that require virtual phone numbers, bulk sign-ups or multiple accounts are not listed.",
        "j_spec": "Integration guide", "j_submit": "Submit a provider", "j_mail": "Email us",
        "llms_title": "# YangmaoSwitch", "llms_intro": "Open-source desktop app for managing LLM API keys and usage. This site lists free quotas and the models you can call for free.",
        "llms_data": "Machine-readable data: catalog.json (providers and quotas), models.json (each provider's models: free / paid, list prices)",
        "llms_p": "## Providers", "llms_m": "## Free models", "llms_api": " ({x} usable as an API)", "llms_can": "", "llms_cannot": "not", "llms_reg": ". Sign up: {u}",
        "feed_title": "YangmaoSwitch providers",
    },
}


# ---------------------------------------------------------------- helpers
def load(src: str) -> dict:
    if src.startswith("http"):
        with urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": "YangmaoSwitch-website"}), timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(pathlib.Path(src).read_text(encoding="utf-8"))


def latest_release() -> dict | None:
    try:
        req = urllib.request.Request("https://api.github.com/repos/YangmaoSwitch/app/releases/latest", headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# Brand logos (static/logos, from LobeHub Icons and Simple Icons). Pages write "@@ROOT@@" and write() fills in the relative root.
PROVIDER_LOGOS = {
    "aihubmix": "aihubmix-color", "aliyun-bailian": "bailian-color", "amd-radeon-cloud": "amd", "cloudflare-workers-ai": "workersai-color",
    "cohere": "cohere-color", "google-ai-studio": "aistudio", "groq": "groq", "modelscope": "modelscope-color", "nvidia-nim": "nvidia-color",
    "opencode": "opencode", "openrouter": "openrouter", "siliconflow": "siliconcloud-color", "tencent-hunyuan": "hunyuan-color",
    "volcengine-ark": "volcengine-color", "zhipu-bigmodel": "zhipu-color", "qiniu": "qiniu-color",
    "kilo-code": "kilocode", "ovhcloud-ai-endpoints": "ovh", "mistral": "mistral-color", "cerebras": "cerebras-color",
    "vercel-ai-gateway": "vercel", "aion-labs": "aionlabs", "z-ai": "zai", "tencent-tokenhub": "tencentcloud-color",
    "sensenova": "sensenova-color", "moark": "giteeai", "xfyun-spark": "spark-color",
    "fireworks": "fireworks-color", "hyperbolic": "hyperbolic-color", "novita": "novita-color", "nous-portal": "nousresearch",
    "pollinations": "pollinations", "inception-labs": "inception",
}
MODEL_LOGOS = [  # first match on "vendor id name"
    (r"qwen|qwq|qvq|tongyi", "qwen-color"), (r"deepseek", "deepseek-color"), (r"\bglm|zhipu|z\.ai|zai-org|chatglm|cogview", "zhipu-color"),
    (r"kimi|moonshot", "kimi-color"), (r"minimax", "minimax-color"), (r"gemma", "gemma-color"), (r"gemini", "gemini-color"),
    (r"nemotron|nvidia", "nvidia-color"), (r"mimo|xiaomi", "xiaomimimo"), (r"llama|\bmeta\b", "meta-color"),
    (r"mistral|magistral|devstral|codestral", "mistral-color"), (r"\bstep|stepfun", "stepfun-color"), (r"ernie|baidu|paddle", "wenxin-color"),
    (r"hunyuan|tencent|\bhy\d", "hunyuan-color"), (r"doubao|seed|bytedance", "doubao-color"), (r"\bling\b|\bring\b|inclusionai", "ling-color"),
    (r"longcat|meituan", "longcat-color"), (r"intern|shanghai_ai", "internlm-color"), (r"cohere|command|\baya\b|north-", "cohere-color"),
    (r"gpt|openai", "openai"), (r"claude|anthropic", "anthropic"), (r"baai|bge", "baai"), (r"google", "google-color"),
]


def logo_img(file: str, cls: str) -> str:
    return f'<span class="{cls} logo"><img src="@@ROOT@@logos/{file}.svg" alt="" width="20" height="20" loading="lazy" decoding="async"></span>'


def provider_logo(pid: str, cls: str = "av") -> str:
    return logo_img(PROVIDER_LOGOS.get(pid, "generic"), cls)


def model_logo(m: dict, cls: str = "av") -> str:
    text = f"{m.get('vendor') or ''} {m['id']} {m['name']}".lower()
    return logo_img(next((f for r, f in MODEL_LOGOS if re.search(r, text)), "generic"), cls)


def avatar(name: str, seed: str, cls: str = "av") -> str:
    color = COLORS[sum(map(ord, seed)) % len(COLORS)]
    letters = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", name)[:2] or "?"
    letters = letters[0] if re.match(r"[\u4e00-\u9fff]", letters) else letters[:1].upper() + letters[1:2].lower()
    return f'<span class="{cls}" style="--c:{color}">{e(letters)}</span>'


def price_text(p: dict | None) -> str:
    if not p or (p["input"] == 0 and p["output"] == 0):
        return ""
    f = lambda x: f"{x:.3f}".rstrip("0").rstrip(".")
    return f"${f(p['input'])} / ${f(p['output'])}"


def ctx_text(n) -> str:
    if not n:
        return ""
    return f"{n / 1048576:.1f}".rstrip("0").rstrip(".") + "M" if n >= 1e6 else f"{round(n / 1024)}K"


BLOG = ROOT / "blog"


def load_posts(lang: str) -> list[dict]:
    """Published posts of one language: blog/<slug>.<lang>.md with a small front matter block."""
    out = []
    for f in sorted(BLOG.glob(f"*.{lang}.md")) if BLOG.exists() else []:
        text = f.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        if text.startswith("---\n"):
            head, _, text = text[4:].partition("\n---\n")
            for line in head.splitlines():
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip('"')
        if meta.get("draft", "").lower() == "true" and not os.environ.get("YM_BLOG_DRAFTS"):  # YM_BLOG_DRAFTS=1 previews drafts locally
            continue
        import markdown  # only needed when there are posts
        out.append({"slug": f.name[: -len(f".{lang}.md")], "title": meta.get("title", f.stem), "date": meta.get("date", ""),
                    "summary": meta.get("summary", ""), "html": markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])})
    return sorted(out, key=lambda x: x["date"], reverse=True)


class Site:
    def __init__(self, lang: str, cat: dict, sq: dict, providers: list, models: list, slug_of: dict):
        self.L = lang
        self.t = T[lang]
        self.cat, self.sq, self.providers, self.models, self.slug_of = cat, sq, providers, models, slug_of
        self.provs = {p["id"]: p for p in providers}
        self.pmodels = sq.get("providers") or {}
        self.out = OUT if lang == "zh" else OUT / "en"
        self.posts = load_posts(lang)

    # text of catalog entries in this language
    def pname(self, pid: str) -> str:
        p = self.provs.get(pid)
        if not p:
            return pid
        return (p.get("name_zh") or p["name"]) if self.L == "zh" else p["name"]

    def ptext(self, p: dict, field: str) -> str:
        if self.L == "en":
            en = p.get("en") or {}
            return {"summary": en.get("summary", ""), "signup_notes": en.get("signup_notes", ""), "free_model_rule": en.get("free_model_rule", "")}[field]
        return {"summary": p.get("summary", ""), "signup_notes": p["signup"].get("notes", ""), "free_model_rule": (p.get("api") or {}).get("free_model_rule", "")}[field]

    def qfield(self, p: dict, i: int, k: str) -> str:
        if self.L == "en":
            qs = (p.get("en") or {}).get("quotas") or []
            return (qs[i] if i < len(qs) else {}).get(k, "")
        return p["quotas"][i].get(k, "")

    def terms(self, p: dict) -> list[tuple[str, str]]:
        ts = p.get("terms", [])
        if self.L == "en":
            en = (p.get("en") or {}).get("terms") or []
            return [(en[i] if i < len(en) else "", t["url"]) for i, t in enumerate(ts) if i < len(en)]
        return [(t["point"], t["url"]) for t in ts]

    def ptags(self, p: dict) -> list[str]:
        return (p.get("en") or {}).get("tags", []) if self.L == "en" else p.get("tags", [])

    @staticmethod
    def is_new_user(q: dict) -> bool:
        """New-user offers: flagged in the data, or conditions like 'within 14 days of signing up'."""
        return bool(q.get("new_users")) or bool(re.search(r"注册.{0,8}(天|日|月)内|新用户|新注册|新账号|首次注册|新人", q.get("condition") or ""))

    def overage_text(self, p: dict) -> str:
        """What happens when the free allowance runs out, and whether it comes back."""
        t = self.t
        base = t["overage"][p["overage"]]
        live = [q for q in p.get("quotas") or [] if not q.get("ended")]
        lasting = [q["period"] for q in live if q.get("period") in ("hour", "day", "week", "month") and not self.is_new_user(q)]
        if lasting:
            order = ["hour", "day", "week", "month"]
            return t["over_refill"].format(o=base, r=t["refill"][min(lasting, key=order.index)])
        if live and all(q.get("period") in ("one-time", "second", "minute") or self.is_new_user(q) for q in live) \
                and any(q.get("period") == "one-time" or self.is_new_user(q) for q in live):
            return t["over_once"].format(o=base)
        return base

    def quota_text(self, p: dict, i: int) -> str:
        t, q = self.t, p["quotas"][i]
        unit, period = t["unit"].get(q["unit"], q["unit"]), t["period"].get(q["period"], q["period"])
        if q.get("amount") is None:
            parts = [t["limit_unknown"].format(period=period, unit=unit)]
        else:
            amount = f"{q['amount']:,.0f}" if float(q["amount"]).is_integer() else str(q["amount"])
            if self.L == "en" and q["amount"] == 1 and unit.endswith("s"):
                unit = unit[:-1]
            parts = [f"{period} {amount} {unit}" if self.L == "zh" else (f"{amount} {unit} {period}" if q["period"] != "one-time" else f"{amount} {unit}, one-time")]
        for k in ("models", "condition"):
            v = self.qfield(p, i, k)
            if v:
                parts.append(v)
        if q.get("reset") and q["reset"] != "rolling":
            hm, _, tz = q["reset"].partition(" ")
            parts.append(t["reset"].format(t=hm, tz=t["tz"].get(tz, tz)))
        if q.get("expires_days"):
            parts.append(t["expires"].format(n=q["expires_days"]))
        if q.get("ended"):
            parts.append(t["ended_on"].format(d=q["ended"]))
        if self.is_new_user(q):
            parts.insert(0, t["new_user"])
        return t["sep"].join(parts)

    def price_cell(self, p: dict | None) -> str:
        if not p:
            return "—"
        return self.t["price_free"] if p["input"] == 0 and p["output"] == 0 else e(price_text(p))

    def pick_quota(self, p: dict, access: str) -> int:
        """Index of the quota that applies: free models use the model-specific limit, others the general quota or credits."""
        qs = p["quotas"]
        want = (lambda q: not q.get("models")) if access == "quota" else (lambda q: bool(q.get("models")))
        return next((i for i, q in enumerate(qs) if want(q)), 0)

    def write(self, rel: str, title: str, body: str, desc: str, nav: str = ""):
        depth = rel.count("/")
        home = "../" * depth
        root = home + ("../" if self.L == "en" else "")
        other_lang, other_label = self.t["other"]
        other = (home + "en/" if self.L == "zh" else home + "../") + rel
        alt_zh, alt_en = SITE + rel, SITE + "en/" + rel
        links = [("models", "models.html"), ("providers", "providers.html")] + ([("blog", "blog/index.html")] if self.posts else [])
        navs = "".join(f'<a href="{home}{h}"{" aria-current=page" if k == nav else ""}>{self.t["nav"][k]}</a>' for k, h in links)
        doc = f"""<!doctype html>
<html lang="{self.t['html_lang']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{alt_zh if self.L == 'zh' else alt_en}">
<link rel="alternate" hreflang="zh-CN" href="{alt_zh}"><link rel="alternate" hreflang="en" href="{alt_en}"><link rel="alternate" hreflang="x-default" href="{alt_zh}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{alt_zh if self.L == 'zh' else alt_en}"><meta property="og:image" content="{SITE}icon.png"><meta property="og:site_name" content="{self.t['brand_text']}">
<meta name="theme-color" content="#fafafa">
<link rel="preload" href="{root}fonts/geist-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}style.css"><link rel="icon" href="{root}icon.png">
<link rel="alternate" type="application/feed+json" href="{home}feed.json">
</head><body>
<a class="skip" href="#main">{self.t['skip']}</a>
<header><div class="bar"><a class="brand" href="{home}index.html" translate="no"><img src="{root}icon.png" alt="" width="26" height="26">{self.t['brand']}</a>
<nav>{navs}</nav>
<div class="tools">
<a class="icon-link" href="{home}submit.html" aria-label="{self.t['submit_btn']}" title="{self.t['submit_btn']}">{ICON_SUBMIT}</a>
<a class="icon-link" href="{other}" hreflang="{other_lang}" lang="{other_lang}" aria-label="{self.t['lang_label']}" title="{self.t['lang_label']}">{ICON_LANG}</a>
<a class="icon-link" href="{REPO}" aria-label="GitHub" title="GitHub">{ICON_GITHUB}</a>
<a class="btn primary small" href="{home}download.html">{ICON_DOWNLOAD}{self.t['get_app']}</a></div></div></header>
<main id="main">{body}</main>
<footer><p>{self.t['footer']}
<a href="{REPO}/catalog/issues/new/choose">{self.t['submit']}</a>{(" · " + self.t['contact'] + f' <a href="mailto:{EMAIL}">{EMAIL}</a>') if EMAIL else ""}</p></footer>
<script src="{root}app.js"></script></body></html>"""
        doc = doc.replace("@@ROOT@@", root)
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc, encoding="utf-8")

    # ---------------------------------------------------------------- models
    def tags(self, m: dict) -> list[str]:
        tg, out = self.t["tag"], []
        mods = m.get("input_modalities") or ["text"]
        for k in ("image", "video", "audio"):
            if k in mods:
                out.append(tg["vision" if k == "image" else k])
        if m.get("tools"):
            out.append(tg["tools"])
        if m.get("reasoning"):
            out.append(tg["reasoning"])
        if m.get("open_weights") or m.get("hugging_face_id"):
            out.append(tg["open"])
        c = ctx_text(m.get("context_length"))
        if c:
            out.append(c)
        return out

    def desc(self, m: dict) -> str:
        """English: the published description. Chinese: a summary written from the structured data, so pages stay in one language."""
        if self.L == "en":
            return m.get("description") or ""
        t = self.t
        lead = (t["gd_vendor"].format(v=m["vendor"]) if m.get("vendor") else "") + (t["gd_open"] if m.get("open_weights") or m.get("hugging_face_id") else "")
        s = lead + t["gd_model"] if lead else ""
        bits = []
        if m.get("context_length"):
            bits.append(t["gd_ctx"].format(c=ctx_text(m["context_length"])))
        mods = [x for x in (m.get("input_modalities") or ["text"])]
        if mods and mods != ["text"]:
            bits.append(t["gd_input"].format(m=t["list"].join(t["modal"].get(x, x) for x in mods)))
        if m.get("tools"):
            bits.append(t["gd_tools"])
        if m.get("reasoning"):
            bits.append(t["gd_reason"])
        if bits:
            s += t["gd_join"].join(bits) + t["gd_end"]
        k = sum(o["access"] != "paid" for o in m["offers"])
        return s + t["gd_avail"].format(n=len(m["offers"]), k=k)

    def model_card(self, m: dict) -> str:
        t, offers = self.t, m["offers"]
        best = offers[0]["access"]
        names = t["list"].join(self.pname(o["provider"]) for o in offers[:2])
        plats = (t["more_platforms"].format(names=names, n=len(offers), k=len(offers) - 2)) if len(offers) > 2 else t["list"].join(self.pname(o["provider"]) for o in offers)
        mods = m.get("input_modalities") or []
        caps = (["vision"] if "image" in mods else []) + (["tools"] if m.get("tools") else []) + (["reasoning"] if m.get("reasoning") else [])
        title = f"{m['vendor']} / {m['name']}" if m.get("vendor") else m["name"]
        search = " ".join([m["name"], m.get("vendor") or "", m["id"]] + [o["model"] for o in offers])
        tone = {"free": "ok", "quota": "ok", "paid": ""}[best]
        tag_html = f'<span class="mtag {tone}">{t["access"][best]}</span>' + "".join(f'<span class="mtag">{e(x)}</span>' for x in self.tags(m))
        return f"""<a class="mcard" href="m/{e(m['slug'])}.html" data-search="{e(search.lower())}" data-caps="{' '.join(caps)}" data-providers=" {' '.join(o['provider'] for o in offers)} " data-access="{best}" data-heat="{m.get('heat', 0)}" data-created="{e(m.get('created') or '')}" data-n="{len(offers)}">
<div class="mcard-head">{model_logo(m)}<div><b translate="no">{e(title)}</b><span>{e(plats)}</span></div></div>
<p class="mdesc">{e(self.desc(m) or t['no_desc'])}</p>
<div class="mtags">{tag_html}</div></a>"""

    def model_page(self, m: dict):
        t = self.t
        rows = []
        for o in m["offers"]:
            p = self.provs.get(o["provider"])
            q = self.quota_text(p, self.pick_quota(p, o["access"])) if p and p.get("quotas") and o["access"] != "paid" else ""
            tone = {"free": "ok", "quota": "ok", "paid": ""}[o["access"]]
            rows.append(f"""<tr><td><a class="plat" href="../p/{e(o['provider'])}.html">{provider_logo(o['provider'], 'av sm')}{e(self.pname(o['provider']))}</a></td>
<td><code translate="no">{e(o['model'])}</code></td><td><span class="mtag {tone}">{t['access'][o['access']]}</span></td><td>{e(q) or '—'}</td><td class="num">{self.price_cell(o.get('price'))}</td></tr>""")
        facts = []
        if m.get("context_length"):
            facts.append((t["ctx"], t["ctx_tokens"].format(n=f"{m['context_length']:,}")))
        facts.append((t["input"], t["list"].join(t["modal"].get(x, x) for x in (m.get("input_modalities") or ["text"]))))
        if m.get("created"):
            facts.append((t["released"], e(m["created"])))
        if m.get("hugging_face_id"):
            facts.append((t["weights"], f'<a href="https://huggingface.co/{e(m["hugging_face_id"])}" target="_blank" rel="noopener">{e(m["hugging_face_id"])}</a>'))
        d = self.desc(m)
        tag_html = "".join(f'<span class="mtag">{e(x)}</span>' for x in self.tags(m))
        body = f"""<p class="crumb"><a href="../models.html">{t['nav']['models']}</a> / {e(m['name'])}</p>
<div class="mhead">{model_logo(m, 'av lg')}<div><h1 translate="no">{e(m['name'])}</h1><p class="muted">{e(m.get('vendor') or '')}</p></div></div>
{f'<p class="lead">{e(d)}</p>' if d else ''}
<div class="mtags">{tag_html}</div>
<table class="kv">{''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in facts)}</table>
<h2>{t['platforms_h']} <span class="muted">{len(m['offers'])}</span></h2>
<div class="table-wrap"><table class="list"><thead><tr><th>{t['th_platform']}</th><th>{t['th_model']}</th><th>{t['th_access']}</th><th>{t['th_quota']}</th><th>{t['th_price']}</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="muted small">{t['m_note']}</p>
<p class="actions"><a class="btn" href="../submit.html?kind=correction&amp;target={urllib.parse.quote(m['id'])}&amp;page=m/{e(m['slug'])}.html">{t['fix_btn']}</a></p>
<p class="cta">{t['m_cta'].format(u='../download.html')}</p>"""
        self.write(f"m/{m['slug']}.html", t["m_title"].format(name=m["name"]), body, t["m_desc"].format(name=m["name"], n=len(m["offers"])), "models")

    # ---------------------------------------------------------------- providers
    def provider_card(self, p: dict) -> str:
        t, pm = self.t, self.pmodels.get(p["id"])
        name = self.pname(p["id"])
        tg = [p["region"], "api" if p["api_usable"] else "product", p["onboarding"]["level"], p["overage"]]
        badges = [f'<span class="badge {e(p["region"])}">{t["region"][p["region"]]}</span>']
        if p.get("ended"):
            badges.append(f'<span class="badge ended" title="{e(t["ended_on"].format(d=p["ended"]))}">{t["ended"]}</span>')
        elif p["status"] != "verified":
            badges.append(f'<span class="badge warn">{t["to_verify"]}</span>')
        if p["onboarding"]["level"] == "L3":
            badges.append(f'<span class="badge ok">{t["one_click"]}</span>')
        quotas = "".join(f'<li><a href="{e(q["evidence"])}" rel="nofollow noopener" target="_blank">{e(self.quota_text(p, i))}</a></li>' for i, q in enumerate(p["quotas"]))
        req = t["list"].join(t["requires"].get(r, r) for r in p["signup"].get("requires", [])) or "—"
        over_cls = ' class="danger"' if p["overage"] == "auto_paid" else ""
        mc = f'<span>{t["models_count"].format(t=pm["total"], f=pm["free"] + pm["quota"], p=pm["paid"])}</span>' if pm and pm["total"] else ""
        summary = self.ptext(p, "summary")
        search = " ".join([p["name"], p.get("name_zh", ""), summary, " ".join(self.ptags(p))])
        mc_text = t["models_short"].format(t=pm["total"], f=pm["free"] + pm["quota"], p=pm["paid"]) if pm and pm["total"] else "—"
        quotas = "".join(
            f'<li><a href="{e(q["evidence"])}" rel="nofollow noopener" target="_blank" title="{e(self.quota_text(p, i))}">{e(self.quota_text(p, i))}</a></li>'
            for i, q in enumerate(p["quotas"][:3]))
        # fixed slots so every card in a row lines up: head, summary (2 lines), quotas (3 lines), facts, footer
        return f"""<article class="card pcard-full" data-tags="{e(' '.join(tg))}" data-search="{e(search.lower())}">
<div class="card-head">{provider_logo(p['id'])}<h3><a href="p/{e(p['id'])}.html" title="{e(name)}">{e(name)}</a></h3><span class="badges">{''.join(badges)}</span></div>
<p class="card-sum">{e(summary)}</p>
<ul class="quotas">{quotas}</ul>
<dl class="card-facts"><dt>{t['signup'].rstrip('：: ')}</dt><dd title="{e(req)}">{e(req)}</dd>
<dt>{t['overage_l'].rstrip('：: ')}</dt><dd{over_cls}>{e(self.overage_text(p))}</dd>
<dt>{t['models_h']}</dt><dd>{mc_text}</dd></dl>
<div class="card-foot"><a class="btn" href="{e(p['signup']['url'])}" rel="nofollow noopener" target="_blank">{t['go_signup']}</a>
<a class="btn" href="p/{e(p['id'])}.html">{t['details']}</a><span class="foot">{t['verified'].format(d=e(p['last_verified']))}</span></div></article>"""

    def provider_page(self, p: dict):
        t, pm = self.t, self.pmodels.get(p["id"])
        name = self.pname(p["id"])
        api = p.get("api") or {}
        rows = [
            (t["k_platform"], f'<a href="{e(p["homepage"])}" target="_blank" rel="noopener">{e(name)}</a>'),
            (t["k_region"], t["region"][p["region"]]),
            (t["k_api"], t["k_yes"] if p["api_usable"] else t["k_no"]),
            (t["k_endpoint"], f'<code translate="no">{e(api["base_url"])}</code>（{e(t["k_protocol"].format(p=t["list"].join(t["proto"].get(x, x) for x in api["protocol"])))}）' if api and self.L == "zh" else
             (f'<code translate="no">{e(api["base_url"])}</code> ({e(t["k_protocol"].format(p=t["list"].join(t["proto"].get(x, x) for x in api["protocol"])))})' if api else "—")),
            (t["k_requires"], e(t["list"].join(t["requires"].get(r, r) for r in p["signup"].get("requires", [])) or "—")),
            (t["k_blocked"], e(t["list"].join(p["signup"].get("regions_blocked", []))) or "—"),
            (t["k_overage"], e(self.overage_text(p))),
            (t["k_level"], t["level"][p["onboarding"]["level"]]),
            (t["k_verified"], e(p["last_verified"])),
        ]
        if p.get("ended"):
            rows.append((t["ended"], e(t["ended_on"].format(d=p["ended"]))))
        elif p.get("ends"):
            rows.append((t["ends_on"].format(d="").strip(), e(p["ends"])))
        notes = self.ptext(p, "signup_notes")
        if notes:
            rows.append((t["k_notes"], e(notes)))
        open_p, close_p = ("（", "）") if self.L == "zh" else (" (", ")")
        quotas = "".join(
            f'<li>{e(self.quota_text(p, i))}{open_p + e(self.qfield(p, i, "note")) + close_p if self.qfield(p, i, "note") else ""} — <a href="{e(q["evidence"])}" target="_blank" rel="nofollow noopener">{t["evidence"]}</a>'
            + (f'<q class="src-quote">{e(q["quote"])}</q>' if q.get("quote") else "") + '</li>'
            for i, q in enumerate(p["quotas"]))
        terms = "".join(f'<li><a href="{e(u)}" target="_blank" rel="nofollow noopener">{e(x)}</a></li>' for x, u in self.terms(p))
        links = [f'<a class="btn primary" href="{e(p["signup"]["url"])}" target="_blank" rel="nofollow noopener">{t["go_signup"]}</a>']
        if p["onboarding"].get("key_page"):
            links.append(f'<a class="btn" href="{e(p["onboarding"]["key_page"])}" target="_blank" rel="nofollow noopener">{t["create_key"]}</a>')
        warn = f'<p class="alert">{t["auto_paid_warn"]}</p>' if p["overage"] == "auto_paid" else ""
        if p.get("ended"):
            warn = f'<p class="alert">{e(t["ended_alert"].format(d=p["ended"]))}</p>' + warn
        models = f'<p class="muted">{t["no_models"].format(u=REPO + "/catalog/issues/new/choose")}</p>'
        if pm and pm["total"]:
            groups = []
            # two groups only: usable for free (free models and models on the free quota) and paid only
            for acc, kinds in (("usable", ("free", "quota")), ("paid", ("paid",))):
                lst = [x for x in pm["models"] if x["access"] in kinds]
                if not lst:
                    continue

                def cell(x):
                    code = f'<code translate="no">{e(x["model"])}</code>'
                    return f'<a href="../m/{e(self.slug_of[x["model"]])}.html">{code}</a>' if x["model"] in self.slug_of else code
                li = "".join(f'<tr><td>{cell(x)}</td><td class="num">{self.price_cell(x.get("price"))}</td></tr>' for x in lst)
                groups.append(f'<details{" open" if acc != "paid" else ""}><summary>{t["group"][acc]} <span class="muted">{len(lst)}</span></summary>'
                              f'<table class="list"><thead><tr><th>{t["th_model"]}</th><th>{t["th_price"]}</th></tr></thead><tbody>{li}</tbody></table></details>')
            models = f'<p class="muted">{t["models_sum"].format(t=pm["total"], f=pm["free"] + pm["quota"], p=pm["paid"])}</p>' + "".join(groups) + f'<p class="muted small">{t["m_note"]}</p>'
        summary = self.ptext(p, "summary")
        sub = p["name"] if self.L == "zh" and p.get("name_zh") else ""
        body = f"""<p class="crumb"><a href="../providers.html">{t['nav']['providers']}</a> / {e(name)}</p>
<div class="mhead">{provider_logo(p['id'], 'av lg')}<div><h1>{e(name)}</h1>{f'<p class="muted">{e(sub)}</p>' if sub else ''}</div></div>
{f'<p class="lead">{e(summary)}</p>' if summary else ''}{warn}
<h2>{t['quota_h']}</h2><ul>{quotas}</ul>
<h2>{t['models_h']}</h2>{models}
<h2>{t['basic_h']}</h2><table class="kv">{''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in rows)}</table>
{f'<h2>{t["terms_h"]}</h2><ul>{terms}</ul>' if terms else ''}
<p class="actions">{' '.join(links)} <a class="btn" href="../submit.html?kind=correction&amp;target={e(p['id'])}&amp;page=p/{e(p['id'])}.html">{t['fix_btn']}</a></p>
<p class="cta">{t['p_cta'].format(u='../download.html')}</p>"""
        self.write(f"p/{p['id']}.html", t["pp_title"].format(name=name), body, summary, "providers")

    def tracker(self, models: list) -> str:
        """The hero visual: the most popular models against the platforms that serve them, one cell per pair."""
        t = self.t
        rows = sorted(models, key=lambda m: m.get("heat", 0), reverse=True)[:8]
        # columns: the best-ranked providers (same order as the providers page) offering at least two of these free
        count: dict[str, int] = {}
        for m in rows:
            for o in m["offers"]:
                if o["access"] != "paid":
                    count[o["provider"]] = count.get(o["provider"], 0) + 1
        rank = {p["id"]: i for i, p in enumerate(self.providers)}
        cols = sorted((p for p in count if count[p] >= 2 and p in rank), key=lambda x: rank[x])[:8]
        def short(pid: str) -> str:  # column labels: drop parentheses, keep at most two words
            n = re.sub(r"\s*\(.*?\)", "", self.pname(pid)).strip()
            w = n.split()
            return " ".join(w[:2]) if len(n) > 16 and len(" ".join(w[:2])) <= 18 else (w[0] if len(n) > 16 else n)
        head = "".join(f'<th scope="col"><a href="p/{e(c)}.html" title="{e(self.pname(c))}"><span>{e(short(c))}</span></a></th>' for c in cols)
        body = []
        for m in rows:
            by = {o["provider"]: o["access"] for o in m["offers"]}
            cells = []
            for c in cols:
                a = by.get(c)
                label = f"{m['name']} · {self.pname(c)} · {t['access'][a] if a else t['not_offered']}"
                cells.append(f'<td><span class="cell {("free" if a == "quota" else a) or "none"}" role="img" aria-label="{e(label)}" title="{e(label)}"></span></td>')
            body.append(f'<tr><th scope="row"><a href="m/{e(m["slug"])}.html" translate="no">{e(m["name"])}</a></th>{"".join(cells)}</tr>')
        legend = "".join(f'<span><i class="cell {k}"></i>{v}</span>' for k, v in
                         (("free", t["access"]["free"]), ("paid", t["access"]["paid"]), ("none", t["not_offered"])))
        return f"""<figure class="tracker"><figcaption>{t['tracker_cap'].format(n=len(rows))}</figcaption>
<div class="tracker-scroll"><table><thead><tr><td></td>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>
<div class="legend">{legend}</div></figure>"""

    def home_sections(self) -> str:
        t, models = self.t, self.models
        today = dt.date.today()
        baseline = self.sq.get("baseline") or ""

        def section(key: str, body: str, more: str) -> str:
            return (f'<section class="home-sec"><div class="sec-head"><div><h2>{t["sec_" + key]}</h2><p class="muted">{t["sec_" + key + "_sub"]}</p></div>'
                    f'<a href="{more}">{t["sec_more"]}</a></div>{body}</section>')

        def days_ago(d: str | None) -> int:
            try:
                return (today - dt.date.fromisoformat((d or "")[:10])).days
            except ValueError:
                return 10**6

        row = lambda ms: '<div class="mgrid one-row">' + "".join(self.model_card(m) for m in ms) + "</div>"
        ranked = sorted(models, key=lambda m: m.get("heat", 0), reverse=True)
        out = [section("hot", row(ranked[:4]), "models.html")]

        # recommended providers: those serving models for free or on a free quota, in the catalog's order
        score: dict[str, float] = {}
        for m in models:
            for o in m["offers"]:
                if o["access"] != "paid" and o["provider"] in self.provs:
                    score[o["provider"]] = score.get(o["provider"], 0) + m.get("heat", 0)
        top = [p["id"] for p in self.providers if p["id"] in score][:4]  # same ranking as the providers page
        cards = []
        for pid in top:
            p, pm = self.provs[pid], self.pmodels.get(pid) or {}
            q = self.quota_text(p, 0) if p.get("quotas") else ""
            cards.append(f'<a class="pcard" href="p/{e(pid)}.html"><div class="mcard-head">{provider_logo(pid)}<div><b>{e(self.pname(pid))}</b>'
                         f'<span>{t["models_count"].format(t=pm.get("total", 0), f=pm.get("free", 0) + pm.get("quota", 0), p=pm.get("paid", 0))}</span></div></div>'
                         f'<p class="mdesc">{e(q)}</p></a>')
        out.append(section("prov", f'<div class="mgrid one-row">{"".join(cards)}</div>', "providers.html"))

        new = sorted((m for m in models if days_ago(m.get("created")) <= 45), key=lambda m: m.get("created") or "", reverse=True)[:4]
        if new:
            out.append(section("new", row(new), "models.html?sort=new"))

        forever = [m for m in ranked if any(o["access"] == "free" for o in m["offers"])][:4]
        out.append(section("forever", row(forever), "models.html?access=free"))
        return "".join(out)

    # ---------------------------------------------------------------- pages
    def build(self, dl_items: list[dict], release: dict | None):
        t, models, providers = self.t, self.models, self.providers
        issues = f"{REPO}/catalog/issues/new/choose"

        used = sorted({o["provider"] for m in models for o in m["offers"]}, key=lambda x: self.pname(x).lower())
        multi = sum(len(m["offers"]) > 1 for m in models)
        hero = f"""<section class="hero split home-hero"><div class="hero-text">
<h1>{t['home_h1']}</h1>
<p class="lead">{t['home_lead'].format(m=len(models), p=len(providers))}</p>
<p class="hero-cta"><a class="btn primary" href="models.html">{t['home_cta'].format(m=len(models))}</a><span class="muted small">{t['home_dl_note']}</span></p>
<p class="muted">{t['home_app']}</p></div>
{self.tracker(models)}</section>"""
        self.write("index.html", t["home_title"], hero + self.home_sections(), t["home_desc"], "home")
        hero = f"""<section class="hero"><h1>{t['sq_h1']}</h1></section>"""
        filters = f"""<div class="toolbar">
<input id="mq" name="q" type="search" autocomplete="off" spellcheck="false" placeholder="{t['search_model']}" aria-label="{t['search_model'].rstrip('…')}">
<div class="seg" id="mcap" role="group" aria-label="{t['lbl_cap']}"><button data-v="" aria-pressed="true">{t['all']}</button><button data-v="vision">{t['cap_vision']}</button><button data-v="tools">{t['cap_tools']}</button><button data-v="reasoning">{t['cap_reasoning']}</button></div>
<select id="macc" name="access" aria-label="{t['lbl_acc']}"><option value="">{t['acc_all']}</option><option value="quota">{t['acc_quota']}</option></select>
<select id="mprov" name="platform" aria-label="{t['lbl_prov']}"><option value="">{t['all_platforms']}</option>{''.join(f'<option value="{e(x)}">{e(self.pname(x))}</option>' for x in used)}</select>
<select id="msort" name="sort" aria-label="{t['sort_lbl']}"><option value="heat">{t['sort_heat']}</option><option value="new">{t['sort_new']}</option><option value="platforms">{t['sort_platforms']}</option></select>
<span id="mcount" class="muted" aria-live="polite" data-tpl="{e(t['showing'])}"></span></div>"""
        grid = '<section class="mgrid" id="mgrid">' + "".join(self.model_card(m) for m in models) + "</section>"
        self.write("models.html", t["sq_title"], hero + filters + grid, t["sq_desc"], "models")
        for m in models:
            self.model_page(m)

        api_n = sum(1 for p in providers if p["api_usable"])
        phero = f"""<section class="hero"><h1>{t['p_h1']}</h1>
<p class="lead">{t['p_lead'].format(n=len(providers), a=api_n)}</p>
<p class="muted">{t['p_updated'].format(d=e((self.cat.get('generated_at') or '')[:10]), j='providers-join.html', u=issues)}</p></section>"""
        pfilters = f"""<div class="toolbar">
<input id="q" name="q" type="search" autocomplete="off" spellcheck="false" placeholder="{t['search_p']}" aria-label="{t['search_p'].rstrip('…')}">
<select id="region" name="region" aria-label="{t['lbl_region']}"><option value="">{t['all_regions']}</option><option value="cn">{t['r_cn']}</option><option value="global">{t['r_global']}</option></select>
<select id="overage" name="overage" aria-label="{t['lbl_over']}"><option value="">{t['ov_any']}</option><option value="blocked">{t['ov_blocked']}</option></select>
<label><input type="checkbox" id="api" checked> {t['api_only']}</label>
<label><input type="checkbox" id="l3"> {t['l3_only']}</label>
<span id="count" class="muted" aria-live="polite" data-tpl="{e(t['showing'])}"></span></div>"""
        pgrid = '<section class="grid" id="grid">' + "".join(self.provider_card(p) for p in providers) + "</section>"
        self.write("providers.html", t["p_title"], phero + pfilters + pgrid, t["p_desc"], "providers")
        for p in providers:
            self.provider_page(p)

        root = "" if self.L == "zh" else "../"
        if release and release.get("assets"):
            assets = "".join(f'<li><a href="{e(a["browser_download_url"])}">{e(a["name"])}</a> ({a["size"] / 1048576:.1f} MB)</li>'
                             for a in release["assets"] if not a["name"].endswith((".sig", ".json")))
            dl = f'<p>{t["d_release"].format(t=e(release["tag_name"]), d=e(release["published_at"][:10]))}</p><ul class="files">{assets}</ul>'
        elif dl_items:
            dl = '<ul class="files">' + "".join(
                f'<li><a class="btn primary" href="{root}download/{e(f["name"])}">{t["d_win"].format(s=f"{f["size"] / 1048576:.1f}")}</a>'
                f'<span class="muted small">{e(f["name"])} · SHA-256 <code translate="no">{f["sha"]}</code></span></li>' for f in dl_items) + f'</ul><p class="muted small">{t["d_note"]}</p>'
        else:
            dl = f'<p class="muted">{t["d_none"]}</p>'
        download = f"""<h1>{t['d_h1']}</h1><p class="lead">{t['d_lead']}</p>{dl}
<p class="actions"><a class="btn" href="{REPO}/app">{t['d_src']}</a> <a class="btn" href="{REPO}/app/issues">{t['d_issues']}</a></p>
<h2>{t['d_sec_h']}</h2><ul>{''.join(f'<li>{x}</li>' for x in t['d_sec'])}</ul>
<h2>{t['d_steps_h']}</h2><ol>{''.join(f'<li>{x}</li>' for x in t['d_steps'])}</ol>
<p class="muted">{t['d_foot']}</p>"""
        self.write("download.html", t["d_title"], download, t["d_desc"], "download")

        sub = t["sub"]
        kinds = "".join(f'<option value="{k}">{v}</option>' for k, v in sub["kinds"].items())
        submit = f"""<h1>{sub['title']}</h1><p class="lead">{sub['lead']}</p>
<div id="submit-app" data-api="{e(API_BASE)}" data-lang="{self.L}" data-text="{e(json.dumps(sub, ensure_ascii=False))}">
<div class="panel" id="s-unavailable" hidden><p>{sub['not_ready']}</p><p class="actions"><a class="btn" href="{issues}">{sub['gh']}</a></p></div>
<form class="panel" id="s-login" hidden>
<label>{sub['email']}<input id="s-email" name="email" type="email" autocomplete="email" spellcheck="false" placeholder="{sub['email_ph']}" required></label>
<div class="row"><label>{sub['code']}<input id="s-code" name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{{6}}" maxlength="6" placeholder="{sub['code_ph']}"></label>
<button type="button" class="btn" id="s-send">{sub['send']}</button></div>
<p class="actions"><button class="btn primary" type="submit">{sub['login']}</button><span class="muted" id="s-gh-or" hidden>{sub['or']}</span><button type="button" class="btn" id="s-gh" hidden>{sub['github']}</button></p>
<p class="form-msg" id="s-login-msg" role="status" aria-live="polite"></p></form>
<div id="s-main" hidden>
<p class="who"><span id="s-who"></span> <button type="button" class="linkbtn" id="s-logout">{sub['logout']}</button></p>
<form class="panel" id="s-form">
<div class="row"><label>{sub['kind']}<select id="s-kind" name="kind">{kinds}</select></label>
<label class="grow">{sub['target']}<input id="s-target" name="target" autocomplete="off" spellcheck="false" maxlength="200" placeholder="{sub['target_ph']}"></label></div>
<label>{sub['stitle']}<input id="s-title" name="title" autocomplete="off" maxlength="120" required placeholder="{sub['stitle_ph']}"></label>
<label>{sub['body']}<textarea id="s-body" name="body" rows="6" maxlength="5000" required placeholder="{sub['body_ph']}"></textarea></label>
<label>{sub['evidence']}<input id="s-evidence" name="evidence_url" type="url" autocomplete="off" maxlength="500" placeholder="{sub['evidence_ph']}"></label>
<p class="actions"><button class="btn primary" type="submit">{sub['submit']}</button></p>
<p class="form-msg" id="s-msg" role="status" aria-live="polite"></p></form>
<h2>{sub['mine']}</h2><ul class="mine" id="s-mine"></ul></div></div>
<script src="{'' if self.L == 'zh' else '../'}submit.js" defer></script>"""
        self.write("submit.html", f"{sub['title']} - {t['brand_text']}", submit, sub["lead"], "")

        th = "".join(f"<th>{x}</th>" for x in t["j_th"])
        jr = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in t["j_rows"])
        join = f"""<h1>{t['j_h1']}</h1><p class="lead">{t['j_lead']}</p>
<table class="kv"><tr>{th}</tr>{jr}</table>
<p>{t['j_models']}</p><p>{t['j_no']}</p>
<p class="actions"><a class="btn primary" href="{REPO}/catalog/blob/main/CONTRIBUTING.md">{t['j_spec']}</a> <a class="btn" href="{issues}">{t['j_submit']}</a> {f'<a class="btn" href="mailto:{EMAIL}">{t["j_mail"]}</a>' if EMAIL else ''}</p>"""
        # providers-join.html is not published until it has a proper design

        if self.posts:
            items = "".join(
                f'<li><a href="{e(x["slug"])}.html"><time datetime="{e(x["date"])}">{e(x["date"])}</time><b>{e(x["title"])}</b>'
                + (f'<span>{e(x["summary"])}</span>' if x["summary"] else "") + '</a></li>' for x in self.posts)
            self.write("blog/index.html", t["blog_title"], f'<section class="hero"><h1>{t["blog_h1"]}</h1><p class="lead">{t["blog_lead"]}</p></section><ul class="post-list">{items}</ul>',
                       t["blog_lead"], "blog")
            for x in self.posts:
                body = (f'<p class="crumb"><a href="index.html">{t["nav"]["blog"]}</a></p><article class="post"><h1>{e(x["title"])}</h1>'
                        f'<p class="muted"><time datetime="{e(x["date"])}">{e(x["date"])}</time></p><div class="prose">{x["html"]}</div></article>')
                self.write(f"blog/{x['slug']}.html", f"{x['title']} - {t['brand_text']}", body, x["summary"], "blog")

        base = SITE if self.L == "zh" else SITE + "en/"
        feed = {"version": "https://jsonfeed.org/version/1.1", "title": t["feed_title"], "home_page_url": base,
                "items": [{"id": p["id"], "title": self.pname(p["id"]), "content_text": "; ".join(self.quota_text(p, i) for i in range(len(p["quotas"]))),
                           "url": f"{base}p/{p['id']}.html", "date_modified": p["last_verified"]} for p in providers]}
        (self.out / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
        llms = [t["llms_title"], "", t["llms_intro"], t["llms_data"], "", t["llms_p"], ""]
        for p in providers:
            api_txt = t["llms_api"].format(x=t["llms_can"] if p["api_usable"] else t["llms_cannot"]).replace("  ", " ")
            llms.append(f"- {self.pname(p['id'])}{api_txt}: " + "; ".join(self.quota_text(p, i) for i in range(len(p["quotas"]))) + t["llms_reg"].format(u=p["signup"]["url"]))
        llms += ["", t["llms_m"], ""]
        for m in models:
            ok = [o for o in m["offers"] if o["access"] != "paid"]
            llms.append(f"- {m['name']}: " + t["list"].join(f"{self.pname(o['provider'])} ({t['access'][o['access']]}, {o['model']})" for o in ok))
        (self.out / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")


def main() -> None:
    cat = load(sys.argv[1] if len(sys.argv) > 1 else f"{DIST}/catalog.json")
    sq = load(sys.argv[2] if len(sys.argv) > 2 else f"{DIST}/models.json")
    # providers rank by the catalog's score: quality of the models each serves without charge, weighted by how
    # lasting the access is (free models x1, renewing free quota x0.5, one-time gift x0.2); unverified entries last
    pinfo = sq.get("providers") or {}
    pheat = {pid: v.get("score", 0) for pid, v in pinfo.items()}
    providers = sorted(cat["providers"], key=lambda p: (p.get("status") != "verified", -pheat.get(p["id"], 0), p["name"].lower()))
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
    (OUT / "download").mkdir(parents=True)
    for f in ("style.css", "app.js", "submit.js", "icon.png"):
        shutil.copy(ROOT / "static" / f, OUT / f)
    shutil.copytree(ROOT / "static" / "fonts", OUT / "fonts")
    shutil.copytree(ROOT / "static" / "logos", OUT / "logos")
    dl_items = []
    for f in sorted((ROOT / "static" / "download").glob("*.exe")) if (ROOT / "static" / "download").exists() else []:
        shutil.copy(f, OUT / "download" / f.name)
        dl_items.append({"name": f.name, "size": f.stat().st_size, "sha": hashlib.sha256(f.read_bytes()).hexdigest()})
    release = latest_release()

    for lang in ("zh", "en"):
        Site(lang, cat, sq, providers, models, slug_of).build(dl_items, release)
    (OUT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    (OUT / "models.json").write_text(json.dumps(sq, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pages = sorted(str(f.relative_to(OUT)).replace("\\", "/") for f in OUT.rglob("*.html"))
    urls = "".join(f"<url><loc>{SITE}{u}</loc></url>" for u in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"ok: {len(models)} models, {len(providers)} providers, zh + en -> {OUT}")


if __name__ == "__main__":
    main()
