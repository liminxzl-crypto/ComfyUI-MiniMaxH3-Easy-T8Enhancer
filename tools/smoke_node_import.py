"""Smoke test: the node module still imports and exposes its inputs."""
import os
import sys
import types

NODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, NODE_DIR)

# Minimal folder_paths stub so INPUT_TYPES can scan ComfyUI/models/LLM
stub = types.ModuleType("folder_paths")
stub.models_dir = os.path.abspath(os.path.join(NODE_DIR, "..", "..", "models"))
stub.folder_names_and_paths = {}
sys.modules["folder_paths"] = stub

import nodes

cls = nodes.NODE_CLASS_MAPPINGS["MiniMaxH3EasyLocalPromptOptimizer"]
spec = cls.INPUT_TYPES()
print("required:", list(spec["required"]))
print("optional:", list(spec["optional"]))
print("models:", spec["required"]["local_model"][0])
assert "output_style" in spec["required"]
assert "media_bundle" in spec["optional"]

import bundle_parser as bp
import qwen_vision_engine as qve

print("limits:", bp.H3_MAX_IMAGES, bp.H3_MAX_VIDEOS, bp.H3_MAX_AUDIOS, bp.H3_MAX_MEDIA)
print("engine alias:", qve.MAX_REFERENCE_IMAGES)
assert (bp.H3_MAX_IMAGES, bp.H3_MAX_VIDEOS, bp.H3_MAX_AUDIOS, bp.H3_MAX_MEDIA) == (9, 3, 3, 15)


class _Item:
    def __init__(self, media_type, value):
        self.media_type = media_type
        self.value = value


class _Bundle:
    def __init__(self, items):
        self.items = items


import torch

node = cls()
over = _Bundle([_Item("image", torch.zeros(1, 32, 32, 3)) for _ in range(10)])
try:
    node.optimize_prompt(
        prompt="test", optimized_text="", language="zh",
        local_model="none", local_mmproj="none", task_type="Ref2VA",
        duration_seconds=5, shot_count="AUTO", rewrite_mode="balanced",
        output_style="h3_standard", local_context_size=32768, local_max_tokens=256,
        seed=0, local_unload_policy="unload_after_run", media_bundle=over,
    )
except ValueError as exc:
    print("expected refusal:", exc)
else:
    raise AssertionError("10 images should be refused before model loading")

print("SMOKE OK")
