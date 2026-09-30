import torch

try:
    from .bundle_parser import collect_all_reference_images, extract_media_from_bundle
    from .qwen_vision_engine import (
        get_llm_model_list,
        get_mmproj_list,
        generate_optimized_prompt,
    )
except ImportError:
    from bundle_parser import collect_all_reference_images, extract_media_from_bundle
    from qwen_vision_engine import (
        get_llm_model_list,
        get_mmproj_list,
        generate_optimized_prompt,
    )

class MiniMaxH3EasyLocalPromptOptimizer:
    """
    Local Multimodal GGUF Prompt Enhancer tailored for ComfyUI-MiniMaxH3-Easy suite.
    Enables T8-grade Qwen visual prompt rewriting while seamlessly ingesting Easy MediaBundles.
    """
    CATEGORY = "MiniMax H3 Easy/Prompt"
    FUNCTION = "optimize_prompt"
    RETURN_TYPES = ("STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("optimized_prompt", "first_frame", "reference_images")
    DESCRIPTION = (
        "Enhances user prompt into official MiniMax-H3 format using local GGUF Qwen vision models. "
        "Directly connects to Easy MediaLoader and automatically frees VRAM after enhancement."
    )

    @classmethod
    def INPUT_TYPES(cls):
        models = get_llm_model_list()
        default_model = "Qwen3.8-9B-heretic-uncensored.i1-Q6_K.gguf" if "Qwen3.8-9B-heretic-uncensored.i1-Q6_K.gguf" in models else models[0]

        mmprojs = get_mmproj_list()
        default_mmproj = "Qwen-Image-2.1-PE-I2I.mmproj-bf16.gguf" if "Qwen-Image-2.1-PE-I2I.mmproj-bf16.gguf" in mmprojs else (mmprojs[1] if len(mmprojs) > 1 else mmprojs[0])

        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": True}),
                "local_model": (models, {"default": default_model}),
                "local_mmproj": (mmprojs, {"default": default_mmproj}),
                "task_type": (["Ref2VA", "T2VA", "I2VA", "FL2VA", "L2VA", "Auto"], {"default": "Ref2VA"}),
                "duration_seconds": ("INT", {"default": 5, "min": 1, "max": 60, "step": 1}),
                "shot_count": (["AUTO", "1", "2", "3", "4", "5"], {"default": "AUTO"}),
                "rewrite_mode": (["balanced", "strict", "creative"], {"default": "balanced"}),
                "output_style": (["h3_standard", "visual_only", "dialogue_enhanced"], {"default": "h3_standard"}),
                "local_context_size": ("INT", {"default": 32768, "min": 2048, "max": 65536, "step": 1024}),
                "local_max_tokens": ("INT", {"default": 4096, "min": 256, "max": 8192, "step": 256}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "local_unload_policy": (["unload_after_run", "keep_loaded"], {"default": "unload_after_run"}),
            },
            "optional": {
                "media_bundle": ("MINIMAX_H3_MEDIA_BUNDLE",),
                "image": ("IMAGE",),
                "first_frame": ("IMAGE",),
                "last_frame": ("IMAGE",),
            }
        }

    def optimize_prompt(
        self,
        prompt: str,
        local_model: str,
        local_mmproj: str,
        task_type: str,
        duration_seconds: int,
        shot_count: str,
        rewrite_mode: str,
        output_style: str,
        local_context_size: int,
        local_max_tokens: int,
        seed: int,
        local_unload_policy: str,
        media_bundle=None,
        image=None,
        first_frame=None,
        last_frame=None,
    ):
        # 1. Collect all reference visual materials
        pil_images = collect_all_reference_images(
            media_bundle=media_bundle,
            image=image,
            first_frame=first_frame,
            last_frame=last_frame,
        )

        # 2. Run local LLM multimodal prompt generation
        unload = (local_unload_policy == "unload_after_run")
        enhanced = generate_optimized_prompt(
            prompt=prompt,
            reference_images=pil_images,
            model_name=local_model,
            mmproj_name=local_mmproj,
            task_type=task_type,
            duration_seconds=duration_seconds,
            shot_count=shot_count,
            rewrite_mode=rewrite_mode,
            output_style=output_style,
            context_size=local_context_size,
            max_tokens=local_max_tokens,
            seed=seed,
            unload_after_run=unload,
        )

        # 3. Formulate passthrough outputs safely without forcing torch.cat on mismatched image dimensions
        out_first_frame = first_frame
        if out_first_frame is None and media_bundle is not None:
            b_imgs, _, _ = extract_media_from_bundle(media_bundle)
            if b_imgs:
                out_first_frame = b_imgs[0]

        out_ref_images = image
        if out_ref_images is None and media_bundle is not None:
            b_imgs, _, _ = extract_media_from_bundle(media_bundle)
            if b_imgs:
                # If all tensors have the exact same shape [B, H, W, C], concatenate them; otherwise keep the first
                shapes = [img.shape[1:] for img in b_imgs if isinstance(img, torch.Tensor)]
                if len(shapes) > 1 and all(s == shapes[0] for s in shapes):
                    out_ref_images = torch.cat(b_imgs, dim=0)
                else:
                    out_ref_images = b_imgs[0]

        return (enhanced, out_first_frame, out_ref_images)

NODE_CLASS_MAPPINGS = {
    "MiniMaxH3EasyLocalPromptOptimizer": MiniMaxH3EasyLocalPromptOptimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasyLocalPromptOptimizer": "MiniMax H3 Easy Local Prompt Optimizer (Qwen GGUF)",
}
