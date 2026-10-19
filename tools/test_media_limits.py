"""Offline check for the H3 media-limit handling (no ComfyUI needed).

Run with the ComfyUI embedded interpreter:
    python_embeded\\python.exe tools\\test_media_limits.py
"""
import os
import sys

NODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, NODE_DIR)

import torch
import bundle_parser as bp
import qwen_vision_engine as qve


class Item:
    def __init__(self, media_type, value):
        self.media_type = media_type
        self.value = value


class Bundle:
    def __init__(self, items):
        self.items = items


def img(h=64, w=64):
    return torch.zeros(1, h, w, 3)


def video(has_audio):
    return {"images": torch.zeros(4, 32, 32, 3), "audio": {"waveform": torch.zeros(1, 100)} if has_audio else None}


def report(title, bundle, **kw):
    media = bp.describe_media(media_bundle=bundle, **kw)
    print(f"\n=== {title} ===")
    print("raw:", media["raw"])
    print("pictures/videos/audios:", media["pictures"], media["videos"], media["audios"])
    print("vision items:", len(media["vision_items"]), [i["tag"] for i in media["vision_items"]])
    print("violations:", media["violations"])
    block = qve._inventory_block(media, "zh")
    assert "超限" not in block or media["violations"], "limit warning missing"
    return media


# 1) The user's actual case: 12 images, 2 videos (one with soundtrack), 4 audios
big = Bundle([Item("image", img()) for _ in range(12)]
             + [Item("video", video(True)), Item("video", video(False))]
             + [Item("audio", {"waveform": torch.zeros(1, 10)}) for _ in range(4)])
media = report("12 images + 2 videos + 4 audios", big)
assert len(media["vision_items"]) == 11, media["vision_items"]
assert media["pictures"] == 9
assert media["videos"] == 2
assert media["audio_ordinal_total"] == 4 + 1
assert len(media["violations"]) >= 3
print(qve._inventory_block(media, "zh"))

# 2) Legal case: 9 + 3 + 3 = 15, no violations
ok = Bundle([Item("image", img()) for _ in range(9)]
            + [Item("video", video(False)) for _ in range(3)]
            + [Item("audio", {"waveform": torch.zeros(1, 10)}) for _ in range(3)])
media = report("9 images + 3 videos + 3 audios", ok)
assert media["violations"] == [], media["violations"]
assert media["pictures"] == 9 and media["videos"] == 3
assert len(media["vision_items"]) == 12
print(qve._inventory_block(media, "en"))

# 3) Empty bundle -> no tags invented
media = report("empty bundle", None)
assert media["pictures"] == 0 and media["violations"] == []
assert not media["vision_items"]

# 4) System prompts accept the inventory and stay consistent
for style in ("official_skill", "h3_standard", "visual_only"):
    for lang in ("zh", "en"):
        text = qve.build_system_prompt(
            output_style=style, language=lang, task_type="Ref2VA",
            num_pictures=9, media_inventory=bp.describe_media(ok),
        )
        assert "<Picture 9>" in text or "<Picture {i}>" in text, (style, lang)
        assert "<Video 3>" in text, (style, lang, "video inventory missing")
        assert "<Audio 3>" in text, (style, lang, "audio inventory missing")
print("\nALL CHECKS PASSED")
