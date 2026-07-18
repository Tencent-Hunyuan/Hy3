"""
HYV3 patches for ms-swift + DeepSpeed ZeRO-3 training.

This module applies necessary runtime patches so that HYV3 (MoE) can be
trained correctly under ms-swift with DeepSpeed ZeRO-3.

Patches applied:
    1. Template fix: Re-register hy_v3 template with dynamic [['eos_token_id']]
       for chat_sep and suffix (fixes inference stop token issue).
    2. Shard-by-shard model loading (Patch 3): Replaces the default
       from_pretrained which loads ALL shards into CPU memory at once,
       causing OOM for large models (~670GB). Instead, loads one shard
       at a time (~7GB each), leveraging transformers 5.8.1's built-in
       conversion_mapping for key rename + expert fusion.

Usage:
    swift sft --custom_register_path hy_v3_swift_patches.py ...
"""

import os
import gc
import json as _json
import logging
from typing import Optional

import torch

logger = logging.getLogger(__name__)

# ============================================================================
# Patch 1: Template fix
# ============================================================================

from swift.template.register import TemplateMeta, register_template
from swift.template.constant import LLMTemplateType
from swift.template.templates.llm import HyV3Template

register_template(
    TemplateMeta(
        LLMTemplateType.hy_v3,
        prefix=['<｜hy_begin▁of▁sentence｜>'],
        system_prefix=['<｜hy_begin▁of▁sentence｜>{{SYSTEM}}'],
        prompt=['<｜hy_User｜>{{QUERY}}<｜hy_Assistant｜>'],
        chat_sep=[['eos_token_id']],
        suffix=[['eos_token_id']],
        template_cls=HyV3Template,
        is_thinking=True,
        thinking_prefix='',
        non_thinking_prefix='',
        history_thinking_prefix='',
        agent_template='hy_v3',
    ),
    exist_ok=True,
)

logger.info(
    "HYV3 template patch applied: hy_v3 template re-registered with "
    "dynamic [['eos_token_id']] for chat_sep and suffix."
)

# ============================================================================
# Patch 3: Memory-efficient shard-by-shard model loading for ZeRO-3
#
# The default transformers 5.8.1 from_pretrained + ZeRO-3 path loads ALL
# shards into a single merged_state_dict in CPU memory before distributing.
# For a ~670GB model with 8 processes per node, this causes CPU OOM.
#
# This patch replaces from_pretrained with a shard-by-shard loader that:
#   1. Creates the model skeleton under deepspeed.zero.Init (meta tensors)
#   2. Loads each safetensors shard one at a time (~7GB each)
#   3. Passes each shard through _load_state_dict_into_zero3_model which
#      internally applies the conversion_mapping (key rename + expert fusion)
#   4. Frees the shard before loading the next one
#
# This reduces per-rank CPU memory from ~670GB to ~7GB.
#
# Note: Unlike the LLaMA-Factory version, we do NOT need to manually handle
# key renames or expert fusion here, because transformers 5.8.1's
# _load_state_dict_into_zero3_model already applies weight_mapping
# (conversion_mapping) internally.
# ============================================================================

def _apply_shard_loading_patch():
    """Monkey-patch AutoModelForCausalLM.from_pretrained to use shard-by-shard
    loading when DeepSpeed ZeRO-3 is active."""
    import transformers

    _orig_from_pretrained = transformers.AutoModelForCausalLM.from_pretrained

    def _shard_loading_from_pretrained(pretrained_model_name_or_path, *args, **kwargs):
        """Memory-efficient from_pretrained that loads shards one at a time."""
        import deepspeed

        model_path = pretrained_model_name_or_path

        # Only apply shard loading if:
        # 1. It's a local directory with safetensors
        # 2. DeepSpeed ZeRO-3 is being used
        if not (isinstance(model_path, str) and os.path.isdir(model_path)):
            return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)

        index_file = os.path.join(model_path, "model.safetensors.index.json")
        single_file = os.path.join(model_path, "model.safetensors")
        if not (os.path.isfile(index_file) or os.path.isfile(single_file)):
            return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)

        # Check if ZeRO-3 is enabled
        try:
            from transformers.integrations.deepspeed import is_deepspeed_zero3_enabled
            if not is_deepspeed_zero3_enabled():
                logger.info(
                    "[HYV3 Patch 3] ZeRO-3 not enabled, using default loader."
                )
                return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)
        except (ImportError, Exception):
            pass

        # Get the deepspeed config
        ds_config = None
        try:
            from transformers.integrations.deepspeed import deepspeed_config as _get_ds_config
            ds_config = _get_ds_config()
        except (ImportError, Exception):
            ds_config = None

        if ds_config is None:
            try:
                from transformers.integrations import deepspeed as _hf_ds
                if hasattr(_hf_ds, '_hf_deepspeed_config_weak_ref'):
                    _weak_ref = _hf_ds._hf_deepspeed_config_weak_ref
                    if _weak_ref is not None:
                        ds_obj = _weak_ref()
                        if ds_obj is not None:
                            ds_config = ds_obj.config
            except (ImportError, AttributeError, Exception):
                pass

        if ds_config is None:
            ds_config_path = os.environ.get("DEEPSPEED_CONFIG_FILE", None)
            if ds_config_path is None:
                ds_config_path = os.environ.get("DEEPSPEED_CONFIG", None)
            if ds_config_path and os.path.isfile(ds_config_path):
                with open(ds_config_path, "r") as f:
                    ds_config = _json.load(f)

        if ds_config is None:
            logger.warning(
                "[HYV3 Patch 3] Cannot determine DeepSpeed config, "
                "falling back to default from_pretrained."
            )
            return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)

        # Ensure ds_config is a dict
        if hasattr(ds_config, 'config'):
            ds_config = ds_config.config
        if not isinstance(ds_config, dict):
            logger.warning(
                "[HYV3 Patch 3] ds_config is not a dict (%s), falling back.",
                type(ds_config)
            )
            return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)

        # Check if it's actually ZeRO stage 3
        zero_stage = ds_config.get("zero_optimization", {}).get("stage", 0)
        if zero_stage != 3:
            logger.info(
                "[HYV3 Patch 3] Not ZeRO-3 (stage=%d), using default loader.",
                zero_stage
            )
            return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)

        logger.info(
            "[HYV3 Patch 3] Using shard-by-shard loading for model at: %s",
            model_path
        )

        try:
            from safetensors import safe_open
            from transformers.integrations.deepspeed import (
                _load_state_dict_into_zero3_model as _load_zero3,
            )
            from transformers.conversion_mapping import get_model_conversion_mapping
            from transformers.modeling_utils import LoadStateDictConfig
        except ImportError as e:
            logger.warning(
                "[HYV3 Patch 3] Required imports not available (%s), "
                "falling back to default from_pretrained.", e
            )
            return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)

        # Replace "auto" values that deepspeed.zero.Init cannot resolve
        ds_config_copy = _json.loads(_json.dumps(ds_config))
        _auto_defaults = {
            "train_batch_size": 32,
            "train_micro_batch_size_per_gpu": 1,
            "gradient_accumulation_steps": 1,
            "gradient_clipping": 1.0,
        }
        for k, v in _auto_defaults.items():
            if k in ds_config_copy and ds_config_copy[k] == "auto":
                ds_config_copy[k] = v

        # Determine dtype - handle both torch_dtype (old) and dtype (new, transformers >= 4.56)
        torch_dtype = kwargs.pop("torch_dtype", None)
        if torch_dtype is None:
            torch_dtype = kwargs.pop("dtype", torch.bfloat16)
        if torch_dtype is None or torch_dtype == "auto":
            torch_dtype = torch.bfloat16
        if isinstance(torch_dtype, str):
            torch_dtype = getattr(torch, torch_dtype, torch.bfloat16)

        trust_remote_code = kwargs.pop("trust_remote_code", True)
        attn_implementation = kwargs.pop("attn_implementation", None)
        config = kwargs.pop("config", None)

        # Step 1: Create model skeleton under ZeRO-3 Init (meta tensors)
        if config is None:
            config = transformers.AutoConfig.from_pretrained(
                model_path, trust_remote_code=trust_remote_code
            )

        with deepspeed.zero.Init(
            dtype=torch_dtype, config_dict_or_path=ds_config_copy
        ):
            model = transformers.AutoModelForCausalLM.from_config(
                config,
                trust_remote_code=trust_remote_code,
                torch_dtype=torch_dtype,
                attn_implementation=attn_implementation,
            )
        logger.info("[HYV3 Patch 3] Model skeleton created under ZeRO-3 Init.")

        # Step 2: Get weight conversion mapping (key rename + expert fusion)
        # transformers 5.8.1 has built-in conversion_mapping for hy_v3
        weight_conversions = get_model_conversion_mapping(model, None, None)

        # Create a minimal load_config with weight_mapping
        load_config = LoadStateDictConfig(
            pretrained_model_name_or_path=model_path,
            weight_mapping=weight_conversions,
        )

        # Step 3: Determine shard files
        if os.path.isfile(index_file):
            with open(index_file, "r") as f:
                index_data = _json.load(f)
            shard_files = list(dict.fromkeys(index_data["weight_map"].values()))
        else:
            shard_files = ["model.safetensors"]

        # Step 4: Load each shard and scatter into ZeRO-3 model
        total_shards = len(shard_files)

        for shard_idx, shard_name in enumerate(shard_files, 1):
            shard_path = os.path.join(model_path, shard_name)
            logger.info(
                "[HYV3 Patch 3] Loading shard %d/%d: %s",
                shard_idx, total_shards, shard_name
            )

            # Load shard into CPU memory
            shard_sd = {}
            with safe_open(shard_path, framework="pt", device="cpu") as f:
                for key in f.keys():
                    shard_sd[key] = f.get_tensor(key)

            # Use transformers' built-in ZeRO-3 loader which handles:
            # - weight_mapping (key rename + expert fusion via conversion_mapping)
            # - buffer loading
            # - parameter scattering into ZeRO-3 partitions
            _load_zero3(model, shard_sd, load_config)

            del shard_sd
            gc.collect()

        logger.info(
            "[HYV3 Patch 3] Shard-by-shard loading complete. "
            "Loaded %d shards.", total_shards
        )

        # Patch G: Disable output_router_logits to save CPU memory during training.
        # When output_router_logits=True, all 79 MoE layers accumulate router logits
        # tensors throughout forward pass, causing significant memory growth under
        # ZeRO-3 offload. Since router_aux_loss_coef=0.0 (no aux loss), these logits
        # are not needed for training.
        if hasattr(model, 'config') and getattr(model.config, 'output_router_logits', False):
            model.config.output_router_logits = False
            logger.info(
                "[HYV3 Patch G] Disabled output_router_logits to reduce "
                "CPU memory usage during ZeRO-3 offload training."
            )

        return model

    # Apply the monkey-patch
    transformers.AutoModelForCausalLM.from_pretrained = staticmethod(_shard_loading_from_pretrained)
    logger.info(
        "HYV3 Patch 3 applied: shard-by-shard model loading for ZeRO-3 "
        "(reduces CPU memory from ~670GB to ~7GB per rank)."
    )


# ============================================================================
# Auto-apply patches on import
# ============================================================================

_apply_shard_loading_patch()

logger.info("HYV3 ms-swift patches loaded successfully.")