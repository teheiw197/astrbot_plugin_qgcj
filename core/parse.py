import os
from pathlib import Path
from PIL import Image
import re


def get_image_info(path: str) -> dict:
    """
    获取图片信息
    Args:
        path: 图片路径

    Returns:
        dict: 图片信息
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return {"size": 0, "height": 0, "width": 0}

    try:
        with Image.open(path_obj) as img:
            width, height = img.size
            size = os.path.getsize(path_obj)
            return {"size": size, "height": height, "width": width}
    except Exception as e:
        return {"size": 0, "height": 0, "width": 0}


def check_image_name(text: str) -> bool:
    """
    检查图片名是否合法
    """
    return bool(re.match(r"^[^\\/:*?\"><|\r\n]+\.(jpg|jpeg|png|gif)$", text))


def check_gallery_name(text: str) -> bool:
    """
    检查图库名是否合法
    """
    return bool(re.match(r"^[^\\/:*?\"><|\r\n]+$", text)) 