# Hy3 数据分析 MCP Server

基于 MCP 协议的数据分析工具服务，内部调用 Hy3（腾讯混元）API，对本地 CSV 文件进行智能分析并生成图表。以 stdio 模式运行，可被 Cline、WorkBuddy 等 MCP 客户端直接接入。

核心能力：
- 读取本地数据文件，生成结构化摘要（含分类分布、数值统计、相关性）
- 调用 Hy3 进行智能分析，支持模糊问题自动生成综合报告
- 推荐可视化方案，输出可渲染的 Vega-Lite 图表规范
- 本地精确查询聚合，为分析提供数据支撑

## 安装

一键安装（创建虚拟环境并安装依赖）：

```bash
# Windows PowerShell
./install.ps1
```

手动安装：

```bash
cd hy3_mcp_server
python -m venv .venv
source .venv/Scripts/activate
pip install mcp "openai>=1.40.0" pandas python-dotenv
```

安装完成后，复制环境变量模板并填入密钥：

```bash
cp .env.example .env
```

.env 内容：

```
HY3_API_KEY=你的密钥
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
LLM_REASONING_EFFORT=high
```

注意：Windows 中文路径下不要用 pip install -e .，改用 PYTHONPATH=src 方式运行。

## 启动

```bash
PYTHONPATH=src python -m hy3_mcp_server.server
```

PowerShell：

```powershell
$env:PYTHONPATH="src"; python -m hy3_mcp_server.server
```

## 工具说明

本 Server 暴露 4 个工具：

### load_dataset

读取本地 CSV 文件，返回数据结构摘要。不调用 LLM。

参数：
- file_path（必填）：文件路径
- format（可选）：csv / json / auto，默认 auto

### analyze_data

基于数据摘要调用 Hy3 进行分析。question 为空或模糊时自动生成综合分析报告。

参数：
- file_path（必填）：文件路径
- question（可选）：分析问题，留空则自动生成全面报告
- evidence（可选）：由 query_data 产出的精确统计结果，JSON 字符串

### describe_chart

根据指定列推荐图表类型，输出 Vega-Lite v5 JSON 规范。

参数：
- file_path（必填）：文件路径
- columns（必填）：要可视化的列名列表
- chart_intent（可选）：图表意图描述
- data_records（可选）：精确数据 JSON，覆盖图表数据源

### query_data

在本地对数据做过滤、聚合、排序，返回结构化结果。不调用 LLM。

参数：
- file_path（必填）：文件路径
- operation（可选）：head / describe / aggregate，默认 head
- columns（可选）：操作的列名列表
- group_by（可选）：分组列名
- agg（可选）：聚合函数 mean / sum / count / min / max
- filter_expr（可选）：过滤表达式，如 "学历 == '硕士'"
- sort_by（可选）：排序列
- ascending（可选）：排序方向，默认 True
- limit（可选）：返回行数上限，默认 50

## 工作流

### 快速概览

直接调用 analyze_data，不填 question，Hy3 自动输出包含数据概况、分布特征、相关性、异常点和建议的综合报告。

### 精确分析

先用 query_data 做本地聚合得到精确数据，再把结果传给 analyze_data 的 evidence 参数。适合排名、占比、分组对比类问题。

### 图表生成

用 query_data 聚合数据，再把结果传给 describe_chart 的 data_records 参数，生成基于精确数据的图表规范。

## 使用示例

连通性测试：

```bash
PYTHONPATH=src python scripts/smoke_test.py
```

端到端测试：

```bash
PYTHONPATH=src python scripts/e2e_test.py
```

在 MCP 客户端中的调用示例（以自然语言描述）：
示例：file_path=examples/graduate_employment_sample.csv
1. 查看数据结构：
   调用 load_dataset，file_path 填数据文件路径

2. 快速分析：
   调用 analyze_data，file_path 填路径，question 留空

3. 按专业统计平均薪资：
   调用 query_data，group_by="专业"，columns=["实际薪资"]，agg="mean"，sort_by="实际薪资"，ascending=false

4. 基于聚合结果深入分析：
   调用 analyze_data，file_path 填路径，question="哪个专业薪资最高，高出平均多少"，evidence 填上一步的结果

5. 生成图表：
   调用 describe_chart，file_path 填路径，columns=["专业","实际薪资"]，chart_intent="各专业薪资对比"

## 客户端配置

Cline：将 configs/cline_mcp_settings.json 内容合并到 Cline 的 MCP 设置中。

WorkBuddy：参照 configs/workbuddy_mcp.md 添加配置。


## 附录：项目结构

```
hy3_mcp_server/
├── .env.example              环境变量模板，复制为 .env 后填入密钥
├── .env                      实际密钥文件（不入仓库）
├── .gitignore                忽略 .env、.venv、__pycache__ 等
├── pyproject.toml            项目元数据与依赖声明
├── install.sh                Linux/macOS 一键安装脚本
├── install.ps1               Windows PowerShell 一键安装脚本
├── README.md                 说明文档
├── configs/
│   ├── cline_mcp_settings.json   Cline 客户端 MCP 配置示例
│   └── workbuddy_mcp.md          WorkBuddy 客户端配置说明
├── examples/
│   ├── graduate_employment_sample.csv  就业数据集示例
│   └── 大学生毕业就业岗位选择数据集.csv  就业数据集（来自和鲸社区）
├── scripts/
│   ├── smoke_test.py             连通性测试，验证 Hy3 API 可用
│   └── e2e_test.py               端到端测试，依次调用四个工具
└── src/hy3_mcp_server/
    ├── __init__.py               包入口，声明版本
    ├── server.py                 MCP Server 主文件，注册四个工具，定义工具逻辑
    ├── llm_client.py             Hy3 API 调用封装，统一管理模型参数
    └── data_loader.py            数据加载、摘要生成、本地查询聚合
```
