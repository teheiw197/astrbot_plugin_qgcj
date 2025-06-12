import random
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .config import GameConfig

class GameSystem:
    def __init__(self, data_dir: str, config: GameConfig):
        self.data_dir = data_dir
        self.config = config
        self.wallet_file = os.path.join(data_dir, "wallet.json")
        self.lottery_file = os.path.join(data_dir, "lottery.json")
        self.load_data()
        
    def load_data(self):
        """加载数据"""
        # 钱包数据
        if os.path.exists(self.wallet_file):
            with open(self.wallet_file, 'r', encoding='utf-8') as f:
                self.wallets = json.load(f)
        else:
            self.wallets = {}
            
        # 抽奖数据
        if os.path.exists(self.lottery_file):
            with open(self.lottery_file, 'r', encoding='utf-8') as f:
                self.lottery_data = json.load(f)
        else:
            self.lottery_data = {
                "last_draw": {},
                "prizes": self.config.lottery_prizes
            }
            
    def save_data(self):
        """保存数据"""
        with open(self.wallet_file, 'w', encoding='utf-8') as f:
            json.dump(self.wallets, f, ensure_ascii=False, indent=2)
            
        with open(self.lottery_file, 'w', encoding='utf-8') as f:
            json.dump(self.lottery_data, f, ensure_ascii=False, indent=2)
            
    def get_balance(self, user_id: str) -> int:
        """获取用户余额"""
        if user_id not in self.wallets:
            self.wallets[user_id] = self.config.initial_balance
            self.save_data()
        return self.wallets[user_id]
        
    def add_balance(self, user_id: str, amount: int) -> int:
        """增加用户余额"""
        if user_id not in self.wallets:
            self.wallets[user_id] = self.config.initial_balance
            
        new_balance = self.wallets[user_id] + amount
        if new_balance > self.config.max_balance:
            new_balance = self.config.max_balance
            
        self.wallets[user_id] = new_balance
        self.save_data()
        return self.wallets[user_id]
        
    def deduct_balance(self, user_id: str, amount: int) -> bool:
        """扣除用户余额"""
        if user_id not in self.wallets:
            self.wallets[user_id] = self.config.initial_balance
            
        if self.wallets[user_id] < amount:
            return False
            
        self.wallets[user_id] -= amount
        self.save_data()
        return True
        
    def gamble(self, user_id: str, amount: int, win_rate: float) -> tuple[bool, int]:
        """赌博游戏"""
        if not self.deduct_balance(user_id, amount):
            return False, 0
            
        if random.random() < win_rate:
            win_amount = amount * 2
            self.add_balance(user_id, win_amount)
            return True, win_amount
        return False, 0
        
    def can_draw_lottery(self, user_id: str) -> bool:
        """检查用户是否可以抽奖"""
        last_draw = self.lottery_data["last_draw"].get(user_id)
        if not last_draw:
            return True
            
        last_time = datetime.fromisoformat(last_draw)
        return datetime.now() - last_time > timedelta(seconds=self.config.lottery_cooldown)
        
    def draw_lottery(self, user_id: str) -> Optional[str]:
        """抽奖"""
        if not self.can_draw_lottery(user_id):
            return None
            
        rand = random.random()
        current_prob = 0
        
        for prize_id, prize in self.lottery_data["prizes"].items():
            current_prob += prize["probability"]
            if rand <= current_prob:
                self.lottery_data["last_draw"][user_id] = datetime.now().isoformat()
                self.add_balance(user_id, prize["reward"])
                self.save_data()
                return prize["name"]
                
        return "谢谢参与"
        
    def set_prize(self, prize_id: str, name: str, probability: float, reward: int):
        """设置奖品"""
        self.lottery_data["prizes"][prize_id] = {
            "name": name,
            "probability": probability,
            "reward": reward
        }
        self.save_data()
        
    def get_prizes(self) -> Dict[str, Dict]:
        """获取所有奖品"""
        return self.lottery_data["prizes"] 