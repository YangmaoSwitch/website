# 羊毛switch 官网 / YangmaoSwitch Website

> 开发中。

## 页面

- **额度目录（首页）**：
  - 汇总各平台的免费额度，可按多个维度筛选。
  - 每个平台的卡片上写明额度口径、可用模型、注册要求，以及风险提示（例如额度用完会自动扣费、条款限制）。
  - 卡片上标注最后核实时间和证据链接。
- **平台详情页**：开通步骤、额度变化历史、条款要点。
- **下载页**：
  - Windows／macOS／Linux 安装包、校验和、更新日志。
  - 安全说明：Key 只存在用户本机，服务器不接触 Key，也不转发调用。
- **平台入驻页**：L1／L2／L3 接入规范，详见 [catalog/CONTRIBUTING.md](https://github.com/YangmaoSwitch/catalog/blob/main/CONTRIBUTING.md)。
- **订阅**：RSS、JSON feed，以及给 Agent 读取的 `llms.txt`。

## 数据与构建

全部来自 [YangmaoSwitch/catalog](https://github.com/YangmaoSwitch/catalog)，由 `build.py` 静态生成到 `public/`，GitHub Actions 部署到 GitHub Pages。

```bash
python build.py                      # 从线上目录构建
python build.py path/to/catalog.json # 用本地目录构建
```

## 许可证

[MIT](LICENSE)
