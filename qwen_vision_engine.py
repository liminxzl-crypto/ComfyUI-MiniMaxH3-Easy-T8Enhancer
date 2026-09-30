import io
import os
import gc
import base64
from typing import List, Optional
import torch
from PIL import Image

def get_llm_model_list() -> List[str]:
    """Scans ComfyUI/models/LLM for GGUF models."""
    import folder_paths
    llm_dir = os.path.join(folder_paths.models_dir, "LLM")
    if not os.path.isdir(llm_dir):
        return ["none"]
    files = [f for f in os.listdir(llm_dir) if f.endswith(".gguf") and not f.startswith(".")]
    # filter out mmproj from main models list
    models = [f for f in files if "mmproj" not in f.lower()]
    return sorted(models) if models else ["none"]

def get_mmproj_list() -> List[str]:
    """Scans ComfyUI/models/LLM for mmproj files."""
    import folder_paths
    llm_dir = os.path.join(folder_paths.models_dir, "LLM")
    if not os.path.isdir(llm_dir):
        return ["none"]
    files = [f for f in os.listdir(llm_dir) if f.endswith(".gguf") and not f.startswith(".")]
    mmprojs = [f for f in files if "mmproj" in f.lower()]
    return ["none"] + sorted(mmprojs)

def pil_to_base64_data_url(image: Image.Image, max_dim: int = 768) -> str:
    """Resizes and converts PIL image to base64 JPEG data URL for llama-cpp vision."""
    w, h = image.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        new_w, new_h = int(w * scale), int(h * scale)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

SYSTEM_PROMPT_H3_STANDARD = """You are the master director and prompt engineer for the MiniMax Hailuo 3 (H3) cinematic video foundation model.
Your task is to analyze the user's creative concept and visual references, and generate a movie-grade H3 prompt.

Output format must strictly follow:
integrated_multimodal_description: [Shot 1] (Shot type, camera movement, composition, rich lighting, colors, character action and micro-expressions, atmospheric particle effects).
[Shot 2] (If multiple shots requested: continuous dynamic motion, transitions, dramatic lighting shifts).

overall_soundscape: Detailed spatial sound effects, Foley actions, and environment ambiances strictly matching the visual action.

non_diegetic_music: Thematic soundtrack instrumentals, tempo, emotion, and musical texture.

Requirements:
- Write vivid, tactile sensory details without buzzwords like 'hyperrealistic' or 'photorealistic'.
- Explicitly integrate key visual details from the provided reference images.
- Provide output directly without preamble.
"""

def generate_optimized_prompt(
    prompt: str,
    reference_images: List[Image.Image],
    model_name: str,
    mmproj_name: str = "none",
    task_type: str = "Ref2VA",
    duration_seconds: int = 5,
    shot_count: str = "AUTO",
    rewrite_mode: str = "balanced",
    output_style: str = "h3_standard",
    context_size: int = 32768,
    max_tokens: int = 4096,
    seed: int = 0,
    unload_after_run: bool = True,
) -> str:
    """Executes local multimodal LLM inference with strict VRAM cleanup."""
    import folder_paths
    llm_dir = os.path.join(folder_paths.models_dir, "LLM")
    model_path = os.path.join(llm_dir, model_name)
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Local LLM model not found: {model_path}")

    mmproj_path = None
    if mmproj_name and mmproj_name != "none":
        p = os.path.join(llm_dir, mmproj_name)
        if os.path.isfile(p):
            mmproj_path = p

    try:
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Llava15ChatHandler
    except ImportError as e:
        raise ImportError(f"llama-cpp-python is required for local prompt enhancement: {e}")

    chat_handler = None
    if mmproj_path:
        chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)

    print(f"[Easy-T8Enhancer] Loading local model: {model_name} (mmproj: {mmproj_name})...")
    llm = Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_ctx=context_size,
        n_gpu_layers=-1, # offload all layers to GPU
        seed=seed if seed >= 0 else 0,
        verbose=False,
    )

    # Build User Content with Multimodal Images
    user_content = []
    # Add reference images as data URLs (limit to 3 for VRAM / context safety)
    for idx, img in enumerate(reference_images[:3]):
        data_url = pil_to_base64_data_url(img)
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    instructions = (
        f"Task Type: {task_type}\n"
        f"Target Duration: {duration_seconds} seconds\n"
        f"Shot Count: {shot_count}\n"
        f"Rewrite Mode: {rewrite_mode}\n"
        f"Output Style: {output_style}\n"
        f"User Concept: {prompt.strip() or 'Cinematic narrative cinematic shot'}\n\n"
        "Please generate the complete enhanced H3 video prompt now:"
    )
    user_content.append({"type": "text", "text": instructions})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_H3_STANDARD},
        {"role": "user", "content": user_content},
    ]

    print("[Easy-T8Enhancer] Generating enhanced prompt with Qwen vision model...")
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
        top_p=0.9,
    )

    result_text = response["choices"][0]["message"]["content"].strip()

    # Clean think tags if model outputs <think>
    if "<think>" in result_text and "</think>" in result_text:
        parts = result_text.split("</think>")
        result_text = parts[-1].strip()

    # Automatic VRAM cleanup
    if unload_after_run:
        print("[Easy-T8Enhancer] Unloading LLM and purging VRAM cache for downstream H3 diffusion...")
        del llm
        if chat_handler is not None:
            del chat_handler
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    return result_text
