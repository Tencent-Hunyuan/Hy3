<p align="left">
   <a href="README.md">English</a> ｜ 中文
</p>

# 模型训练

Hy3 提供了模型训练相关流程，您可以在此章节对训练数据格式进行处理以供模型训练使用。

## 训练数据格式及处理

**Hy3 同时支持慢思考与快思考两种模式，模型的默认输出是慢思考模式，若想让模型进行快思考，可通过 `reasoning_effort` 参数控制（可选值：`high`、`low`、`no_think`）。**

训练数据按照以下形式处理为 messages 格式，训练和推理的默认 system prompt 为空，可以根据自己的需求进行设定。

```python
# Fast thinking pattern (no_think)
{"reasoning_effort": "no_think", "messages": [{"content": "你是一个有用的人工智能助手。\n现在的时间是2026-01-01 13:26:12 周四", "role": "system"}, {"content": "1+1=?", "role": "user"}, {"role": "assistant", "content": "1+1=2"}]}

# Slow thinking pattern (high)
{"reasoning_effort": "high", "messages": [{"content": "你是一个有用的人工智能助手。\n现在的时间是2026-01-01 13:26:12 周四", "role": "system"}, {"content": "1+1=?", "role": "user"}, {"role": "assistant", "content": "1+1=2", "reasoning_content": "用户问的是1+1等于多少。在基本的十进制算术中，1+1等于2。"}]}

from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("./models", use_fast=False, trust_remote_code=True)
ids = tokenizer.apply_chat_template(messages, is_training=True)
```

## 权重格式转换

Hy3 的原始 checkpoint 采用每个 expert 独立存储的格式，在训练前建议转换为 expert 融合后的 HuggingFace 标准格式（将同一层的多个 expert 权重融合为 3D 张量，并统一 key 命名），用于提高加载和训练的速率。不进行转换也可以直接使用原始格式进行训练，但加载速度会较慢。我们提供了转换脚本 `convert_ckpt_to_outer.py` 和校验脚本 `check_converted.py`，位于 `train/tools` 目录下。

### 转换

```sh
python convert_ckpt_to_outer.py \
    --input_dir <原始checkpoint目录> \
    --output_dir <输出目录> \
    --workers 8
```

**参数说明：**

- `--input_dir`：原始 checkpoint 目录路径（必选）
- `--output_dir`：转换后的 checkpoint 输出目录路径（必选）
- `--workers`：并行转换的进程数，默认为 8（可选）

转换脚本会执行以下步骤：
1. 预扫描 `model.safetensors.index.json`，检测跨 shard 的 expert 分组
2. 逐 shard 并行转换权重（key 重命名 + expert 融合）
3. 后处理跨 shard 的 expert 分组（合并来自多个 shard 的数据）
4. 复制 `config.json`、tokenizer 等其他文件
5. 重建 `model.safetensors.index.json`

### 校验

转换完成后，建议使用校验脚本验证转换结果的完整性：

```sh
python check_converted.py <转换后的checkpoint目录> --spot-check 3
```

**参数说明：**

- 第一个参数：转换后的 checkpoint 目录路径（必选）
- `--spot-check`：随机抽检的 shard 文件数量，会加载 tensor 并检查 shape、dtype、NaN/Inf 等，默认为 3（可选）

校验脚本会检查以下内容：
1. `config.json` 的完整性
2. `model.safetensors.index.json` 中所有预期 key 是否齐全（包括常规层和 MTP 层）
3. 所有引用的 shard 文件是否存在且非空
4. 抽检 shard 文件中 tensor 的 shape、dtype 是否正确，是否存在 NaN/Inf
5. 检测孤立的空 shard 文件（跨 shard 合并残留，可安全删除）

## 快速开始

您可以参照快速开始文档中的内容进行快速上手。

## 模型训练

### 硬件需求

经过测试，不开 make_moe_param_leaf_module 以及 zero3+offload，max_seq_length 为 4096：

- **LoRA 微调**：最少需要单机 8 卡（显存至少 80GB）。
- **全量微调**：最少需要 4 机 32 卡（显存至少 80GB）。

### 配置机器间免密 ssh 登录（多机训练）

> 如果只使用单机训练，可跳过本节。

以下操作以两个机器为例，两台机器的 ip 分别以`${ip1}`和`${ip2}`标识，以下操作均在 docker container 内执行。

首先，配置多机container免密，在每台机器上执行。

```sh
ssh-keygen			# 生成id_rsa和id_rsa.pub，用于免密登录
ssh-keygen -t rsa -A    # 生成/etc/ssh/ssh_host_rsa_key和ssh_host_ecdsa_key， 用于后面启动ssh listen
/usr/sbin/sshd -p 36005 -o ListenAddress=0.0.0.0        # 启动 SSH 监听
echo "Port 36005" > ~/.ssh/config   # ssh 连接端口修改为 36005
passwd root    # 需要配置root密码，否则监测平台会报警
```

注意：这里的`36005`是一个示例端口，可以选用任意端口，但需要保证使用的端口**开放**且**不被其他的进程占用**。

接下来，在每台机器的 container 内，执行：

```sh
cat ~/.ssh/id_rsa.pub
```

**将输出的 ssh 公钥复制并粘贴到`~/.ssh/authorized_keys`文件中，每行一个公钥，每台机器上都要做这个操作**。最终每台机器上的`~/.ssh/authorized_keys`文件内容应当是一致的，并且包含了所有机器的公钥。

需要注意，多节点训练时，每个节点上执行的代码都得一致，建议挂载一个共享的网络盘，如果无法挂载共享网盘，则需要手动将数据集、脚本、代码复制在多台机器的相同目录下。

### 启动方式

本项目提供三种训练方式，您可以根据需求选择：

- **DeepSpeed 原生训练**（基于 HuggingFace Transformers Trainer）：位于 `train/deepspeed_support` 目录下
- **LLaMA-Factory 训练**：位于 `train/llama_factory_support` 目录下
- **ms-swift 训练**：位于 `train/ms_swift_support` 目录下

#### DeepSpeed 原生训练

参考：[HuggingFace Transformers Trainer](https://huggingface.co/docs/transformers/main/en/main_classes/trainer)

##### 单机启动训练

在 `train/deepspeed_support` 目录下，执行：

```sh
pip install -r requirements.txt
bash train.sh
```

##### 多机启动训练

如果要用多台机器启动训练，请先完成 [配置机器间免密 ssh 登录](#配置机器间免密-ssh-登录多机训练) 中的配置，并保证多台机器在一个集群内。

确认依赖已经安装完成（如未安装，请执行`pip install -r requirements.txt`安装），然后在`train.sh`中的开头增加以下配置：

```shell
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "192.168.1.1,192.168.1.2" or single node "192.168.1.1"
IP_LIST=${IP_LIST:-"127.0.0.1"}
```

注意：如果`IP_LIST`环境变量未设置，则将`IP_LIST`替换为IP列表！格式为：
```
如果只有一个IP：
IP_LIST=${ip_1}

如果有多个IP：
IP_LIST=${ip_1},${ip_2}

```

请将`${ip_1}`和`${ip_2}`替换为真实的IP地址。

然后，在`${ip1}`的机器上，在`train/deepspeed_support/`目录下，执行`bash train.sh`即可，注意第一次启动时可能会看见以下的输出：

```ssh
The authenticity of host '[ip]:36005 ([ip]:36005)' can't be established.
ECDSA key fingerprint is xxxxxx.
ECDSA key fingerprint is MD5:xxxxxx.
Are you sure you want to continue connecting (yes/no)?
```

此时输入`yes`即可继续。

##### 关键参数

脚本中的关键参数如下：

- `--deepspeed`: 此参数应当指向一个 deepspeed 的配置文件，`train/deepspeed_support`文件夹下提供了三种 DeepSpeed 的默认配置文件：`ds_zero2_no_offload.json`, `ds_zero3_no_offload.json`, `ds_zero3_offload.json`，这三个配置文件所需显存依次减少
- `--model_name_or_path`: 要加载的 Hy3 的 HF 预训练模型权重，否则无法加载
- `--tokenizer_name_or_path`: tokenizer 文件夹路径, 否则无法加载
- `--train_data_file`: 训练文件路径，应该为一个 jsonl 文件
- `--output_dir`: 输出文件夹，log、tensorboard 和权重都会存储在这个路径下
- `--per_device_train_batch_size`: 每张卡上的 batch size
- `--gradient_accumulation_steps`: 梯度累计次数，`per_device_train_batch_size * gradient_accumulation_steps * dp_size`为 global_batch_size
- `--max_steps`: 训练的总步数
- `--save_steps`: 每多少个 step 存储一个 checkpoint
- `--use_lora`: 是否用 lora 训练，同时接收`--lora_rank`，`--lora_alpha`和`--lora_dropout`参数。lora 默认应用于 "q_proj", "k_proj", "v_proj", "o_proj" 四个参数，如果需要改变的话在代码中修改即可。注意：**使用 lora 训练时，只会保存 lora 的权重，而不会保存 base 模型的权重**，如果需要合并 lora 权重，看下面的"Lora 权重合并"一节
- `--make_moe_param_leaf_module`：当用 zero3 以及 MoE 训练时，将 MoE 模块视作一个 leaf module，即它的参数不进行 zero3 切分，这个选项预计会显著增加显存占用
- `--gradient_checkpointing`：开启梯度重计算
- `--train_attention_params_only`: 是否只训练 attention 参数
- `--learning_rate`: 训练时的最大学习率
- `--min_lr`: 训练时的最小学习率
- `--use_flash_attn`: 开启 flash-attention 进行训练加速

**注意：**

- 如果想从一个中途保存的 ckpt 继续训练，而不是加载一个预训练的权重，直接指定`--resume_from_checkpoint`为之前训练保存的 ckpt 路径，不要指定`--model_name_or_path`，这样只会加载权重，而不会加载训练状态
- 从 ckpt 继续训练时，loss 可能会有微小的偏差，这是由一些非确定性算法带来的随机性，是正常现象。参考：[HuggingFace Transformers Trainer Randomness](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#randomness)
- 当 `--model_name_or_path` 有效时，所有模型相关的参数都会被忽略
- 一个 batch 内的样本会通过 padding 对齐 batch 内最长的样本，而每条样本的长度最长为 max_seq_length，超出的部分会被裁剪
- 如果报出 bias 权重没有 load 的 warning，忽略即可，Hunyuan-Large 中不会用到 bias

##### 显存不足怎么办？

参考：[DeepSpeed Configuration](https://www.deepspeed.ai/docs/config-json/)

可以尝试修改 ds config，去掉这几个参数的 auto 属性，改小试试看：

- `stage3_param_persistence_threshold`
- `stage3_prefetch_bucket_size`
- `stage3_max_reuse_distance`

##### Lora 模型合并

保存下来的 lora 权重没法在训练运行时合并到 zero3 模型中，因为 zero3 开启时模型权重会切分到各 dp rank 上。因此如果想把 lora 权重合并到 base 模型上，可以通过离线的方式合并后得到权重文件。执行`merge_lora_weight.sh`即可完成 lora 权重和 base 模型权重的合并，其中的参数有：

- `--base_model_path`：base 模型的权重目录
- `--adapter_model_path`：lora 权重目录
- `--output_path`：合并后的权重保存目录
- `--save_dtype`： 以什么数据格式存储合并后的权重，可选值：fp16，bf16，fp32

#### LLaMA-Factory 训练

如果对 LLaMA-Factory 较为熟悉，可使用 LLaMA-Factory 进行微调。脚本、代码以及配置文件都归档在 `train/llama_factory_support` 目录下。如果没有特别说明，接下来我们提到的文件都是该目录下的文件。

##### 安装

可以通过下载源码 https://github.com/hiyouga/LLaMA-Factory/tree/main ，根据网站的指引进行安装。

##### 配置文件

我们提供了 llama-factory 的训练示例配置文件 `hy_v3_lora_sft.yaml`和`hy_v3_full_sft.yaml`文件，分别对应 LoRA 训练和全量微调。

脚本中的关键参数如下：

**模型相关：**

- `model_name_or_path`: Hy3 HF 格式预训练模型权重路径
- `trust_remote_code`: 是否信任远程代码, Hy3 需要设置为 `true`

**训练方法：**

- `stage`: 训练阶段, 当前为 `sft`(监督微调)
- `finetuning_type`: 微调类型, 可选 `full`(全量微调) 或 `lora`(LoRA 微调)
- `deepspeed`: DeepSpeed 配置文件路径, 全量微调推荐 `ds_zero3_offload.json`, LoRA 微调推荐 `ds_zero2_offload_lora.json`

**LoRA 参数(仅 LoRA 微调时生效)：**

- `lora_rank`: LoRA 秩, 默认 `64`
- `lora_alpha`: LoRA alpha 系数, 默认 `128`
- `lora_dropout`: LoRA dropout 比率, 默认 `0.05`
- `lora_target`: LoRA 应用的目标模块, 默认为 `q_proj,k_proj,v_proj,o_proj`

**数据集：**

- `dataset_dir`: 数据集目录路径
- `dataset`: 数据集名称, 需要在 `dataset_dir` 下的 `dataset_info.json` 中注册
- `template`: 对话模板, Hy3 使用 `hy_v3`
- `cutoff_len`: 最大序列长度, 超出部分会被截断; 全量微调可设为 `262144`(262K), LoRA 微调建议设为 `8192` 以节省显存
- `max_samples`: 每个数据集最多使用的样本数
- `overwrite_cache`: 是否覆盖已缓存的预处理数据集

**输出：**

- `output_dir`: 输出目录, 日志、TensorBoard 和权重都会存储在此路径下
- `logging_steps`: 每多少步记录一次日志
- `save_steps`: 每多少步保存一次 checkpoint
- `plot_loss`: 是否绘制训练 loss 曲线
- `overwrite_output_dir`: 是否覆盖已有的输出目录
- `save_only_model`: 是否只保存模型权重(不保存优化器状态等)
- `report_to`: 日志上报工具, 可选 `none`, `wandb`, `tensorboard`, `swanlab`, `mlflow`

**训练超参数：**

- `per_device_train_batch_size`: 每张卡上的 batch size
- `gradient_accumulation_steps`: 梯度累积步数, `per_device_train_batch_size * gradient_accumulation_steps * dp_size` 为 global batch size
- `learning_rate`: 最大学习率, 全量微调推荐 `1.0e-5`, LoRA 微调推荐 `2.0e-4`
- `num_train_epochs`: 训练轮数
- `lr_scheduler_type`: 学习率调度器类型, 推荐使用 `cosine_with_min_lr`
- `lr_scheduler_kwargs.min_lr_rate`: 最小学习率与最大学习率的比值, 例如 `0.1` 表示最小学习率为最大学习率的 10%
- `warmup_ratio`: 预热阶段占总训练步数的比例
- `bf16`: 是否使用 BFloat16 混合精度训练
- `gradient_checkpointing`: 是否开启梯度重计算以节省显存
- `ddp_timeout`: 分布式训练超时时间(毫秒)
- `flash_attn`: 注意力实现方式, 推荐 `fa2`(FlashAttention-2), 也可选 `sdpa`; 使用 `fa2` 需要安装 flash-attn 包
- `resume_from_checkpoint`: 从指定 checkpoint 路径恢复训练, 设为 `null` 表示从头开始训练

##### 启动训练

如需多机训练，请先完成 [配置机器间免密 ssh 登录](#配置机器间免密-ssh-登录多机训练) 中的配置（单机训练可跳过此步骤）。

修改`train_lf.sh`中开头的以下配置：

```shell
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "192.168.1.1,192.168.1.2" or single node "192.168.1.1"
export IP_LIST=${IP_LIST:-"127.0.0.1"}
```

注意：如果`IP_LIST`环境变量未设置，则将`IP_LIST`替换为IP列表！格式为：
```
如果只有一个IP：
IP_LIST=${ip_1}

如果有多个IP：
IP_LIST=${ip_1},${ip_2}

```

请将`${ip_1}`和`${ip_2}`替换为真实的IP地址。

然后，在每一台机器上，在`train/llama_factory_support/`目录下执行`bash train_lf.sh`。

#### ms-swift 训练

如果对 ms-swift 较为熟悉，可使用 ms-swift 进行微调。脚本、代码以及配置文件都归档在 `train/ms_swift_support` 目录下。如果没有特别说明，接下来我们提到的文件都是该目录下的文件。

##### 安装

可以通过 pip 安装 ms-swift：

```sh
pip install ms-swift==4.2.2
```

或从源码安装：https://github.com/modelscope/ms-swift

##### 训练脚本与配置文件

| 训练方式 | 配置文件 | 启动脚本 |
|---------|---------|---------|
| 全量微调 | `hy_v3_full_sft.yaml` | `bash sft_train.sh` |
| LoRA 微调 | `hy_v3_lora_sft.yaml` | `bash sft_train.sh` |

##### 关于 eos_token_id Patch

目录下的 `hy_v3_swift_patches.py` 文件用于修复 ms-swift 默认模板中 eos token 的问题。默认模板将 `<｜hy_eos｜>` 字符串作为 `chat_sep` 和 `suffix`，该字符串会被 tokenize 为多个 token ID，导致推理时 `model.generate()` 无法正确停止。

Patch 通过 `[['eos_token_id']]` 语法重新注册模板，使 ms-swift 在运行时动态解析 `tokenizer.eos_token_id`，生成正确的单个 token。

启动脚本已通过 `--custom_register_path hy_v3_swift_patches.py` 自动加载此 patch，无需额外操作。

##### 关键参数

配置文件中的关键参数如下：

**模型相关：**

- `model`: 模型路径，可以是 HuggingFace Hub ID 或本地路径
- `model_type`: 模型类型，设为 `hy_v3`
- `template`: 对话模板，设为 `hy_v3`
- `torch_dtype`: 数据类型，推荐 `bfloat16`
- `attn_impl`: 注意力实现，推荐 `flash_attn`

**训练方法：**

- `tuner_type`: 微调类型，全量微调设为 `full`，LoRA 微调设为 `lora`
- `tuner_backend`: LoRA 后端，设为 `peft`
- `lora_rank`: LoRA 秩，默认 `8`
- `lora_alpha`: LoRA alpha 系数，默认 `16`
- `lora_dropout`: LoRA dropout 比率，默认 `0.05`

**数据集：**

- `dataset`: 数据集路径，支持本地 jsonl 文件（sharegpt 格式）
- `max_length`: 最大序列长度，超出部分会被截断
- `truncation_strategy`: 截断策略，可选 `delete`（丢弃超长样本）或 `truncation_left`
- `lazy_tokenize`: 是否延迟 tokenize，推荐 `true`

**输出：**

- `output_dir`: 输出目录
- `save_steps`: 每多少步保存一次 checkpoint
- `save_total_limit`: 最多保留的 checkpoint 数量
- `logging_steps`: 每多少步记录一次日志
- `report_to`: 日志上报工具，可选 `none`, `wandb`, `tensorboard`, `swanlab`, `mlflow`

**训练超参数：**

- `per_device_train_batch_size`: 每张卡上的 batch size
- `gradient_accumulation_steps`: 梯度累积步数
- `learning_rate`: 最大学习率，全量微调推荐 `1.0e-5`，LoRA 微调推荐 `3.0e-4`
- `num_train_epochs`: 训练轮数
- `lr_scheduler_type`: 学习率调度器类型，推荐 `cosine`
- `warmup_ratio`: 预热阶段占总训练步数的比例
- `bf16`: 是否使用 BFloat16 混合精度训练

**DeepSpeed / 优化：**

- `deepspeed`: DeepSpeed 策略，可选 `zero0`, `zero2`, `zero2_offload`, `zero3`, `zero3_offload`；全量微调推荐 `zero3_offload`，LoRA 微调推荐 `zero2_offload`
- `gradient_checkpointing`: 是否开启梯度重计算
- `max_grad_norm`: 梯度裁剪阈值

**其他：**

- `ddp_timeout`: 分布式训练超时时间（毫秒）
- `seed`: 随机种子
- `resume_from_checkpoint`: 从指定 checkpoint 路径恢复训练

##### 启动训练

如需多机训练，请先完成 [配置机器间免密 ssh 登录](#配置机器间免密-ssh-登录多机训练) 中的配置（单机训练可跳过此步骤）。

修改 `sft_train.sh` 脚本中的以下配置：

```shell
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "10.0.0.1,10.0.0.2" or single node "127.0.0.1"
export IP_LIST=${IP_LIST:-"127.0.0.1"}
```

然后，在每一台机器上，在 `train/ms_swift_support/` 目录下执行启动脚本：

```sh
# 单机训练
bash sft_train.sh

# 多机训练（在每台机器上执行）
IP_LIST="10.0.0.1,10.0.0.2" bash sft_train.sh
```