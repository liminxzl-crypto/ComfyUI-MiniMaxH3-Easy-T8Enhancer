import os
from typing import Any, List, Optional
import torch
from PIL import Image

def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """Converts a torch Tensor [H, W, C] or [1, H, W, C] in range [0, 1] to PIL Image."""
    if tensor is None:
        return None
    if tensor.ndim == 4:
        tensor = tensor[0]
    tensor = tensor.detach().cpu().clamp(0, 1)
    np_img = (tensor.numpy() * 255.0).astype("uint8")
    return Image.fromarray(np_img)

def extract_media_from_bundle(bundle: Any) -> tuple[List[torch.Tensor], List[Any], List[Any]]:
    """
    Safely extracts images, audios, and videos from Easy's MiniMaxH3MediaBundle.
    Returns: (images, audios, videos)
    """
    images = []
    audios = []
    videos = []

    if bundle is None:
        return images, audios, videos

    items = getattr(bundle, "items", None)
    if items is None and isinstance(bundle, (list, tuple)):
        items = bundle

    if items:
        for item in items:
            m_type = getattr(item, "media_type", None)
            val = getattr(item, "value", None)
            if m_type is None and isinstance(item, dict):
                m_type = item.get("media_type")
                val = item.get("value")

            if m_type == "image":
                if isinstance(val, torch.Tensor):
                    images.append(val)
            elif m_type == "audio":
                audios.append(val)
            elif m_type == "video":
                videos.append(val)

    return images, audios, videos

def collect_all_reference_images(
    media_bundle: Optional[Any] = None,
    image: Optional[torch.Tensor] = None,
    first_frame: Optional[torch.Tensor] = None,
    last_frame: Optional[torch.Tensor] = None,
) -> List[Image.Image]:
    """
    Collects and normalizes all visual inputs into PIL Images for visual LLM processing.
    素材箱（media_bundle）的图片优先排列在最前面，确保 <Picture 1>, <Picture 2>...
    与素材箱里的 @图片1, @图片2... 一一对应。
    """
    pil_images = []

    # 1. 素材箱图片优先（保证 <Picture N> 与 @图片N 对应）
    if media_bundle is not None:
        b_images, _, b_videos = extract_media_from_bundle(media_bundle)
        for img_tensor in b_images:
            if isinstance(img_tensor, torch.Tensor):
                for i in range(img_tensor.shape[0]):
                    pil_images.append(tensor_to_pil(img_tensor[i]))

        for vid in b_videos:
            if isinstance(vid, dict) and "images" in vid:
                v_frames = vid["images"]
                if isinstance(v_frames, torch.Tensor) and v_frames.shape[0] > 0:
                    pil_images.append(tensor_to_pil(v_frames[0]))

    # 2. 直接连接的 image 输入（补充到素材箱图片之后）
    if image is not None and isinstance(image, torch.Tensor):
        for i in range(image.shape[0]):
            pil_images.append(tensor_to_pil(image[i]))

    # 3. first_frame
    if first_frame is not None and isinstance(first_frame, torch.Tensor):
        pil_images.append(tensor_to_pil(first_frame))

    # 4. last_frame
    if last_frame is not None and isinstance(last_frame, torch.Tensor):
        pil_images.append(tensor_to_pil(last_frame))

    return pil_images
