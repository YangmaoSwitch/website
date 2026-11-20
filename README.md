# 羊毛switch 官网 / YangmaoSwitch Website

> 开源的大模型 Key 与用量管理桌面应用的官网：https://yangmaoswitch.github.io/website/

## 页面

- **模型广场（首页）**：可以免费调用的模型，按能力、调用方式、平台筛选；每个模型一页，列出提供它的全部平台、调用方式（免费模型／用免费额度／付费）、免费额度和标价。
- **Providers**：各平台的免费额度（附官方依据）、注册要求、超额处理；每个平台一页，含该平台的模型列表和标价。
- **下载页**：Windows 安装包和 SHA-256；安全说明（Key 只存在用户本机，服务器不接触 Key，也不转发调用）。
- **平台入驻页**：L1／L2／L3 接入规范，详见 [catalog/CONTRIBUTING.md](https://github.com/YangmaoSwitch/catalog/blob/main/CONTRIBUTING.md)。
- **机器可读**：`catalog.json`、`models.json`、JSON feed、给 Agent 读取的 `llms.txt`。

## 数据与构建

全部来自 [YangmaoSwitch/catalog](https://github.com/YangmaoSwitch/catalog) 的 `dist` 分支（`catalog.json`、`models.json`），由 `build.py` 静态生成到 `public/`，GitHub Actions 部署到 GitHub Pages。

```bash
python build.py                                   # 从线上数据构建
python build.py path/to/catalog.json path/to/models.json  # 用本地数据构建
```

## 许可证

[MIT](LICENSE)
