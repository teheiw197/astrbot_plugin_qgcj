import asyncio
import os
from PIL import Image
import httpx
import random
import re
from typing import Dict, List, Optional, Union
from astrbot import logger
from astrbot.core.platform.message_components import Image as AstrImage

# 图像压缩
async def compress_image(image_bytes: bytes, max_size: int = 512) -> bytes:
    """
    压缩图片到指定大小
    Args:
        image_bytes: 图片字节流
        max_size: 最大边长（像素）

    Returns:
        压缩后的图片字节流
    """
    try:
        from io import BytesIO

        img = Image.open(BytesIO(image_bytes))
        width, height = img.size

        if max(width, height) > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            img = img.resize((new_width, new_height), Image.ANTIALIAS)

        output_buffer = BytesIO()
        img.save(output_buffer, format="JPEG")
        return output_buffer.getvalue()
    except Exception as e:
        logger.error(f"压缩图片失败: {e}")
        return image_bytes


# 获取消息内容
async def get_message_content(event, reply: bool = True) -> Dict[str, str]:
    """
    获取消息内容
    """
    text = event.get_message_str()
    if not text:
        if reply and event.message_obj.reply: # 如果是回复消息
            reply_id = event.message_obj.reply.message_id
            if reply_id: # 确认回复的消息存在
                reply_event = await event.get_event_by_msg_id(reply_id)
                text = reply_event.get_message_str()
    return {"text": text.strip()}


# 下载文件
async def download_file(url: str, save_path: str) -> bool:
    """
    下载文件
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return False


# 获取昵称
def get_nickname(event) -> str:
    """
    获取用户昵称
    """
    return event.get_sender_name() or str(event.get_sender_id())


# 获取图片
async def get_image(event, reply: bool = True) -> bytes | None:
    """
    获取图片
    """
    image_bytes = None
    # 优先从当前消息中获取图片
    for comp in event.get_messages():
        if isinstance(comp, AstrImage):
            if comp.url:
                async with httpx.AsyncClient() as client:
                    response = await client.get(comp.url)
                    response.raise_for_status()
                    image_bytes = response.content
                    break
            elif comp.path:
                with open(comp.path, "rb") as f:
                    image_bytes = f.read()
                    break
    
    # 如果当前消息没有图片，且是回复消息，尝试从回复消息中获取
    if image_bytes is None and reply and event.message_obj.reply:
        reply_id = event.message_obj.reply.message_id
        if reply_id:
            reply_event = await event.get_event_by_msg_id(reply_id)
            for comp in reply_event.get_messages():
                if isinstance(comp, AstrImage):
                    if comp.url:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(comp.url)
                            response.raise_for_status()
                            image_bytes = response.content
                            break
                    elif comp.path:
                        with open(comp.path, "rb") as f:
                            image_bytes = f.read()
                            break
    return image_bytes 