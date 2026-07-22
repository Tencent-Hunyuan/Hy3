"""
HYV3 monkey-patches for LLaMA Factory + DeepSpeed ZeRO-3 training.

This module applies all necessary runtime patches so that HYV3 (MoE)
can be trained correctly under LLaMA Factory with DeepSpeed ZeRO-3.

Usage:
    Import this module **before** calling `llamafactory-cli train`:

        import hy_v3_patches          # applies patches on import
        # ... then start training

    Or add to the LLaMA Factory YAML via a custom entry-point wrapper.

Patches applied:
    1. ZeRO-3 key rename + expert fuse + buffer loading
       Handles both inner format (original) and outer format (pre-converted) checkpoints.
       - Key renaming: mlp.router.gate -> mlp.gate, etc.
       - Per-expert -> 3D fuse: experts.N.gate_proj -> experts.gate_up_proj
       - Buffer loading: e_score_correction_bias (ZeRO-3 only handles parameters)
    2. Tokenizer file copy (CustomSaveCallback)
       Ensures each checkpoint directory is self-contained for inference.
"""

import os
import re
import logging
import shutil
from typing import Optional

import torch

logger = logging.getLogger(__name__)

# ============================================================================
# Patch 1: Key rename + expert fuse + buffer loading for ZeRO-3
#
# The checkpoint may be in either inner format (original) or outer format
# (pre-converted by convert_ckpt_to_outer.py). This patch handles both:
#   - Key renaming: mlp.router.gate -> mlp.gate, etc.
#   - Per-expert -> 3D fuse: experts.N.gate_proj -> experts.gate_up_proj
#   - Buffer loading: e_score_correction_bias (ZeRO-3 only handles parameters)
#
# If the checkpoint is already in outer format, the rename/fuse logic is
# effectively a no-op (no matching keys to transform).
# ============================================================================

# Key renames: checkpoint inner format -> model format
_CKPT_KEY_RENAMES = [
    ("mlp.router.gate.", "mlp.gate."),
    ("mlp.expert_bias", "mlp.e_score_correction_bias"),
    ("mlp.shared_mlp.", "mlp.shared_experts."),
    # Also handle even older checkpoints that use mlp.gate.wg
    ("mlp.gate.wg.", "mlp.gate."),
]

# Regex to match per-expert keys in checkpoint
# e.g. model.layers.10.mlp.experts.5.gate_proj.weight
_EXPERT_KEY_RE = re.compile(
    r"^(.*\.mlp\.experts\.)(\d+)\.(gate_proj|up_proj|down_proj)\.weight$"
)


def _apply_buffer_loading_patch():
    """Patch the DeepSpeed ZeRO-3 state_dict loader to handle:
    1. Key renaming (inner checkpoint format -> model format)
    2. Per-expert -> 3D fused expert tensors
    3. Manual buffer loading (e_score_correction_bias etc.)

    ZeRO-3's _load_state_dict_into_zero3_model only handles named_parameters.
    Buffers like e_score_correction_bias must be loaded manually.
    """
    try:
        from transformers.integrations.deepspeed import (
            _load_state_dict_into_zero3_model as _orig_load_zero3,
        )
        import transformers.integrations.deepspeed as _ds_mod
        import transformers.modeling_utils as _mu_mod
    except ImportError:
        logger.warning(
            "Could not import transformers.integrations.deepspeed; "
            "buffer loading patch NOT applied."
        )
        return

    def _patched_load_zero3(model_to_load, state_dict, *args, **kwargs):
        # Step 1: Key rename + per-expert collection
        new_sd = {}
        expert_groups = {}  # prefix -> {expert_idx -> {proj_name -> tensor}}

        for k, v in state_dict.items():
            m = _EXPERT_KEY_RE.match(k)
            if m:
                # Per-expert key: collect for fusion
                prefix = m.group(1)
                expert_idx = int(m.group(2))
                proj_name = m.group(3)
                if prefix not in expert_groups:
                    expert_groups[prefix] = {}
                if expert_idx not in expert_groups[prefix]:
                    expert_groups[prefix][expert_idx] = {}
                expert_groups[prefix][expert_idx][proj_name] = v
            else:
                # Non-expert key: apply simple renames
                new_k = k
                for old_sub, new_sub in _CKPT_KEY_RENAMES:
                    if old_sub in new_k:
                        new_k = new_k.replace(old_sub, new_sub)
                        break
                new_sd[new_k] = v

        # Step 2: Fuse expert groups into 3D tensors
        if expert_groups:
            for prefix in sorted(expert_groups.keys()):
                experts = expert_groups[prefix]
                num_experts = max(experts.keys()) + 1
                gate_up_list = []
                down_list = []
                for i in range(num_experts):
                    if i not in experts:
                        logger.warning(
                            "HYV3 Patch 1: Missing expert %d in %s", i, prefix
                        )
                        continue
                    exp = experts[i]
                    if "gate_proj" in exp and "up_proj" in exp:
                        gate_up_list.append(
                            torch.cat([exp["gate_proj"], exp["up_proj"]], dim=0)
                        )
                    if "down_proj" in exp:
                        down_list.append(exp["down_proj"])
                if gate_up_list:
                    new_sd[f"{prefix}gate_up_proj"] = torch.stack(gate_up_list, dim=0)
                if down_list:
                    new_sd[f"{prefix}down_proj"] = torch.stack(down_list, dim=0)
            logger.info(
                "HYV3 Patch 1: Fused %d expert groups from per-expert to 3D format.",
                len(expert_groups)
            )
            del expert_groups

        # Step 3: Load parameters via original ZeRO-3 loader
        result = _orig_load_zero3(model_to_load, new_sd, *args, **kwargs)

        # Step 4: Manually load buffers (e.g. e_score_correction_bias)
        # ZeRO-3's loader only handles named_parameters, not named_buffers.
        buffers_loaded = 0
        for name, buf in model_to_load.named_buffers():
            if name in new_sd:
                src_tensor = new_sd[name]
                if isinstance(src_tensor, torch.Tensor):
                    buf.data.copy_(src_tensor.to(buf.dtype))
                    buffers_loaded += 1
                    if isinstance(result, tuple) and len(result) >= 2:
                        if isinstance(result[1], set):
                            result[1].discard(name)
        if buffers_loaded > 0:
            logger.info(
                "HYV3 Patch 1: Manually loaded %d buffers into model.",
                buffers_loaded
            )

        del new_sd
        return result

    _ds_mod._load_state_dict_into_zero3_model = _patched_load_zero3
    _mu_mod._load_state_dict_into_zero3_model = _patched_load_zero3
    logger.info(
        "HYV3 patch applied: ZeRO-3 key rename + expert fuse + buffer loading."
    )

# ============================================================================
# Patch 2: Tokenizer file copy callback
#
# Ensures each checkpoint directory is self-contained for inference by
# copying all tokenizer-related files from the original tokenizer path.
# ============================================================================

# Tokenizer files that should be copied to each checkpoint
_TOKENIZER_FILES = [
    "generation_config.json",
    "hy.tiktoken",
    "tokenizer_config.json",
    "tokenization_hy.py",
    "tokenizer.json",
    "special_tokens_map.json",
    "chat_template.jinja",
]

def _copy_tokenizer_to_checkpoint(tokenizer_dir: str, checkpoint_dir: str):
    """Copy tokenizer files from tokenizer_dir to checkpoint_dir."""
    for fname in _TOKENIZER_FILES:
        src = os.path.join(tokenizer_dir, fname)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(checkpoint_dir, fname))

# ============================================================================
# LLaMA Factory Callback: integrates patch 2 (tokenizer copy) into the
# training loop.
# ============================================================================

try:
    from transformers import TrainerCallback
    from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

    class HYV3PatchCallback(TrainerCallback):
        """
        LLaMA Factory compatible callback that applies HYV3-specific patches.

        Add to your YAML or pass to Trainer:
            callbacks: [hy_v3_patches.HYV3PatchCallback]
        """

        def __init__(self, tokenizer_dir: Optional[str] = None):
            """
            Args:
                tokenizer_dir: Path to the original tokenizer directory.
                    If None, will try to use model_name_or_path from training args.
            """
            self._tokenizer_dir = tokenizer_dir

        def on_save(self, args, state, control, **kwargs):
            # --- Patch 2: Copy tokenizer files ---
            if torch.distributed.is_initialized() and torch.distributed.get_rank() != 0:
                return control

            checkpoint_dir = os.path.join(
                args.output_dir,
                f"{PREFIX_CHECKPOINT_DIR}-{state.global_step}",
            )

            # Determine tokenizer directory
            tokenizer_dir = self._tokenizer_dir
            if tokenizer_dir is None:
                # Try common locations
                tokenizer_dir = getattr(args, "tokenizer_name_or_path", None)
                if tokenizer_dir is None:
                    tokenizer_dir = getattr(args, "model_name_or_path", None)

            if tokenizer_dir and os.path.isdir(tokenizer_dir):
                _copy_tokenizer_to_checkpoint(tokenizer_dir, checkpoint_dir)
                logger.info(
                    "HYV3: Copied tokenizer files from %s to %s",
                    tokenizer_dir, checkpoint_dir
                )

            return control

except ImportError:
    logger.warning(
        "transformers not available; HYV3PatchCallback not defined."
    )

# ============================================================================
# Patch 3: Memory-efficient shard-by-shard model loading for ZeRO-3
#
# The default transformers from_pretrained + ZeRO-3 path loads ALL shards
# into a single state_dict in CPU memory before distributing. For a ~670GB
# model with 8 processes per node, this causes CPU OOM.
#
# This patch replaces from_pretrained with a shard-by-shard loader that:
#   1. Creates the model skeleton under deepspeed.zero.Init (meta tensors)
#   2. Loads each safetensors shard one at a time (~7GB each)
#   3. Applies key renames + expert fusion per shard
#   4. Scatters into ZeRO-3 partitions immediately
#   5. Frees the shard before loading the next one
#
# This reduces per-rank CPU memory from ~670GB to ~7GB.
# ============================================================================

def _apply_shard_loading_patch():
    """Monkey-patch AutoModelForCausalLM.from_pretrained to use shard-by-shard
    loading when DeepSpeed ZeRO-3 is active."""
    import gc
    import json as _json
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

        # Try to determine the DeepSpeed config
        ds_config = None

        # Check if there's a deepspeed config in the HfTrainerDeepSpeedConfig
        try:
            from transformers.integrations.deepspeed import is_deepspeed_zero3_enabled
            if not is_deepspeed_zero3_enabled():
                logger.info(
                    "[HYV3 Patch 3] ZeRO-3 not enabled, using default loader."
                )
                return _orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)
        except (ImportError, Exception):
            # If we can't determine, try to proceed anyway
            pass

        # Get the deepspeed config from HF's global state
        try:
            from transformers.integrations.deepspeed import deepspeed_config as _get_ds_config
            ds_config = _get_ds_config()
        except (ImportError, Exception):
            ds_config = None

        if ds_config is None:
            # Fallback: try weak ref approach
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
            # Last resort: look for the config file path in environment
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

        # Determine dtype
        torch_dtype = kwargs.pop("torch_dtype", torch.bfloat16)
        if torch_dtype is None or torch_dtype == "auto":
            torch_dtype = torch.bfloat16
        trust_remote_code = kwargs.pop("trust_remote_code", True)
        attn_implementation = kwargs.pop("attn_implementation", None)
        # Pop config if already provided by caller (e.g. LLaMA Factory)
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

        # Step 2: Determine shard files
        if os.path.isfile(index_file):
            with open(index_file, "r") as f:
                index_data = _json.load(f)
            shard_files = list(dict.fromkeys(index_data["weight_map"].values()))
        else:
            shard_files = ["model.safetensors"]

        # Step 3: Load each shard and scatter into ZeRO-3 model
        total_shards = len(shard_files)
        all_loaded_keys = set()
        pending_experts = {}  # prefix -> {expert_idx -> {proj_name -> tensor}}

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

            # Separate expert keys from non-expert keys, apply renames
            renamed_sd = {}
            expert_keys_in_shard = {}

            for k, v in shard_sd.items():
                m = _EXPERT_KEY_RE.match(k)
                if m:
                    prefix = m.group(1)
                    expert_idx = int(m.group(2))
                    proj_name = m.group(3)
                    if prefix not in expert_keys_in_shard:
                        expert_keys_in_shard[prefix] = {}
                    if expert_idx not in expert_keys_in_shard[prefix]:
                        expert_keys_in_shard[prefix][expert_idx] = {}
                    expert_keys_in_shard[prefix][expert_idx][proj_name] = v
                else:
                    new_k = k
                    for old_sub, new_sub in _CKPT_KEY_RENAMES:
                        if old_sub in new_k:
                            new_k = new_k.replace(old_sub, new_sub)
                            break
                    renamed_sd[new_k] = v
            del shard_sd

            # Merge expert keys into pending_experts
            for prefix, experts in expert_keys_in_shard.items():
                if prefix not in pending_experts:
                    pending_experts[prefix] = {}
                for idx, projs in experts.items():
                    if idx not in pending_experts[prefix]:
                        pending_experts[prefix][idx] = {}
                    pending_experts[prefix][idx].update(projs)
            del expert_keys_in_shard

            # Check for completed expert groups
            completed_prefixes = []
            for prefix, experts in pending_experts.items():
                if not experts:
                    continue
                max_idx = max(experts.keys())
                num_experts_found = len(experts)
                all_complete = all(
                    len(projs) == 3 for projs in experts.values()
                )
                if all_complete and num_experts_found == (max_idx + 1):
                    completed_prefixes.append(prefix)

            # Fuse completed expert groups
            for prefix in completed_prefixes:
                experts = pending_experts.pop(prefix)
                num_experts_layer = max(experts.keys()) + 1
                gate_up_list = []
                down_list = []
                for i in range(num_experts_layer):
                    exp = experts[i]
                    gate_up = torch.cat([exp["gate_proj"], exp["up_proj"]], dim=0)
                    gate_up_list.append(gate_up)
                    down_list.append(exp["down_proj"])
                fused_gate_up = torch.stack(gate_up_list, dim=0)
                fused_down = torch.stack(down_list, dim=0)
                del gate_up_list, down_list, experts
                renamed_sd[f"{prefix}gate_up_proj"] = fused_gate_up
                renamed_sd[f"{prefix}down_proj"] = fused_down
                logger.info(
                    "[HYV3 Patch 3]   Fused %d experts for %s",
                    num_experts_layer, prefix
                )

            # Scatter this shard's weights into ZeRO-3 model
            if renamed_sd:
                _load_zero3(model, renamed_sd)
                # Also load buffers
                for name, buf in model.named_buffers():
                    if name in renamed_sd:
                        src_tensor = renamed_sd[name]
                        if isinstance(src_tensor, torch.Tensor):
                            buf.data.copy_(src_tensor.to(buf.dtype))
                all_loaded_keys.update(renamed_sd.keys())
            del renamed_sd
            gc.collect()

        # Flush remaining pending experts
        if pending_experts:
            logger.info(
                "[HYV3 Patch 3] Flushing %d remaining expert group(s)...",
                len(pending_experts)
            )
            flush_sd = {}
            for prefix, experts in pending_experts.items():
                num_experts_layer = max(experts.keys()) + 1
                gate_up_list = []
                down_list = []
                for i in range(num_experts_layer):
                    if i not in experts:
                        logger.warning(
                            "[HYV3 Patch 3] Missing expert %d in %s", i, prefix
                        )
                        continue
                    exp = experts[i]
                    gate_up = torch.cat([exp["gate_proj"], exp["up_proj"]], dim=0)
                    gate_up_list.append(gate_up)
                    down_list.append(exp["down_proj"])
                if gate_up_list:
                    fused_gate_up = torch.stack(gate_up_list, dim=0)
                    fused_down = torch.stack(down_list, dim=0)
                    flush_sd[f"{prefix}gate_up_proj"] = fused_gate_up
                    flush_sd[f"{prefix}down_proj"] = fused_down
                    logger.info(
                        "[HYV3 Patch 3]   Fused %d experts for %s",
                        len(gate_up_list), prefix
                    )
                del gate_up_list, down_list
            del pending_experts

            if flush_sd:
                _load_zero3(model, flush_sd)
                for name, buf in model.named_buffers():
                    if name in flush_sd:
                        src_tensor = flush_sd[name]
                        if isinstance(src_tensor, torch.Tensor):
                            buf.data.copy_(src_tensor.to(buf.dtype))
                all_loaded_keys.update(flush_sd.keys())
            del flush_sd
            gc.collect()

        # Report missing/unexpected keys
        model_keys = set(n for n, _ in model.named_parameters())
        model_keys.update(n for n, _ in model.named_buffers())
        missing = model_keys - all_loaded_keys
        unexpected = all_loaded_keys - model_keys
        if missing:
            real_missing = {k for k in missing if "lm_head" not in k}
            if real_missing:
                logger.warning(
                    "[HYV3 Patch 3] %d keys not found in checkpoint (first 10): %s",
                    len(real_missing), list(real_missing)[:10]
                )
        if unexpected:
            logger.warning(
                "[HYV3 Patch 3] %d unexpected keys (first 10): %s",
                len(unexpected), list(unexpected)[:10]
            )
        logger.info(
            "[HYV3 Patch 3] Shard-by-shard loading complete. "
            "Loaded %d keys from %d shards.",
            len(all_loaded_keys), total_shards
        )

        return model

    # Apply the monkey-patch
    transformers.AutoModelForCausalLM.from_pretrained = staticmethod(_shard_loading_from_pretrained)
    logger.info(
        "HYV3 patch applied: shard-by-shard model loading for ZeRO-3 "
        "(reduces CPU memory from ~670GB to ~7GB per rank)."
    )


# ============================================================================
# Auto-apply patches on import
# ============================================================================

# Patch 1: ZeRO-3 key rename + expert fuse + buffer loading
_apply_buffer_loading_patch()

# Patch 3: Memory-efficient shard-by-shard loading
_apply_shard_loading_patch()

# Patch 2 (tokenizer copy) is applied via HYV3PatchCallback during training.
# Users should add HYV3PatchCallback to their Trainer callbacks.

logger.info(
    "HYV3 patches module loaded. Remember to add HYV3PatchCallback to "
    "your Trainer callbacks for tokenizer file copy on save."
)
