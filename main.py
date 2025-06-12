from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import json
import os
from datetime import datetime, timedelta
import asyncio
import aiohttp
import random
import re
from typing import List, Dict, Optional
import traceback

class PluginError(Exception):
    """插件基础异常类"""
    pass

class ConfigError(PluginError):
    """配置相关异常"""
    pass

class APIError(PluginError):
    """API调用相关异常"""
    pass

@register(
    name="qgcj",
    author="特嘿工作室",
    desc="一个功能丰富的群管理插件，包含游戏系统、娱乐功能、群管理等功能",
    version="1.0.0",
    repo="https://github.com/your-repo/qgcj"
)
class QGCJPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.data_dir = os.path.join("data", "qgcj")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化数据文件
        self.group_data_file = os.path.join(self.data_dir, "group_data.json")
        self.user_data_file = os.path.join(self.data_dir, "user_data.json")
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.log_file = os.path.join(self.data_dir, "plugin.log")
        
        # 初始化日志
        self.setup_logging()
        
        # 初始化数据文件
        self.init_data_files()
        
        # 加载配置
        self.config = config
        self.load_config()
        
        # 启动定时任务
        asyncio.create_task(self.periodic_tasks())
        
        logger.info("QGCJ插件初始化完成")

    def setup_logging(self):
        """设置日志记录"""
        import logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('qgcj')

    def log_error(self, error: Exception, context: str = ""):
        """记录错误日志"""
        error_msg = f"错误发生在{context}: {str(error)}\n{traceback.format_exc()}"
        self.logger.error(error_msg)
        logger.error(error_msg)

    def init_data_files(self):
        """初始化数据文件"""
        try:
            if not os.path.exists(self.config_file):
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            
            if not os.path.exists(self.group_data_file):
                with open(self.group_data_file, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            
            if not os.path.exists(self.user_data_file):
                with open(self.user_data_file, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_error(e, "初始化数据文件")
            raise ConfigError("初始化数据文件失败")

    def load_config(self):
        """加载配置"""
        # API密钥
        self.api_keys = self.config.get('api_keys', {})
        
        # 管理员设置
        admin_settings = self.config.get('admin_settings', {})
        self.super_admins = set(admin_settings.get('super_admin', '').split(','))
        self.group_admins = set(admin_settings.get('group_admin', '').split(','))
        
        # 群设置
        group_settings = self.config.get('group_settings', {})
        self.enabled_groups = set(group_settings.get('enabled_groups', '').split(','))
        self.welcome_message = group_settings.get('welcome_message', '欢迎 {user_name} 加入 {group_name}！')
        
        # 自动审核设置
        auto_review = group_settings.get('auto_review', {})
        self.auto_review_enabled = auto_review.get('enabled', False)
        self.min_level = auto_review.get('min_level', 1)
        self.min_age = auto_review.get('min_age', 30)
        
        # 游戏设置
        game_settings = self.config.get('game_settings', {})
        gamble_settings = game_settings.get('gamble', {})
        self.min_bet = gamble_settings.get('min_bet', 10)
        self.max_bet = gamble_settings.get('max_bet', 1000)
        self.win_rate = gamble_settings.get('win_rate', 0.5)
        
        # 安全设置
        security_settings = self.config.get('security_settings', {})
        keyword_filter = security_settings.get('keyword_filter', {})
        self.keyword_filter_enabled = keyword_filter.get('enabled', True)
        self.sensitive_words = set(keyword_filter.get('words', '').split('\n'))
        self.keyword_action = keyword_filter.get('action', 'warn')
        self.warning_threshold = security_settings.get('warning_threshold', 3)
        
        # 用户警告记录
        self.user_warnings = {}

    def is_admin(self, user_id: str) -> bool:
        """检查用户是否是管理员"""
        return user_id in self.super_admins or user_id in self.group_admins
        
    def is_super_admin(self, user_id: str) -> bool:
        """检查用户是否是超级管理员"""
        return user_id in self.super_admins
        
    def is_group_enabled(self, group_id: str) -> bool:
        """检查群是否启用插件"""
        return group_id in self.enabled_groups
        
    def check_sensitive_words(self, text: str) -> Optional[str]:
        """检查文本是否包含敏感词"""
        if not self.keyword_filter_enabled:
            return None
        for word in self.sensitive_words:
            if word and word in text:
                return word
        return None
        
    def handle_sensitive_word(self, event: AstrMessageEvent, word: str):
        """处理敏感词"""
        user_id = event.get_sender_id()
        if user_id not in self.user_warnings:
            self.user_warnings[user_id] = 0
            
        self.user_warnings[user_id] += 1
        
        if self.user_warnings[user_id] >= self.warning_threshold:
            if self.keyword_action == 'kick':
                yield event.kick_result()
            elif self.keyword_action == 'ban':
                yield event.ban_result()
        else:
            yield event.plain_result(f"警告：检测到敏感词 '{word}'，这是第 {self.user_warnings[user_id]} 次警告")
            
    @filter.command("reload")
    async def reload_config(self, event: AstrMessageEvent):
        """重载配置"""
        if not self.is_super_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        self.load_config()
        yield event.plain_result("配置已重载")
        
    @filter.command("setwelcome")
    async def set_welcome(self, event: AstrMessageEvent, message: str):
        """设置群欢迎语"""
        if not self.is_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        self.config['group_settings']['welcome_message'] = message
        self.config.save_config()
        self.welcome_message = message
        yield event.plain_result("欢迎语已更新")
        
    @filter.command("addadmin")
    async def add_admin(self, event: AstrMessageEvent, user_id: str):
        """添加管理员"""
        if not self.is_super_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        self.group_admins.add(user_id)
        self.config['admin_settings']['group_admin'] = ','.join(self.group_admins)
        self.config.save_config()
        yield event.plain_result(f"已添加管理员 {user_id}")
        
    @filter.command("deladmin")
    async def del_admin(self, event: AstrMessageEvent, user_id: str):
        """删除管理员"""
        if not self.is_super_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        if user_id in self.group_admins:
            self.group_admins.remove(user_id)
            self.config['admin_settings']['group_admin'] = ','.join(self.group_admins)
            self.config.save_config()
            yield event.plain_result(f"已删除管理员 {user_id}")
        else:
            yield event.plain_result("该用户不是管理员")
            
    @filter.command("enablegroup")
    async def enable_group(self, event: AstrMessageEvent, group_id: str):
        """启用群"""
        if not self.is_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        self.enabled_groups.add(group_id)
        self.config['group_settings']['enabled_groups'] = ','.join(self.enabled_groups)
        self.config.save_config()
        yield event.plain_result(f"已启用群 {group_id}")
        
    @filter.command("disablegroup")
    async def disable_group(self, event: AstrMessageEvent, group_id: str):
        """禁用群"""
        if not self.is_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        if group_id in self.enabled_groups:
            self.enabled_groups.remove(group_id)
            self.config['group_settings']['enabled_groups'] = ','.join(self.enabled_groups)
            self.config.save_config()
            yield event.plain_result(f"已禁用群 {group_id}")
        else:
            yield event.plain_result("该群未启用")
            
    @filter.command("addword")
    async def add_sensitive_word(self, event: AstrMessageEvent, word: str):
        """添加敏感词"""
        if not self.is_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        self.sensitive_words.add(word)
        self.config['security_settings']['keyword_filter']['words'] = '\n'.join(self.sensitive_words)
        self.config.save_config()
        yield event.plain_result(f"已添加敏感词 {word}")
        
    @filter.command("delword")
    async def del_sensitive_word(self, event: AstrMessageEvent, word: str):
        """删除敏感词"""
        if not self.is_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        if word in self.sensitive_words:
            self.sensitive_words.remove(word)
            self.config['security_settings']['keyword_filter']['words'] = '\n'.join(self.sensitive_words)
            self.config.save_config()
            yield event.plain_result(f"已删除敏感词 {word}")
        else:
            yield event.plain_result("该敏感词不存在")
            
    @filter.command("setaction")
    async def set_keyword_action(self, event: AstrMessageEvent, action: str):
        """设置敏感词触发动作"""
        if not self.is_admin(event.get_sender_id()):
            yield event.plain_result("权限不足")
            return
            
        if action not in ['warn', 'kick', 'ban']:
            yield event.plain_result("无效的动作，可选值：warn、kick、ban")
            return
            
        self.keyword_action = action
        self.config['security_settings']['keyword_filter']['action'] = action
        self.config.save_config()
        yield event.plain_result(f"已设置敏感词触发动作为 {action}")
        
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """消息处理"""
        # 检查群是否启用
        group_id = event.get_group_id()
        if group_id and not self.is_group_enabled(group_id):
            return
            
        # 检查敏感词
        text = event.message_str
        sensitive_word = self.check_sensitive_words(text)
        if sensitive_word:
            yield from self.handle_sensitive_word(event, sensitive_word)
            
    async def terminate(self):
        """插件终止时保存配置"""
        self.config.save_config()

    async def check_api_key(self, api_name: str) -> bool:
        """检查API密钥是否配置"""
        api_config = self.config.get(f"{api_name}_api", {})
        if not api_config or not api_config.get("api_key"):
            self.logger.warning(f"{api_name} API密钥未配置")
            return False
        return True

    async def make_api_request(self, api_name: str, endpoint: str, method: str = "GET", **kwargs) -> dict:
        """发送API请求"""
        if not await self.check_api_key(api_name):
            raise APIError(f"{api_name} API未配置")

        api_config = self.config.get(f"{api_name}_api", {})
        base_url = api_config.get("base_url")
        api_key = api_config.get("api_key")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(f"{base_url}/{endpoint}", headers=headers, params=kwargs) as resp:
                        if resp.status != 200:
                            raise APIError(f"API请求失败: {resp.status}")
                        return await resp.json()
                else:
                    async with session.post(f"{base_url}/{endpoint}", headers=headers, json=kwargs) as resp:
                        if resp.status != 200:
                            raise APIError(f"API请求失败: {resp.status}")
                        return await resp.json()
        except Exception as e:
            self.log_error(e, f"API请求 {api_name}")
            raise APIError(f"API请求失败: {str(e)}")

    async def periodic_tasks(self):
        """定时任务"""
        while True:
            try:
                # 检查签到重置
                await self.check_sign_in_reset()
                # 检查游戏冷却
                await self.check_game_cooldown()
                # 检查群统计
                await self.update_group_stats()
                # 检查新成员审核
                await self.check_new_members()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.log_error(e, "定时任务")
                await asyncio.sleep(60)

    async def check_sign_in_reset(self):
        """检查签到重置"""
        try:
            user_data = self.load_data(self.user_data_file)
            now = datetime.now()
            for user_id, data in user_data.items():
                if "last_sign_in" in data:
                    last_sign_in = datetime.fromisoformat(data["last_sign_in"])
                    if (now - last_sign_in).days >= 1:
                        data["can_sign_in"] = True
            self.save_data(self.user_data_file, user_data)
        except Exception as e:
            self.log_error(e, "检查签到重置")

    async def check_game_cooldown(self):
        """检查游戏冷却"""
        try:
            user_data = self.load_data(self.user_data_file)
            now = datetime.now()
            for user_id, data in user_data.items():
                if "game_cooldown" in data:
                    cooldown_time = datetime.fromisoformat(data["game_cooldown"])
                    if now >= cooldown_time:
                        data["can_play_game"] = True
                        del data["game_cooldown"]
            self.save_data(self.user_data_file, user_data)
        except Exception as e:
            self.log_error(e, "检查游戏冷却")

    async def update_group_stats(self):
        """更新群统计信息"""
        try:
            group_data = self.load_data(self.group_data_file)
            for group_id in group_data:
                # 这里需要根据具体平台实现获取群成员信息的功能
                pass
        except Exception as e:
            self.log_error(e, "更新群统计")

    async def check_new_members(self):
        """检查新成员"""
        if not self.config.get("auto_review", {}).get("enabled", False):
            return
            
        try:
            group_data = self.load_data(self.group_data_file)
            for group_id, data in group_data.items():
                if "pending_members" in data:
                    for member_id in data["pending_members"]:
                        await self.review_new_member(group_id, member_id)
        except Exception as e:
            self.log_error(e, "检查新成员")

    async def review_new_member(self, group_id: str, member_id: str):
        """审核新成员"""
        try:
            # 这里需要根据具体平台实现审核功能
            pass
        except Exception as e:
            self.log_error(e, f"审核新成员 {member_id}")

    @filter.command("help")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """群管理插件使用说明：
1. 基础功能：
   /help - 显示此帮助信息
   /welcome - 设置群欢迎语
   /ban - 禁言成员
   /unban - 解除禁言
   /kick - 踢出成员
   /mute - 全体禁言
   /unmute - 解除全体禁言
   /notice - 发布群公告
   /admin - 设置管理员
   /unadmin - 取消管理员

2. 游戏系统：
   /sign - 每日签到
   /wallet - 查看钱包
   /gamble - 赌博游戏
   /guess - 猜数字游戏
   /fight - 对战游戏
   /lottery - 抽奖系统

3. 群管理：
   /warn - 警告成员
   /mute - 禁言成员
   /kick - 踢出成员
   /ban - 封禁成员
   /unban - 解除封禁
   /notice - 发布公告

4. 娱乐功能：
   /music - 点歌系统
   /joke - 讲笑话
   /weather - 天气查询
   /translate - 翻译功能
   /news - 新闻资讯"""
        yield event.plain_result(help_text)

    @filter.command("sign")
    async def sign_command(self, event: AstrMessageEvent):
        """每日签到"""
        user_id = event.get_sender_id()
        user_data = self.load_data(self.user_data_file)
        
        if user_id not in user_data:
            user_data[user_id] = {"coins": 0, "sign_in_days": 0}
        
        if not user_data[user_id].get("can_sign_in", True):
            yield event.plain_result("你今天已经签到过了，明天再来吧！")
            return
        
        # 计算签到奖励
        sign_in_days = user_data[user_id].get("sign_in_days", 0) + 1
        coins = random.randint(10, 50) * (1 + sign_in_days // 7)  # 每7天额外奖励
        
        # 更新用户数据
        user_data[user_id].update({
            "coins": user_data[user_id].get("coins", 0) + coins,
            "sign_in_days": sign_in_days,
            "last_sign_in": datetime.now().isoformat(),
            "can_sign_in": False
        })
        
        self.save_data(self.user_data_file, user_data)
        yield event.plain_result(f"签到成功！获得 {coins} 金币\n当前金币：{user_data[user_id]['coins']}\n连续签到：{sign_in_days} 天")

    @filter.command("wallet")
    async def wallet_command(self, event: AstrMessageEvent):
        """查看钱包"""
        user_id = event.get_sender_id()
        user_data = self.load_data(self.user_data_file)
        
        if user_id not in user_data:
            user_data[user_id] = {"coins": 0, "sign_in_days": 0}
            self.save_data(self.user_data_file, user_data)
        
        coins = user_data[user_id].get("coins", 0)
        sign_in_days = user_data[user_id].get("sign_in_days", 0)
        
        yield event.plain_result(f"钱包信息：\n金币：{coins}\n连续签到：{sign_in_days} 天")

    @filter.command("gamble")
    async def gamble_command(self, event: AstrMessageEvent, amount: int = 0):
        """赌博游戏"""
        if amount <= 0:
            yield event.plain_result("请输入正确的赌注金额！")
            return
        
        user_id = event.get_sender_id()
        user_data = self.load_data(self.user_data_file)
        
        if user_id not in user_data or user_data[user_id].get("coins", 0) < amount:
            yield event.plain_result("你的金币不足！")
            return
        
        if not user_data[user_id].get("can_play_game", True):
            yield event.plain_result("游戏冷却中，请稍后再试！")
            return
        
        # 赌博逻辑
        win = random.random() < 0.4  # 40% 胜率
        if win:
            coins = amount * 2
            user_data[user_id]["coins"] += amount
            result = f"恭喜你赢了 {amount} 金币！"
        else:
            user_data[user_id]["coins"] -= amount
            result = f"很遗憾，你输了 {amount} 金币！"
        
        # 设置游戏冷却
        user_data[user_id]["can_play_game"] = False
        user_data[user_id]["game_cooldown"] = (datetime.now() + timedelta(minutes=5)).isoformat()
        
        self.save_data(self.user_data_file, user_data)
        yield event.plain_result(f"{result}\n当前金币：{user_data[user_id]['coins']}")

    @filter.command("guess")
    async def guess_command(self, event: AstrMessageEvent):
        """猜数字游戏"""
        user_id = event.get_sender_id()
        user_data = self.load_data(self.user_data_file)
        
        if not user_data[user_id].get("can_play_game", True):
            yield event.plain_result("游戏冷却中，请稍后再试！")
            return
        
        # 生成随机数
        number = random.randint(1, 100)
        user_data[user_id]["current_game"] = {
            "type": "guess",
            "number": number,
            "attempts": 0
        }
        
        self.save_data(self.user_data_file, user_data)
        yield event.plain_result("我已经想好了一个1-100之间的数字，请猜一猜！")

    @filter.command("fight")
    async def fight_command(self, event: AstrMessageEvent, target_id: str = ""):
        """对战游戏"""
        if not target_id:
            yield event.plain_result("请指定对战目标！")
            return
        
        user_id = event.get_sender_id()
        user_data = self.load_data(self.user_data_file)
        
        if not user_data[user_id].get("can_play_game", True):
            yield event.plain_result("游戏冷却中，请稍后再试！")
            return
        
        if target_id not in user_data:
            yield event.plain_result("目标用户不存在！")
            return
        
        # 对战逻辑
        user_power = random.randint(1, 100)
        target_power = random.randint(1, 100)
        
        if user_power > target_power:
            coins = random.randint(10, 50)
            user_data[user_id]["coins"] = user_data[user_id].get("coins", 0) + coins
            result = f"你赢了！获得 {coins} 金币"
        else:
            result = "你输了！"
        
        # 设置游戏冷却
        user_data[user_id]["can_play_game"] = False
        user_data[user_id]["game_cooldown"] = (datetime.now() + timedelta(minutes=5)).isoformat()
        
        self.save_data(self.user_data_file, user_data)
        yield event.plain_result(f"{result}\n你的战力：{user_power}\n对方战力：{target_power}")

    @filter.command("lottery")
    async def lottery_command(self, event: AstrMessageEvent):
        """抽奖系统"""
        user_id = event.get_sender_id()
        user_data = self.load_data(self.user_data_file)
        
        if not user_data[user_id].get("can_play_game", True):
            yield event.plain_result("抽奖冷却中，请稍后再试！")
            return
        
        # 抽奖逻辑
        prizes = [
            (0.01, 1000, "特等奖"),
            (0.05, 500, "一等奖"),
            (0.1, 200, "二等奖"),
            (0.2, 100, "三等奖"),
            (0.64, 50, "安慰奖")
        ]
        
        rand = random.random()
        current_prob = 0
        for prob, coins, name in prizes:
            current_prob += prob
            if rand <= current_prob:
                user_data[user_id]["coins"] = user_data[user_id].get("coins", 0) + coins
                result = f"恭喜获得{name}！奖励 {coins} 金币"
                break
        
        # 设置抽奖冷却
        user_data[user_id]["can_play_game"] = False
        user_data[user_id]["game_cooldown"] = (datetime.now() + timedelta(minutes=30)).isoformat()
        
        self.save_data(self.user_data_file, user_data)
        yield event.plain_result(f"{result}\n当前金币：{user_data[user_id]['coins']}")

    @filter.command("music")
    async def music_command(self, event: AstrMessageEvent, song_name: str = ""):
        """点歌系统"""
        if not song_name:
            yield event.plain_result("请输入要搜索的歌曲名称！")
            return

        async with aiohttp.ClientSession() as session:
            try:
                # 这里需要实现具体的音乐API调用
                # 示例使用网易云音乐API
                api_url = self.config.get("music_api", {}).get("netease")
                if not api_url:
                    yield event.plain_result("音乐API未配置！")
                    return

                async with session.get(f"{api_url}/search", params={"keyword": song_name}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("songs"):
                            song = data["songs"][0]
                            yield event.plain_result(f"找到歌曲：{song['name']} - {song['artist']}\n{song['url']}")
                        else:
                            yield event.plain_result("未找到相关歌曲！")
                    else:
                        yield event.plain_result("搜索歌曲失败，请稍后重试！")
            except Exception as e:
                logger.error(f"点歌失败: {str(e)}")
                yield event.plain_result("点歌失败，请稍后重试！")

    @filter.command("joke")
    async def joke_command(self, event: AstrMessageEvent):
        """讲笑话"""
        jokes = [
            "为什么程序员总是分不清万圣节和圣诞节？因为 Oct 31 == Dec 25",
            "有一天，我在调试代码，突然发现一个bug，然后我就把它修好了。第二天，我发现那个bug又回来了，而且带着它的朋友们。",
            "为什么程序员不喜欢户外活动？因为有太多的bug。",
            "一个程序员走进一家咖啡店，点了一杯咖啡。服务员问：'要加糖吗？'程序员说：'不，谢谢，我已经够甜了。'",
            "为什么程序员总是分不清左右？因为他们总是用二进制思考。"
        ]
        yield event.plain_result(random.choice(jokes))

    @filter.command("weather")
    async def weather_command(self, event: AstrMessageEvent, city: str = ""):
        """天气查询"""
        if not city:
            yield event.plain_result("请输入要查询的城市名称！")
            return

        async with aiohttp.ClientSession() as session:
            try:
                api_url = self.config.get("weather_api")
                if not api_url:
                    yield event.plain_result("天气API未配置！")
                    return

                async with session.get(f"{api_url}/weather", params={"city": city}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        weather_info = f"城市：{city}\n温度：{data['temperature']}°C\n天气：{data['weather']}\n湿度：{data['humidity']}%"
                        yield event.plain_result(weather_info)
                    else:
                        yield event.plain_result("获取天气信息失败，请稍后重试！")
            except Exception as e:
                logger.error(f"天气查询失败: {str(e)}")
                yield event.plain_result("天气查询失败，请稍后重试！")

    @filter.command("translate")
    async def translate_command(self, event: AstrMessageEvent, text: str = "", target_lang: str = "en"):
        """翻译功能"""
        if not text:
            yield event.plain_result("请输入要翻译的文本！")
            return

        async with aiohttp.ClientSession() as session:
            try:
                api_url = self.config.get("translate_api")
                if not api_url:
                    yield event.plain_result("翻译API未配置！")
                    return

                async with session.post(api_url, json={
                    "text": text,
                    "target_lang": target_lang
                }) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        yield event.plain_result(f"翻译结果：{data['translated_text']}")
                    else:
                        yield event.plain_result("翻译失败，请稍后重试！")
            except Exception as e:
                logger.error(f"翻译失败: {str(e)}")
                yield event.plain_result("翻译失败，请稍后重试！")

    @filter.command("news")
    async def news_command(self, event: AstrMessageEvent, category: str = "general"):
        """新闻资讯"""
        async with aiohttp.ClientSession() as session:
            try:
                api_url = self.config.get("news_api")
                if not api_url:
                    yield event.plain_result("新闻API未配置！")
                    return

                async with session.get(f"{api_url}/news", params={"category": category}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        news_list = data.get("news", [])[:5]  # 只显示前5条新闻
                        if news_list:
                            result = "最新新闻：\n"
                            for i, news in enumerate(news_list, 1):
                                result += f"{i}. {news['title']}\n"
                            yield event.plain_result(result)
                        else:
                            yield event.plain_result("暂无相关新闻！")
                    else:
                        yield event.plain_result("获取新闻失败，请稍后重试！")
            except Exception as e:
                logger.error(f"获取新闻失败: {str(e)}")
                yield event.plain_result("获取新闻失败，请稍后重试！")

    @filter.command("setprefix")
    async def set_prefix_command(self, event: AstrMessageEvent, prefix: str = ""):
        """设置命令前缀"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能设置命令前缀！")
            return

        if not prefix:
            yield event.plain_result("请输入新的命令前缀！")
            return

        self.config["command_prefix"] = prefix
        self.config.save_config()
        yield event.plain_result(f"命令前缀已设置为：{prefix}")

    @filter.command("setreview")
    async def set_review_command(self, event: AstrMessageEvent, action: str = ""):
        """设置自动审核规则"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能设置审核规则！")
            return

        if not action or action not in ["warn", "kick", "ban"]:
            yield event.plain_result("请指定审核动作：warn（警告）、kick（踢出）或 ban（封禁）")
            return

        self.config["auto_review"]["action"] = action
        self.config.save_config()
        yield event.plain_result(f"自动审核动作已设置为：{action}")

    @filter.command("addkeyword")
    async def add_keyword_command(self, event: AstrMessageEvent, keyword: str = ""):
        """添加关键词"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能添加关键词！")
            return

        if not keyword:
            yield event.plain_result("请输入要添加的关键词！")
            return

        if "keywords" not in self.config["auto_review"]:
            self.config["auto_review"]["keywords"] = []
        
        if keyword not in self.config["auto_review"]["keywords"]:
            self.config["auto_review"]["keywords"].append(keyword)
            self.config.save_config()
            yield event.plain_result(f"关键词 {keyword} 添加成功！")
        else:
            yield event.plain_result("该关键词已存在！")

    @filter.command("delkeyword")
    async def del_keyword_command(self, event: AstrMessageEvent, keyword: str = ""):
        """删除关键词"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能删除关键词！")
            return

        if not keyword:
            yield event.plain_result("请输入要删除的关键词！")
            return

        if keyword in self.config["auto_review"]["keywords"]:
            self.config["auto_review"]["keywords"].remove(keyword)
            self.config.save_config()
            yield event.plain_result(f"关键词 {keyword} 删除成功！")
        else:
            yield event.plain_result("该关键词不存在！")

    @filter.command("stats")
    async def stats_command(self, event: AstrMessageEvent):
        """查看群统计"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        group_data = self.load_data(self.group_data_file)
        if group_id not in group_data:
            yield event.plain_result("未找到群组数据！")
            return

        stats = group_data[group_id].get("stats", {})
        result = "群统计信息：\n"
        result += f"总消息数：{stats.get('total_messages', 0)}\n"
        result += f"今日消息数：{stats.get('today_messages', 0)}\n"
        result += f"活跃成员数：{stats.get('active_members', 0)}\n"
        result += f"新成员数：{stats.get('new_members', 0)}\n"
        result += f"退群成员数：{stats.get('left_members', 0)}"
        
        yield event.plain_result(result) 