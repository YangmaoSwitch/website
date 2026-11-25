# 羊毛switch 官网 / YangmaoSwitch Website

> 开源的大模型 Key 与用量管理桌面应用的官网：https://yangmaoswitch.github.io/website/

## 页面

中英双语：中文在根目录，英文在 `/en/`，页面一一对应，互有切换链接。英文文本来自目录条目的 `en` 字段。

- **模型广场（首页）**：可以免费调用的模型，按“模型质量 × 免费可得程度”排序，可按能力、平台筛选，“只看免费”；每个模型一页，列出提供它的全部平台、调用方式、免费额度和标价。
- **Providers**：各平台的免费额度、注册要求、超额处理（写明用完即停时额度是否每日／每月刷新）；每个平台一页，模型按“免费 / 付费”分组。
  - 每条额度附官方依据链接和原文引用；只给新用户的活动标“新用户活动”；已结束的活动标“已下线”，保留不删。
- **调用方式**：全站只分“免费”（免费模型或用免费额度）和“付费”两类，数量写成“免费 X · 付费 Y”。
- **下载页**：Windows 安装包和 SHA-256；安全说明（Key 只存在用户本机，服务器不接触 Key，也不转发调用）。
- **平台入驻页**：L1／L2／L3 接入规范，详见 [catalog/CONTRIBUTING.md](https://github.com/YangmaoSwitch/catalog/blob/main/CONTRIBUTING.md)。
- **机器可读**：`catalog.json`、`models.json`、JSON feed、给 Agent 读取的 `llms.txt`。

## 博客

文章放在 `blog/<slug>.<语言>.md`（语言为 `zh` 或 `en`），开头是简单的头信息：

```
---
title: 标题
date: 2026-11-20
summary: 一句话摘要
draft: true
---
```

`draft: true` 的文章不发布；本地预览草稿用 `YM_BLOG_DRAFTS=1 python build.py`。某种语言没有已发布文章时，导航里不显示“博客”。构建需要 `pip install markdown`。

## 数据与构建

全部来自 [YangmaoSwitch/catalog](https://github.com/YangmaoSwitch/catalog) 的 `dist` 分支（`catalog.json`、`models.json`），由 `build.py` 静态生成到 `public/`，GitHub Actions 部署到 GitHub Pages（`.github/workflows/pages.yml`：推送到 `main`、每 6 小时定时、catalog 发来 `catalog-updated` 时触发）。GitHub 的定时任务常会延后，目录更新后急需上线时，可以向本仓库推一个空提交触发构建。

```bash
python build.py                                   # 从线上数据构建
python build.py path/to/catalog.json path/to/models.json  # 用本地数据构建
```

## 许可证

[MIT](LICENSE)

字体：`static/fonts` 为 Geist / Geist Mono（Vercel，SIL Open Font License 1.1，取自 Fontsource），只用于拉丁字符，中文使用系统字体。

标志：`static/logos` 取自 [LobeHub Icons](https://github.com/lobehub/lobe-icons)（MIT）和 [Simple Icons](https://simpleicons.org)（CC0），商标归各自所有者，仅用于指代对应厂商。
