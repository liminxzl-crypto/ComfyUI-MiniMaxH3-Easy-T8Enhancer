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


def _build_system_prompt_zh(num_pictures: int) -> str:
    """构建中文系统提示词：以初始文本的语义环境和叙事基调为最高准则进行最标准的六段式影视级扩写。
    先不做任何主观风格/剧情限定，完全顺应并深化初始文本的意图；除非初始文本有明确要求，才进行对应定制。
    """
    subject_defs = []
    retention_items = []
    for i in range(1, num_pictures + 1):
        subject_defs.append(
            f"<Subject {i}> 的外貌、发型、身形与服装来自 <Picture {i}>（@图片{i}）："
            f"（提炼并细致描述来自 <Picture {i}> 的核心视觉特征，如五官轮廓、发型发色、衣着服饰面料与质感）。"
        )
        retention_items.append(
            f"<Subject {i}>（主体身份与外貌，贯穿所有分镜）：fully_preserved - "
            f"外貌、服装来自 <Picture {i}>，完整保留。\n"
            f"<Picture {i}>（视觉参考资产）：fully_preserved - 作为身份锚点。"
        )

    subject_block = "\n".join(subject_defs) if subject_defs else (
        "<Subject 1> 是场景核心主体：（严格依据用户初始文本描述提炼并细化其外貌与服饰特征）。"
    )
    retention_block = "\n".join(retention_items) if retention_items else (
        "<Subject 1>（主体身份与外貌）：fully_preserved。"
    )

    binding_rule = ""
    if num_pictures > 0:
        tags = ", ".join(f"<Subject {i}>↔<Picture {i}>" for i in range(1, num_pictures + 1))
        binding_rule = (
            f"\n【素材资产绑定规则】：素材箱已连接 {num_pictures} 张参考图。"
            f"你必须在 subject_definitions 中严格建立绑定：{tags}。"
            f"在 detailed_description 中，凡是该主体出场必须使用 <Subject N> 标签精准引用。"
        )

    return f"""你是由 MiniMax 官方 Hailuo 3 (H3) 认证的顶级影视提示词导演与剧本专家。
你的任务是：深度理解用户初始文本的【语义环境、情绪基调、叙事逻辑与场景氛围】，并结合提供的参考图片，进行最专业、最标准、最契合原意的 MiniMax H3 影视六段式提示词扩写。

【核心原则 - 语义忠实与无偏见扩展】：
1. **顺应原意，不做强加限定**：先不做预设的画风或桥段限定，一切扩写必须完全建立在用户初始文本所营造的语义环境与世界观之下。除非初始文本明确提出了特定风格、对白、镜头或道具要求，否则不随意添加违背原意的冲突元素。
2. **如果初始文本包含对话/台词**：必须使用 `<d>台词内容</d>` 标签精准包裹，并细致刻画说话时的微表情、口型开合与情感起伏。如果初始文本没有对话需求，则专注于肢体语言、眼神交流与环境叙事。
3. **分镜与时序连贯**：根据目标时长自然分段（如 [Shot 1]、[Shot 2]...），镜头机位、运镜方式、光影投射、物理交互与动作节奏必须具备电影工业级的画面表现力与连续性。
{binding_rule}

请使用【中文】严格按照以下标准六段式输出（分段标题保持英文小写带英文冒号）：

subject_definitions:
{subject_block}

summary:
[视频整体概述] 依据初始文本核心事件，概括提炼视频的整体叙事、主体行为与核心情境。

retention_analysis:
{retention_block}

detailed_description:
根据初始文本的语义环境展开写实电影级视觉描述，包含自然的光影投射、材质物理动态与环境细节。
[Shot 1] 镜头景别与运镜轨迹，构图角度，光线与环境氛围，<Subject 1> 的具体行为动作、眼神流转、面部微表情，以及与环境或其他主体的真实物理互动。
（按时序展开多镜头，如 At 00:03.000 [Shot 2]，每个分镜均需保持连贯的叙事与视觉一致性）。

overall_soundscape:
与画面动作及场景环境高度吻合的空间声学效果（包括环境底噪、拟音细节、动作音效、脚步声等）。

non_diegetic_music:
与初始文本情绪基调完美匹配的背景配乐说明（配乐风格、乐器编排、节奏起伏与情感烘托）。

【严格执行要求】：
1. 必须包含全部 6 个段落，段落标题必须为小写字母且带冒号。
2. 初始文本中的人物台词必须使用 `<d>对话内容</d>` 进行标记。
3. 有参考图片时，必须在 subject_definitions 中声明 `<Subject N> 来自 <Picture N>`，并在分镜中规范引用。
4. 直接输出纯文本提示词正文，严禁使用 markdown 代码块（```）、JSON 格式包裹，严禁任何客套问候或前后解释说明。
"""


def _build_system_prompt_en(num_pictures: int) -> str:
    """Build English system prompt with dynamic Subject/Picture bindings."""
    subject_defs = []
    retention_items = []
    for i in range(1, num_pictures + 1):
        subject_defs.append(
            f"<Subject {i}> originates from <Picture {i}>: "
            f"(describe key visual traits extracted from <Picture {i}>: facial features, hairstyle, clothing, body structure)."
        )
        retention_items.append(
            f"<Subject {i}> (identity and appearance, present in all shots): fully_preserved - "
            f"appearance from <Picture {i}> fully retained.\n"
            f"<Picture {i}> (visual reference asset): fully_preserved - identity anchor."
        )

    subject_block = "\n".join(subject_defs) if subject_defs else (
        "<Subject 1> is the primary subject: (generate appearance from user description)."
    )
    retention_block = "\n".join(retention_items) if retention_items else (
        "<Subject 1> (identity and appearance): fully_preserved."
    )

    binding_rule = ""
    if num_pictures > 0:
        tags = ", ".join(f"<Subject {i}>↔<Picture {i}>" for i in range(1, num_pictures + 1))
        binding_rule = (
            f"\nCRITICAL BINDING RULE: {num_pictures} reference image(s) are attached from the media loader. "
            f"You MUST establish these bindings in subject_definitions: {tags}. "
            f"In detailed_description, always use <Subject N> tags when the subject appears."
        )

    return f"""You are the official MiniMax Hailuo 3 (H3) prompt director.
Your task is to analyze the user's creative concept and reference images, producing a strict official H3 Ref2VA prompt.
{binding_rule}

You MUST strictly output the following 6 sections in English in this exact order:

subject_definitions:
{subject_block}

summary:
[reference generation] The target video portrays <Subject 1> in (action and context).

retention_analysis:
{retention_block}

detailed_description:
The target video adopts a realistic cinematic visual style with rich lighting, tactile textures, and atmosphere.
[Shot 1] (Shot type, camera movement, composition, lighting, actions of <Subject 1> with micro-expressions).
(Expand multi-shot with timestamps for longer durations, e.g. At 00:03.000 [Shot 2]).

overall_soundscape:
Realistic ambient spatial acoustics, foley, and environment atmosphere matching the visual action.

non_diegetic_music:
Background musical score with instrumentation, tempo, mood, and emotional resonance.

STRICT CONSTRAINTS:
1. All 6 section headers must be present and lowercase with colons.
2. Explicitly bind each <Subject N> to <Picture N> in subject_definitions.
3. Use <Subject N> tags in detailed_description whenever the subject appears.
4. Output purely plain text structured prompt. Do NOT use JSON, markdown code fences, or any structured data format.
5. No preamble, greeting, explanation, or summary.
"""


def _select_chat_handler(mmproj_path: str):
    """选择适配 Qwen3.5 架构的 chat handler，自动回退。"""
    from llama_cpp import llama_chat_format

    # Qwen3.5 hybrid (Qwen-Image-2.1-PE 系列) 需要专用 handler
    handler_candidates = [
        ("Qwen35ChatHandler", {"enable_thinking": False}),
        ("Qwen3VLChatHandler", {"force_reasoning": False}),
        ("Qwen25VLChatHandler", {}),
        ("MTMDChatHandler", {}),
        ("Llava15ChatHandler", {}),
    ]
    for name, options in handler_candidates:
        handler_class = getattr(llama_chat_format, name, None)
        if handler_class is not None:
            try:
                handler = handler_class(
                    clip_model_path=mmproj_path,
                    verbose=False,
                    use_gpu=True,
                    image_min_tokens=1024,
                    image_max_tokens=1024,
                    **options,
                )
                print(f"[Easy-T8Enhancer] Using chat handler: {name}")
                return handler
            except (TypeError, ValueError) as e:
                # 某些 handler 不支持 use_gpu/image_*_tokens 参数，用精简参数重试
                try:
                    handler = handler_class(clip_model_path=mmproj_path, verbose=False, **options)
                    print(f"[Easy-T8Enhancer] Using chat handler: {name} (basic init)")
                    return handler
                except Exception:
                    continue
            except Exception:
                continue

    raise RuntimeError(
        "[Easy-T8Enhancer] No compatible multimodal chat handler found. "
        "Update llama-cpp-python or check your mmproj file."
    )


def _clean_output(text: str) -> str:
    """清理 LLM 输出：移除 markdown 代码块、尝试将 JSON 转为纯文本六段式格式。"""
    import re
    import json as _json

    text = text.strip()

    # 移除 markdown 代码块包裹
    text = re.sub(r'^```(?:json|text|markdown)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()

    # 如果输出是 JSON 格式，尝试转为纯文本六段式
    if text.startswith('{'):
        try:
            obj = _json.loads(text)
            sections = []
            section_keys = [
                "subject_definitions", "summary", "retention_analysis",
                "detailed_description", "overall_soundscape", "non_diegetic_music",
            ]
            for key in section_keys:
                val = obj.get(key, "")
                if val:
                    sections.append(f"{key}:\n{val}")
            if sections:
                return "\n\n".join(sections)
        except (_json.JSONDecodeError, AttributeError, TypeError):
            pass

    return text


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
    except ImportError as e:
        raise ImportError(f"llama-cpp-python is required for local prompt enhancement: {e}")

    chat_handler = None
    if mmproj_path and reference_images:
        chat_handler = _select_chat_handler(mmproj_path)

    print(f"[Easy-T8Enhancer] Loading local model: {model_name} (mmproj: {mmproj_name}, lang: {language})...")
    
    llama_kwargs = {
        "model_path": model_path,
        "chat_handler": chat_handler,
        "n_ctx": context_size,
        "n_gpu_layers": -1,
        "seed": seed if seed >= 0 else 0,
        "verbose": False,
        "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": False},
    }
    llm = Llama(**llama_kwargs)

    # 根据实际素材数量动态构建系统提示词
    num_pictures = min(len(reference_images), 3)
    if language == "en":
        system_prompt = _build_system_prompt_en(num_pictures)
    else:
        system_prompt = _build_system_prompt_zh(num_pictures)

    # 构建用户消息：每张图单独一个 image_url 条目
    user_content = []
    for idx, img in enumerate(reference_images[:3]):
        data_url = pil_to_base64_data_url(img)
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    # 构建素材绑定映射说明
    if num_pictures > 0:
        binding_lines = []
        for i in range(1, num_pictures + 1):
            binding_lines.append(f"  <Picture {i}> = @图片{i}（素材箱第{i}张图）→ 绑定为 <Subject {i}>")
        binding_map = "\n".join(binding_lines)
        material_info = f"素材箱已连接 {num_pictures} 张参考图，绑定关系如下：\n{binding_map}\n"
    else:
        material_info = "素材箱未连接参考图，请根据用户描述生成纯文字提示词。\n"

    lang_desc = "中文 (Chinese)" if language == "zh" else "English"
    instructions = (
        f"{material_info}"
        f"Task Type: {task_type}\n"
        f"Output Language: {lang_desc}\n"
        f"Target Duration: {duration_seconds} seconds\n"
        f"Shot Count: {shot_count}\n"
        f"Rewrite Mode: {rewrite_mode}\n\n"
        f"【用户初始输入文本】：\n\"\"\"\n{prompt.strip() or '电影级叙事人物场景'}\n\"\"\"\n\n"
        f"【导演扩写指令】：\n"
        f"请深度理解上述初始文本的语义情境与核心意图，完全顺应其叙事与情绪氛围进行最标准的影视级六段式扩写（除非初始文本有特别要求，否则先不做预设限制）。"
        f"若涉及台词请规范使用 <d>...</d> 标记，必须在 subject_definitions 中声明并绑定素材资产："
    )
    user_content.append({"type": "text", "text": instructions})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    print(f"[Easy-T8Enhancer] Generating prompt ({num_pictures} reference images)...")
    from comfy.model_management import throw_exception_if_processing_interrupted

    result_text = ""
    try:
        collected = []
        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            stream=True,
        )
        for chunk in stream:
            throw_exception_if_processing_interrupted()
            delta = chunk["choices"][0].get("delta", {}).get("content")
            if delta:
                collected.append(delta)
                print(delta, end="", flush=True)
        print()

        result_text = "".join(collected).strip()
        if "<think>" in result_text and "</think>" in result_text:
            result_text = result_text.split("</think>")[-1].strip()
        result_text = _clean_output(result_text)
    finally:
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
