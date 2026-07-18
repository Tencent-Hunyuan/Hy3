# rhinobird2026 Issue 完成度对照清单

对照 issue【Build a vibe-coded application powered by Hy3】逐条核对。
✅ = 已完成  ⏳ = 待你处理  ❌ = 未完成

---

## 一、硬性提交要求

- [x] **基于活动分支 `rhinobird2026` 开发**
  - 本地分支 `rhinobird2026` 已提交到 fork `northernmountai8n/Hy3`。
- [x] **向 `rhinobird2026` 提交 Pull Request**
  - 开 PR 链接：`https://github.com/Tencent-Hunyuan/Hy3/compare/rhinobird2026...northernmountai8n:Hy3:rhinobird2026`
  - 目标分支选 **rhinobird2026**（不是 main，之前给的"PR 到 main"已纠正）。
- [x] **项目开源 + README 写明 Hy3 角色**
  - 见 `README.md` → 「Hy3 在系统中的角色」章节。
- [x] **README 记录 CodeBuddy/WorkBuddy 协作**
  - 见 `README.md` → 「CodeBuddy / WorkBuddy 协作说明」章节。

## 二、应用本身要求

- [x] **全程通过 API 调用 Hy3，不做训练/微调/本地部署**
  - Hy3 仅用于问答生成（OpenAI 兼容 `/v1`，`extra_body={"reasoning_effort":"low"}`）。
  - 嵌入用本地 ONNX（paraphrase-multilingual-MiniLM-L12-v2），无 torch/sentence-transformers。
- [x] **至少 1 个可交互前端**
  - Web UI：上传 / 文件夹管理 / 检索问答 / 对话记忆，运行于 http://127.0.0.1:8766。
- [x] **端到端可运行**
  - `python run.py` 一键启动；`/api/health` 返回 `{"status":"ok",...}`。

## 三、演示素材（唯一硬性缺口）

- [⏳] **至少 2 个端到端 demo 流程**
  - Demo 1：上传 → 检索 → 流式问答（见 `demo/README.md` §2）
  - Demo 2：文件夹限定 + 多轮记忆（见 `demo/README.md` §3）
- [⏳] **≤2 分钟视频或 GIF**
  - 录制后放入 `demo/`，命名 `demo1-*.gif` / `demo2-*.gif`。
  - 提交：`git add demo/*.gif && git commit -m "demo: ..." && git push`

## 四、活动流程（需你手动）

- [⏳] **在 issue 评论区回复「已认领本任务」**
  - 否则认领无效（7/1~7/31 内，7/1 前无效）。
- [⏳] **完成犀牛鸟报名问卷**
  - https://wj.qq.com/s2/26888567/gh2q （用于活动登记和奖励发放）。

## 五、加分项（已具备，可在 PR 中突出）

- [x] 多语种 embedding（中英文均支持）
- [x] 14 种文档格式解析（含 PDF 防段错误兜底）
- [x] 对话持久化 + 文档记忆 + 文件夹分类
- [x] 完整可复现 Prompt（`REPRODUCE_PROMPT.md`，可交其他 agent 重建）

---

## 提交前最后自查

1. `git push` 后，fork 的 `rhinobird2026` 含最新 README + demo 素材。
2. PR 描述用了 `PR_DESCRIPTION.md` 模板，demo 链接已填。
3. issue 评论「已认领本任务」+ 问卷已填。
