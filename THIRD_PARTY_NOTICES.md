# Third-party notices

## MiniMax official Skill resources

- `official_skills/h3-prompt-writing/` is a verbatim, CRLF-normalized snapshot of the
  portable official prompt-writing Skill from
  [`MiniMax-AI/MiniMax-H3`](https://github.com/MiniMax-AI/MiniMax-H3), pinned at commit
  `d21241f0a4b3acbb34c97dae47fa417b7065e438`. It contains exactly four files:
  - `SKILL.md`
  - `agents/openai.yaml`
  - `references/base-en.txt`
  - `references/ref-en.txt`
- `official_skills/H3_SOURCE.json` records that commit together with the per-file SHA-256
  hashes and the normalized tree hash
  (`b6c4af89b79c044efc8c05865d52cee2cd726ec69c70a6770a707ecf1b18ba89`). `official_skill.py`
  re-verifies these hashes at load time and fails loudly if the snapshot is incomplete or
  modified.
- Those official materials **remain copyright MiniMax-AI** and are **not relicensed** under
  this project's Apache-2.0 license. They are bundled solely so the node can implement the
  official prompt-writing contract offline with deterministic provenance. See
  `official_skills/H3_NOTICE.md` for the upstream notice text.
- The upstream Skill declares compatibility with MiniMax Hub agent/canvas/hub tooling. This
  project only reproduces the prompt-writing constraints in `h3-prompt-writing`; it does not
  port any Hub tooling, agent runtime, or the other upstream Skills.

## Local Qwen GGUF models

The node loads GGUF models that the user installs themselves into `ComfyUI/models/LLM/`.
**No model weights are bundled or redistributed by this repository.** Model availability,
licensing, and suitability are governed by the terms of whichever GGUF the user downloads;
those terms remain with the respective model publishers.

## Other components

- `llama-cpp-python` is an optional runtime dependency, licensed under the MIT License by its
  contributors. It is not bundled here.
- ComfyUI itself is licensed by its own upstream terms and is not bundled here.
