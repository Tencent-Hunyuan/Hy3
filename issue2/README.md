# Hy3 主流工具集成与 Evidence Board

本目录对应 [Issue #2](https://github.com/Tencent-Hunyuan/Hy3/issues/2)，包含：

- [5 个主流工具的 Hy3 接入指南](integrations/README.md)
- [Hy3 Evidence Board 小作品](demo/README.md)：一个以服务端保管密钥、用 Hy3 工具调用检索本地资料并生成带证据报告的 Web 应用

![Evidence Board 8 秒离线交互演示](assets/evidence-board-demo.gif)

> English: [README.en.md](README.en.md)

## 验证边界

文档中的字段和命令已按各工具官方文档核对；仓库内的离线模式、单元测试和 Web 页面可以在没有 API Key 的环境运行。真实 Hy3 请求需要自行提供 OpenRouter Key 或可访问的自建 Hy3 OpenAI 兼容端点。离线模式会在界面显著标注，不会冒充真实模型输出。

## 目录

```text
issue2/
├── integrations/       # 中英双语接入指南
├── demo/               # 可独立发布的小作品源码
└── assets/             # 本地运行所得截图与演示素材
```
