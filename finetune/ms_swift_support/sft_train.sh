#!/bin/bash
# ============================================================================
# ms-swift SFT training launch script for HYV3
#
# ms-swift 4.2.2 has native HYV3 support:
#   - Model registered: LLMModelType.hy_v3
#   - Template registered: TemplateType.hy_v3
#   - Agent template: HyV3AgentTemplate
#   - No monkey-patches needed for basic full-parameter or LoRA SFT.
#
# Usage:
#   Single node:  bash sft_train.sh
#   Multi-node:   Run this script on EACH node with the same IP_LIST.
#                 IP_LIST="10.0.0.1,10.0.0.2" bash sft_train.sh
#
# Note: ms-swift does NOT support --config parameter.
#       All parameters must be passed directly via command line.
# ============================================================================

set -euo pipefail

# -------------------- Network Configuration --------------------
NET_TYPE="high"
export NCCL_DEBUG=WARN
export NCCL_P2P_LEVEL=NVL
export NCCL_IB_TIMEOUT=24
export NCCL_NVLS_ENABLE=0
export NCCL_MPI_PROFILE_PRIMS_ENABLE=0
export CUDA_DEVICE_MAX_CONNECTIONS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=3600
if [[ "${NET_TYPE}" = "low" ]]; then
    export NCCL_SOCKET_IFNAME=eth1
    export NCCL_IB_GID_INDEX=3
    export NCCL_IB_HCA=mlx5_2:1
    export NCCL_IB_SL=3
    export NCCL_CHECK_DISABLE=1
    export NCCL_P2P_DISABLE=0
    export NCCL_LL_THRESHOLD=16384
    export NCCL_IB_CUDA_SUPPORT=1
else
    export NCCL_IB_GID_INDEX=3
    export NCCL_IB_SL=3
    export NCCL_CHECK_DISABLE=1
    export NCCL_P2P_DISABLE=0
    export NCCL_IB_DISABLE=0
    export NCCL_LL_THRESHOLD=16384
    export NCCL_IB_CUDA_SUPPORT=1
    export NCCL_SOCKET_IFNAME=bond1
    export UCX_NET_DEVICES=bond1
    export NCCL_IB_HCA=mlx5_bond_1,mlx5_bond_5,mlx5_bond_3,mlx5_bond_7,mlx5_bond_4,mlx5_bond_8,mlx5_bond_2,mlx5_bond_6
    export NCCL_COLLNET_ENABLE=0
    export SHARP_COLL_ENABLE_SAT=0
    export NCCL_NET_GDR_LEVEL=2
    export NCCL_IB_QPS_PER_CONNECTION=4
    export NCCL_IB_TC=160
    export NCCL_PXN_DISABLE=1
fi

# -------------------- Node Configuration --------------------
export HOST_GPU_NUM=8
# IP list, comma separated. e.g. "10.0.0.1,10.0.0.2" or single node "127.0.0.1"
export IP_LIST=${IP_LIST:-"127.0.0.1"}

MASTER_PORT=${MASTER_PORT:-29500}

IFS=',' read -ra IP_ARRAY <<< "$IP_LIST"
NODES=${#IP_ARRAY[@]}
MASTER_ADDR=${IP_ARRAY[0]}

# -------------------- Distributed Environment --------------------
export MASTER_ADDR="${MASTER_ADDR}"
export MASTER_PORT="${MASTER_PORT}"
export NNODES="${NODES}"

if [ ${NODES} -gt 1 ]; then
    # Determine local node rank by matching local IP against IP_LIST
    LOCAL_IP=$(hostname -i | awk '{print $1}')
    NODE_RANK=0
    for i in "${!IP_ARRAY[@]}"; do
        if [[ "${IP_ARRAY[$i]}" == "${LOCAL_IP}" ]]; then
            NODE_RANK=$i
            break
        fi
    done
    export RANK="${NODE_RANK}"
else
    export RANK=0
fi

echo "============================================"
echo "  HYV3 ms-swift SFT Training"
echo "  Nodes: ${NNODES}, Rank: ${RANK}"
echo "  Master: ${MASTER_ADDR}:${MASTER_PORT}"
echo "  GPUs per node: ${HOST_GPU_NUM}"
echo "  Total GPUs: $((NODES * HOST_GPU_NUM))"
echo "============================================"

# -------------------- Launch --------------------
# ms-swift does NOT support --config parameter.
# All parameters must be passed directly via command line.
# For multi-node, we need to set the distributed env vars and let swift handle it.

# Common SFT parameters from hy_v3_full_sft.yaml
SFT_PARAMS=(
    # ---- Model Settings ----
    --model /path/to/Hy3
    --model_type hy_v3
    --template hy_v3
    --torch_dtype bfloat16
    --tuner_type full
    --attn_impl flash_attn

    # ---- Dataset Settings ----
    --dataset ../data/example_data.jsonl
    --max_length 4096
    --truncation_strategy delete
    --lazy_tokenize true
    --dataset_num_proc 4

    # ---- Output Settings ----
    --output_dir saves/hy_v3/full/sft
    --save_steps 500
    --save_strategy steps
    --save_total_limit 3
    --save_only_model false
    --logging_steps 10
    --report_to none

    # ---- Training Hyperparameters ----
    --per_device_train_batch_size 1
    --gradient_accumulation_steps 1
    --learning_rate 1.0e-5
    --num_train_epochs 3.0
    --max_steps -1
    --warmup_ratio 0.1
    --lr_scheduler_type cosine
    --bf16 true

    # ---- DeepSpeed / Optimization ----
    --deepspeed zero3_offload
    --gradient_checkpointing true
    --max_grad_norm 1.0
    --weight_decay 0.1
    --adam_beta1 0.9
    --adam_beta2 0.95
    --optim adamw_torch

    # ---- Distributed Training ----
    --ddp_timeout 180000000

    # ---- Generation Settings ----
    --max_new_tokens 2048
    --temperature 0.7
    --top_p 0.9

    # ---- Misc ----
    --seed 42
    --ignore_data_skip true
)

if [ ${NODES} -eq 1 ]; then
    # Single-node: use torchrun to ensure local_world_size is set correctly
    # This avoids the DeepSpeed + device_map compatibility error
    export NODE_RANK=0
    export NNODES=1

    # Add current directory to PYTHONPATH so hy_v3_swift_patches can be imported
    export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"

    torchrun \
        --nproc_per_node "${HOST_GPU_NUM}" \
        --master_port "${MASTER_PORT}" \
        -m swift.cli.sft \
        --custom_register_path hy_v3_swift_patches.py \
        "${SFT_PARAMS[@]}"
else
    # Multi-node: use torchrun
    # Determine local node rank
    LOCAL_IP=$(hostname -i 2>/dev/null || hostname -I | awk '{print $1}')
    NODE_RANK=0
    for i in "${!IP_ARRAY[@]}"; do
        if [[ "${IP_ARRAY[$i]}" == "${LOCAL_IP}" ]]; then
            NODE_RANK=$i
            break
        fi
    done

    export NODE_RANK="${NODE_RANK}"
    export NNODES="${NODES}"
    export MASTER_ADDR="${MASTER_ADDR}"
    export MASTER_PORT="${MASTER_PORT}"

    # Add current directory to PYTHONPATH so hy_v3_swift_patches can be imported
    export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"

    torchrun \
        --nnodes "${NNODES}" \
        --node_rank "${NODE_RANK}" \
        --nproc_per_node "${HOST_GPU_NUM}" \
        --master_addr "${MASTER_ADDR}" \
        --master_port "${MASTER_PORT}" \
        -m swift.cli.sft \
        --custom_register_path hy_v3_swift_patches.py \
        "${SFT_PARAMS[@]}"
fi