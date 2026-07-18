# Hy3 接入指南

在常用开发工具和平台里配置 Hy3 的说明与截图。

关联：[Issue #2](https://github.com/Tencent-Hunyuan/Hy3/issues/2)

## 通用参数

Hy3 走 OpenAI 兼容接口，常见有两种地址：

**OpenRouter**（下文截图主要用这个）

| 项 | 值 |
|----|-----|
| Base URL | `https://openrouter.ai/api/v1` |
| API Key | [OpenRouter](https://openrouter.ai/keys) 创建 |
| Model | 页面上的模型 ID，例如 `tencent/hy3:free` |
| Max tokens | 建议 4096～8192，别填特别大的数（容易 400） |

**腾讯云 TokenHub**

| 项 | 值 |
|----|-----|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| API Key | TokenHub 控制台 |
| Model | `hy3` |

截图里的 Key 请打码，仓库里也不要提交真实密钥。

## 工具列表

| 工具 | 说明 | 文档 |
|------|------|------|
| Continue | VS Code 插件 | [continue.md](./continue.md) |
| Cline | VS Code 插件 | [cline.md](./cline.md) |
| Roo Code | VS Code 插件 | [roo-code.md](./roo-code.md) |
| OpenRouter | 网页对话 + API | [openrouter.md](./openrouter.md) |
| Dify | 应用搭建平台 | [dify.md](./dify.md) |

每篇结构大致是：安装 → 配置 → 试一次 → 截图 → 坑。

截图目录：[`assets/`](./assets/)

## 小 demo

另开了一个仓库，用命令行给代码补注释（同样调 Hy3）：

- 仓库：`https://github.com/<username>/hy3-showcase-demo`
- 演示：`demo.mp4`（或仓库里写的视频链接）

本地跑：

```powershell
pip install openai
$env:HY3_API_KEY = "your-key"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
python comment_gen.py -f sample.py -o sample_commented.py
```
