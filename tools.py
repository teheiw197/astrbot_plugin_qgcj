import json
import os
import re
import random
import string
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class ToolsSystem:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.reminder_file = os.path.join(data_dir, "reminders.json")
        self.load_data()
        
    def load_data(self):
        """加载数据"""
        if os.path.exists(self.reminder_file):
            with open(self.reminder_file, 'r', encoding='utf-8') as f:
                self.reminders = json.load(f)
        else:
            self.reminders = {}
            
    def save_data(self):
        """保存数据"""
        with open(self.reminder_file, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)
            
    def add_reminder(self, user_id: str, content: str, time: str) -> bool:
        """添加提醒"""
        try:
            reminder_time = datetime.fromisoformat(time)
            if reminder_time < datetime.now():
                return False
                
            if user_id not in self.reminders:
                self.reminders[user_id] = []
                
            self.reminders[user_id].append({
                "content": content,
                "time": time
            })
            self.save_data()
            return True
        except:
            return False
            
    def get_reminders(self, user_id: str) -> List[Dict]:
        """获取提醒列表"""
        return self.reminders.get(user_id, [])
        
    def remove_reminder(self, user_id: str, index: int) -> bool:
        """删除提醒"""
        if user_id not in self.reminders or index >= len(self.reminders[user_id]):
            return False
            
        self.reminders[user_id].pop(index)
        self.save_data()
        return True
        
    def generate_password(self, length: int = 12, include_special: bool = True) -> str:
        """生成随机密码"""
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += string.punctuation
            
        while True:
            password = ''.join(random.choice(chars) for _ in range(length))
            if (any(c.islower() for c in password) and
                any(c.isupper() for c in password) and
                any(c.isdigit() for c in password) and
                (not include_special or any(c in string.punctuation for c in password))):
                return password
                
    def calculate(self, expression: str) -> Optional[float]:
        """计算表达式"""
        try:
            # 移除所有空格
            expression = expression.replace(" ", "")
            
            # 检查表达式是否安全
            if not re.match(r'^[0-9+\-*/().]+$', expression):
                return None
                
            return eval(expression)
        except:
            return None
            
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """货币转换"""
        # 这里应该调用汇率API，这里仅作示例
        rates = {
            "USD": 1.0,
            "CNY": 6.5,
            "EUR": 0.85,
            "JPY": 110.0
        }
        
        if from_currency not in rates or to_currency not in rates:
            return None
            
        return amount * rates[to_currency] / rates[from_currency]
        
    def format_time(self, timestamp: float) -> str:
        """格式化时间戳"""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
    def parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            return None
            
    def get_time_diff(self, time1: str, time2: str) -> Optional[timedelta]:
        """计算时间差"""
        t1 = self.parse_time(time1)
        t2 = self.parse_time(time2)
        
        if t1 and t2:
            return abs(t1 - t2)
        return None 