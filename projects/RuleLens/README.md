# RuleLens · 规则透镜

> 把规则文档变成可验证的边界案例。

RuleLens 接收一份规则类文档（比赛章程、课程制度、报销规定、实验室规范等），借助 **Hy3** 完成：
规则提取 → 边界案例生成 → 互动裁决闯关 → 歧义 / 冲突审查 → Markdown / JSON 导出。
每条结论都必须关联本地生成的来源编号，并由程序核验引用是否真实存在于原文。

## 效果演示

### 创新比赛报名规则

![创新比赛报名规则演示](assets/demo1.gif)

### 课程考勤与作业制度

![课程考勤与作业制度演示](assets/demo2.gif)

---

## 主要功能

- **规则地图**：从文档中提取资格、义务、禁止、截止、阈值、例外、后果、定义与优先级，按主题分组展示，并标注来源编号。
- **情景闯关**：生成 6～12 个覆盖临界值、组合条件、例外、跨条款、冲突、累计等边界类型的现实情景，用户判断「符合 / 不符合 / 信息不足」。
- **可核验裁决**：每题由 Hy3 给出结论、简短依据、适用规则与原文证据；程序本地核验引用是否存在、引文是否逐字来自原文。
- **歧义雷达**：识别条款冲突、术语模糊、边界缺失、流程缺失、例外缺失、不可验证、重复等问题，按严重程度排序。
- **原文与导出**：带来源编号的原文检索，报告可导出为 Markdown 或 JSON。

## 与通用文档问答的区别

普通 PDF 聊天只能压缩内容、回答单点问题。RuleLens 的差异：

- **面向「规则理解与压力测试」**，而非通用摘要；
- 强调 **Hy3 的长上下文理解、复杂条件推理与指令遵循**；
- **每条结论可追溯到本地来源编号**，且引用经程序核验，杜绝「编造来源」；
- 通过 **边界案例闯关** 提供明确的交互闭环，暴露读者对规则的误解；
- 无需训练、微调、本地推理、向量库或复杂 Agent 框架。

## Hy3 的作用

| 阶段 | Hy3 承担的工作 |
|---|---|
| 规则提取 | 从带来源编号的文档中识别条件、例外、后果、定义与优先级，输出结构化规则 |
| 情景生成 | 基于规则 JSON 生成覆盖不同边界类型的现实情景 |
| 单题裁决 | 仅依据关联规则与来源块，给出结论、依据、适用规则与原文证据 |
| 歧义分析 | 识别冲突、模糊、缺失与不可执行条款，区分「明确问题」与「建议确认」 |

本地代码只负责文件解析、来源编号、数据校验、引用核验、状态管理、页面渲染与导出，
**不使用其他大语言模型替代 Hy3**。

## 系统架构

```text
Streamlit UI (src/rulelens/ui)
    -> AnalysisService (src/rulelens/services/analysis_service.py)
        -> DocumentExtractor   (src/rulelens/ingestion/extractors.py)
        -> SourceIndexer       (src/rulelens/ingestion/source_indexer.py)
        -> Hy3Client           (src/rulelens/llm/hy3_client.py)
        -> CitationVerifier    (src/rulelens/services/citation_verifier.py)
        -> ExportService       (src/rulelens/services/export_service.py)
```

目录结构：

```text
rulelens/
├─ README.md
├─ pyproject.toml
├─ .env.example
├─ .gitignore
├─ app.py
├─ data/samples/                # 两份内置示例文档
├─ src/rulelens/
│  ├─ config.py  models.py  exceptions.py
│  ├─ ingestion/                # 文件解析 + 来源编号
│  ├─ llm/                      # Hy3 客户端 + JSON 解析 + Prompt
│  ├─ services/                 # 分析流水线 + 引用核验 + 导出
│  └─ ui/                       # Streamlit 状态与组件
└─ tests/                       # 自动化测试
```

## 本地安装与启动

要求 Python 3.11+。

```powershell
cd rulelens
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
# 编辑 .env，填入 Hy3 API 配置
streamlit run app.py
```

Linux / macOS：

```bash
cd rulelens
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env          # 然后编辑填入 Hy3 配置
streamlit run app.py
```

## 环境变量

| 变量 | 说明 | 示例值 |
|---|---|---|
| `HY3_API_KEY` | Hy3 API 密钥（仅从环境变量读取） | `replace_me` |
| `HY3_BASE_URL` | Hy3 OpenAI 兼容端点 | `https://api.example.com/v1` |
| `HY3_MODEL` | 模型名 | `hy3` |
| `HY3_REASONING_EFFORT` | 推理强度 `high` / `no_think` | `high` |
| `HY3_ENABLE_REASONING_PARAM` | API 不支持推理扩展参数时设为 `false` | `true` |
| `HY3_REASONING_PARAM_STYLE` | 推理参数格式：`chat_template_kwargs` 或 `direct` | `chat_template_kwargs` |
| `HY3_ENABLE_RESPONSE_FORMAT` | 是否请求 JSON Schema 结构化输出 | `true` |
| `HY3_TIMEOUT_SECONDS` | 单次 API 超时 | `120` |
| `HY3_MAX_RETRIES` | 瞬时错误重试次数 | `2` |
| `RULELENS_MAX_FILE_MB` | 文件大小上限 | `10` |
| `RULELENS_MAX_CHARS` | 提取后字符数上限 | `100000` |

## 快速体验

1. 启动后在初始页点击 **「📘 载入比赛规则示例」** 或 **「📗 载入课程制度示例」**；
2. 点击 **「🚀 开始分析」**（未配置 API 时会提示先填写 `.env`）；
3. 在「规则地图」查看结构化规则与来源；
4. 在「情景闯关」逐题作答，查看裁决、依据与原文证据；
5. 在「歧义雷达」查看潜在冲突与缺失；
6. 在「导出」下载 Markdown 或 JSON 报告。

两个示例包含可供检测的典型规则问题：
- 比赛规则：总则允许补交 vs 后文「逾期补充一律无效」的**冲突**，以及「5 个工作日」中**工作日未定义**；
- 课程制度：「严重迟交」**表述模糊**，以及**恰好迟到 15 分钟**如何处理这一边界未说明。

## 隐私、限制与免责声明

- 密钥仅从环境变量读取；日志不打印密钥、Authorization 头或完整文档。
- 默认不把上传文件与分析结果持久化到磁盘。
- 当前版本**不支持 OCR / 扫描版 PDF**，请上传含文本层的 PDF 或转换为 TXT / MD。
- 不支持登录注册、多用户权限、云数据库、法律 / 医疗结论保证、自动执行文档操作、联网搜索、训练微调。
- **免责声明**：本报告由 AI 辅助生成，不构成法律、合规或专业意见；引用核验仅验证原文一致性，不保证规则解释无误。
- 请勿上传机密文件。

## 开源许可

本项目采用 **MIT** 许可。
