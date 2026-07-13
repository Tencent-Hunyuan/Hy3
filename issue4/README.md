# Hy3 深度研究助手

> 基于**腾讯混元 Hy3 API** 构建的个人研究助手。全程通过 TokenHub API 调用 Hy3，不依赖本地模型、不涉及训练或微调。
>
> 核心思路：充分压榨 Hy3 的推理思考、长上下文和多语种能力，让对话有深度、研究有结构、翻译有风格。
>
> 演示视频.mp4
> 链接: https://pan.baidu.com/s/1sHcLqZMKfLmMZupdJrfzgA?pwd=1111 提取码: 1111

---

## 功能概览

| 模块 | Hy3 能力 | 实现方式 |
| --- | --- | --- |
| 智能对话 | 推理思考 + 文本生成 | SSE 流式，可选深度思考模式，展示推理过程 |
| 深度研究 | 推理思考 + 长文结构化输出 | SSE 流式，可选深度思考，六段式结构化报告 |
| 翻译重写 | 多语种翻译 + 风格转换 | JSON 返回，支持 14 种语言方向 + 7 种风格 |

所有能力通过 [腾讯云 TokenHub](https://tokenhub.tencentmaas.com/) 的 OpenAI 兼容接口 (`/v1/chat/completions`) 调用，模型名 `hy3`。

### 深度思考模式

勾选"深度思考"后，后端向 Hy3 传入 `reasoning_effort: "high"` 和 `thinking: { type: "enabled" }` 参数。Hy3 会先进行内部推理，输出思考过程（`reasoning_content`），再给出最终答案。前端以可折叠面板展示推理过程：

- **对话面板**：思考过程以独立气泡展示，点击"思考过程"按钮展开/折叠
- **研究面板**：推理过程以 `<details>` 折叠面板展示，默认展开

---

## 快速开始

### 前置条件

- Node.js >= 18
- 腾讯云 TokenHub API Key

### 1. 获取 API Key

访问 [TokenHub 控制台](https://tokenhub.tencentmaas.com/)，创建 API Key。

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的密钥：

```env
HY3_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
PORT=3000
```

### 3. 安装依赖并启动

```bash
npm install
npm start
```

打开 `http://localhost:3000` 即可使用。

### 离线演示（Mock 模式）

如果暂时没有 API Key：

```bash
HY3_MOCK=1 npm start
```

所有接口返回模拟数据，不产生任何真实 API 调用。配置 `HY3_API_KEY` 后 Mock 模式自动失效。

---

## API 接口

| 方法 | 路径 | 类型 | 参数 |
| --- | --- | --- | --- |
| `GET` | `/api/health` | JSON | — |
| `POST` | `/api/chat` | SSE 流 | `messages`, `think` |
| `POST` | `/api/research` | SSE 流 | `topic`, `think` |
| `POST` | `/api/translate` | JSON | `text`, `direction`, `style` |

### `think` 参数

传递 `think: true` 时：
- 请求体附带 `reasoning_effort: "high"` 和 `thinking: { type: "enabled" }`
- SSE 事件追加 `reasoning` 类型，包含模型的内部推理过程
- 前端自动渲染可折叠的思考面板

### `direction` 参数

| 值 | 说明 | 值 | 说明 |
| --- | --- | --- | --- |
| `auto` | 自动检测中英互译 | `zh2ru` | 中文 → 俄文 |
| `zh2en` | 中文 → 英文 | `zh2ar` | 中文 → 阿拉伯文 |
| `en2zh` | 英文 → 中文 | `en2ja` | 英文 → 日文 |
| `zh2ja` | 中文 → 日文 | `en2ko` | 英文 → 韩文 |
| `zh2ko` | 中文 → 韩文 | `en2fr` | 英文 → 法文 |
| `zh2fr` | 中文 → 法文 | `en2de` | 英文 → 德文 |
| `zh2de` | 中文 → 德文 | `en2es` | 英文 → 西班牙文 |
| `zh2es` | 中文 → 西班牙文 | | |

### `style` 参数

`casual` / `formal` / `academic` / `technical` / `marketing` / `creative` / `social`

---

## 项目结构

```
.
├── server.js           # Express 后端：路由、SSE 流代理、推理解析
├── public/
│   ├── index.html      # 前端页面（三面板 Tab 切换）
│   ├── style.css       # 暗色主题 + 推理面板样式
│   └── app.js          # SSE 流渲染、推理展示、状态管理
├── demos/
│   ├── chat-demo.js    # CLI 流式对话演示
│   ├── research-demo.js # CLI 深度研究演示
│   └── translate-demo.js # CLI 翻译重写演示
├── .env.example        # 环境变量模板
├── .gitignore
├── package.json
└── README.md
```

---

## 工作流程

### 对话

```
用户输入 → POST /api/chat (SSE) → Hy3 流式生成 → 逐字渲染
                                    ├─ 推理内容 → reasoning 事件 → 可折叠思考面板
                                    └─ 正文内容 → text 事件 → 对话气泡
```

### 深度研究

```
用户输入主题 → POST /api/research (SSE) → Hy3 流式生成结构化报告
                                              ├─ 推理过程 → reasoning → <details> 面板
                                              └─ 正文 → text → Markdown 渲染
```

System Prompt 要求 Hy3 输出六段式报告：概述 → 现状分析 → 深度剖析 → 案例对比 → 趋势展望 → 结论建议。

### 翻译重写

```
用户输入文本 → POST /api/translate (JSON) → Hy3 一次性翻译 → 返回结果
               direction: 语言方向        style: 风格要求
```

根据 `direction` 和 `style` 构造翻译提示词，设定 `temperature: 0.2` 确保翻译准确性。输出仅包含译文，不含解释。

---

## CLI Demo

Demos 直连 Hy3 API，**无需启动服务**即可运行。未配置 API Key 时自动降级为 Mock 模式。

```bash
# 对话（可选 --think 开启深度思考）
node demos/chat-demo.js "什么是量子纠缠"
node demos/chat-demo.js --think "解释相对论"

# 深度研究
node demos/research-demo.js "量子计算对密码学的冲击"
node demos/research-demo.js --think "AGI 时间线"

# 翻译（不传参批量测试，传参单次翻译）
node demos/translate-demo.js
node demos/translate-demo.js "Hello World" en2zh casual

# 强制 Mock 模式
HY3_MOCK=1 node demos/chat-demo.js "你好"
```

---

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `HY3_API_KEY` | 否* | — | TokenHub API 密钥 |
| `HY3_BASE_URL` | 否 | `https://tokenhub.tencentmaas.com/v1` | API 地址 |
| `HY3_MODEL` | 否 | `hy3` | 模型名称 |
| `PORT` | 否 | `3000` | 服务端口 |
| `HY3_MOCK` | 否 | — | 设为 `1` 启用 Mock 模式 |

> *未配置 API Key 且非 Mock 模式时，服务仍可启动，但 API 接口返回配置错误。

---

## 许可证

MIT
