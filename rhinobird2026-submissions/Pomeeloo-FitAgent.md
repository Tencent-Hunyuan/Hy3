# FitAgent — 基于 Hy3 的 AI 健身助手

> 犀牛鸟实战 issue《Build a vibe-coded application powered by Hy3》提交
> 作者:Pomeeloo　|　独立应用仓库:https://github.com/Pomeeloo/fitagent

## 项目简介
一站式 AI 健身助手:拍照识食 · 姿态分析 · 智能配餐 · 训练计划 · AI 教练对话。计算机视觉 + 大语言模型,已有 61 位真实用户稳定使用。

## Hy3 在系统中的角色(核心大脑)
腾讯混元 Hy3(腾讯云 TokenHub,model=hy3,OpenAI 兼容)全程 API 调用,无训练/微调/本地推理:任务规划、json_object 结构化产出、AI 教练多轮对话+跨会话记忆、基于 MediaPipe 的姿态报告。视觉感知(Qwen-VL 识食)与视觉生成(z-image-turbo 配图)为辅助模块。

## 满足要求
全程 API 调用 Hy3(无训练/微调/本地部署) · 可交互前端(React 19 Web + CLI) · 2 个端到端 demo + 78s 视频(<2min) · 开源 MIT,README 写明 Hy3 角色 + WorkBuddy 协作记录
