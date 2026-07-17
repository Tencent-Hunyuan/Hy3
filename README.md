# TimePlanner · 个人工作时间规划 
仓库地址：https://github.com/Lyqie/TimePlanner.git  
一个'前后端分离、本地优先（Local-first）'的个人时间规划 Web 应用，覆盖「规划 — 专注 — 复盘」完整闭环：在日历上以时间块排程任务，用番茄钟专注并记录会话，最终通过报表复盘时间投入。

> 数据存放在本地 SQLite，无需任何外部服务即可运行；同时保留完整后端 API，未来可平滑扩展云端同步与多设备账号。

## ✨ 功能特性

- **仪表盘 Dashboard**：今日任务数、已完成、专注时长、时间利用率一览，及今日时间轴预览与快捷入口。
- **日历排程 Calendar**：日 / 周 / 月视图，拖拽安排时间块，按分类着色，点击编辑。
- **任务清单 Tasks**：任务增删改查，优先级 / 状态 / 分类筛选与搜索，分类管理。
- **番茄钟 Pomodoro**：圆形进度环计时，可绑定当前任务，自定义工作 / 休息时长，自动落库专注会话。
- **统计报表 Reports**：按本周 / 本月 / 自定义区间，展示每日专注趋势、分类时间占比、任务专注榜。
- **暗色模式**：玻璃拟态 + 靛蓝紫渐变，支持亮 / 暗主题切换。

## 🧱 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 18 + Vite + TypeScript + Tailwind CSS |
| 状态 | Zustand（局部 UI / 计时）+ TanStack Query（服务端缓存） |
| 组件 | FullCalendar（日历）、Recharts（图表）、framer-motion（动效）、lucide-react（图标） |
| 后端 | Node.js + Express + TypeScript |
| 数据 | Prisma ORM + SQLite（零配置本地库） |
| 工程 | pnpm workspace 单体仓库，前后端共享 `@app/shared` 类型契约 |

## 🗂️ 架构

```
浏览器 React SPA ──TanStack Query──▶ Express REST API (/api/v1) ──Prisma──▶ SQLite
        │                                 ▲
        └──────── Zustand（UI/计时） ─────┘
        @app/shared 类型契约同时约束前后端，改一处即全量类型校验
```

## 🚀 本地运行

```bash
# 1. 安装依赖（pnpm 11 会在 pnpm-workspace.yaml 中放行 prisma/esbuild 构建脚本）
pnpm install

# 2. 生成 Prisma 客户端并初始化数据库（首次需执行）
pnpm --filter backend prisma:generate
pnpm --filter backend db:push
pnpm --filter backend db:seed      # 写入示例分类/任务/时间块/番茄记录

# 3. 同时启动前后端（Vite 5173 + API 4000）
pnpm dev
```

打开 http://localhost:5173 即可使用。单独运行：`pnpm --filter backend start`、`pnpm --filter frontend dev`。

## 📁 目录结构

```
.
├── shared/types/      # 前后端共享领域模型与 API DTO
├── backend/           # Express + Prisma + SQLite（routes / controllers / middleware）
└── frontend/          # React + Vite（pages / components / hooks / store / api）
```

## 🤖 Hy3 在本项目中的作用

本项目由 **Hy3**（驱动 CodeBuddy 编程助手的 AI 模型）从零端到端生成：

1. **需求澄清与设计**：在仅有「想做个人时间规划 app」这一初始想法时，Hy3 主动给出技术选型、数据模型、功能模块与分期落地建议，并把方案落成可执行的计划。
2. **架构与脚手架**：搭建 pnpm 单体仓库、共享类型契约，确定「前后端分离 + 本地优先」架构，避免后续云同步时的重构成本。
3. **后端实现**：编写 Express 路由、Prisma Schema（Category / Task / TimeBlock / PomodoroSession）、统一错误处理、统计与仪表盘聚合查询，以及种子数据。
4. **前端实现**：搭建 React + Vite + Tailwind 工程，实现路由与玻璃拟态布局、FullCalendar 时间块拖拽、TanStack Query 数据层、Zustand 计时器、Recharts 报表，以及五个核心页面。
5. **工程问题排查**：识别并解决 pnpm 11 默认阻止依赖构建脚本（`onlyBuiltDependencies` 配置位置变更）、共享类型与 API 返回结构不一致等真实问题。
6. **验证交付**：通过类型检查、生产构建、运行时健康检查与 API 代理冒烟测试，确认全栈可用后再交付。

简而言之，Hy3 承担了从「想法」到「可运行应用」的设计、编码、排障与验证全过程，使用者只需提出需求与确认方向。
