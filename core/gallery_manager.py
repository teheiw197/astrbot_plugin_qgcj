import asyncio
import os
import json
from typing import Dict, List, Optional
from data.plugins.qgcj.core.gallery import Gallery
from astrbot import logger


class GalleryManager:
    """
    图库管理器
    """

    def __init__(
        self, galleries_dirs: List[str], gallery_info_file: str, default_gallery_info: dict
    ):
        self.galleries_dirs = galleries_dirs
        self.gallery_info_file = gallery_info_file
        self.default_gallery_info = default_gallery_info
        self.galleries: Dict[str, Gallery] = {}
        self.exact_keywords: List[str] = []
        self.fuzzy_keywords: List[str] = []

    async def initialize(self):
        """
        初始化图库管理器
        """
        if not os.path.exists(os.path.dirname(self.gallery_info_file)):
            os.makedirs(os.path.dirname(self.gallery_info_file))

        if os.path.exists(self.gallery_info_file):
            with open(self.gallery_info_file, "r", encoding="utf-8") as f:
                galleries_info = json.load(f)
        else:
            galleries_info = []

        for gallery_info in galleries_info:
            gallery = await self.load_gallery(gallery_info)
            if gallery:
                self.galleries[gallery.name] = gallery

        # 如果没有图库，创建一个默认图库
        if not self.galleries:
            await self.load_gallery(self.default_gallery_info)

        self._update_keywords()
        logger.info("图库管理器初始化完成！")

    async def load_gallery(self, gallery_info: dict) -> Optional[Gallery]:
        """
        加载图库
        """
        name = gallery_info["name"]
        path = gallery_info["path"]
        if not os.path.exists(path):
            os.makedirs(path)

        try:
            gallery = Gallery(gallery_info)
            self.galleries[name] = gallery
            self._save_galleries_info()
            self._update_keywords()
            logger.info(f"图库【{name}】加载成功！")
            return gallery
        except Exception as e:
            logger.error(f"加载图库【{name}】失败: {e}")
            return None

    async def delete_gallery(self, name: str) -> str:
        """
        删除图库
        """
        if name not in self.galleries:
            return f"图库【{name}】不存在！"

        gallery = self.galleries[name]
        try:
            shutil.rmtree(gallery.path)
            del self.galleries[name]
            self._save_galleries_info()
            self._update_keywords()
            logger.info(f"图库【{name}】删除成功！")
            return f"图库【{name}】已删除。"
        except Exception as e:
            logger.error(f"删除图库【{name}】失败: {e}")
            return f"删除图库【{name}】失败！"

    def get_gallery(self, name: str) -> Optional[Gallery]:
        """
        获取图库
        """
        return self.galleries.get(name)

    def get_all_galleries(self) -> List[Gallery]:
        """
        获取所有图库
        """
        return list(self.galleries.values())

    def _save_galleries_info(self):
        """
        保存图库信息
        """
        with open(self.gallery_info_file, "w", encoding="utf-8") as f:
            json.dump([g.get_info() for g in self.galleries.values()], f, ensure_ascii=False, indent=2)

    def _update_keywords(self):
        """
        更新关键词列表
        """
        self.exact_keywords = []
        self.fuzzy_keywords = []
        for gallery in self.galleries.values():
            self.exact_keywords.extend(gallery.exact_keywords)
            self.fuzzy_keywords.extend(gallery.fuzzy_keywords)

    def get_gallery_by_attribute(self, **kwargs) -> List[Gallery]:
        """
        通过属性获取图库
        """
        result = []
        for gallery in self.galleries.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(gallery, key) or getattr(gallery, key) != value:
                    match = False
                    break
            if match:
                result.append(gallery)
        return result

    def get_gallery_by_keyword(self, keyword: str) -> List[Gallery]:
        """
        通过关键词获取图库
        """
        result = []
        for gallery in self.galleries.values():
            if keyword in gallery.exact_keywords or keyword in gallery.fuzzy_keywords:
                result.append(gallery)
        return result

    async def set_fuzzy(self, name: str, fuzzy: bool) -> str:
        """
        设置图库的模糊匹配模式
        """
        gallery = self.get_gallery(name)
        if not gallery:
            return f"图库【{name}】不存在！"
        res = gallery.set_fuzzy(fuzzy)
        self._save_galleries_info()
        return res 