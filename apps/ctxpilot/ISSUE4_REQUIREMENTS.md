# 犀牛鸟实战 Issue #4 —— Build a vibe-coded application powered by Hy3

> 本文件记录活动 issue 的硬性要求与边界，作为 `Hy3_APP` 目录开发的验收基线。
> 来源：https://github.com/Tencent-Hunyuan/Hy3/issues/4

---

## 一、基本信息

| 项 | 内容 |
|---|---|
| 仓库 | `Tencent-Hunyuan/Hy3` |
| Issue | **#4** 【犀牛鸟实战issue】Build a vibe-coded application powered by Hy3 |
| 作者 / 时间 | yqc01，开放于 2026-07-06 |
| 标签 | 犀牛鸟-中高难度 · 腾讯犀牛鸟开源专属 |
| 性质 | 2026 犀牛鸟开源人才培养活动专属 issue，仅限已报名同学认领 |
| 活跃度 | 81 条评论（竞争激烈，需做出差异度）|

---

## 二、硬性要求（必须满足）

1. **全程通过 API 调用 Hy3** —— 不允许训练 / 微调 / 本地推理部署。使用 CodeBuddy / WorkBuddy + Hy3 API 进行 vibe coding。
2. **基于专用分支 `rhinobird2026` 开发并提 PR**；若产出为独立应用仓库，需在 PR 中补充项目说明与仓库链接。
3. **至少 1 个可交互前端**（Web / CLI / IDE 插件 均可）。
4. **至少跑通 2 个端到端 demo 流程**，附 **≤ 2 分钟视频或 GIF**。
5. **项目开源**，README 必须写明 **Hy3 在系统中承担的角色**。
6. 鼓励（非必须）在 README 记录「哪些代码块由 CodeBuddy 协作完成」。

---

## 三、参考选题（可自拟）

- 个人深度研究助手（plan + 搜索 + 长文报告 + 引用）
- 代码评审 / PR 摘要机器人
- 多文档 RAG 问答（论文 / 法规 / 技术手册）
- 多语种翻译 + 语气重写工具
- 复杂任务 Agent（多工具：搜索 / 代码执行 / 文件处理）
- 教育类：自动出题 + 解析 + 错题本
- 知识图谱 / 思维导图自动生成器
- 终端命令行助手（自然语言 → shell 命令并解释）

---

## 四、时间节点

- **认领时间：2026-07-01 ～ 2026-07-31**（7/1 前认领无效）
- 认领方式：在 issue #4 评论区回复「已认领本任务」
- 需先完成犀牛鸟报名问卷：https://wj.qq.com/s2/26888567/gh2q

---

## 五、Hy3 API 接入要点

- **OpenAI 兼容接口**：本地部署（vLLM/SGLang）`base_url=http://127.0.0.1:8000/v1`，model=`hy3`；云端腾讯云 / AI Studio 另有接入文档。
- **推荐参数**：`temperature=0.9`，`top_p=1.0`。
- **推理模式** `reasoning_effort`：`no_think`（默认直接回复）/ `low` / `high`（深度思维链，复杂任务）。
- **关键能力卖点**：256K 上下文、工具调用稳定（适合 Agent）、抗幻觉（「有依据才回答」）、多轮意图保持好 —— PR 中展示 Hy3 能力时可重点戳。

---

## 六、目标分支结构（rhinobird2026）

当前分支仅含官方 `README` / `assets` / `finetune`，**无提交模板**。参与者需自建项目目录（本应用即落在 `Hy3_APP/` 或 `apps/<app-name>/`）并向该分支提 PR。

---

## 七、本应用（待定稿）对照验收清单

| 要求 | 本应用对应方案 |
|---|---|
| API 调用 Hy3 | （开发时填充：Hy3 在系统中承担的智能角色）|
| 基于 rhinobird2026 提 PR | 在 `Hy3_APP/` 下开发，最终合入该分支 |
| 至少 1 个可交互前端 | （Web 仪表盘 / CLI，待定）|
| 至少 2 个端到端 demo + ≤2min 视频 | demo1：___；demo2：___ |
| README 写明 Hy3 角色 | 在 README 中明确 |
| 记录 CodeBuddy 协作块 | 在 README 标注 |
