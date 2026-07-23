# Hy3 模型概览

Source: https://github.com/Tencent-Hunyuan/Hy3/blob/rhinobird2026/README_CN.md

Hy3 是腾讯混元团队研发的快慢思考融合混合专家模型。总参数量 295B，激活参数 21B，MTP 层参数 3.8B；共有 192 个专家，每次 top-8 激活。

模型上下文长度为 256K。它重点增强了推理、智能体、长上下文、多轮意图保持、工具调用和输出格式稳定性。

官方推荐参数为 temperature=0.9、top_p=1.0。reasoning_effort 支持 no_think、low 和 high：复杂数学、编程和推理任务建议 high，日常问题可使用 no_think。
