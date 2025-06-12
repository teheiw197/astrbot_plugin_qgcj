import aiohttp
import json
from typing import Optional, Dict, List
import random
from datetime import datetime, timedelta
from .config import EntertainmentConfig

class EntertainmentSystem:
    def __init__(self, config: EntertainmentConfig, api_keys: Dict[str, str]):
        self.config = config
        self.api_keys = api_keys
        self.jokes = [
            "为什么程序员总是分不清万圣节和圣诞节？因为 Oct 31 == Dec 25",
            "有一天，我在调试代码，突然发现一个bug，然后我就把它修好了。第二天，我发现那个bug又回来了，而且带着它的朋友们。",
            "为什么程序员不喜欢户外活动？因为有太多的bug。",
            "有一天，我问我的代码：'你爱我吗？' 它说：'404 Not Found'。",
            "为什么程序员总是分不清现实和虚拟？因为他们的生活就是0和1。"
        ]
        self.last_joke_update = datetime.now()
        self.weather_cache = {}
        
    async def get_music(self, keyword: str, source: str = None) -> Optional[Dict]:
        """获取音乐信息"""
        if source is None:
            source = random.choice(self.config.music_sources)
            
        if source == "netease":
            return await self._get_netease_music(keyword)
        elif source == "qq":
            return await self._get_qq_music(keyword)
        return None
        
    async def _get_netease_music(self, keyword: str) -> Optional[Dict]:
        """获取网易云音乐"""
        if not self.api_keys.get("netease_music"):
            return None
            
        async with aiohttp.ClientSession() as session:
            try:
                url = f"http://music.163.com/api/search/get/web?type=1&s={keyword}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data["result"]["songs"]:
                            song = data["result"]["songs"][0]
                            return {
                                "name": song["name"],
                                "artist": song["artists"][0]["name"],
                                "url": f"http://music.163.com/#/song?id={song['id']}"
                            }
            except Exception as e:
                print(f"获取网易云音乐失败: {e}")
        return None
        
    async def _get_qq_music(self, keyword: str) -> Optional[Dict]:
        """获取QQ音乐"""
        if not self.api_keys.get("qq_music"):
            return None
            
        async with aiohttp.ClientSession() as session:
            try:
                url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?w={keyword}&format=json"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data["data"]["song"]["list"]:
                            song = data["data"]["song"]["list"][0]
                            return {
                                "name": song["songname"],
                                "artist": song["singer"][0]["name"],
                                "url": f"https://y.qq.com/n/ryqq/songDetail/{song['songmid']}"
                            }
            except Exception as e:
                print(f"获取QQ音乐失败: {e}")
        return None
        
    def get_joke(self) -> str:
        """获取笑话"""
        # 检查是否需要更新笑话列表
        if datetime.now() - self.last_joke_update > timedelta(seconds=self.config.joke_update_interval):
            # 这里可以添加从API获取新笑话的逻辑
            self.last_joke_update = datetime.now()
            
        return random.choice(self.jokes)
        
    async def get_weather(self, city: str) -> Optional[Dict]:
        """获取天气信息"""
        if not self.api_keys.get("weather"):
            return None
            
        # 检查缓存
        if city in self.weather_cache:
            cache_time, cache_data = self.weather_cache[city]
            if datetime.now() - cache_time < timedelta(seconds=self.config.weather_cache_time):
                return cache_data
                
        async with aiohttp.ClientSession() as session:
            try:
                url = f"http://api.weatherapi.com/v1/current.json?key={self.api_keys['weather']}&q={city}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = {
                            "city": data["location"]["name"],
                            "temp": data["current"]["temp_c"],
                            "condition": data["current"]["condition"]["text"],
                            "humidity": data["current"]["humidity"],
                            "wind": data["current"]["wind_kph"]
                        }
                        # 更新缓存
                        self.weather_cache[city] = (datetime.now(), result)
                        return result
            except Exception as e:
                print(f"获取天气信息失败: {e}")
        return None
        
    async def translate(self, text: str, target_lang: str = "zh") -> Optional[str]:
        """翻译文本"""
        if not self.api_keys.get("translate"):
            return None
            
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://translation.googleapis.com/language/translate/v2"
                params = {
                    "key": self.api_keys["translate"],
                    "q": text,
                    "target": target_lang
                }
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["data"]["translations"][0]["translatedText"]
            except Exception as e:
                print(f"翻译失败: {e}")
        return None
        
    async def get_news(self, category: str = "general") -> Optional[List[Dict]]:
        """获取新闻"""
        if not self.api_keys.get("news"):
            return None
            
        if category not in self.config.news_categories:
            category = "general"
            
        async with aiohttp.ClientSession() as session:
            try:
                url = f"https://newsapi.org/v2/top-headlines?country=cn&category={category}&apiKey={self.api_keys['news']}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [{
                            "title": article["title"],
                            "description": article["description"],
                            "url": article["url"]
                        } for article in data["articles"][:self.config.max_news_count]]
            except Exception as e:
                print(f"获取新闻失败: {e}")
        return None 