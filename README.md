# ComfyUI-MiniMaxH3-Easy-T8Enhancer

A powerful local GGUF multimodal prompt optimizer extension for [ComfyUI-MiniMaxH3-Easy](https://github.com/nkxx188/ComfyUI-MiniMaxH3-Easy), combining Easy media management with T8-grade local Qwen vision model enhancement.

## Features
- **Zero modification to upstream Easy**: Completely isolated custom node. Upstream `ComfyUI-MiniMaxH3-Easy` can be updated anytime with zero merge conflicts.
- **Easy MediaBundle native support**: Directly connects to `MiniMaxH3EasyMediaLoader` output, automatically extracting reference images and videos.
- **Local GGUF Multimodal Vision**: Powered by local `llama-cpp-python`, natively supporting `Qwen3.8-9B` and `Qwen-Image-2.1-PE-I2I` mmproj vision projectors.
- **Automatic VRAM Offloading**: Automatically unloads LLM and clears CUDA cache immediately after prompt enhancement, keeping VRAM 100% available for downstream MiniMax-H3 diffusion sampling on 8GB laptops.

## License
Apache-2.0
