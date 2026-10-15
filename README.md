# ComfyUI-MiniMaxH3-Easy-T8Enhancer

A high-performance local multimodal prompt optimization node designed for [ComfyUI-MiniMaxH3-Easy](https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy). It combines Easy's intuitive media loader with T8-grade local Qwen vision model rewriting, empowering creators to generate official MiniMax Hailuo 3 (H3) cinematic prompts completely offline with zero API costs.

---

## 🌟 核心特性 (Key Features)

- **完全独立、零污染上游 (Zero Conflict & Clean Isolation)**:
  - 作为一个独立的自定义节点存在，无需修改 `ComfyUI-MiniMaxH3-Easy` 原仓库的一行代码。
  - 上游 Easy 节点随时可以 `git pull` 无缝更新，绝无合并冲突。

- **深度兼容 Easy 素材箱 (Native Easy MediaBundle Integration)**:
  - 输入端原生支持连接 `MiniMaxH3EasyMediaLoader` 的 `media_bundle` 输出。
  - 自动提取素材箱内的多张参考图片与视频关键帧，并建立 `<Picture N>` 与素材箱 `@图片N` 的严格映射。

- **内置 MiniMax 官方 H3 提示词 Skill (Bundled Official H3 Prompt-Writing Skill)**:
  - `output_style=official_skill`（默认）会把 **[MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)** 官方 `h3-prompt-writing` Skill 的**逐字快照**注入系统提示词，并以官方规范作为唯一权威。
  - 快照固定在上游 commit `d21241f0a4b3acbb34c97dae47fa417b7065e438`，逐文件 SHA-256 与归一化树哈希记录在 `official_skills/H3_SOURCE.json`，**每次加载都会重新校验**，不一致就直接报错而不是静默降级。
  - 官方素材版权归 MiniMax-AI，未按本项目许可再授权，详见 `THIRD_PARTY_NOTICES.md`。

- **按任务类型自动切换官方结构 (Task-Type Aware Structure)**:
  - `Ref2VA`（全参考改写）→ 官方六段式：`subject_definitions:` / `summary:` / `retention_analysis:` / `detailed_description:` / `overall_soundscape:` / `non_diegetic_music:`
  - `T2VA` / `I2VA` / `FL2VA` / `L2VA` → 官方三段式：`integrated_multimodal_description:` / `overall_soundscape:` / `non_diegetic_music:`
  - `I2VA` / `FL2VA` / `L2VA` 会**强制把首/尾帧对齐指令作为提示词第一行**，并按官方记号（`[Shot N]`、`At S.SS`）书写时序。
  - `Auto` → 接了参考图按 `Ref2VA`，否则按 `T2VA`。

- **三种输出风格 (Three Output Styles)**:
  - `official_skill`（默认）：逐字注入官方 Skill，字段名、段落顺序、标签规则、时序记号、声音规则一律不可改动；`language=zh` 时只允许把描述性正文中文化。
  - `h3_standard`：沿用节点自带的六段式提示词，**不加载官方 Skill**，与旧版本行为一致。
  - `visual_only`：同样基于官方 Skill，但**剔除 `overall_soundscape` 与 `non_diegetic_music` 两段**，只输出画面描述。

- **节点独立运行按钮 (Standalone Optimization Button)**:
  - 节点底部配备 **`▶ 运行提示词优化`** 按钮。
  - 可在不触发后续漫长视频生成的前提下，单独秒级运行本地提示词扩写，修改满意后再跑全流程。

- **自动下游同步与跳过机制 (Auto Downstream Sync & Skip)**:
  - **自动回显**：优化完成后，生成的提示词会自动写入节点自身，并**实时透传给下游 `MiniMaxH3Easy` 节点并在其提示框中直观显示**。
  - **秒级跳过**：已存在优化提示词时，全流程运行将直接跳过大模型重复生成，绝不浪费时间。

- **极致显存管理 (Automatic VRAM Offload for 8GB GPUs)**:
  - 专为 8GB 显存（如 RTX 4060 Laptop）精心优化，支持 GPU 硬件级多模态加速（CUDA 12/13）。
  - 推理完成后自动执行 `del llm` 与 `torch.cuda.empty_cache()`，将 100% 显存完整释放给后续的 MiniMax H3 视频去噪扩散模型。

---

## 📦 支持的模型与推荐配置 (Supported Models)

将 GGUF 大语言模型及配套的 `mmproj` 视觉投影文件放入 `ComfyUI/models/LLM/` 目录下即可自动识别：

| 推荐模型 | 文件名 | 显存占用 | 说明 |
| :--- | :--- | :--- | :--- |
| **Qwen-Image 2.1 PE (推荐)** | `Qwen-Image-2.1-PE-I2I.Q4_K_M.gguf` | ~5.2 GB | **8G 显卡首选**，速度极快（15~20秒） |
| **视觉投影文件 (必备)** | `Qwen-Image-2.1-PE-I2I.mmproj-bf16.gguf` | ~0.9 GB | 赋能 Qwen 理解素材箱图片 |
| **Qwen3.8 9B Heretic** | `Qwen3.8-9B-heretic-uncensored.i1-Q6_K.gguf` | ~7.3 GB | 高质量无审查影视扩写 |

---

## 🚀 节点参数说明 (Node Inputs)

- `prompt`: 您的初始创意或简单描述（如“两个女人在未来街道上争吵”）。
- `optimized_text`: 存放优化后的完整六段式提示词。不为空时全流程运行将直接使用并跳过大模型推理。
- `language`: 输出语言选择（`zh` 中文 / `en` 英文，默认中文）。
- `local_model`: 选择已放置在 `models/LLM` 下的 GGUF 大模型。
- `local_mmproj`: 选择配套的视觉投影权重（`none` 表示纯文本模式）。
- `task_type`: 生成任务模式，决定用官方 Skill 的哪份参考指南与段落结构。
  - `Ref2VA` → 六段式（`references/ref-en.txt`）
  - `T2VA` / `I2VA` / `FL2VA` / `L2VA` → 三段式（`references/base-en.txt`），其中 `I2VA` / `FL2VA` / `L2VA` 强制首行输出首/尾帧对齐指令
  - `Auto` → 有参考图按 `Ref2VA`，无参考图按 `T2VA`
- `duration_seconds`: 目标视频时长（自动决定多镜头分段密度）。
- `shot_count`: 镜头数量（`AUTO` 智能自适应 / `1`~`5` 指定分镜数）。
- `rewrite_mode`: 改写策略（`balanced` 平衡 / `strict` 严格忠实 / `creative` 创意发散）。
- `output_style`: 输出风格。
  - `official_skill`（默认）→ 逐字注入官方 H3 Skill 快照
  - `h3_standard` → 节点自带六段式提示词，不加载官方 Skill（旧版行为）
  - `visual_only` → 官方 Skill 基础上去掉两个音频段，只留画面
- `local_unload_policy`: 显存释放策略（默认 `unload_after_run` 跑完即卸载）。

---

## 🛠️ 安装方法 (Installation)

1. 进入 ComfyUI 根目录下的 `custom_nodes` 文件夹：
   ```bash
   cd ComfyUI/custom_nodes
   ```
2. 克隆本仓库：
   ```bash
   git clone https://github.com/liminxzl-crypto/ComfyUI-MiniMaxH3-Easy-T8Enhancer.git
   ```
3. 重启 ComfyUI 即可在节点菜单 `MiniMax H3 Easy/Prompt` 下找到该节点。

---

## 📄 开源协议 (License)

本项目代码以 **Apache-2.0** 授权，全文见 [`LICENSE`](LICENSE)。

**第三方素材**：`official_skills/h3-prompt-writing/` 是 [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)
官方 Skill 的逐字快照，**版权归 MiniMax-AI，不受本项目 Apache-2.0 再授权**。完整声明见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 与 [`official_skills/H3_NOTICE.md`](official_skills/H3_NOTICE.md)。

本仓库**不打包、不再分发**任何模型权重（GGUF / safetensors）。
