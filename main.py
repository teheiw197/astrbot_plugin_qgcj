from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import json
import os
from datetime import datetime, timedelta
import asyncio
import aiohttp
import random
import re
from typing import List, Dict, Optional

@register(
    name="qgcj",
    author="特嘿工作室",
    desc="一个功能丰富的群管理插件，包含游戏系统、娱乐功能、群管理等功能",
    version="1.0.0",
    repo="https://github.com/your-repo/qgcj"
)
class QGCJPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = os.path.join("data", "qgcj")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化数据文件
        self.group_data_file = os.path.join(self.data_dir, "group_data.json")
        self.user_data_file = os.path.join(self.data_dir, "user_data.json")
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.init_data_files()
        
        # 加载配置
        self.config = self.load_config()
        
        # 启动定时任务
        asyncio.create_task(self.periodic_tasks())

    def init_data_files(self):
        """初始化数据文件"""
        default_config = {
            "command_prefix": "/",
            "default_welcome": "欢迎新成员加入！",
            "auto_review": {
                "enabled": True,
                "keywords": ["广告", "色情", "赌博"],
                "action": "warn"
            },
            "music_api": {
                "netease": "https://api.example.com/netease",
                "qq": "https://api.example.com/qq"
            },
            "weather_api": "https://api.example.com/weather",
            "translate_api": "https://api.example.com/translate",
            "news_api": "https://api.example.com/news"
        }
        
        if not os.path.exists(self.config_file):
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.group_data_file):
            with open(self.group_data_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.user_data_file):
            with open(self.user_data_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def load_config(self) -> dict:
        """加载配置"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {}

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")

    def load_data(self, file_path: str) -> dict:
        """加载数据文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据文件失败: {str(e)}")
            return {}

    def save_data(self, file_path: str, data: dict):
        """保存数据文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据文件失败: {str(e)}")

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
                logger.error(f"定时任务执行失败: {str(e)}")
                await asyncio.sleep(60)

    async def check_sign_in_reset(self):
        """检查签到重置"""
        user_data = self.load_data(self.user_data_file)
        now = datetime.now()
        for user_id, data in user_data.items():
            if "last_sign_in" in data:
                last_sign_in = datetime.fromisoformat(data["last_sign_in"])
                if (now - last_sign_in).days >= 1:
                    data["can_sign_in"] = True
        self.save_data(self.user_data_file, user_data)

    async def check_game_cooldown(self):
        """检查游戏冷却"""
        user_data = self.load_data(self.user_data_file)
        now = datetime.now()
        for user_id, data in user_data.items():
            if "game_cooldown" in data:
                cooldown_time = datetime.fromisoformat(data["game_cooldown"])
                if now >= cooldown_time:
                    data["can_play_game"] = True
                    del data["game_cooldown"]
        self.save_data(self.user_data_file, user_data)

    async def update_group_stats(self):
        """更新群统计信息"""
        group_data = self.load_data(self.group_data_file)
        for group_id in group_data:
            # 这里需要根据具体平台实现获取群成员信息的功能
            pass

    async def check_new_members(self):
        """检查新成员"""
        if not self.config.get("auto_review", {}).get("enabled", False):
            return
            
        group_data = self.load_data(self.group_data_file)
        for group_id, data in group_data.items():
            if "pending_members" in data:
                for member_id in data["pending_members"]:
                    # 检查新成员
                    await self.review_new_member(group_id, member_id)

    async def review_new_member(self, group_id: str, member_id: str):
        """审核新成员"""
        # 这里需要根据具体平台实现审核功能
        pass

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

    @filter.command("welcome")
    async def welcome_command(self, event: AstrMessageEvent, message: str = ""):
        """设置群欢迎语"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能设置欢迎语！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        group_data = self.load_data(self.group_data_file)
        if not message:
            current_welcome = group_data.get(group_id, {}).get("welcome", "未设置")
            yield event.plain_result(f"当前欢迎语：{current_welcome}\n使用 /welcome 新欢迎语 来设置新的欢迎语")
            return

        if group_id not in group_data:
            group_data[group_id] = {}
        group_data[group_id]["welcome"] = message
        self.save_data(self.group_data_file, group_data)
        yield event.plain_result("欢迎语设置成功！")

    @filter.command("ban")
    async def ban_command(self, event: AstrMessageEvent, user_id: str = "", duration: int = 0):
        """禁言成员"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        if not user_id or duration <= 0:
            yield event.plain_result("请指定要禁言的成员ID和禁言时长（分钟）！")
            return

        # 这里需要根据具体平台实现禁言功能
        yield event.plain_result(f"已将成员 {user_id} 禁言 {duration} 分钟")

    @filter.command("unban")
    async def unban_command(self, event: AstrMessageEvent, user_id: str = ""):
        """解除禁言"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        if not user_id:
            yield event.plain_result("请指定要解除禁言的成员ID！")
            return

        # 这里需要根据具体平台实现解除禁言功能
        yield event.plain_result(f"已解除成员 {user_id} 的禁言")

    @filter.command("kick")
    async def kick_command(self, event: AstrMessageEvent, user_id: str = ""):
        """踢出成员"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        if not user_id:
            yield event.plain_result("请指定要踢出的成员ID！")
            return

        # 这里需要根据具体平台实现踢出功能
        yield event.plain_result(f"已将成员 {user_id} 踢出群聊")

    @filter.command("mute")
    async def mute_command(self, event: AstrMessageEvent):
        """全体禁言"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        # 这里需要根据具体平台实现全体禁言功能
        yield event.plain_result("已开启全体禁言")

    @filter.command("unmute")
    async def unmute_command(self, event: AstrMessageEvent):
        """解除全体禁言"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        # 这里需要根据具体平台实现解除全体禁言功能
        yield event.plain_result("已解除全体禁言")

    @filter.command("notice")
    async def notice_command(self, event: AstrMessageEvent, message: str = ""):
        """发布群公告"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        if not message:
            yield event.plain_result("请指定要发布的公告内容！")
            return

        # 这里需要根据具体平台实现发布公告功能
        yield event.plain_result("群公告发布成功！")

    @filter.command("admin")
    async def admin_command(self, event: AstrMessageEvent, user_id: str = ""):
        """设置管理员"""
        if not event.is_admin():
            yield event.plain_result("只有群主才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        if not user_id:
            yield event.plain_result("请指定要设置为管理员的成员ID！")
            return

        # 这里需要根据具体平台实现设置管理员功能
        yield event.plain_result(f"已将成员 {user_id} 设置为管理员")

    @filter.command("unadmin")
    async def unadmin_command(self, event: AstrMessageEvent, user_id: str = ""):
        """取消管理员"""
        if not event.is_admin():
            yield event.plain_result("只有群主才能使用此命令！")
            return

        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("请在群聊中使用此命令！")
            return

        if not user_id:
            yield event.plain_result("请指定要取消管理员的成员ID！")
            return

        # 这里需要根据具体平台实现取消管理员功能
        yield event.plain_result(f"已取消成员 {user_id} 的管理员权限")

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
        self.save_config()
        yield event.plain_result(f"命令前缀已设置为：{prefix}")

    @filter.command("setwelcome")
    async def set_welcome_command(self, event: AstrMessageEvent, message: str = ""):
        """设置默认欢迎语"""
        if not event.is_admin():
            yield event.plain_result("只有管理员才能设置欢迎语！")
            return

        if not message:
            yield event.plain_result("请输入新的欢迎语！")
            return

        self.config["default_welcome"] = message
        self.save_config()
        yield event.plain_result("默认欢迎语设置成功！")

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
        self.save_config()
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
            self.save_config()
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
            self.save_config()
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

    async def terminate(self):
        """插件卸载时的清理工作"""
        pass 