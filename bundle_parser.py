"""Media-bundle helpers for the MiniMax H3 Easy T8 enhancer.

MiniMax H3 hard limits for ONE reference generation (source of truth:
``ComfyUI-MiniMaxH3-Easy/nodes.py``)::

    MAX_MEDIA  = 15   # images + videos + audio clips, combined
    MAX_IMAGES = 9
    MAX_VIDEOS = 3
    MAX_AUDIOS = 3

The Easy node enforces them with
``"Reference mode media limits are 9 images, 3 videos and 3 audio clips"``.
Context Segments may hold 27 images in the shared library, but every single
segment generation still obeys the per-type caps above.

The prompt optimizer therefore must never *claim* or *bind* more media than H3
can actually consume, and it may only *see* images (still pictures plus one
representative frame per reference video); audio is described, never analysed.
"""

import torch
from PIL import Image
from typing import Any, List, Optional

H3_MAX_MEDIA = 15
H3_MAX_IMAGES = 9
H3_MAX_VIDEOS = 3
H3_MAX_AUDIOS = 3


def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """Converts a torch Tensor [H, W, C] or [1, H, W, C] in range [0, 1] to PIL Image."""
    if tensor is None:
        return None
    if tensor.ndim == 4:
        tensor = tensor[0]
    tensor = tensor.detach().cpu().clamp(0, 1)
    np_img = (tensor.numpy() * 255.0).astype("uint8")
    return Image.fromarray(np_img)


def _bundle_items(bundle: Any):
    if bundle is None:
        return []
    items = getattr(bundle, "items", None)
    if items is None and isinstance(bundle, (list, tuple)):
        items = bundle
    return list(items or [])


def _split_item(item):
    m_type = getattr(item, "media_type", None)
    val = getattr(item, "value", None)
    if m_type is None and isinstance(item, dict):
        m_type = item.get("media_type")
        val = item.get("value")
    return m_type, val


def video_has_audio(value: Any) -> bool:
    """True when a reference-video payload carries its own soundtrack."""
    if isinstance(value, dict):
        return value.get("audio") is not None
    getter = getattr(value, "get", None)
    return bool(getter and getter("audio") is not None)


def summarize_media_bundle(bundle: Any) -> dict:
    """Split a Media Bundle into typed, order-preserving lists."""
    summary = {"images": [], "videos": [], "audios": []}
    for item in _bundle_items(bundle):
        m_type, val = _split_item(item)
        if m_type == "image" and isinstance(val, torch.Tensor):
            summary["images"].append(val)
        elif m_type == "video":
            summary["videos"].append(val)
        elif m_type == "audio":
            summary["audios"].append(val)
    return summary


def extract_media_from_bundle(bundle: Any) -> tuple[List[torch.Tensor], List[Any], List[Any]]:
    """
    Safely extracts images, audios, and videos from Easy's MiniMaxH3MediaBundle.
    Returns: (images, audios, videos)
    """
    summary = summarize_media_bundle(bundle)
    return summary["images"], summary["audios"], summary["videos"]


def describe_media(
    media_bundle: Optional[Any] = None,
    image: Optional[torch.Tensor] = None,
    first_frame: Optional[torch.Tensor] = None,
    last_frame: Optional[torch.Tensor] = None,
) -> dict:
    """Build the vision payload *and* the H3-limit report for one generation.

    Returns a dict with:
      vision_items:  [{"tag", "kind", "image"}] images actually shown to the
                     local vision model. ``kind`` is one of image / video /
                     first_frame / last_frame.
      pictures/videos/audios: how many media assets are described in the prompt.
      video_audio_pairs: [(video_ordinal, audio_ordinal)] for video soundtracks.
      raw:           counts as supplied by the user (before capping).
      violations:    human-readable limit breaches.
    """
    summary = summarize_media_bundle(media_bundle)

    raw_images = sum(max(1, int(t.shape[0])) for t in summary["images"])
    if image is not None and isinstance(image, torch.Tensor):
        raw_images += max(1, int(image.shape[0]))
    raw_videos = len(summary["videos"])
    raw_audios = len(summary["audios"])
    raw = {"images": raw_images, "videos": raw_videos, "audios": raw_audios}
    raw["total"] = raw_images + raw_videos + raw_audios

    violations = []
    if raw_images > H3_MAX_IMAGES:
        violations.append(f"图片 {raw_images} 张 > H3 上限 {H3_MAX_IMAGES} 张")
    if raw_videos > H3_MAX_VIDEOS:
        violations.append(f"视频 {raw_videos} 段 > H3 上限 {H3_MAX_VIDEOS} 段")
    if raw_audios > H3_MAX_AUDIOS:
        violations.append(f"音频 {raw_audios} 条 > H3 上限 {H3_MAX_AUDIOS} 条")
    if raw["total"] > H3_MAX_MEDIA:
        violations.append(f"媒体合计 {raw['total']} > H3 上限 {H3_MAX_MEDIA}")

    vision_items = []

    # 1) Still pictures keep H3's own <Picture N> ordinals, capped at 9.
    picture_ordinal = 0
    for tensor in summary["images"]:
        for i in range(int(tensor.shape[0])):
            if picture_ordinal >= H3_MAX_IMAGES:
                break
            picture_ordinal += 1
            vision_items.append(
                {
                    "tag": f"<Picture {picture_ordinal}>",
                    "kind": "image",
                    "image": tensor_to_pil(tensor[i]),
                }
            )
        if picture_ordinal >= H3_MAX_IMAGES:
            break

    # 2) Direct IMAGE input continues the picture series.
    if isinstance(image, torch.Tensor):
        for i in range(int(image.shape[0])):
            if picture_ordinal >= H3_MAX_IMAGES:
                break
            picture_ordinal += 1
            vision_items.append(
                {
                    "tag": f"<Picture {picture_ordinal}>",
                    "kind": "image",
                    "image": tensor_to_pil(image[i]),
                }
            )

    # 3) One representative frame per reference video, capped at 3.
    video_audio_pairs = []
    audio_ordinal = 0
    video_items = summary["videos"][:H3_MAX_VIDEOS]
    for v_idx, vid in enumerate(video_items, start=1):
        if video_has_audio(vid):
            audio_ordinal += 1
            video_audio_pairs.append((v_idx, audio_ordinal))
        frames = vid.get("images") if isinstance(vid, dict) else None
        if isinstance(frames, torch.Tensor) and frames.shape[0] > 0:
            vision_items.append(
                {
                    "tag": f"<Video {v_idx}>",
                    "kind": "video",
                    "image": tensor_to_pil(frames[0]),
                }
            )

    # 4) Keyframes are structured inputs, not <Picture N> assets.
    if isinstance(first_frame, torch.Tensor):
        vision_items.append(
            {"tag": "<First Frame>", "kind": "first_frame", "image": tensor_to_pil(first_frame)}
        )
    if isinstance(last_frame, torch.Tensor):
        vision_items.append(
            {"tag": "<Last Frame>", "kind": "last_frame", "image": tensor_to_pil(last_frame)}
        )

    return {
        "vision_items": vision_items,
        "pictures": picture_ordinal,
        "videos": len(video_items),
        "audios": len(summary["audios"]),
        "audio_ordinal_total": audio_ordinal + len(summary["audios"]),
        "video_audio_pairs": video_audio_pairs,
        "raw": raw,
        "violations": violations,
    }


def collect_vision_items(
    media_bundle: Optional[Any] = None,
    image: Optional[torch.Tensor] = None,
    first_frame: Optional[torch.Tensor] = None,
    last_frame: Optional[torch.Tensor] = None,
) -> List[dict]:
    """Tagged images for the vision model, capped to H3's per-type limits."""
    return describe_media(media_bundle, image, first_frame, last_frame)["vision_items"]


def collect_all_reference_images(
    media_bundle: Optional[Any] = None,
    image: Optional[torch.Tensor] = None,
    first_frame: Optional[torch.Tensor] = None,
    last_frame: Optional[torch.Tensor] = None,
) -> List[Image.Image]:
    """Backwards-compatible flat list of PIL images (order = vision order)."""
    return [item["image"] for item in collect_vision_items(media_bundle, image, first_frame, last_frame)]
