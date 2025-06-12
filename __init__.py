import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.params import CommandArg
from nonebot import on_command, on_message
import os
import json
from .game import GameSystem
from .entertainment import EntertainmentSystem
from .tools import ToolsSystem
from .config import QGCJConfig, load_config, save_config

# 初始化插件
nonebot.init()

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

# 创建数据目录
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

# 加载配置
config_file = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)
        config = load_config(config_dict)
else:
    config = load_config()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(save_config(config), f, ensure_ascii=False, indent=2)

# 初始化系统
game_system = GameSystem(data_dir, config.game)
entertainment_system = EntertainmentSystem(config.entertainment, config.api_keys)
tools_system = ToolsSystem(data_dir, config.tools)

# 帮助命令
help_cmd = on_command("帮助", rule=to_me(), priority=5)
@help_cmd.handle()
async def handle_help(bot, event, state: T_State):
    if not config.enabled:
        await help_cmd.finish("插件当前已禁用")
        
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
"""
    await help_cmd.finish(help_text)

# 游戏命令
gamble = on_command("赌博", rule=to_me(), priority=5)
@gamble.handle()
async def handle_gamble(bot, event, args: Message = CommandArg()):
    if not config.enabled:
        await gamble.finish("插件当前已禁用")
        
    try:
        amount = int(args.extract_plain_text())
        if amount < config.game.min_bet:
            await gamble.finish(f"最小下注金额为 {config.game.min_bet} 金币！")
        if amount > config.game.max_bet:
            await gamble.finish(f"最大下注金额为 {config.game.max_bet} 金币！")
            
        user_id = str(event.user_id)
        success, win_amount = game_system.gamble(user_id, amount, config.game.win_rate)
        
        if success:
            await gamble.finish(f"恭喜你赢了 {win_amount} 金币！")
        else:
            await gamble.finish(f"很遗憾，你输了 {amount} 金币。")
    except:
        await gamble.finish("请输入正确的金额！")

lottery = on_command("抽奖", rule=to_me(), priority=5)
@lottery.handle()
async def handle_lottery(bot, event):
    if not config.enabled:
        await lottery.finish("插件当前已禁用")
        
    user_id = str(event.user_id)
    if not game_system.can_draw_lottery(user_id):
        await lottery.finish("你今天的抽奖次数已用完，明天再来吧！")
        
    prize = game_system.draw_lottery(user_id)
    await lottery.finish(f"恭喜你获得：{prize}！")

# 娱乐命令
music = on_command("音乐", rule=to_me(), priority=5)
@music.handle()
async def handle_music(bot, event, args: Message = CommandArg()):
    if not config.enabled:
        await music.finish("插件当前已禁用")
        
    keyword = args.extract_plain_text()
    if not keyword:
        await music.finish("请输入要搜索的音乐！")
        
    result = await entertainment_system.get_music(keyword)
    if result:
        await music.finish(
            f"歌曲：{result['name']}\n"
            f"歌手：{result['artist']}\n"
            f"链接：{result['url']}"
        )
    else:
        await music.finish("未找到相关音乐！")

joke = on_command("笑话", rule=to_me(), priority=5)
@joke.handle()
async def handle_joke(bot, event):
    if not config.enabled:
        await joke.finish("插件当前已禁用")
        
    joke_text = entertainment_system.get_joke()
    await joke.finish(joke_text)

weather = on_command("天气", rule=to_me(), priority=5)
@weather.handle()
async def handle_weather(bot, event, args: Message = CommandArg()):
    if not config.enabled:
        await weather.finish("插件当前已禁用")
        
    city = args.extract_plain_text()
    if not city:
        await weather.finish("请输入城市名称！")
        
    result = await entertainment_system.get_weather(city)
    if result:
        await weather.finish(
            f"城市：{result['city']}\n"
            f"温度：{result['temp']}°C\n"
            f"天气：{result['condition']}\n"
            f"湿度：{result['humidity']}%\n"
            f"风速：{result['wind']}km/h"
        )
    else:
        await weather.finish("获取天气信息失败！")

# 工具命令
reminder = on_command("提醒", rule=to_me(), priority=5)
@reminder.handle()
async def handle_reminder(bot, event, args: Message = CommandArg()):
    if not config.enabled:
        await reminder.finish("插件当前已禁用")
        
    try:
        content, time = args.extract_plain_text().split(" ", 1)
        user_id = str(event.user_id)
        
        if tools_system.add_reminder(user_id, content, time):
            await reminder.finish("提醒设置成功！")
        else:
            await reminder.finish("提醒设置失败，请检查时间格式！")
    except:
        await reminder.finish("请使用正确的格式：提醒 内容 时间")

reminder_list = on_command("提醒列表", rule=to_me(), priority=5)
@reminder_list.handle()
async def handle_reminder_list(bot, event):
    if not config.enabled:
        await reminder_list.finish("插件当前已禁用")
        
    user_id = str(event.user_id)
    reminders = tools_system.get_reminders(user_id)
    
    if not reminders:
        await reminder_list.finish("你还没有设置任何提醒！")
        
    msg = "你的提醒列表：\n"
    for i, reminder in enumerate(reminders):
        msg += f"{i+1}. {reminder['content']} - {reminder['time']}\n"
    await reminder_list.finish(msg)

password = on_command("密码", rule=to_me(), priority=5)
@password.handle()
async def handle_password(bot, event, args: Message = CommandArg()):
    if not config.enabled:
        await password.finish("插件当前已禁用")
        
    try:
        length = int(args.extract_plain_text())
        if length < config.tools.password_min_length or length > config.tools.password_max_length:
            await password.finish(f"密码长度必须在{config.tools.password_min_length}-{config.tools.password_max_length}之间！")
            
        pwd = tools_system.generate_password(length, config.tools.password_require_special)
        await password.finish(f"生成的密码：{pwd}")
    except:
        await password.finish("请输入正确的密码长度！")

calculate = on_command("计算", rule=to_me(), priority=5)
@calculate.handle()
async def handle_calculate(bot, event, args: Message = CommandArg()):
    if not config.enabled:
        await calculate.finish("插件当前已禁用")
        
    expression = args.extract_plain_text()
    result = tools_system.calculate(expression)
    
    if result is not None:
        await calculate.finish(f"计算结果：{result}")
    else:
        await calculate.finish("计算表达式无效！")

# 导出插件
__plugin_name__ = "qgcj"
__plugin_usage__ = """
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
""" 