"""Bundled MiniMax H3 official prompt-writing Skill.

`official_skills/h3-prompt-writing/` is a verbatim, CRLF-normalized snapshot of the
portable official prompt-writing Skill from
[`MiniMax-AI/MiniMax-H3`](https://github.com/MiniMax-AI/MiniMax-H3), pinned at the
commit recorded in `official_skills/H3_SOURCE.json`.

This module only *reads* those files. It never downloads, installs, or invokes
anything remote, and it never rewrites the snapshot. `verify_integrity()` re-checks
every file hash plus the normalized tree hash against the manifest so that a
tampered or partially copied snapshot fails loudly instead of silently degrading
prompt quality.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

NODE_ROOT = Path(__file__).resolve().parent
OFFICIAL_SKILLS_ROOT = NODE_ROOT / "official_skills"
H3_SKILL_ROOT = OFFICIAL_SKILLS_ROOT / "h3-prompt-writing"
H3_SOURCE_MANIFEST = OFFICIAL_SKILLS_ROOT / "H3_SOURCE.json"
H3_NOTICE = OFFICIAL_SKILLS_ROOT / "H3_NOTICE.md"

SKILL_FILENAME = "SKILL.md"
BASE_GUIDE_FILENAME = "base-en.txt"
REF_GUIDE_FILENAME = "ref-en.txt"
BASE_GUIDE_REL = ("references", BASE_GUIDE_FILENAME)
REF_GUIDE_REL = ("references", REF_GUIDE_FILENAME)

#: Task types exposed by the node. "Auto" is resolved at runtime.
TASK_TYPES = ("Ref2VA", "T2VA", "I2VA", "FL2VA", "L2VA", "Auto")

#: Modes served by references/base-en.txt (three core fields).
BASE_MODES = ("T2VA", "I2VA", "FL2VA", "L2VA")

#: Mode served by references/ref-en.txt (six rewrite sections).
REFERENCE_MODE = "Ref2VA"

#: Base modes that carry a mandatory first/last-frame alignment instruction line.
KEYFRAME_MODES = ("I2VA", "FL2VA", "L2VA")

#: Sections dropped by output_style="visual_only".
AUDIO_SECTIONS = ("overall_soundscape", "non_diegetic_music")

#: Output styles exposed by the node.
OUTPUT_STYLES = ("official_skill", "h3_standard", "visual_only")
DEFAULT_OUTPUT_STYLE = "official_skill"

#: Sections the official guides define for each mode, in mandatory order.
BASE_SECTIONS = (
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music",
)
REFERENCE_SECTIONS = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)


class OfficialSkillError(RuntimeError):
    """Raised when the bundled official H3 Skill is missing or inconsistent."""


def _normalize_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _sha256_normalized(path: Path) -> str:
    return hashlib.sha256(_normalize_bytes(path.read_bytes())).hexdigest()


def normalize_output_style(style: Any) -> str:
    value = str(style or "").strip()
    return value if value in OUTPUT_STYLES else DEFAULT_OUTPUT_STYLE


def normalize_task_type(task_type: Any) -> str:
    value = str(task_type or "").strip()
    for known in TASK_TYPES:
        if value.casefold() == known.casefold():
            return known
    return "Ref2VA"


def resolve_task_type(task_type: Any, *, has_reference_images: bool) -> str:
    """Resolve "Auto" into a concrete mode.

    Reference images mean the caller can actually honour full-reference labels,
    so Auto picks Ref2VA in that case and T2VA (pure text-to-video) otherwise.
    """
    value = normalize_task_type(task_type)
    if value != "Auto":
        return value
    return REFERENCE_MODE if has_reference_images else "T2VA"


def is_reference_mode(task_type: str) -> bool:
    return normalize_task_type(task_type) == REFERENCE_MODE


def is_keyframe_mode(task_type: str) -> bool:
    return normalize_task_type(task_type) in KEYFRAME_MODES


def guide_filename_for(task_type: str) -> str:
    return REF_GUIDE_FILENAME if is_reference_mode(task_type) else BASE_GUIDE_FILENAME


def sections_for(task_type: str) -> Tuple[str, ...]:
    return REFERENCE_SECTIONS if is_reference_mode(task_type) else BASE_SECTIONS


def sections_for_style(task_type: str, output_style: str) -> Tuple[str, ...]:
    """Sections the model is expected to emit for a given mode + style."""
    sections = sections_for(task_type)
    if normalize_output_style(output_style) == "visual_only":
        sections = tuple(name for name in sections if name not in AUDIO_SECTIONS)
    return sections


@lru_cache(maxsize=4)
def load_source_manifest() -> Dict[str, Any]:
    try:
        raw = H3_SOURCE_MANIFEST.read_text(encoding="utf-8")
    except OSError as exc:
        raise OfficialSkillError(
            f"Official H3 Skill manifest is unavailable: {H3_SOURCE_MANIFEST} ({exc})"
        ) from exc
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OfficialSkillError(
            f"Official H3 Skill manifest is not valid JSON: {H3_SOURCE_MANIFEST}"
        ) from exc
    if not isinstance(manifest, dict) or not manifest.get("files"):
        raise OfficialSkillError(
            f"Official H3 Skill manifest is missing its file inventory: {H3_SOURCE_MANIFEST}"
        )
    return manifest


@lru_cache(maxsize=1)
def verify_integrity() -> Tuple[bool, Tuple[str, ...]]:
    """Re-hash the bundled snapshot against the pinned manifest."""
    try:
        manifest = load_source_manifest()
    except OfficialSkillError as exc:
        return False, (str(exc),)

    files = manifest.get("files") or {}
    problems = []
    records = []

    for rel, expected in sorted(files.items()):
        path = H3_SKILL_ROOT / rel
        if not path.is_file():
            problems.append(f"missing file: {rel}")
            continue
        actual = _sha256_normalized(path)
        records.append(
            Path(rel).as_posix().encode("utf-8") + b"\x00" + actual.encode("ascii")
        )
        if actual != expected:
            problems.append(f"sha256 mismatch: {rel}")

    expected_tree = str(manifest.get("normalized_tree_sha256") or "")
    if expected_tree:
        actual_tree = hashlib.sha256(b"\n".join(records)).hexdigest()
        if actual_tree != expected_tree:
            problems.append("normalized_tree_sha256 mismatch")

    return (not problems), tuple(problems)


def skill_provenance() -> Tuple[str, str, str]:
    """Return (authority, repository, commit) recorded by the manifest."""
    try:
        manifest = load_source_manifest()
    except OfficialSkillError:
        return ("MiniMax-AI", "https://github.com/MiniMax-AI/MiniMax-H3", "")
    return (
        str(manifest.get("authority") or "MiniMax-AI"),
        str(manifest.get("repository") or "https://github.com/MiniMax-AI/MiniMax-H3"),
        str(manifest.get("commit") or ""),
    )


def provenance_banner() -> str:
    authority, repository, commit = skill_provenance()
    tree = ""
    try:
        tree = str(load_source_manifest().get("normalized_tree_sha256") or "")
    except OfficialSkillError:
        tree = ""
    parts = [f"VERBATIM_OFFICIAL_H3_SKILL_SOURCE authority={authority} source={repository}"]
    if commit:
        parts.append(f"commit={commit}")
    if tree:
        parts.append(f"tree_sha256={tree}")
    return " ".join(parts)


def _read_required(path: Path, label: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OfficialSkillError(
            f"Bundled official H3 Skill is unavailable ({label}): {path} ({exc})"
        ) from exc
    if not text.strip():
        raise OfficialSkillError(f"Bundled official H3 Skill is empty ({label}): {path}")
    return text


def _assert_trustworthy() -> None:
    ok, problems = verify_integrity()
    if not ok:
        raise OfficialSkillError(
            "Bundled official H3 Skill failed its integrity check. "
            "Re-install the node, or switch output_style to 'h3_standard' to use the "
            "built-in prompt. Problems: " + "; ".join(problems)
        )


@lru_cache(maxsize=2)
def load_skill_source_bundle() -> Tuple[str, str, str]:
    """Return (skill_md, guide_filename, guide_text) for the reference mode."""
    _assert_trustworthy()
    skill_md = _read_required(H3_SKILL_ROOT / SKILL_FILENAME, SKILL_FILENAME)
    guide_name = REF_GUIDE_FILENAME
    guide = _read_required(H3_SKILL_ROOT.joinpath(*REF_GUIDE_REL), guide_name)
    return skill_md, guide_name, guide


@lru_cache(maxsize=8)
def load_skill_bundle(task_type: str) -> Tuple[str, str, str]:
    """Return (skill_md, guide_filename, guide_text) for the given task type."""
    _assert_trustworthy()
    skill_md = _read_required(H3_SKILL_ROOT / SKILL_FILENAME, SKILL_FILENAME)
    if is_reference_mode(task_type):
        guide_name = REF_GUIDE_FILENAME
        guide = _read_required(H3_SKILL_ROOT.joinpath(*REF_GUIDE_REL), guide_name)
    else:
        guide_name = BASE_GUIDE_FILENAME
        guide = _read_required(H3_SKILL_ROOT.joinpath(*BASE_GUIDE_REL), guide_name)
    return skill_md, guide_name, guide


def clear_caches() -> None:
    """Drop memoized snapshot reads (useful for tests and hot-reload)."""
    for cached in (
        load_source_manifest,
        verify_integrity,
        load_skill_source_bundle,
        load_skill_bundle,
    ):
        cached.cache_clear()
