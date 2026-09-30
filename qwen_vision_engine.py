import io
import os
import gc
import base64
from typing import List, Optional
import torch
from PIL import Image

def _llm_directories():
    import folder_paths
    dirs = [os.path.join(folder_paths.models_dir, "LLM")]
    registered = folder_paths.folder_names_and_paths.get("LLM")
    if registered:
        dirs.extend(registered[0])
    seen = set()
    result = []
    for path in dirs:
        path = os.path.abspath(path)
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def _scan_gguf_files(include_mmproj):
    files = []
    for llm_dir in _llm_directories():
        if not os.path.isdir(llm_dir):
            continue
        for name in os.listdir(llm_dir):
            if not name.endswith(".gguf") or name.startswith("."):
                continue
            is_mmproj = "mmproj" in name.lower()
            if is_mmproj == include_mmproj:
                files.append(name)
    return sorted(set(files))


def get_llm_model_list() -> List[str]:
    models = _scan_gguf_files(include_mmproj=False)
    return models if models else ["none"]


def get_mmproj_list() -> List[str]:
    mmprojs = _scan_gguf_files(include_mmproj=True)
    return ["none"] + mmprojs

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

SYSTEM_PROMPT_OFFICIAL_SKILL_REF2VA_ZH = """你是由 MiniMax 官方 Hailuo 3 (H3) 影视视频大模型认证的资深提示词导演与影视多模态工程专家。
你的任务是深入解析用户的创意概念以及输入的参考图片（标记为 <Picture 1>、<Picture 2> 等），编写严格符合 MiniMax 官方六段式影视标准的 Ref2VA 提示词。

请使用【中文】严格按照以下顺序输出完整的 6 个分段（分段标题保持英文小写并带冒号）：

subject_definitions:
<Subject 1> 是人物主体，外貌、发型、身形与服装来自 <Picture 1>：（提炼并细致描述来自 Picture 1 的视觉核心特征，如五官轮廓、发型、衣物面料材质与质感）。
（如果有 <Picture 2>，则定义 <Subject 2> 来自 <Picture 2>，或者定义场景/道具主体）。

summary:
[参考生视频] 目标视频生动呈现 <Subject 1> 在特定场景中的动态事件与行为交互。

retention_analysis:
<Subject 1>（主体身份与外貌，贯穿所有分镜）：partially_preserved / fully_preserved - （说明保留了哪些面容发型特征，服装和动作如何根据场景情境演变适应）。
<Picture 1>（视觉参考资产）：fully_preserved - 作为人物身份、造型与构图的核心锚点。

detailed_description:
目标视频采用写实电影级视觉质感，具有极其真实丰富的光影投射、布料微动态与自然环境粒子。
[Shot 1] 镜头景别与运镜（如全景推进/中景平移/特写微距），构图角度，光线投射氛围，<Subject 1> 的具体动作、眼神流转、面部微表情，以及与环境衣物的细腻物理交互。
（根据总时长展开连贯的多镜头，如 At 00:03.000 [Shot 2] 镜头切换或视线转向，人物关系的冲突或发展，连贯动态）。

overall_soundscape:
真实的空间环境声学效果，包括脚步踩踏声、衣料沙沙声、环境风声或嘈杂人声拟音细节，与画面动作严密同步。

non_diegetic_music:
观众侧背景配乐，说明乐器配置（如弦乐、钢琴或民族乐器）、节奏速率、情绪基调与高潮收束。

严格要求：
1. 必须包含全部 6 个段落，且段落标识严格为小写带冒号。
2. 必须明确绑定 <Subject 1>、<Subject 2> 与 <Picture 1>、<Picture 2>。
3. 直接输出提示词正文，禁止包含任何开场白、问候语或 markdown 代码块标记。
"""

SYSTEM_PROMPT_OFFICIAL_SKILL_REF2VA_EN = """You are the official MiniMax Hailuo 3 (H3) prompt director and multimodal skill engineer.
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

def _resolve_model_path(name):
    for llm_dir in _llm_directories():
        path = os.path.join(llm_dir, name)
        if os.path.isfile(path):
            return path
    return None


def generate_optimized_prompt(
    prompt: str,
    reference_images: List[Image.Image],
    model_name: str,
    mmproj_name: str = "none",
    language: str = "zh",
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
    model_path = _resolve_model_path(model_name)
    if model_path is None:
        raise FileNotFoundError(f"Local LLM model not found: {model_name}")

    mmproj_path = None
    if mmproj_name and mmproj_name != "none":
        mmproj_path = _resolve_model_path(mmproj_name)

    try:
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Llava15ChatHandler
    except ImportError as e:
        raise ImportError(f"llama-cpp-python is required for local prompt enhancement: {e}")

    chat_handler = None
    if mmproj_path:
        chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)

    print(f"[Easy-T8Enhancer] Loading local model: {model_name} (mmproj: {mmproj_name}, lang: {language})...")
    llm = Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_ctx=context_size,
        n_gpu_layers=-1,
        seed=seed if seed >= 0 else 0,
        verbose=False,
    )

    # Select System Prompt based on language
    if language == "en":
        system_prompt = SYSTEM_PROMPT_OFFICIAL_SKILL_REF2VA_EN
    else:
        system_prompt = SYSTEM_PROMPT_OFFICIAL_SKILL_REF2VA_ZH

    user_content = []
    # Add reference images with Picture labels
    for idx, img in enumerate(reference_images[:3]):
        data_url = pil_to_base64_data_url(img)
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    pic_list_str = ", ".join([f"<Picture {i+1}>" for i in range(len(reference_images[:3]))]) if reference_images else "None"

    lang_desc = "中文 (Chinese)" if language == "zh" else "English"
    instructions = (
        f"Task Type: {task_type}\n"
        f"Output Language: {lang_desc}\n"
        f"Reference Images Attached: {pic_list_str}\n"
        f"Target Duration: {duration_seconds} seconds\n"
        f"Shot Count: {shot_count}\n"
        f"Rewrite Mode: {rewrite_mode}\n"
        f"User Concept: {prompt.strip() or '电影级叙事人物场景'}\n\n"
        f"请立即以 {lang_desc} 生成完整的官方 MiniMax H3 影视六段式提示词："
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
