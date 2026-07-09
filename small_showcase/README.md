# 小说设定编写器

一个**纯前端、零依赖、单文件**的小说设定生成工具。调用腾讯混元（Hunyuan）OpenAI 兼容接口，根据关键词生成结构完整的小说设定，支持流式逐字输出。

## 功能

1. **API 设置**：填写并保存自己的 Hunyuan API Key（仅存于本机浏览器 `localStorage`），支持「测试连接」验证有效性。
2. **作者风格库**：提前写好你欣赏的作者的写作风格，创作时一键套用（单选）。
3. **创作聊天**：输入关键词 + 选择字数规模 + 选择作者风格，像聊天室一样生成小说设定，AI 逐字流式显示，支持复制、重新生成、清空记录、多轮上下文。

## 文件

| 文件 | 说明 |
|------|------|
| `index.html` | 主程序（HTML + CSS + JS 全部内联），双击即可打开 |
| `proxy.js`   | 可选本地 CORS 代理，仅当浏览器直连被跨域拦截时使用 |

## 快速开始

1. 准备一个腾讯混元 API Key（腾讯云控制台 → 混元大模型 → 创建密钥）。
2. 双击 `index.html` 在浏览器打开。
3. 进入 **① API 设置**，粘贴 Key，选模型，点「测试连接」确认可用，点「保存配置」。
4. 进入 **② 作者风格**，新建你想要的作者风格（如「金庸 / 武侠快意恩仇」）。
5. 进入 **③ 创作**，输入关键词、选字数与风格，点「生成」（或 `Ctrl/Cmd + Enter`）。

## 关于 CORS（跨域）

本程序默认**直接调用混元接口**。若浏览器控制台报 CORS 错误导致生成失败，启用随附的本地代理：

```bash
# 需要已安装 Node.js
node proxy.js
```

启动后把 **① API 设置**里的 Base URL 改为：

```
http://localhost:8787/v1
```

代理只在你本机运行，转发你的请求，密钥不经过任何第三方。用完 `Ctrl + C` 关闭即可。

## 数据说明

所有数据（API 配置、作者库、聊天记录）均保存在浏览器的 `localStorage`，清除浏览器数据即会丢失，不会上传到任何服务器。

## 接口信息

- 接口地址：`https://api.hunyuan.cloud.tencent.com/v1/chat/completions`
- 鉴权方式：`Authorization: Bearer <API Key>`
- 流式协议：SSE（`stream: true`，按 `choices[0].delta.content` 增量返回，结束符 `data: [DONE]`）
- 默认模型：`hunyuan-turbos-latest`（另可选 `hunyuan-turbos`、`hunyuan-lite`、`hunyuan-standard` 或自定义）

> 混元能力正逐步迁移至 TokenHub，若将来接口地址变化，只需在「① API 设置」里修改 Base URL。
