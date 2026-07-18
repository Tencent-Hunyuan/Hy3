<p align="left">
    <a href="README_CN.md">中文</a> ｜ English
</p>

# Model Training

Hy3 provides processes related to model training. This section details how to process training data for model training purposes.

## Training Data Format and Processing

**Hy3 supports both "slow thinking" and "fast thinking" modes. By default, the model outputs in slow thinking mode. If you wish the model to use fast thinking, you can control it via the `reasoning_effort` parameter (options: `high`, `low`, `no_think`).**

The training data should be formatted as a list of messages. By default, the system prompt for both training and inference is empty, but you may customize it as needed.

```python
# Fast thinking pattern (no_think)
{"reasoning_effort": "no_think", "messages": [{"content": "You are a helpful assistant.\nThe current time is 2026-01-01 13:26:12 Thursday", "role": "system"}, {"content": "1+1=?", "role": "user"}, {"role": "assistant", "content": "1+1=2"}]}

# Slow thinking pattern (high)
{"reasoning_effort": "high", "messages": [{"content": "You are a helpful assistant.\nThe current time is 2026-01-01 13:26:12 Thursday", "role": "system"}, {"content": "1+1=?", "role": "user"}, {"role": "assistant", "content": "1+1=2", "reasoning_content": "The user is asking for the result of 1 + 1. In basic decimal arithmetic, 1 + 1 equals 2."}]}

from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("./models", use_fast=False, trust_remote_code=True)
ids = tokenizer.apply_chat_template(messages, is_training=True)
```

## Checkpoint Format Conversion

The original Hy3 checkpoint stores each expert's weights independently. Before training, it is recommended to convert it to the HuggingFace-compatible format (fusing multiple experts per layer into 3D tensors with unified key naming) to improve loading and training speed. You can also train directly with the original format without conversion, but the loading speed will be slower. We provide a conversion script `convert_ckpt_to_outer.py` and a validation script `check_converted.py`, located in the `train/tools` directory.

### Conversion

```sh
python convert_ckpt_to_outer.py \
    --input_dir <original_checkpoint_dir> \
    --output_dir <output_dir> \
    --workers 8
```

**Parameters:**

- `--input_dir`: Path to the original checkpoint directory (required)
- `--output_dir`: Path to the converted checkpoint output directory (required)
- `--workers`: Number of parallel worker processes, default is 8 (optional)

The conversion script performs the following steps:
1. Pre-scans `model.safetensors.index.json` to detect cross-shard expert groups
2. Converts weights shard-by-shard in parallel (key renaming + expert fusion)
3. Post-processes cross-shard expert groups (merges data from multiple shards)
4. Copies `config.json`, tokenizer, and other files
5. Rebuilds `model.safetensors.index.json`

### Validation

After conversion, it is recommended to validate the result using the validation script:

```sh
python check_converted.py <converted_checkpoint_dir> --spot-check 3
```

**Parameters:**

- First argument: Path to the converted checkpoint directory (required)
- `--spot-check`: Number of shard files to spot-check by loading tensors and verifying shape, dtype, NaN/Inf, etc. Default is 3 (optional)

The validation script checks the following:
1. Completeness of `config.json`
2. Whether all expected keys in `model.safetensors.index.json` are present (including regular layers and MTP layers)
3. Whether all referenced shard files exist and are non-empty
4. Spot-checks tensor shape, dtype, and NaN/Inf in selected shard files
5. Detects orphan empty shard files (cross-shard merge residues, safe to delete)

## Quick Start

You can quickly get started by following the instructions in the Quick Start Guide.

## Model Training

### Hardware Requirements

Based on testing, when `make_moe_param_leaf_module` and `zero3+offload` are disabled and `max_seq_length` is set to 4096:

- **LoRA Fine-tuning**: Requires at least a single machine with 8 GPUs (at least 80GB memory each).
- **Full Fine-tuning**: Requires at least 4 machines with 32 GPUs (at least 80GB memory each).

### Configure Passwordless SSH Login Between Machines (Multi-Machine Training)

> If you only use single-machine training, you can skip this section.

The following instructions use two machines as an example, with their IPs denoted as `${ip1}` and `${ip2}`. All steps should be performed inside the Docker container.

First, configure passwordless SSH for each container on every machine:

```sh
ssh-keygen			# Generate id_rsa and id_rsa.pub for passwordless login
ssh-keygen -t rsa -A    # Generate /etc/ssh/ssh_host_rsa_key and ssh_host_ecdsa_key for SSH listening
/usr/sbin/sshd -p 36005 -o ListenAddress=0.0.0.0        # Start SSH listening
echo "Port 36005" > ~/.ssh/config   # Set SSH connection port to 36005
passwd root    # Set the root password to avoid monitoring platform alerts
```

Note: `36005` is an example port. You may use any available port, but ensure it is **open** and **not occupied by other processes**.

Next, in each machine's container, execute:

```sh
cat ~/.ssh/id_rsa.pub
```

**Copy the output SSH public key and paste it into the `~/.ssh/authorized_keys` file, one key per line. This must be done on every machine.** In the end, the `~/.ssh/authorized_keys` file on each machine should be identical and contain the public keys of all machines.

Please note that for multi-node training, the code executed on each node must be identical. It is recommended to mount a shared network drive. If this is not possible, you must manually copy the dataset, scripts, and code to the same directory on each machine.

### Launch Methods

This project provides three training methods. You can choose based on your needs:

- **DeepSpeed Native Training** (based on HuggingFace Transformers Trainer): Located in the `train/deepspeed_support` directory
- **LLaMA-Factory Training**: Located in the `train/llama_factory_support` directory
- **ms-swift Training**: Located in the `train/ms_swift_support` directory

#### DeepSpeed Native Training

Reference: [HuggingFace Transformers Trainer](https://huggingface.co/docs/transformers/main/en/main_classes/trainer)

##### Single-Machine Training

In the `train/deepspeed_support` directory, execute:

```sh
pip install -r requirements.txt
bash train.sh
```

##### Multi-Machine Training

To launch training across multiple machines, please first complete the configuration in [Configure Passwordless SSH Login Between Machines](#configure-passwordless-ssh-login-between-machines-multi-machine-training), and ensure all machines are within the same cluster.

Confirm that dependencies are installed (if not, run `pip install -r requirements.txt`), then add the following configuration at the beginning of `train.sh`:

```shell
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "192.168.1.1,192.168.1.2" or single node "192.168.1.1"
IP_LIST=${IP_LIST:-"127.0.0.1"}
```

Note: If the `IP_LIST` environment variable is not set, replace `IP_LIST` with the IP list! The format is:
```
For a single IP:
IP_LIST=${ip_1}

For multiple IPs:
IP_LIST=${ip_1},${ip_2}

```

Replace `${ip_1}` and `${ip_2}` with the actual IP addresses.

Then, on the machine with `${ip1}`, execute `bash train.sh` in the `train/deepspeed_support/` directory. On first launch, you may see the following output:

```ssh
The authenticity of host '[ip]:36005 ([ip]:36005)' can't be established.
ECDSA key fingerprint is xxxxxx.
ECDSA key fingerprint is MD5:xxxxxx.
Are you sure you want to continue connecting (yes/no)?
```

Type `yes` to continue.

##### Key Parameters

The key parameters in the script are as follows:

- `--deepspeed`: Path to the DeepSpeed configuration file. Three default DeepSpeed configuration files are provided in the `train/deepspeed_support` folder: `ds_zero2_no_offload.json`, `ds_zero3_no_offload.json`, and `ds_zero3_offload.json`, with decreasing memory requirements in that order.
- `--model_name_or_path`: Path to the Hy3 HF pre-trained model weights to load, otherwise loading will fail.
- `--tokenizer_name_or_path`: Path to the tokenizer folder, otherwise loading will fail.
- `--train_data_file`: Path to the training file, which should be a jsonl file.
- `--output_dir`: Output directory where logs, tensorboard files, and model weights will be stored.
- `--per_device_train_batch_size`: Batch size per GPU.
- `--gradient_accumulation_steps`: Number of gradient accumulation steps. The global batch size is `per_device_train_batch_size * gradient_accumulation_steps * dp_size`.
- `--max_steps`: Total number of training steps.
- `--save_steps`: Number of steps between saving checkpoints.
- `--use_lora`: Whether to use LoRA training. Also accepts `--lora_rank`, `--lora_alpha`, and `--lora_dropout` parameters. By default, LoRA is applied to "q_proj", "k_proj", "v_proj", and "o_proj". To change this, modify the code. Note: **When using LoRA training, only the LoRA weights are saved, not the base model weights.** To merge LoRA weights, see the "LoRA Weight Merging" section below.
- `--make_moe_param_leaf_module`: When using ZeRO-3 with MoE training, treat the MoE module as a leaf module, i.e., its parameters are not partitioned by ZeRO-3. This option is expected to significantly increase memory usage.
- `--gradient_checkpointing`: Enable gradient checkpointing.
- `--train_attention_params_only`: Whether to train only attention parameters.
- `--learning_rate`: Maximum learning rate during training.
- `--min_lr`: Minimum learning rate during training.
- `--use_flash_attn`: Enable flash-attention for accelerated training.

**Notes:**

- To resume training from a previously saved checkpoint rather than loading pre-trained weights, specify `--resume_from_checkpoint` with the path to the checkpoint. Do not specify `--model_name_or_path`; this will load only the weights without the training state.
- When resuming from a checkpoint, there may be minor differences in loss due to the randomness of some non-deterministic algorithms. This is normal. See: [HuggingFace Transformers Trainer Randomness](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#randomness)
- When `--model_name_or_path` is specified, all model-related parameters will be ignored.
- Samples within a batch are padded to the length of the longest sample in the batch, but the maximum length of each sample is `max_seq_length`. Any excess will be truncated.
- If you see a warning about bias weights not being loaded, you can ignore it. Hunyuan-Large does not use bias.

##### What if GPU Memory is Insufficient?

Reference: [DeepSpeed Configuration](https://www.deepspeed.ai/docs/config-json/)

You can try modifying the DeepSpeed configuration by removing the `auto` attribute from the following parameters and reducing their values:

- `stage3_param_persistence_threshold`
- `stage3_prefetch_bucket_size`
- `stage3_max_reuse_distance`

##### LoRA Weight Merging

LoRA weights saved during training cannot be merged into the ZeRO-3 model at runtime, as ZeRO-3 partitions model weights across data parallel ranks. To merge LoRA weights into the base model, you can do so offline to obtain a merged weight file. Run `merge_lora_weight.sh` to merge the LoRA and base model weights. The parameters are:

- `--base_model_path`: Directory of the base model weights
- `--adapter_model_path`: Directory of the LoRA weights
- `--output_path`: Directory to save the merged weights
- `--save_dtype`: Data type for saving the merged weights; options are: fp16, bf16, fp32

#### LLaMA-Factory Training

If you are familiar with LLaMA-Factory, you may use it for fine-tuning. All scripts, code, and configuration files are archived in the `train/llama_factory_support` directory. Unless otherwise specified, all files mentioned below are located in this directory.

##### Installation

You can install LLaMA-Factory by downloading the source code from https://github.com/hiyouga/LLaMA-Factory/tree/main and following the instructions on the website.

##### Configuration Files

We provide sample LLaMA-Factory training configuration files: `hy_v3_lora_sft.yaml` and `hy_v3_full_sft.yaml`, corresponding to LoRA training and full fine-tuning respectively.

Key parameters in the configuration files are as follows:

**Model:**

- `model_name_or_path`: Path to the Hy3 HF format pre-trained model weights
- `trust_remote_code`: Whether to trust remote code; Hy3 requires this to be set to `true`

**Training Method:**

- `stage`: Training stage, currently `sft` (supervised fine-tuning)
- `finetuning_type`: Fine-tuning type, either `full` (full fine-tuning) or `lora` (LoRA fine-tuning)
- `deepspeed`: DeepSpeed configuration file path; `ds_zero3_offload.json` is recommended for full fine-tuning, `ds_zero2_offload_lora.json` for LoRA fine-tuning

**LoRA Parameters (only effective during LoRA fine-tuning):**

- `lora_rank`: LoRA rank, default `64`
- `lora_alpha`: LoRA alpha coefficient, default `128`
- `lora_dropout`: LoRA dropout ratio, default `0.05`
- `lora_target`: Target modules for LoRA, default `q_proj,k_proj,v_proj,o_proj`

**Dataset:**

- `dataset_dir`: Dataset directory path
- `dataset`: Dataset name, must be registered in `dataset_info.json` under `dataset_dir`
- `template`: Chat template; Hy3 uses `hy_v3`
- `cutoff_len`: Maximum sequence length; sequences exceeding this will be truncated. For full fine-tuning, can be set to `262144` (262K); for LoRA fine-tuning, `8192` is recommended to save memory
- `max_samples`: Maximum number of samples per dataset
- `overwrite_cache`: Whether to overwrite cached preprocessed datasets

**Output:**

- `output_dir`: Output directory where logs, TensorBoard files, and weights will be stored
- `logging_steps`: Number of steps between logging
- `save_steps`: Number of steps between saving checkpoints
- `plot_loss`: Whether to plot the training loss curve
- `overwrite_output_dir`: Whether to overwrite the existing output directory
- `save_only_model`: Whether to save only model weights (excluding optimizer states, etc.)
- `report_to`: Logging tool, options: `none`, `wandb`, `tensorboard`, `swanlab`, `mlflow`

**Training Hyperparameters:**

- `per_device_train_batch_size`: Batch size per GPU
- `gradient_accumulation_steps`: Gradient accumulation steps; `per_device_train_batch_size * gradient_accumulation_steps * dp_size` equals the global batch size
- `learning_rate`: Maximum learning rate; `1.0e-5` recommended for full fine-tuning, `2.0e-4` for LoRA fine-tuning
- `num_train_epochs`: Number of training epochs
- `lr_scheduler_type`: Learning rate scheduler type; `cosine_with_min_lr` is recommended
- `lr_scheduler_kwargs.min_lr_rate`: Ratio of minimum to maximum learning rate; e.g., `0.1` means the minimum learning rate is 10% of the maximum
- `warmup_ratio`: Proportion of total training steps used for warmup
- `bf16`: Whether to use BFloat16 mixed precision training
- `gradient_checkpointing`: Whether to enable gradient checkpointing to save memory
- `ddp_timeout`: Distributed training timeout (milliseconds)
- `flash_attn`: Attention implementation; `fa2` (FlashAttention-2) is recommended, `sdpa` is also available; using `fa2` requires the flash-attn package
- `resume_from_checkpoint`: Resume training from a specified checkpoint path; set to `null` to start from scratch

##### Launch Training

For multi-machine training, please first complete the configuration in [Configure Passwordless SSH Login Between Machines](#configure-passwordless-ssh-login-between-machines-multi-machine-training) (single-machine training can skip this step).

Modify the following configuration at the beginning of `train_lf.sh`:

```shell
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "192.168.1.1,192.168.1.2" or single node "192.168.1.1"
export IP_LIST=${IP_LIST:-"127.0.0.1"}
```

Note: If the `IP_LIST` environment variable is not set, replace `IP_LIST` with the IP list! The format is:
```
For a single IP:
IP_LIST=${ip_1}

For multiple IPs:
IP_LIST=${ip_1},${ip_2}

```

Replace `${ip_1}` and `${ip_2}` with the actual IP addresses.

Then, on each machine, run `bash train_lf.sh` in the `train/llama_factory_support/` directory.

#### ms-swift Training

If you are familiar with ms-swift, you may use it for fine-tuning. All scripts, code, and configuration files are archived in the `train/ms_swift_support` directory. Unless otherwise specified, all files mentioned below are located in this directory.

##### Installation

You can install ms-swift via pip:

```sh
pip install ms-swift==4.2.2
```

Or install from source: https://github.com/modelscope/ms-swift

##### Training Scripts and Configuration Files

| Training Method | Configuration File | Launch Script |
|----------------|-------------------|---------------|
| Full Fine-tuning | `hy_v3_full_sft.yaml` | `bash sft_train.sh` |
| LoRA Fine-tuning | `hy_v3_lora_sft.yaml` | `bash sft_train.sh` |

##### About the eos_token_id Patch

The `hy_v3_swift_patches.py` file in the directory fixes an issue with the eos token in ms-swift's default template. The default template uses the `<｜hy_eos｜>` string as `chat_sep` and `suffix`, which gets tokenized into multiple token IDs, causing `model.generate()` to fail to stop correctly during inference.

The patch re-registers the template using the `[['eos_token_id']]` syntax, allowing ms-swift to dynamically resolve `tokenizer.eos_token_id` at runtime and generate the correct single token.

The launch script automatically loads this patch via `--custom_register_path hy_v3_swift_patches.py`, requiring no additional action.

##### Key Parameters

Key parameters in the configuration files are as follows:

**Model:**

- `model`: Model path, can be a HuggingFace Hub ID or a local path
- `model_type`: Model type, set to `hy_v3`
- `template`: Chat template, set to `hy_v3`
- `torch_dtype`: Data type, `bfloat16` is recommended
- `attn_impl`: Attention implementation, `flash_attn` is recommended

**Training Method:**

- `tuner_type`: Fine-tuning type; set to `full` for full fine-tuning, `lora` for LoRA fine-tuning
- `tuner_backend`: LoRA backend, set to `peft`
- `lora_rank`: LoRA rank, default `8`
- `lora_alpha`: LoRA alpha coefficient, default `16`
- `lora_dropout`: LoRA dropout ratio, default `0.05`

**Dataset:**

- `dataset`: Dataset path, supports local jsonl files (sharegpt format)
- `max_length`: Maximum sequence length; sequences exceeding this will be truncated
- `truncation_strategy`: Truncation strategy, options: `delete` (discard overlong samples) or `truncation_left`
- `lazy_tokenize`: Whether to use lazy tokenization, `true` is recommended

**Output:**

- `output_dir`: Output directory
- `save_steps`: Number of steps between saving checkpoints
- `save_total_limit`: Maximum number of checkpoints to keep
- `logging_steps`: Number of steps between logging
- `report_to`: Logging tool, options: `none`, `wandb`, `tensorboard`, `swanlab`, `mlflow`

**Training Hyperparameters:**

- `per_device_train_batch_size`: Batch size per GPU
- `gradient_accumulation_steps`: Gradient accumulation steps
- `learning_rate`: Maximum learning rate; `1.0e-5` recommended for full fine-tuning, `3.0e-4` for LoRA fine-tuning
- `num_train_epochs`: Number of training epochs
- `lr_scheduler_type`: Learning rate scheduler type, `cosine` is recommended
- `warmup_ratio`: Proportion of total training steps used for warmup
- `bf16`: Whether to use BFloat16 mixed precision training

**DeepSpeed / Optimization:**

- `deepspeed`: DeepSpeed strategy, options: `zero0`, `zero2`, `zero2_offload`, `zero3`, `zero3_offload`; `zero3_offload` recommended for full fine-tuning, `zero2_offload` for LoRA fine-tuning
- `gradient_checkpointing`: Whether to enable gradient checkpointing
- `max_grad_norm`: Gradient clipping threshold

**Other:**

- `ddp_timeout`: Distributed training timeout (milliseconds)
- `seed`: Random seed
- `resume_from_checkpoint`: Resume training from a specified checkpoint path

##### Launch Training

For multi-machine training, please first complete the configuration in [Configure Passwordless SSH Login Between Machines](#configure-passwordless-ssh-login-between-machines-multi-machine-training) (single-machine training can skip this step).

Modify the following configuration in the `sft_train.sh` script:

```shell
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "10.0.0.1,10.0.0.2" or single node "127.0.0.1"
export IP_LIST=${IP_LIST:-"127.0.0.1"}
```

Then, on each machine, execute the launch script in the `train/ms_swift_support/` directory:

```sh
# Single-machine training
bash sft_train.sh

# Multi-machine training (execute on each machine)
IP_LIST="10.0.0.1,10.0.0.2" bash sft_train.sh
```