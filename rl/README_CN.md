# Hy3 强化学习训练

[English](./README.md) | 简体中文

本文档介绍如何使用 [verl](https://github.com/volcengine/verl) 对 Hy3 进行强化学习训练。训练侧使用 [Megatron-LM](https://github.com/NVIDIA/Megatron-LM)，并通过 NVIDIA [Megatron-Bridge](https://github.com/NVIDIA-NeMo/Megatron-Bridge)（`HYV3Bridge`）在训练启动时将 HF checkpoint 在线转换为 Megatron 模型，无需离线转换；rollout 侧使用 [vLLM](https://github.com/vllm-project/vllm)。

训练脚本：verl 仓库 [`examples/grpo_trainer/run_hy_v3_megatron.sh`](https://github.com/verl-project/verl/blob/main/examples/grpo_trainer/run_hy_v3_megatron.sh)

## 快速开始

### 环境

推荐镜像：`verlai/verl:vllm023.dev1`

已验证的版本组合：

| 组件 | 版本 |
| --- | --- |
| verl | [220e903](https://github.com/verl-project/verl/commit/220e9039902c6db56860e2afd659803dc34ec005) |
| Megatron-Bridge | [df0852c](https://github.com/NVIDIA-NeMo/Megatron-Bridge/commit/df0852cf94c674de07f9f7ef933c484de8aca505) |
| transformers | 5.6.0 |
| nvidia-modelopt | 0.44.0rc5 |

### 准备依赖

clone verl 并切换到已验证版本，然后在仓库根目录下将依赖 clone 到 `third_party/`：

```bash
git clone https://github.com/verl-project/verl.git
cd verl
git checkout 220e903

mkdir third_party
git clone https://github.com/NVIDIA-NeMo/Megatron-Bridge.git third_party/Megatron-Bridge
git -C third_party/Megatron-Bridge checkout df0852c

git clone https://github.com/Ascend/TransferQueue.git third_party/TransferQueue
```

编写 `runtime_env.yaml`，通过 Ray runtime env 将工作目录（含 `third_party/`）分发到各 worker 节点，并加入 `PYTHONPATH`：

```yaml
# runtime_env.yaml
working_dir: ./
excludes: [
  "/.git/",
  "/third_party/Megatron-Bridge/.git/",
  "/third_party/TransferQueue/.git/",
  "**/__pycache__/",
]
env_vars:
  PYTHONPATH: third_party/Megatron-Bridge/src:third_party/TransferQueue
```

### 准备数据集

脚本默认使用 [DAPO-Math-17k](https://huggingface.co/datasets/BytedTsinghua-SIA/DAPO-Math-17k)（训练）和 [AIME-2024](https://huggingface.co/datasets/BytedTsinghua-SIA/AIME-2024)（验证），两者在 HuggingFace 上已是 verl 所需格式，下载后转存 parquet 即可：

```python
# prepare_data.py
import datasets

dapo = datasets.load_dataset("BytedTsinghua-SIA/DAPO-Math-17k", "default")["train"]
dapo.to_parquet("DAPO-Math-17k/dapo-math-17k.parquet")

aime = datasets.load_dataset("BytedTsinghua-SIA/AIME-2024", "default")["train"]
aime.to_parquet("AIME-2024/aime-2024.parquet")
```

```bash
python prepare_data.py   # 输出路径与脚本默认的 DATA_DIR 布局一致
```

数据放在 verl 仓库根目录（`DATA_DIR` 默认为 `$PWD`）下，或通过 `DATA_DIR=/path/to/data` 指定。

### 提交任务

模型直接使用 HuggingFace 格式 checkpoint，训练数据为 parquet 格式。设置 `RAY_ADDRESS` 指向集群 head 节点后，通过 `ray job submit` 提交：

```bash
export RAY_ADDRESS=http://<head_node_ip>:<port>

ray job submit --no-wait --runtime-env=runtime_env.yaml -- \
    bash examples/grpo_trainer/run_hy_v3_megatron.sh
```

> **注**：H20 上 rollout（vLLM 推理）最小需要 TP=16（脚本默认 `ROLLOUT_TP=16`），单实例权重需跨 16 卡切分才放得下。

### 关键参数

**Hy3配置**

| 参数 | 值 | 原因 |
| --- | --- | --- |
| `moe_router_enable_expert_bias` | True | Hy3 使用 per-expert bias 路由（aux-loss-free） |
| `moe_router_bias_update_rate` | 0 | 设 0 冻结 bias（只参与打分、不再更新）。 |
| `moe_router_load_balancing_type` | none | 不使用辅助负载均衡 loss |

**训练设置**

| 参数 | 作用 | 
| --- | --- | 
| `data.train_batch_size` | 每步采样的 prompt 数 | 
| `rollout.n` | 每个 prompt 生成的 response 数，即 GRPO 组大小（组内计算 advantage 基线），常用 8–16；
| `actor.ppo_mini_batch_size` | actor 每次参数更新的样本量 | 
| `actor.optim.lr` | actor 学习率，常用 1e-6 量级 |
| `data.max_response_length` | 最长生成长度，依任务而定 |

**算法行为**

| 参数 | 作用 | 怎么设 |
| --- | --- | --- |
| `algorithm.norm_adv_by_std_in_grpo` | advantage 是否除以组内 std | True 为原版 GRPO；False 为 [Dr.GRPO](https://arxiv.org/abs/2503.20783) 修正，避免过易/过难样本因方差小被放大 |
| `actor.clip_ratio_low` / `clip_ratio_high` | PPO 信任域上下界 | 上界略放宽（clip-higher，如 0.2/0.28）给低概率 token 更多上升空间，缓解熵坍缩 |
| `actor.clip_ratio_c` | [dual-clip](https://arxiv.org/abs/1912.09729) 下界常数 | 封顶负 advantage token 的惩罚，防止策略被单步拉爆 |
| `actor.kl_loss_coef` | 向参考策略的 KL 正则强度 | 0 为 KL-free（靠 clip 约束）；训练不稳时可加小值（如 1e-3） |
| `algorithm.rollout_correction.rollout_is` / `rollout_is_threshold` | rollout 与训练引擎的 log-prob 偏差校正（IcePop） | `token` + 上下阈值（如 `0.5_4.0`，权重超界的 token 置零）；两侧引擎精度偏差不可忽略时建议开启 |
| `rollout.temperature` / `top_p` | rollout 采样探索强度 | 常用 0.9–1.0；温度过低组内多样性不足，GRPO 组内基线退化 |

**显存与序列长度**

| 参数 | 联动关系 |
| --- | --- |
| `data.max_response_length` | 目标响应长度 |
| `rollout.max_model_len` | vLLM 上下文长度，需 ≥ prompt + response |
| `actor.ppo_max_token_len_per_gpu` | 训练侧每卡 token 预算；序列被 CP 切分到多卡，单条序列每卡实际占 `(prompt+response)/CP`，故需满足 预算 × CP ≥ prompt + response |
| `actor.megatron.context_parallel_size` | 序列显著变长时按比例增大（激活显存随序列长度线性增长，由 CP 分摊） |

训练侧 OOM（报错发生在 actor update / log_prob 阶段），可尝试：

1. 调小 `actor.ppo_max_token_len_per_gpu`——动态 batch 按它打包 micro batch，直接决定激活峰值；
2. `actor.ppo_micro_batch_size_per_gpu` 调为 1；
3. 调小 `ref.log_prob_max_token_len_per_gpu` / `rollout.log_prob_max_token_len_per_gpu`；
4. 增大 `actor.megatron.context_parallel_size`（激活按 CP 分摊）或 `pipeline_model_parallel_size`（每 stage 层数更少）。

offload 与 recompute：

| 配置 | 脚本默认 | 作用 |
| --- | --- | --- |
| `actor.megatron.param_offload` | True | 训练空闲期把参数下放 CPU，给 rollout 腾显存 |
| `actor.megatron.optimizer_offload` | True | 优化器状态（fp32 master 权重 + 动量，显存大头）放 CPU |
| `actor.megatron.grad_offload` | True | 梯度缓冲放 CPU |
| `override_transformer_config.recompute_granularity` | full | 全量激活重算：前向不存激活、反向重算，用约 30% 额外计算换掉大部分激活显存 |
| `override_transformer_config.recompute_method` / `recompute_num_layers` | uniform / 1 | 按每 1 层为单位均匀重算，粒度最细、峰值最低 |

两者都能显著缓解 OOM，offload 用每步 CPU↔GPU 搬运耗时换取参数/优化器/梯度不占显存，recompute 用反向多一次前向计算换取激活不占显存。

## 自定义训练

### 使用自己的数据集

verl 读取 parquet 格式数据，每行需包含 5 个字段（详见 verl 官方文档 [Prepare Data](https://verl.readthedocs.io/en/latest/preparation/prepare_data.html)）：

```python
{
    "data_source": "my_dataset",          # 数据集名称，RewardManager 据此索引对应的打分函数
    "prompt": [                           # HuggingFace chat template 格式，tokenizer 会渲染并分词
        {"role": "user", "content": "1+1=?"}
    ],
    "ability": "math",                    # 任务类别
    "reward_model": {
        "style": "rule",
        "ground_truth": "2"               # 标准答案；reward 函数的判分逻辑须与其格式对齐
    },
    "extra_info": {"split": "train", "index": 0},   # 元信息
}
```

编写预处理脚本转换为上述格式（verl 的 [`examples/data_preprocess/`](https://github.com/verl-project/verl/tree/main/examples/data_preprocess) 提供了 GSM8K、MATH 等十余个可直接套用的模板），保存为 parquet 后通过环境变量指定：

```bash
TRAIN_FILES=/path/to/my_train.parquet \
VAL_FILES=/path/to/my_val.parquet \
bash examples/grpo_trainer/run_hy_v3_megatron.sh
```

**reward 函数**：答案可规则判分的数学类任务可直接沿用默认的 DAPO reward（按 `data_source` 自动路由到内置打分函数）；其他任务需自定义 reward 函数，通过 `custom_reward_function.path` 指定（见 verl 文档 [Implement Reward Function](https://verl.readthedocs.io/en/latest/preparation/reward_function.html)）。


### 更换 RL 算法

训练脚本默认 GRPO，但算法层与模型层解耦，换算法时 Hy3 相关配置无需改动。

**切换内置算法（改一个配置项）**：verl 内置了十余种 advantage 估计器，通过 `algorithm.adv_estimator` 直接切换，可选值包括 `gae`（PPO）、`grpo`、`rloo`、`remax`、`reinforce_plus_plus`、`opo`、`gpg` 等（完整列表见 [`core_algos.py`](https://github.com/verl-project/verl/blob/main/verl/trainer/ppo/core_algos.py) 的 `AdvantageEstimator`）；policy loss 通过 `actor_rollout_ref.actor.policy_loss.loss_mode` 切换（`vanilla`、`gspo`、`cispo`、`clip_cov` 等）。各算法的原理与配置说明见 verl 文档：[PPO](https://verl.readthedocs.io/en/latest/algo/ppo.html) / [GRPO](https://verl.readthedocs.io/en/latest/algo/grpo.html) / [DAPO](https://verl.readthedocs.io/en/latest/algo/dapo.html)。


**使用 recipe 训练 Hy3**：训练流程级的完整算法（如 dynamic sampling 版 DAPO）在 verl [`recipe/`](https://github.com/verl-project/verl/tree/main/recipe) 目录下有独立实现，各自带启动脚本。将其模型指向 Hy3 时，须把以下 Hy3 必需配置带入 recipe 的启动脚本：

```bash
# Hy3 必需配置（任何 recipe 通用）
actor_rollout_ref.model.path=/path/to/Hy3
actor_rollout_ref.model.trust_remote_code=True
data.trust_remote_code=True
actor_rollout_ref.actor.megatron.use_mbridge=True
actor_rollout_ref.actor.megatron.vanilla_mbridge=False
+actor_rollout_ref.actor.megatron.override_transformer_config.moe_router_enable_expert_bias=True
+actor_rollout_ref.actor.megatron.override_transformer_config.moe_router_bias_update_rate=0
+actor_rollout_ref.actor.megatron.override_transformer_config.moe_router_load_balancing_type=none
+actor_rollout_ref.actor.megatron.override_transformer_config.moe_grouped_gemm=True
```

自定义全新算法的扩展方式见 verl 文档 [Extend to other RL algorithms](https://verl.readthedocs.io/en/latest/advance/dpo_extension.html)。

## 实验结果

我们在 128 张 H20 GPU（16 机 × 8 卡）上启动了 Hy3 的 GRPO 训练（脚本：[`run_hy_v3_megatron.sh`](https://github.com/verl-project/verl/blob/main/examples/grpo_trainer/run_hy_v3_megatron.sh)）：数学推理任务（DAPO 数据集），max response length 8192，采用 PP/CP/EP 多维并行 + 全量 offload，BF16 rollout + BF16 训练。

本次实验的具体取值：batch 128 prompts × 16 samples（2048 条轨迹/步）、`ppo_mini_batch_size=128`（每步单次更新）、lr 1e-6、clip 0.2/0.28（dual-clip c=10.0）、KL-free、DAPO overlong buffer（len 4096 / penalty 1.0）、IcePop 阈值 `0.5_4.0`、采样 temperature 0.9 / top_p 1.0。

训练动态稳定：rollout 与训练侧的 log-prob 偏差（`rollout_probs_diff`）全程基本小于 0.015，reward 与 AIME 验证集分数在整个训练过程中稳步上升。

![Hy3 RL 训练曲线](../assets/rl-training.png)

## 致谢

感谢腾讯混元（Hunyuan）团队在模型训练与工程落地上的支持，以及 [verl](https://github.com/volcengine/verl)、[Megatron-Bridge](https://github.com/NVIDIA-NeMo/Megatron-Bridge)、[Megatron-LM](https://github.com/NVIDIA/Megatron-LM)、[vLLM](https://github.com/vllm-project/vllm) 社区的帮助。
