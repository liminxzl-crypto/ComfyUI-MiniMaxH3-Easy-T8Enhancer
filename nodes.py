import torch

try:
    from .bundle_parser import collect_all_reference_images, extract_media_from_bundle
    from .qwen_vision_engine import get_llm_model_list, get_mmproj_list, generate_optimized_prompt
except ImportError:
    from bundle_parser import collect_all_reference_images, extract_media_from_bundle
    from qwen_vision_engine import get_llm_model_list, get_mmproj_list, generate_optimized_prompt


class MiniMaxH3EasyLocalPromptOptimizer:
    CATEGORY = "MiniMax H3 Easy/Prompt"
    FUNCTION = "optimize_prompt"
    RETURN_TYPES = ("STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("optimized_prompt", "first_frame", "reference_images")
    OUTPUT_NODE = True
    DESCRIPTION = "Optimize prompts into official MiniMax H3 structure with local GGUF multimodal models."

    @classmethod
    def INPUT_TYPES(cls):
        models = get_llm_model_list()
        default_model = "Qwen3.8-9B-heretic-uncensored.i1-Q6_K.gguf" if "Qwen3.8-9B-heretic-uncensored.i1-Q6_K.gguf" in models else models[0]

        mmprojs = get_mmproj_list()
        default_mmproj = "Qwen-Image-2.1-PE-I2I.mmproj-bf16.gguf" if "Qwen-Image-2.1-PE-I2I.mmproj-bf16.gguf" in mmprojs else (mmprojs[1] if len(mmprojs) > 1 else mmprojs[0])

        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": True}),
                "optimized_text": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": True}),
                "language": (["zh", "en"], {"default": "zh"}),
                "local_model": (models, {"default": default_model}),
                "local_mmproj": (mmprojs, {"default": default_mmproj}),
                "task_type": (["Ref2VA", "T2VA", "I2VA", "FL2VA", "L2VA", "Auto"], {"default": "Ref2VA"}),
                "duration_seconds": ("INT", {"default": 5, "min": 1, "max": 60, "step": 1}),
                "shot_count": (["AUTO", "1", "2", "3", "4", "5"], {"default": "AUTO"}),
                "rewrite_mode": (["balanced", "strict", "creative"], {"default": "balanced"}),
                "output_style": (["official_skill", "h3_standard", "visual_only"], {"default": "official_skill"}),
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
            },
        }

    def optimize_prompt(
        self,
        prompt,
        optimized_text,
        language,
        local_model,
        local_mmproj,
        task_type,
        duration_seconds,
        shot_count,
        rewrite_mode,
        output_style,
        local_context_size,
        local_max_tokens,
        seed,
        local_unload_policy,
        media_bundle=None,
        image=None,
        first_frame=None,
        last_frame=None,
    ):
        pil_images = collect_all_reference_images(
            media_bundle=media_bundle,
            image=image,
            first_frame=first_frame,
            last_frame=last_frame,
        )

        if optimized_text.strip():
            enhanced = optimized_text
        else:
            enhanced = generate_optimized_prompt(
                prompt=prompt,
                reference_images=pil_images,
                model_name=local_model,
                mmproj_name=local_mmproj,
                language=language,
                task_type=task_type,
                duration_seconds=duration_seconds,
                shot_count=shot_count,
                rewrite_mode=rewrite_mode,
                output_style=output_style,
                context_size=local_context_size,
                max_tokens=local_max_tokens,
                seed=seed,
                unload_after_run=(local_unload_policy == "unload_after_run"),
            )

        out_first_frame = first_frame
        out_ref_images = image
        if media_bundle is not None:
            b_imgs, _, _ = extract_media_from_bundle(media_bundle)
            if b_imgs:
                if out_first_frame is None:
                    out_first_frame = b_imgs[0]
                if out_ref_images is None:
                    shapes = [img.shape[1:] for img in b_imgs if isinstance(img, torch.Tensor)]
                    out_ref_images = torch.cat(b_imgs, dim=0) if len(set(shapes)) == 1 else b_imgs[0]

        return {"ui": {"optimized_prompt": [enhanced]}, "result": (enhanced, out_first_frame, out_ref_images)}


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3EasyLocalPromptOptimizer": MiniMaxH3EasyLocalPromptOptimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3EasyLocalPromptOptimizer": "MiniMax H3 Easy Local Prompt Optimizer (Qwen GGUF)",
}
