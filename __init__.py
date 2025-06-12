import asyncio
import os
import json
import random
import re
from typing import Callable, Awaitable, Dict, List, Optional, Union

# AstrBot imports
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.provider.entities import LLMResponse
import astrbot.core.message.components as Comp
from PIL import Image # For auto_collect_image to get image info

# Local imports
from .game import GameSystem
from .entertainment import EntertainmentSystem
from .tools import ToolsSystem
from .config import QGCJConfig, load_config, save_config

# Gallery plugin core modules
from .core.gallery import Gallery
from .core.gallery_manager import GalleryManager
from .core.parse import get_image_info, check_image_name, check_gallery_name
from .utils import compress_image, download_file, get_nickname, get_image

# Constants for Gallery Plugin
GALLERIES_INFO_FILE = os.path.join(os.path.dirname(__file__), "data", "plugins_data", "qgcj_gallery_info.json")

@register("qgcj", "YourName", "群管理插件与图库功能", "1.0.0")
class QGCJPlugin(Star):
    def __init__(self, context: Context, config: QGCJConfig):
        super().__init__(context)
        self.context = context # Store context for future use, e.g., context.get_config()
        self.config = config

        # Create data directory (already handled by main script likely, but good to ensure)
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize systems
        self.game_system = GameSystem(self.data_dir, self.config.game)
        self.entertainment_system = EntertainmentSystem(self.config.entertainment, self.config.api_keys)
        self.tools_system = ToolsSystem(self.data_dir, self.config.tools)

        # Initialize GalleryManager
        galleries_dirs = [os.path.abspath(os.path.join(os.path.dirname(__file__), dir_path)) for dir_path in self.config.gallery_main.galleries_dirs]
        
        # Ensure the default gallery path exists
        if not galleries_dirs:
            logger.error("No gallery directories configured. Please check your config.json.")
            # Fallback to a default temp directory if no directories are configured
            default_temp_gallery_path = os.path.join(self.data_dir, "temp_galleries")
            os.makedirs(default_temp_gallery_path, exist_ok=True)
            galleries_dirs = [default_temp_gallery_path]
            
        default_gallery_info = {
            "name": "local",
            "path": os.path.join(galleries_dirs[0], "local"),
            "creator_id": "127001",
            "creator_name": "local",
            "capacity": self.config.add_default.default_capacity,
            "compress": self.config.add_default.default_compress,
            "duplicate": self.config.add_default.default_duplicate,
            "fuzzy": self.config.add_default.default_fuzzy,
        }
        self.gallery_manager = GalleryManager(
            galleries_dirs, GALLERIES_INFO_FILE, default_gallery_info
        )
        asyncio.create_task(self.gallery_manager.initialize())

    async def _creat_gallery(self, event: AstrMessageEvent, name: str) -> Gallery:
        # Helper function from original plugin, made into a method
        gallery_info = self.gallery_manager.default_gallery_info.copy()
        # Ensure path is within configured galleries_dirs, using the first one
        gallery_info["path"] = os.path.join(self.gallery_manager.galleries_dirs[0], name)
        gallery_info["name"] = name # Ensure name is updated in info
        gallery_info["creator_id"] = event.get_sender_id()
        gallery_info["creator_name"] = event.get_sender_name() # This seems like a bug in original as it overwrites creator_id, but keeping original behavior
        gallery = await self.gallery_manager.load_gallery(gallery_info)
        return gallery

    async def _get_args(self, event: AstrMessageEvent, cmd: str) -> Dict[str, List[str]]:
        # This is a complex helper function from the original plugin.
        # It parses arguments from the message, handling different formats.
        # Original `_get_args` uses regex and other parsing logic. For AstrBot's filter.command,
        # arguments are generally passed directly to the handler functions. 
        # This method is primarily used by gallery commands that parse complex arguments (e.g., names, labels, urls).
        # For now, a simplified version. Will need to be refined as commands are added.
        
        # Placeholder implementation for now, should be replaced with actual parsing logic from original _get_args
        # if message_text.startswith(cmd):
        #     remaining_text = message_text[len(cmd):].strip()
        #     parts = remaining_text.split()
        #     # This is highly simplified and will likely need to be much more robust
        #     if len(parts) > 0:
        #         args["names"].append(parts[0])
        #     if len(parts) > 1:
        #         args["labels"].append(parts[1])
        
        # For now, returning dummy data or relying on filter.command to parse. 
        # The original _get_args was very complex (lines 645-707 in main.py). 
        # I'll re-evaluate its necessity or precise re-implementation when integrating specific commands that use it.
        logger.warning(f"_get_args called for command: {cmd}. This helper might need full implementation from original plugin.")
        return {}
    
    def _filter_text(self, text: str) -> str:
        # This helper function was in original plugin to remove wake_prefix
        # Since AstrBot's filter.command handles prefix removal, this might not be strictly needed for commands.
        # But if it's used for general message parsing (e.g., auto_collect), it might be.
        # The original `wake_prefix` was taken from `context.get_config()`, which we don't have direct access to here.
        # Assuming `filter.command` handles prefixes, we can skip this for now or get `wake_prefix` from `self.context.get_config()`
        # For now, returning text as is.
        return text

    async def _get_image(self, event: AstrMessageEvent, reply: bool = True) -> bytes | None:
        # Helper function to get image bytes from event
        return await get_image(event, reply)


    # Help command (QGCJ original)
    @filter.command("帮助", alias={"help"})
    async def help_command(self, event: AstrMessageEvent, *args, **kwargs):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        # Optional: Print args and kwargs for debugging if needed
        # logger.debug(f"Help command received args: {args}, kwargs: {kwargs}")
        help_text = """
游戏功能：
- 赌博 [金额]：进行赌博游戏
- 抽奖：参与抽奖活动

娱乐功能：
- 音乐 [关键词]：搜索音乐
- 笑话：获取随机笑话
- 天气 [城市]：查询天气信息

工具功能：
- 提醒 [内容] [时间]：设置提醒
- 提醒列表：查看提醒列表
- 密码 [长度]：生成随机密码
- 计算 [表达式]：计算数学表达式

图库功能：
- 存图 [图库名] [标签]：存储图片到图库 (回复图片消息)
- 删图 [图库名] [图片名]：删除图库中的图片
- 查看 [图库名]：查看图库中的随机图片
- 图库列表：查看所有图库
- 图库详情 [图库名]：查看图库详细信息
- 添加匹配词 [精准|模糊] [图库名] [关键词]：为图库添加匹配词
- 删除匹配词 [精准|模糊] [图库名] [关键词]：删除图库的匹配词
- 精准匹配词：查看所有精准匹配词
- 模糊匹配词：查看所有模糊匹配词
- 图库帮助：图库功能帮助
"""
        yield event.plain_result(help_text)

    # Game commands (QGCJ original)
    @filter.command("赌博")
    async def gamble_command(self, event: AstrMessageEvent, amount: int):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        try:
            if amount < self.config.game.min_bet:
                yield event.plain_result(f"最小下注金额为 {self.config.game.min_bet} 金币！")
                return
            if amount > self.config.game.max_bet:
                yield event.plain_result(f"最大下注金额为 {self.config.game.max_bet} 金币！")
                return
            
            user_id = event.get_sender_id()
            success, win_amount = self.game_system.gamble(user_id, amount, self.config.game.win_rate)
            
            if success:
                yield event.plain_result(f"恭喜你赢了 {win_amount} 金币！")
            else:
                yield event.plain_result(f"很遗憾，你输了 {amount} 金币。")
        except ValueError:
            yield event.plain_result("请输入正确的金额！")

    @filter.command("抽奖")
    async def lottery_command(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        
        user_id = event.get_sender_id()
        if not self.game_system.can_draw_lottery(user_id):
            yield event.plain_result("你今天的抽奖次数已用完，明天再来吧！")
            return
            
        prize = self.game_system.draw_lottery(user_id)
        yield event.plain_result(f"恭喜你获得：{prize}！")

    # Entertainment commands (QGCJ original)
    @filter.command("音乐")
    async def music_command(self, event: AstrMessageEvent, keyword: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        
        if not keyword:
            yield event.plain_result("请输入要搜索的音乐！")
            return
            
        result = await self.entertainment_system.get_music(keyword)
        if result:
            yield event.plain_result(
                f"歌曲：{result['name']}\n"
                f"歌手：{result['artist']}\n"
                f"链接：{result['url']}"
            )
        else:
            yield event.plain_result("未找到相关音乐！")

    @filter.command("笑话")
    async def joke_command(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
            
        joke_text = self.entertainment_system.get_joke()
        yield event.plain_result(joke_text)

    @filter.command("天气")
    async def weather_command(self, event: AstrMessageEvent, city: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
            
        if not city:
            yield event.plain_result("请输入城市名称！")
            return
            
        result = await self.entertainment_system.get_weather(city)
        if result:
            yield event.plain_result(
                f"城市：{result['city']}\n"
                f"温度：{result['temp']}°C\n"
                f"天气：{result['condition']}\n"
                f"湿度：{result['humidity']}% \n"
                f"风速：{result['wind']}km/h"
            )
        else:
            yield event.plain_result("获取天气信息失败！")

    # Tools commands (QGCJ original)
    @filter.command("提醒")
    async def reminder_command(self, event: AstrMessageEvent, content: str, time: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
            
        user_id = event.get_sender_id()
        
        if self.tools_system.add_reminder(user_id, content, time):
            yield event.plain_result("提醒设置成功！")
        else:
            yield event.plain_result("提醒设置失败，请检查时间格式或提醒数量是否达到上限！")

    @filter.command("提醒列表")
    async def reminder_list_command(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
            
        user_id = event.get_sender_id()
        reminders = self.tools_system.get_reminders(user_id)
        
        if not reminders:
            yield event.plain_result("你还没有设置任何提醒！")
            return
            
        msg = "你的提醒列表：\n"
        for i, reminder in enumerate(reminders):
            msg += f"{i+1}. {reminder['content']} - {reminder['time']}\n"
        yield event.plain_result(msg)

    @filter.command("密码")
    async def password_command(self, event: AstrMessageEvent, length: int):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
            
        if length < self.config.tools.password_min_length or length > self.config.tools.password_max_length:
            yield event.plain_result(f"密码长度必须在{self.config.tools.password_min_length}-{self.config.tools.password_max_length}之间！")
            return
            
        pwd = self.tools_system.generate_password(length, self.config.tools.password_require_special)
        yield event.plain_result(f"生成的密码：{pwd}")

    @filter.command("计算")
    async def calculate_command(self, event: AstrMessageEvent, expression: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
            
        result = self.tools_system.calculate(expression)
        
        if result is not None:
            yield event.plain_result(f"计算结果：{result}")
        else:
            yield event.plain_result("计算表达式无效！")

    # Gallery Plugin Integration

    # auto_collect_image (original @filter.event_message_type(EventMessageType.ALL))
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def auto_collect_image(self, event: AstrMessageEvent):
        if not self.config.enabled or not self.config.auto_collect.enable_collect:
            return

        # Group chat whitelist
        group_id = event.get_group_id()
        if self.config.auto_collect.white_list and group_id and group_id not in self.config.auto_collect.white_list:
            return

        # Respond to messages containing a single image
        chain = event.get_messages()
        if len(chain) == 1 and isinstance(chain[0], Comp.Image):
            gallery_name = "auto_collected" # Default gallery for auto-collection
            label = "auto" # Default label

            gallery = self.gallery_manager.get_gallery(gallery_name)
            if not gallery:
                # Create a default gallery if it doesn't exist
                gallery = await self._creat_gallery(event, name=gallery_name)
                if not gallery:
                    logger.error(f"Failed to create auto-collect gallery: {gallery_name}")
                    return

            if image_bytes := await self._get_image(event, reply=False): # reply=False as it's the current message
                # If configured to "not collect images that need compression" and current image needs compression
                if not self.config.auto_collect.collect_compressed_img and gallery.compress:
                    try:
                        from io import BytesIO
                        img = Image.open(BytesIO(image_bytes))
                        width, height = img.size
                        # Assume need_compress based on original size vs compress_size
                        if max(width, height) > self.config.add_default.compress_size:
                            if not self.config.auto_collect.collect_compressed_img:
                                # If it would be compressed and we don't collect compressed, then skip.
                                logger.info(f"Skipping auto-collection: image needs compression and collect_compressed_img is false for gallery {gallery_name}.")
                                # If gallery is empty, delete it
                                if not os.listdir(gallery.path):
                                     await self.gallery_manager.delete_gallery(gallery_name)
                                return # Skip collection
                    except Exception as e:
                        logger.warning(f"Error checking image for compression during auto-collect: {e}")
                        # Continue, don't block collection due to this error

                result = gallery.add_image(image=image_bytes, label=label)
                logger.info(f"自动收集图片：{result}")
            else:
                logger.warning("Failed to get image bytes for auto-collection.")

    # handle_match - Exact/Fuzzy matching for user messages (original @filter.event_message_type(EventMessageType.ALL))
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_match(self, event: AstrMessageEvent):
        if not self.config.enabled:
            return

        text = event.message_str.strip()
        if not (self.config.user_trigger.user_min_msg_len <= len(text) <= self.config.user_trigger.user_max_msg_len):
            return

        image_path = await self._match(
            text, self.config.user_trigger.user_exact_prob, self.config.user_trigger.user_fuzzy_prob
        )
        if image_path:
            yield event.image_result(str(image_path))


    # _match helper function (from original plugin, made into a method)
    async def _match(self, text: str, exact_prob: float, fuzzy_prob: float) -> str | None:
        image_path = None
        # Exact match
        if text in self.gallery_manager.exact_keywords:
            if random.random() < exact_prob:
                # Original had `get_gallery_by_attribute(name=text)`, which was likely incorrect.
                # It should find galleries that contain `text` as an exact keyword.
                galleries_with_exact_keyword = self.gallery_manager.get_gallery_by_keyword(text)
                if galleries_with_exact_keyword:
                    # Filter to only galleries where `text` is an exact keyword
                    filtered_galleries = [g for g in galleries_with_exact_keyword if text in g.exact_keywords]
                    if filtered_galleries:
                        gallery = random.choice(filtered_galleries)
                        image_path = gallery.get_random_image()
                        logger.info(f"匹配到图片（精准）：{image_path}")
        
        if not image_path: # Only try fuzzy if exact match not found
            # Fuzzy match
            for keyword in self.gallery_manager.fuzzy_keywords:
                if keyword in text: # If fuzzy keyword is a substring of the message text
                    if random.random() < fuzzy_prob:
                        galleries_with_fuzzy_keyword = self.gallery_manager.get_gallery_by_keyword(keyword)
                        if galleries_with_fuzzy_keyword:
                            # Filter to only galleries where `keyword` is a fuzzy keyword
                            filtered_galleries = [g for g in galleries_with_fuzzy_keyword if keyword in g.fuzzy_keywords]
                            if filtered_galleries:
                                gallery = random.choice(filtered_galleries)
                                image_path = gallery.get_random_image()
                                logger.info(f"匹配到图片（模糊）：{image_path}")
                                break # Stop after first fuzzy match
        return image_path

    # on_llm_response hook (original @filter.on_llm_response())
    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        if not self.config.enabled:
            return
            
        chain = resp.result_chain.chain
        text = ""
        if len(chain) == 1 and isinstance(chain[0], Comp.Plain):
            text = chain[0].text
        
        if not (self.config.llm_trigger.llm_min_msg_len <= len(text) <= self.config.llm_trigger.llm_max_msg_len):
            return
            
        image_path = await self._match(
            text, self.config.llm_trigger.llm_exact_prob, self.config.llm_trigger.llm_fuzzy_prob
        )
        if image_path:
            await event.send(event.image_result(image_path))

    # Gallery Commands (integrating gradually)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("精准匹配词", alias={"exact_keywords"})
    async def list_accurate_keywords(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        reply = f"【精准匹配词】：\n{str(self.gallery_manager.exact_keywords)}"
        yield event.plain_result(reply)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("模糊匹配词", alias={"fuzzy_keywords"})
    async def list_fuzzy_keywords(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        reply = f"【模糊匹配词】：\n{str(self.gallery_manager.fuzzy_keywords)}"
        yield event.plain_result(reply)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("模糊匹配", alias={"set_fuzzy_match"})
    async def fuzzy_match_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        
        result = await self.gallery_manager.set_fuzzy(gallery_name, fuzzy=True)
        yield event.plain_result(result)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("精准匹配", alias={"set_exact_match"})
    async def accurate_match_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        
        result = await self.gallery_manager.set_fuzzy(gallery_name, fuzzy=False)
        yield event.plain_result(result)

    @filter.command("存图")
    async def add_image_command(self, event: AstrMessageEvent, gallery_name: str, label: str = ""):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.config.permission.allow_add and not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return
        
        if not check_gallery_name(gallery_name):
            yield event.plain_result("图库名包含非法字符，请重新输入。")
            return

        if len(gallery_name) > self.config.add_default.label_max_length or len(label) > self.config.add_default.label_max_length:
            yield event.plain_result(f"图库名或标签的长度不能超过{self.config.add_default.label_max_length}个字符。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            gallery = await self._creat_gallery(event, name=gallery_name)
            if not gallery:
                yield event.plain_result(f"创建图库【{gallery_name}】失败。")
                return

        image_bytes = await self._get_image(event, reply=True)
        if image_bytes:
            if gallery.compress:
                image_bytes = await compress_image(image_bytes, self.config.add_default.compress_size)

            result_message = gallery.add_image(image=image_bytes, label=label)
            yield event.plain_result(result_message)
        else:
            yield event.plain_result("请回复或发送图片！")

    @filter.command("删图")
    async def delete_image_command(self, event: AstrMessageEvent, gallery_name: str, image_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        
        if not self.config.permission.allow_del and not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.del_image(image_name)
        yield event.plain_result(result_message)

    @filter.command("查看")
    async def view_image_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.config.permission.allow_view and not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return
            
        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        try:
            image_path = gallery.get_random_image()
            yield event.image_result(image_path)
        except IndexError:
            yield event.plain_result(f"图库【{gallery_name}】中没有图片。")

    @filter.command("图库列表")
    async def view_all_galleries_command(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.config.permission.allow_view and not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        galleries = self.gallery_manager.get_all_galleries()
        if not galleries:
            yield event.plain_result("目前没有可用的图库。")
            return
        
        msg = "图库列表：\n"
        for g in galleries:
            msg += f"- {g.name} ({len(g.images)}张图片)\n"
        yield event.plain_result(msg)

    @filter.command("图库详情")
    async def gallery_details_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.config.permission.allow_view and not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return
            
        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        info = gallery.get_info()
        msg = f"图库【{info['name']}】详情：\n"
        msg += f"路径：{info['path']}\n"
        msg += f"创建者：{info['creator_name']} ({info['creator_id']})\n"
        msg += f"容量：{info['capacity']}\n"
        msg += f"图片数量：{len(gallery.images)}\n"
        msg += f"压缩：{'开启' if info['compress'] else '关闭'}\n"
        msg += f"去重：{'开启' if info['duplicate'] else '关闭'}\n"
        msg += f"模糊匹配模式：{'开启' if info['fuzzy'] else '关闭'}\n"
        msg += f"精准匹配词：{info['exact_keywords']}\n"
        msg += f"模糊匹配词：{info['fuzzy_keywords']}"
        yield event.plain_result(msg)

    @filter.command("添加匹配词")
    async def add_keyword_command(self, event: AstrMessageEvent, match_type: str, gallery_name: str, keyword: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        is_fuzzy = False
        if match_type == "精准":
            is_fuzzy = False
        elif match_type == "模糊":
            is_fuzzy = True
        else:
            yield event.plain_result("匹配类型无效，请输入'精准'或'模糊'。")
            return

        result_message = gallery.add_keyword(keyword, is_fuzzy)
        self.gallery_manager._save_galleries_info() # Save updated keywords
        self.gallery_manager._update_keywords()
        yield event.plain_result(result_message)

    @filter.command("删除匹配词")
    async def delete_keyword_command(self, event: AstrMessageEvent, match_type: str, gallery_name: str, keyword: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        is_fuzzy = False
        if match_type == "精准":
            is_fuzzy = False
        elif match_type == "模糊":
            is_fuzzy = True
        else:
            yield event.plain_result("匹配类型无效，请输入'精准'或'模糊'。")
            return

        result_message = gallery.del_keyword(keyword, is_fuzzy)
        self.gallery_manager._save_galleries_info() # Save updated keywords
        self.gallery_manager._update_keywords()
        yield event.plain_result(result_message)

    @filter.command("设置容量")
    async def set_capacity_command(self, event: AstrMessageEvent, gallery_name: str, capacity: int):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.set_capacity(capacity)
        self.gallery_manager._save_galleries_info()
        yield event.plain_result(result_message)

    @filter.command("打开压缩")
    async def open_compress_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.set_compress(True)
        self.gallery_manager._save_galleries_info()
        yield event.plain_result(result_message)

    @filter.command("关闭压缩")
    async def close_compress_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.set_compress(False)
        self.gallery_manager._save_galleries_info()
        yield event.plain_result(result_message)

    @filter.command("打开去重")
    async def open_duplicate_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.set_duplicate(True)
        self.gallery_manager._save_galleries_info()
        yield event.plain_result(result_message)

    @filter.command("关闭去重")
    async def close_duplicate_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.set_duplicate(False)
        self.gallery_manager._save_galleries_info()
        yield event.plain_result(result_message)

    @filter.command("去重")
    async def remove_duplicates_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        result_message = gallery.remove_duplicates()
        self.gallery_manager._save_galleries_info() # Save changes after removing duplicates
        yield event.plain_result(result_message)

    @filter.command("路径")
    async def find_path_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.config.permission.allow_view and not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return
            
        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        yield event.plain_result(f"图库【{gallery_name}】的路径是：{gallery.path}")

    @filter.command("图库帮助")
    async def gallery_help_command(self, event: AstrMessageEvent, *args, **kwargs):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return
        help_text = """
图库功能命令：
- 存图 [图库名] [标签]：存储图片到图库 (回复图片消息或直接发送图片)
- 删图 [图库名] [图片名]：删除图库中的图片
- 查看 [图库名]：查看图库中的随机图片
- 图库列表：查看所有图库
- 图库详情 [图库名]：查看图库详细信息
- 添加匹配词 [精准|模糊] [图库名] [关键词]：为图库添加匹配词
- 删除匹配词 [精准|模糊] [图库名] [关键词]：删除图库的匹配词
- 精准匹配词：查看所有精准匹配词
- 模糊匹配词：查看所有模糊匹配词
- 设置容量 [图库名] [容量]：设置图库的最大容量
- 打开压缩 [图库名]：开启图库图片压缩功能
- 关闭压缩 [图库名]：关闭图库图片压缩功能
- 打开去重 [图库名]：开启图库图片去重功能
- 关闭去重 [图库名]：关闭图库图片去重功能
- 去重 [图库名]：移除图库中的重复图片
- 路径 [图库名]：获取图库的存储路径
- 上传图库 [图库名]：上传整个图库为压缩包 (仅支持aiocqhttp)
- 下载图库 [图库名]：下载图库的压缩包
- 解析：解析图片信息 (回复图片消息或直接发送图片)
"""
        yield event.plain_result(help_text)

    # Upload/Download Gallery Commands
    @filter.command("上传图库")
    async def upload_gallery_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        # This command originally was for aiocqhttp. It requires aiocqhttp specific event and client.
        # Need to check if current platform adapter is aiocqhttp and cast the event.
        if event.get_platform_name() != "aiocqhttp":
            yield event.plain_result("上传图库功能目前仅支持 Aiocqhttp 平台。")
            return

        from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
        if not isinstance(event, AiocqhttpMessageEvent):
            yield event.plain_result("内部错误：事件类型不匹配 AiocqhttpMessageEvent。")
            return

        try:
            # Compress the gallery into a zip file first
            import shutil
            zip_file_path = os.path.join(self.data_dir, f"{gallery_name}.zip")
            shutil.make_archive(zip_file_path.replace(".zip", ""), 'zip', gallery.path)
            
            # Upload the zip file via aiocqhttp client API
            ret = await event.bot.upload_group_file(group_id=event.get_group_id(), file=zip_file_path, name=f"{gallery_name}.zip")
            if ret.get("retcode") == 0: # Check if upload was successful
                yield event.plain_result(f"图库【{gallery_name}】已成功上传。")
            else:
                logger.error(f"Upload failed for gallery {gallery_name}: {ret}")
                yield event.plain_result(f"上传图库【{gallery_name}】失败。错误信息：{ret.get("msg", "未知错误")}")
            
            os.remove(zip_file_path) # Clean up the zip file

        except Exception as e:
            logger.error(f"上传图库【{gallery_name}】时发生错误: {e}")
            yield event.plain_result(f"上传图库【{gallery_name}】时发生错误：{e}")

    @filter.command("下载图库")
    async def download_gallery_command(self, event: AstrMessageEvent, gallery_name: str):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        gallery = self.gallery_manager.get_gallery(gallery_name)
        if not gallery:
            yield event.plain_result(f"未找到图库【{gallery_name}】。")
            return

        try:
            # Compress the gallery into a zip file first
            import shutil
            zip_file_name = f"{gallery_name}.zip"
            zip_file_path = os.path.join(self.data_dir, zip_file_name)
            shutil.make_archive(zip_file_path.replace(".zip", ""), 'zip', gallery.path)
            
            # Send the zip file as a message (if platform supports sending local files)
            # This part assumes AstrBot's platform adapter can send local files directly.
            # For some platforms (like QQ Official), sending local files might not be straightforward.
            # For simplicity, we assume event.file_result works for local files.
            yield event.file_result(zip_file_path, name=zip_file_name)
            yield event.plain_result(f"图库【{gallery_name}】已打包发送。")
            
            os.remove(zip_file_path) # Clean up the zip file

        except Exception as e:
            logger.error(f"下载图库【{gallery_name}】时发生错误: {e}")
            yield event.plain_result(f"下载图库【{gallery_name}】时发生错误：{e}")

    @filter.command("解析")
    async def parse_command(self, event: AstrMessageEvent):
        if not self.config.enabled:
            yield event.plain_result("插件当前已禁用")
            return

        if not self.context.get_user_is_admin(event.get_sender_id()):
            yield event.plain_result("你没有权限使用此功能。")
            return

        # This command in the original plugin seems to be for parsing information from an image.
        # The original implementation used _get_args to get the image URL/path, then get_image_info.
        # We will adapt it to directly get image bytes from the event.
        image_bytes = await self._get_image(event, reply=True)
        if not image_bytes:
            yield event.plain_result("请回复或发送图片以便解析。")
            return
        
        try:
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes))
            width, height = img.size
            size = len(image_bytes) # Use length of bytes as approximate size, true size needs file on disk
            
            msg = f"图片信息：\n宽度：{width}px\n高度：{height}px\n大小：{size / 1024:.2f} KB"
            yield event.plain_result(msg)

        except Exception as e:
            logger.error(f"解析图片信息失败: {e}")
            yield event.plain_result(f"解析图片信息失败: {e}") 