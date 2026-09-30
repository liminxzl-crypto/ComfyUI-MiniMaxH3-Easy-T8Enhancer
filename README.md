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

- **官方六段式影视标准提示词 (Official 6-Section MiniMax Prompt Format)**:
  - 深度定制影视级系统提示词，严格按照 MiniMax 官方六段式规范输出：
    1. `subject_definitions:`（精准建立 `<Subject 1> ↔ <Picture 1>` 的主体与服装特征绑定）
    2. `summary:`（事件整体摘要）
    3. `retention_analysis:`（主体身份与参考图一致性保持分析）
    4. `detailed_description:`（按 `[Shot 1]`、`[Shot 2]` 时间轴展开镜头机位、运镜与微表情动作）
    5. `overall_soundscape:`（环境声学音效与拟音细节）
    6. `non_diegetic_music:`（情绪配乐与乐器配置）

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
- `task_type`: 生成任务模式（`Ref2VA` 参考生视频 / `T2VA` 文生视频 / `I2VA` 图生视频 等）。
- `duration_seconds`: 目标视频时长（自动决定多镜头分段密度）。
- `shot_count`: 镜头数量（`AUTO` 智能自适应 / `1`~`5` 指定分镜数）。
- `rewrite_mode`: 改写策略（`balanced` 平衡 / `strict` 严格忠实 / `creative` 创意发散）。
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

Apache-2.0 License
