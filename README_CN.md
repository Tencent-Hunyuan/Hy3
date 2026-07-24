<p align="left">
   <a href="README.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

<p align="center">
 <img src="assets/logo-zh.png" width="400"/> <br>
</p>

<div align="center" style="line-height: 1;">


[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](#许可证)
&nbsp;&nbsp;
[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Tencent%20Hy-ffc107?color=ffc107&logoColor=white)](https://huggingface.co/tencent/Hy3)
&nbsp;&nbsp;
[![ModelScope](https://img.shields.io/badge/ModelScope-Tencent%20Hy-624aff)](https://modelscope.cn/models/Tencent-Hunyuan/Hy3)
&nbsp;&nbsp;
[![cnb.cool](https://img.shields.io/badge/cnb.cool-Tencent%20Hy-blue?logoColor=white)](https://cnb.cool/ai-models/tencent/Hy3)
&nbsp;&nbsp;
[![GitCode](https://img.shields.io/badge/GitCode-Tencent%20Hy-red?logoColor=white)](https://ai.gitcode.com/tencent_hunyuan/Hy3)

</div>

<p align="center">
    🖥️&nbsp;<a href="https://aistudio.tencent.com/"><b>官方网站</b></a>&nbsp;&nbsp;|&nbsp;&nbsp;
    💬&nbsp;<a href="https://github.com/Tencent-Hunyuan/Hy3"><b>GitHub</b></a></p>

---

## 目录

- [模型介绍](#模型介绍)
- [更强大的智能体能力](#更强大的智能体能力)
- [更可靠的产品体验](#更可靠的产品体验)
- [Benchmark 附录](#benchmark-附录)
- [新闻](#新闻)
- [模型链接](#模型链接)
- [快速开始](#快速开始)
- [推理和部署](#推理和部署)
  - [vLLM](#使用-vllm-推理)
  - [SGLang](#使用-sglang-推理)
- [模型微调](#模型微调)
- [强化学习训练](#强化学习训练)
- [量化工具](#量化工具)
- [许可证](#许可证)
- [联系我们](#联系我们)

---

## 模型介绍

**Hy3** 是由腾讯混元团队研发的快慢思考融合的混合专家模型，总参数量 295B，激活参数 21B，MTP 层参数 3.8B。4 月底发布 Hy3 Preview 后，我们在 50 多个业务中获得了广泛的反馈，修复了各种体验问题，进一步提升了后训练的质量和规模。今天，我们正式发布 Hy3。它展现出显著强于同尺寸模型的智能水平，并比肩更大尺寸旗舰模型的效果，大幅提升了在各类产品和生产力任务中的实用价值。


| 属性 | 值 |
|:---|:---|
| 架构 | 混合专家（MoE） |
| 总参数量 | 295B |
| 激活参数量 | 21B |
| MTP层参数量 | 3.8B |
| 层数（不含MTP层） | 80 |
| MTP层数 | 1 |
| 注意力头 | 64（GQA，8 个 KV 头，head dim 128） |
| 隐藏层维度 | 4096 |
| FFN 中间层维度 | 13312 |
| 上下文长度 | 256K |
| 词表大小 | 120832 |
| 专家数量 | 192 个专家，top-8 激活 |
| 支持精度 | BF16 |

## 更强大的智能体能力

Hy3 基于 Preview 进一步提升了后训练数据的质量和多样性，扩大了 RL 算力规模，在推理、智能体、长上下文等任务上显著进步，取得了比肩国内外更大尺寸旗舰模型（参数规模往往是 Hy3 的 2～5 倍）的效果。

<p align="center">
  <img src="assets/benchmark.png" width="100%"/>
</p>

Hy3 在软件开发、办公生产、金融建模、前端设计、游戏制作等生产力任务上的进步尤其显著，可以成为高性价比的可靠选择。在内部组织的 270 位专家基于真实工作的模型盲测中，Hy3（均分 2.67 / 4）展现出优于 GLM5.1（均分 2.51 / 4）的表现，尤其在前端、数据与存储、CI/CD 等类别优势显著。

## 更可靠的产品体验

模型的实用体验不完全与榜单成绩挂钩。基于广泛的用户反馈和分析，我们定位并优化了一系列体验向能力，获得了产品侧一致且积极的评价。

**输出格式和工具调用稳定性**：我们显著改善了一系列基础底线问题，确保模型在各种工具设置和输出要求下达到生产级标准，工具调用的错误恢复能力和效率大幅提升。另外，Hy3 还增强了跨脚手架泛化性，不同脚手架（如 CodeBuddy、Cline、KiloCode）在 SWE Bench Verified 上的分数标准差控制在 4 个百分点以内。

**知识常识和抗幻觉能力**：基于“有依据才回答、无依据明示缺失，多来源信息不乱拼，数据和状态不乱编”的理想态，我们进行了细粒度的数据清洗和训练约束。在基于真实产品的内部评测中，Hy3 的幻觉率从 12.5% 降至 5.4%，常识错误率从 25.4% 降至 12.7%，显著改善了“张冠李戴”、无中生有、逻辑矛盾等问题。

**复杂上下文承接与多轮意图保持能力**：Hy3 在 SFT 与 RL 阶段联合优化了指代消解、省略还原及多轮约束继承等业务痛点问题，内部评测的多轮问题率从 17.4% 降至 7.9%。同时 Hy3 在长对话理解基准中取得显著跨越（如 MRCR 从 42.9% 升至 75.1%），输出更精炼的同时确保复杂意图在长程交互中不衰减、不跑偏。

## Benchmark 附录

<p align="center">
  <img src="assets/benchmark-appendix.png" width="100%"/>
</p>

## 新闻

* 🔥 我们在 [Hugging Face](https://huggingface.co/tencent/Hy3)、[ModelScope](https://modelscope.cn/models/Tencent-Hunyuan/Hy3)、[GitCode](https://ai.gitcode.com/tencent_hunyuan/Hy3) 和 [CNB](https://cnb.cool/ai-models/tencent/Hy3) 开源了 **Hy3** 和 **Hy3-FP8** 模型权重。

## 模型链接


| 模型名 | 简介 | Hugging Face | ModelScope | GitCode | CNB |
|:---|:---|:---:|:---:|:---:|:---:|
| Hy3 | Instruct 模型 | 🤗 [Model](https://huggingface.co/tencent/Hy3) | [Model](https://modelscope.cn/models/Tencent-Hunyuan/Hy3) | [Model](https://ai.gitcode.com/tencent_hunyuan/Hy3) | [Model](https://cnb.cool/ai-models/tencent/Hy3) |
| Hy3-FP8 | FP8 量化 Instruct 模型 | 🤗 [Model](https://huggingface.co/tencent/Hy3-FP8) | [Model](https://modelscope.cn/models/Tencent-Hunyuan/Hy3-FP8) | [Model](https://ai.gitcode.com/tencent_hunyuan/Hy3-FP8) | [Model](https://cnb.cool/ai-models/tencent/Hy3-FP8) |

## 快速开始

建议先通过 [vLLM](#使用-vllm-推理) 或 [SGLang](#使用-sglang-推理) 部署服务，然后通过 OpenAI 兼容 API 调用：

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    # reasoning_effort: "no_think"（默认，直接回复）、"low"、"high"（深度思维链）
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print(response.choices[0].message.content)
```

> **推荐参数**：`temperature=0.9`，`top_p=1.0`。
>
> **推理模式**：复杂任务（数学、编程、推理）建议设置 `reasoning_effort="high"`，日常对话可使用默认的 `"no_think"` 直接回复。

具体部署方式请参考下方[推理和部署](#推理和部署)章节。

## 推理和部署

Hy3 总参数量为 295B，当使用 8 张 GPU 时，建议使用 H20-3e 或其他有更大显存的卡型。

对于生产环境部署，我们建议使用 vLLM 或 SGLang，这两个框架都为 Hy3 提供了专门的配置方案：

- [vLLM](https://github.com/vllm-project/vllm) - 请查阅 [vLLM recipes](https://recipes.vllm.ai/tencent/Hy3)

- [SGLang](https://docs.sglang.io/) - 请查阅 [SGLang cookbook](https://lmsysorg.mintlify.app/cookbook/autoregressive/Tencent/Hy3)

### vLLM

从源码构建 vLLM：

```bash
uv venv --python 3.12 --seed --managed-python
source .venv/bin/activate
git clone https://github.com/vllm-project/vllm.git
cd vllm
uv pip install --editable . --torch-backend=auto
```

启动 vLLM 服务，开启 MTP：

```bash
# Switch to trtllm backend to work-around mnnvl workspace size issue.
export VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm

vllm serve tencent/Hy3 \
  --tensor-parallel-size 8 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 2 \
  --tool-call-parser hy_v3 \
  --reasoning-parser hy_v3 \
  --enable-auto-tool-choice \
  --port 8000 \
  --served-model-name hy3
```

### SGLang

从源码构建 SGLang：

```bash
git clone https://github.com/sgl-project/sglang
cd sglang
pip3 install pip --upgrade
pip3 install "transformers>=5.6.0"
pip3 install -e "python"
```

启动 SGLang 服务，开启 MTP：

```bash
python3 -m sglang.launch_server \
  --model tencent/Hy3 \
  --tp-size 8 \
  --tool-call-parser hunyuan \
  --reasoning-parser hunyuan \
  --speculative-num-steps 2 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 3 \
  --speculative-algorithm EAGLE \
  --port 8000 \
  --served-model-name hy3
```

## 模型微调

Hy3 提供了完整的模型微调流程，详细的微调文档请参考：[模型微调指南](./finetune/README_CN.md)

## 强化学习训练

Hy3 支持基于 [verl](https://github.com/volcengine/verl) 的 GRPO 强化学习训练，训练侧使用 Megatron-LM（通过 NVIDIA Megatron-Bridge 完成模型转换），rollout 侧使用 vLLM。详细文档请参考：[强化学习训练指南](./rl/README_CN.md)

## 量化工具

我们提供了 [AngelSlim](https://github.com/tencent/AngelSlim)——一套易用、全面、高效的大模型压缩工具包，涵盖常用量化算法、低比特量化和投机采样等能力。

## 许可证


Hy3 基于 **Apache 2.0 许可证** 发布。详情请参阅 [LICENSE](./LICENSE)。

## 联系我们

如有问题或建议，欢迎通过邮件联系我们：

📧 **hunyuan_opensource@tencent.com**

---

<p align="center">
  <i>Hy3 由腾讯混元团队研发。</i>
</p>
