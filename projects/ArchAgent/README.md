# ArchAgent：由 Hy3 驱动的桌面空间设计智能体

- 项目仓库：[xy200303/ArchAgent](https://github.com/xy200303/ArchAgent)
- 许可证：AGPL-3.0-only
- 形态：Electron 桌面应用（React + React Three Fiber）

ArchAgent 面向建筑、房间与室内场景的快速设计。用户可在对话面板中描述空间需求，应用会将需求转换为可编辑的墙体、门窗、楼板、区域和家具节点，并在同一工作台中实时预览、调整和导出 3D 场景。

## Hy3 在系统中的角色

ArchAgent 全程通过 API 调用 Hy3，不进行训练、微调或本地推理部署。应用在 Electron Main 进程中读取 `HY3_API_KEY`、`HY3_BASE_URL` 和 `HY3_CHAT_MODEL`，以 OpenAI-compatible Chat Completions 协议连接 Hy3；API Key 不会暴露给 Renderer。

Hy3 作为多轮设计 Agent 的核心模型，负责：

- 理解用户的自然语言空间设计需求和图片附件。
- 基于会话上下文规划下一步操作，并调用受限建模工具。
- 生成和修订场景命令，包括创建或修改墙体、门窗、楼板、房间区域和家具。
- 在需要时调用混元图像与 3D API，完成参考图预览和图像转 3D 工作流。

## 可交互前端

应用提供完整的 Electron 图形界面：右侧对话区用于输入需求和查看 Agent 工具调用，中央 React Three Fiber 编辑器用于实时 3D 预览，工具栏和属性面板支持选择、移动、旋转、缩放、画墙、放置构件与导出 GLB / STL / OBJ / JSON。

## 端到端演示流程

以下两条流程的操作脚本和可复现入口已包含在项目中；录屏或 GIF 将在本 PR 更新为 Ready for review 前补充：

1. **自然语言创建并迭代房间**：输入“创建一个 5m x 4m 的卧室，南墙开一扇门和一扇窗”，Hy3 调用场景工具建立节点；用户在 3D 编辑器中检查布局，再以对话继续调整尺寸或家具位置，最后导出模型。
2. **参考图到可编辑 3D 资产**：导入参考图片，Hy3 结合混元图像与 3D API 生成预览或 3D 资产；用户将资产放入场景、在属性面板调整位置和旋转，并导出结果。

## 运行

```bash
git clone https://github.com/xy200303/ArchAgent.git
cd ArchAgent
npm install
copy .env.example .env.local
npm run dev
```

在 `.env.local` 中填写 Hy3 API 配置后，即可通过桌面界面完成上述流程。更多配置、工具列表、测试命令和设计说明见 [ArchAgent README](https://github.com/xy200303/ArchAgent#readme)。
