import os
import random
import shutil
from typing import List
from astrbot import logger
from astrbot.core.platform.message_components import Image
from data.plugins.qgcj.core.parse import get_image_info


class Gallery:
    """
    图库类
    """

    def __init__(self, gallery_info: dict):
        self.name: str = gallery_info["name"]
        self.path: str = gallery_info["path"]
        self.creator_id: str = gallery_info["creator_id"]
        self.creator_name: str = gallery_info["creator_name"]
        self.capacity: int = gallery_info["capacity"]
        self.compress: bool = gallery_info["compress"]
        self.duplicate: bool = gallery_info["duplicate"]
        self.fuzzy: bool = gallery_info["fuzzy"]
        self.exact_keywords: List[str] = gallery_info.get("exact_keywords", [])
        self.fuzzy_keywords: List[str] = gallery_info.get("fuzzy_keywords", [])
        self.images: List[str] = [
            os.path.join(self.path, f) for f in os.listdir(self.path)
        ]
        self.image_info: dict = {}

    def get_random_image(self) -> str:
        """
        随机获取图片
        """
        return random.choice(self.images)

    def add_image(self, image: bytes, label: str = "") -> str:
        """
        添加图片
        """
        if self.is_full():
            return f"图库【{self.name}】已满，请清理后再添加！"

        if self.duplicate and self.is_duplicate(image):
            return f"图片已存在于图库【{self.name}】，已跳过。"

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        image_name = f"{label}_{len(self.images) + 1}.jpg"
        image_path = os.path.join(self.path, image_name)
        with open(image_path, "wb") as f:
            f.write(image)
        self.images.append(image_path)
        return f"已添加图片到图库【{self.name}】。"

    def del_image(self, image_name: str) -> str:
        """
        删除图片
        """
        image_path = os.path.join(self.path, image_name)
        if os.path.exists(image_path):
            os.remove(image_path)
            self.images.remove(image_path)
            return f"已删除图片【{image_name}】。"
        return f"未找到图片【{image_name}】。"

    def is_full(self) -> bool:
        """
        判断图库是否已满
        """
        return len(self.images) >= self.capacity

    def is_duplicate(self, image: bytes) -> bool:
        """
        判断图片是否重复
        """
        # 简单的哈希检查，实际应用中可能需要更复杂的图像相似度算法
        image_hash = hash(image)
        for img_path in self.images:
            with open(img_path, "rb") as f:
                if hash(f.read()) == image_hash:
                    return True
        return False

    def add_keyword(self, keyword: str, is_fuzzy: bool = False) -> str:
        """
        添加匹配关键词
        """
        if is_fuzzy:
            if keyword not in self.fuzzy_keywords:
                self.fuzzy_keywords.append(keyword)
                return f"已添加模糊匹配词【{keyword}】到图库【{self.name}】。"
            return f"模糊匹配词【{keyword}】已存在。"
        else:
            if keyword not in self.exact_keywords:
                self.exact_keywords.append(keyword)
                return f"已添加精准匹配词【{keyword}】到图库【{self.name}】。"
            return f"精准匹配词【{keyword}】已存在。"

    def del_keyword(self, keyword: str, is_fuzzy: bool = False) -> str:
        """
        删除匹配关键词
        """
        if is_fuzzy:
            if keyword in self.fuzzy_keywords:
                self.fuzzy_keywords.remove(keyword)
                return f"已删除模糊匹配词【{keyword}】。"
            return f"模糊匹配词【{keyword}】不存在。"
        else:
            if keyword in self.exact_keywords:
                self.exact_keywords.remove(keyword)
                return f"已删除精准匹配词【{keyword}】。"
            return f"精准匹配词【{keyword}】不存在。"

    def set_fuzzy(self, fuzzy: bool) -> str:
        """
        设置图库的模糊匹配模式
        """
        self.fuzzy = fuzzy
        return f"图库【{self.name}】已切换到{'模糊' if fuzzy else '精准'}匹配模式。"

    def set_capacity(self, capacity: int) -> str:
        """
        设置图库容量
        """
        self.capacity = capacity
        return f"图库【{self.name}】容量已设置为{capacity}。"

    def set_compress(self, compress: bool) -> str:
        """
        设置是否压缩图片
        """
        self.compress = compress
        return f"图库【{self.name}】图片压缩功能已{'开启' if compress else '关闭'}。"

    def set_duplicate(self, duplicate: bool) -> str:
        """
        设置是否去重
        """
        self.duplicate = duplicate
        return f"图库【{self.name}】图片去重功能已{'开启' if duplicate else '关闭'}。"

    def remove_duplicates(self) -> str:
        """
        移除图库中的重复图片
        """
        unique_hashes = set()
        images_to_keep = []
        duplicates_removed_count = 0

        for image_path in sorted(self.images): # Sort to ensure consistent removal order if multiple duplicates
            try:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                    image_hash = hash(image_bytes)
                
                if image_hash in unique_hashes:
                    os.remove(image_path)
                    duplicates_removed_count += 1
                    logger.info(f"Removed duplicate image: {image_path} from gallery {self.name}")
                else:
                    unique_hashes.add(image_hash)
                    images_to_keep.append(image_path)
            except Exception as e:
                logger.error(f"Error processing image {image_path} for duplicate removal: {e}")

        self.images = images_to_keep
        
        if duplicates_removed_count > 0:
            return f"图库【{self.name}】已移除 {duplicates_removed_count} 张重复图片。"
        else:
            return f"图库【{self.name}】中没有发现重复图片。"

    def need_compress(self, image_bytes: bytes) -> bool:
        """
        判断图片是否需要压缩 (根据配置)
        """
        if not self.compress:
            return False
        
        # This logic is handled in auto_collect_image or wherever image is added
        # For now, just return self.compress status
        return self.compress

    def get_info(self) -> dict:
        """
        获取图库信息
        """
        info = self.__dict__.copy()
        info.pop("images")
        return info

    def __str__(self) -> str:
        return f"图库名: {self.name}, 路径: {self.path}, 图片数量: {len(self.images)}" 