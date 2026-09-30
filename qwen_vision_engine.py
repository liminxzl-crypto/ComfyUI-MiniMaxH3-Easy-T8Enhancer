import io
import os
import gc
import base64
from typing import List, Optional
import torch
from PIL import Image

def get_llm_model_list() -> List[str]:
    import folder_paths
    llm_dir = os.path.join(folder_paths.models_dir, "LLM")
    if not os.path.isdir(llm_dir):
        return ["none"]
    files = [f for f in os.listdir(llm_dir) if f.endswith(".gguf") and not f.startswith(".")]
    models = [f for f in files if "mmproj" not in f.lower()]
    return sorted(models) if models else ["none"]

def get_mmproj_list() -> List[str]:
    import folder_paths
    llm_dir = os.path.join(folder_paths.models_dir, "LLM")
    if not os.path.isdir(llm_dir):
        return ["none"]
    files = [f for f in os.listdir(llm_dir) if f.endswith(".gguf") and not f.startswith(".")]
    mmprojs = [f for f in files if "mmproj" in f.lower()]
    return ["none"] + sorted(mmprojs)

def pil_to_base64_data_url(image: Image.Image, max_dim: int = 768) -> str:
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

SYSTEM_PROMPT_OFFICIAL_SKILL_REF2VA = """You are the official MiniMax Hailuo 3 (H3) prompt director and multimodal skill engineer.
Your task is to analyze the user's creative concept and the provided reference images (<Picture 1>, <Picture 2>, etc.), and produce a strict official MiniMax H3 Ref2VA prompt.

You MUST strictly output the following 6 sections in English in this exact order:

subject_definitions:
<Subject 1> is the primary subject, whose facial features, hairstyle, clothing, and body structure originate from <Picture 1>: (describe key visual traits extracted from Picture 1).
(If more pictures provided, define <Subject 2> from <Picture 2>, etc., or describe scene environment elements).

summary:
[reference generation] The target video portrays <Subject 1> in (action and context). Describe how characters and environment interact.

retention_analysis:
<Subject 1> (identity, features, clothing, appearing in all shots): fully_preserved / partially_preserved - (details of what is kept and what adapts to the scene).
<Picture 1> (character / scene visual reference): fully_preserved - serves as identity, costume, and visual anchor.

detailed_description:
The target video adopts a realistic cinematic visual style with rich lighting, tactile textures, and atmosphere.
[Shot 1] (Shot type e.g. Wide / Medium / Close-up, camera movement, composition, lighting atmosphere, actions of <Subject 1> with micro-expressions and fabric / environmental interaction).
(If duration > 5s or multi-shot requested, provide [Shot 2] with timestamp e.g. At 00:03.000, shot transition, camera movement, continuing action).

overall_soundscape:
Realistic ambient spatial acoustics, foley footsteps, rustling of clothing/objects, and environment atmosphere matching the visual action.

non_diegetic_music:
Audience-side background musical score, instrumentation (e.g. acoustic strings, subtle piano, flute), tempo, mood, and emotional resonance.

STRICT CONSTRAINTS:
1. All 6 section headers must be present and lowercase with colons.
2. Explicitly bind <Subject 1>, <Subject 2>, etc. to <Picture 1>, <Picture 2>.
3. Output purely the structured prompt text without conversational preamble or markdown code fences.
"""

SYSTEM_PROMPT_OFFICIAL_SKILL_BASE = """You are the official MiniMax Hailuo 3 (H3) prompt director and multimodal skill engineer.
Your task is to analyze the user's creative concept and produce an official MiniMax H3 base prompt.

You MUST strictly output the following 3 sections in this exact order:

integrated_multimodal_description:
[Shot 1] (Shot type, camera movement, composition, rich lighting, colors, character action and micro-expressions, atmospheric particle effects).
[Shot 2] (If multi-shot requested: continuous dynamic motion, transitions, dramatic lighting shifts).

overall_soundscape:
Detailed spatial sound effects, Foley actions, and environment ambiances strictly matching the visual action.

non_diegetic_music:
Thematic soundtrack instrumentals, tempo, emotion, and musical texture.

Requirements:
- Write vivid, tactile sensory details without buzzwords like 'hyperrealistic' or 'photorealistic'.
- Output directly without conversational preamble or code blocks.
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
    output_style: str = "official_skill",
    context_size: int = 32768,
    max_tokens: int = 4096,
    seed: int = 0,
    unload_after_run: bool = True,
) -> str:
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
        n_gpu_layers=-1,
        seed=seed if seed >= 0 else 0,
        verbose=False,
    )

    # Select System Prompt based on Task and Output Style
    if task_type in ["Ref2VA", "Auto"] and (reference_images or output_style == "official_skill"):
        system_prompt = SYSTEM_PROMPT_OFFICIAL_SKILL_REF2VA
    else:
        system_prompt = SYSTEM_PROMPT_OFFICIAL_SKILL_BASE

    user_content = []
    # Add reference images with Picture labels
    for idx, img in enumerate(reference_images[:3]):
        data_url = pil_to_base64_data_url(img)
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    pic_list_str = ", ".join([f"<Picture {i+1}>" for i in range(len(reference_images[:3]))]) if reference_images else "None"

    instructions = (
        f"Task Type: {task_type}\n"
        f"Reference Images Attached: {pic_list_str}\n"
        f"Target Duration: {duration_seconds} seconds\n"
        f"Shot Count: {shot_count}\n"
        f"Rewrite Mode: {rewrite_mode}\n"
        f"User Concept: {prompt.strip() or 'Cinematic narrative character scene'}\n\n"
        "Generate the official MiniMax H3 prompt with full reference mapping (<Subject N> / <Picture N>) now:"
    )
    user_content.append({"type": "text", "text": instructions})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    print("[Easy-T8Enhancer] Generating official skill prompt with Qwen vision model...")
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
        top_p=0.9,
    )

    result_text = response["choices"][0]["message"]["content"].strip()

    if "<think>" in result_text and "</think>" in result_text:
        parts = result_text.split("</think>")
        result_text = parts[-1].strip()

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
