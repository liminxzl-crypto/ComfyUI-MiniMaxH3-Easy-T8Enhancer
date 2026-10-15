"""Verify the bundled MiniMax H3 official Skill snapshot against its pinned manifest.

Run from the node directory:

    python tools/verify_official_skill.py

Exit code is 0 when every recorded hash matches, 1 otherwise. This is the same check
`official_skill.verify_integrity()` performs at node load time, exposed as a CLI so
contributors and CI can confirm the snapshot was not altered.
"""

from __future__ import annotations

import sys
from pathlib import Path

NODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NODE_ROOT))

from official_skill import (  # noqa: E402
    H3_SKILL_ROOT,
    OfficialSkillError,
    load_source_manifest,
    skill_provenance,
    verify_integrity,
)


def main() -> int:
    authority, repository, commit = skill_provenance()
    print("Bundled MiniMax H3 official prompt-writing Skill")
    print(f"  authority : {authority}")
    print(f"  source    : {repository}")
    print(f"  commit    : {commit}")
    print(f"  skill dir : {H3_SKILL_ROOT}")
    print()

    try:
        manifest = load_source_manifest()
    except OfficialSkillError as exc:
        print(f"FAIL  manifest unreadable: {exc}")
        return 1

    ok, problems = verify_integrity()
    for rel in sorted(manifest.get("files") or {}):
        print(f"  {'OK  ' if all(rel not in p for p in problems) else 'FAIL'}  {rel}")

    tree = manifest.get("normalized_tree_sha256") or ""
    if tree:
        tree_ok = not any("tree_sha256" in p for p in problems)
        print(f"\n  {'OK  ' if tree_ok else 'FAIL'}  normalized_tree_sha256 {tree}")

    print()
    if ok:
        print("PASS  snapshot matches the pinned manifest.")
        return 0

    print("FAIL  snapshot does not match the pinned manifest:")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
