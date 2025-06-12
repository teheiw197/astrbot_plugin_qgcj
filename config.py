from typing import Dict, Optional, List
from pydantic import BaseModel, Field

class GameConfig(BaseModel):
    """游戏系统配置"""
    initial_balance: int = Field(default=1000, description="初始金币数量")
    max_balance: int = Field(default=100000, description="最大金币数量")
    min_bet: int = Field(default=10, description="最小下注金额")
    max_bet: int = Field(default=1000, description="最大下注金额")
    win_rate: float = Field(default=0.5, description="赌博获胜概率")
    lottery_cooldown: int = Field(default=86400, description="抽奖冷却时间(秒)")
    lottery_prizes: Dict[str, Dict] = Field(
        default={
            "first": {"name": "一等奖", "probability": 0.01, "reward": 1000},
            "second": {"name": "二等奖", "probability": 0.05, "reward": 500},
            "third": {"name": "三等奖", "probability": 0.1, "reward": 100}
        },
        description="抽奖奖品配置"
    )

class EntertainmentConfig(BaseModel):
    """娱乐系统配置"""
    music_sources: list = Field(default=["netease", "qq"], description="音乐源列表")
    joke_update_interval: int = Field(default=86400, description="笑话更新间隔(秒)")
    weather_cache_time: int = Field(default=3600, description="天气缓存时间(秒)")
    news_categories: list = Field(
        default=["general", "technology", "sports", "entertainment"],
        description="新闻分类列表"
    )
    max_news_count: int = Field(default=5, description="最大新闻条数")

class ToolsConfig(BaseModel):
    """工具系统配置"""
    max_reminders: int = Field(default=10, description="最大提醒数量")
    reminder_check_interval: int = Field(default=60, description="提醒检查间隔(秒)")
    password_min_length: int = Field(default=8, description="密码最小长度")
    password_max_length: int = Field(default=32, description="密码最大长度")
    password_require_special: bool = Field(default=True, description="密码是否需要特殊字符")
    calculator_max_digits: int = Field(default=10, description="计算器最大位数")

class GalleryMainConfig(BaseModel):
    """图库主配置"""
    galleries_dirs: List[str] = Field(default=["temp_galleries"], description="图库总目录列表，第一个路径为默认的总目录，自定义的路径请务必使用绝对路径(不要带双引号)")

class UserTriggerConfig(BaseModel):
    """用户消息触发配置"""
    user_min_msg_len: int = Field(default=1, description="用户消息长度不超过此长度时不进行匹配")
    user_max_msg_len: int = Field(default=30, description="用户消息长度超过此长度时不进行匹配")
    user_exact_prob: float = Field(default=0.9, description="精准匹配用户消息时发送图片的概率")
    user_fuzzy_prob: float = Field(default=0.5, description="模糊匹配用户消息时发送图片的概率")

class LLMTriggerConfig(BaseModel):
    """LLM消息触发配置"""
    llm_min_msg_len: int = Field(default=1, description="LLM消息长度不超过此长度时不响应")
    llm_max_msg_len: int = Field(default=20, description="LLM消息长度超过此长度时不响应")
    llm_exact_prob: float = Field(default=0.9, description="精准匹配LLM消息时发送图片的概率")
    llm_fuzzy_prob: float = Field(default=0.9, description="模糊匹配LLM消息时发送图片的概率")

class AddDefaultConfig(BaseModel):
    """添加图片时默认配置"""
    default_compress: bool = Field(default=True, description="下载图片时是否压缩图片")
    compress_size: int = Field(default=512, description="压缩阈值(单位为像素)，图片在512像素以下时qq以表情包大小显示")
    default_duplicate: bool = Field(default=True, description="添加图片时是否检查并跳过重复图片")
    default_fuzzy: bool = Field(default=False, description="是否默认模糊匹配")
    label_max_length: int = Field(default=4, description="允许的图库名、图片名的最大长度")
    default_capacity: int = Field(default=200, description="图库的默认容量")

class PermissionConfig(BaseModel):
    """权限配置"""
    allow_add: bool = Field(default=False, description="是否允许非管理员向任意图库添加图片")
    allow_del: bool = Field(default=False, description="是否允许非管理员向任意图库删除图片")
    allow_view: bool = Field(default=True, description="是否允许非管理员查看任意图库")

class AutoCollectConfig(BaseModel):
    """自动收集配置"""
    enable_collect: bool = Field(default=False, description="是否启用自动收集功能")
    white_list: List[str] = Field(default=[], description="自动收集的群聊白名单, 留空表示启用所有群聊")
    collect_compressed_img: bool = Field(default=False, description="收集的图片大小限制(MB)")

class QGCJConfig(BaseModel):
    """插件总配置"""
    enabled: bool = Field(default=True, description="是否启用插件")
    game: GameConfig = Field(default_factory=GameConfig, description="游戏系统配置")
    entertainment: EntertainmentConfig = Field(default_factory=EntertainmentConfig, description="娱乐系统配置")
    tools: ToolsConfig = Field(default_factory=ToolsConfig, description="工具系统配置")
    gallery_main: GalleryMainConfig = Field(default_factory=GalleryMainConfig, description="图库主配置")
    user_trigger: UserTriggerConfig = Field(default_factory=UserTriggerConfig, description="用户消息触发配置")
    llm_trigger: LLMTriggerConfig = Field(default_factory=LLMTriggerConfig, description="LLM消息触发配置")
    add_default: AddDefaultConfig = Field(default_factory=AddDefaultConfig, description="添加图片时默认配置")
    permission: PermissionConfig = Field(default_factory=PermissionConfig, description="权限配置")
    auto_collect: AutoCollectConfig = Field(default_factory=AutoCollectConfig, description="自动收集配置")
    api_keys: Dict[str, str] = Field(
        default={
            "netease_music": "",
            "qq_music": "",
            "weather": "",
            "translate": "",
            "news": ""
        },
        description="API密钥配置"
    )
    
    class Config:
        """配置类设置"""
        title = "QGCJ插件配置"
        description = "QGCJ插件的完整配置项"
        arbitrary_types_allowed = True

# 创建默认配置实例
default_config = QGCJConfig()

def load_config(config_dict: Optional[Dict] = None) -> QGCJConfig:
    """加载配置
    
    Args:
        config_dict: 配置字典，如果为None则使用默认配置
        
    Returns:
        QGCJConfig: 配置实例
    """
    if config_dict is None:
        return default_config
    return QGCJConfig(**config_dict)

def save_config(config: QGCJConfig) -> Dict:
    """保存配置
    
    Args:
        config: 配置实例
        
    Returns:
        Dict: 配置字典
    """
    return config.dict() 