"""
状态管理模块
负责游戏状态的读写、持久化
"""
import json
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import yaml
import copy


class GameState:
    """游戏状态管理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 状态文件路径
        self.paths = {
            "character": self.data_dir / "character.json",
            "npcs": self.data_dir / "npcs.json",
            "inventory": self.data_dir / "inventory.json",
            "quests": self.data_dir / "quests.json",
            "world": self.data_dir / "world_state.json",
            "story_log": self.data_dir / "story_log.json",
            "relationships": self.data_dir / "relationships.json",
        }

        # 内存缓存
        self._cache: dict[str, Any] = {}
        self._dirty: set[str] = set()  # 标记需要保存的文件

    def load_config(self, config_path: str) -> dict:
        """加载YAML配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_json(self, key: str) -> dict:
        """加载JSON文件"""
        path = self.paths.get(key)
        if not path:
            raise KeyError(f"Unknown state key: {key}")

        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_json(self, key: str, data: dict) -> None:
        """保存JSON文件"""
        path = self.paths.get(key)
        if not path:
            raise KeyError(f"Unknown state key: {key}")

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """获取状态数据"""
        if key not in self._cache:
            self._cache[key] = self._load_json(key)
        return self._cache.get(key, default)

    def set(self, key: str, data: dict) -> None:
        """设置状态数据"""
        self._cache[key] = data
        self._dirty.add(key)

    def update(self, key: str, updates: dict) -> None:
        """更新状态数据（合并）"""
        current = self.get(key, {})
        self._deep_update(current, updates)
        self._dirty.add(key)

    def _deep_update(self, base: dict, updates: dict) -> None:
        """深度合并字典"""
        for k, v in updates.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    def save(self, key: Optional[str] = None) -> None:
        """保存状态到文件"""
        if key:
            if key in self._cache:
                self._save_json(key, self._cache[key])
                self._dirty.discard(key)
        else:
            # 保存所有脏数据
            for k in list(self._dirty):
                if k in self._cache:
                    self._save_json(k, self._cache[k])
            self._dirty.clear()

    def save_all(self) -> None:
        """强制保存所有缓存数据"""
        for key, data in self._cache.items():
            self._save_json(key, data)
        self._dirty.clear()


class Character:
    """角色数据类"""

    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def create_new(cls, name: str, config: dict) -> "Character":
        """创建新角色"""
        # 获取凡人境界的基础属性
        mortal_realm = next(r for r in config['realms'] if r['id'] == 'mortal')

        data = {
            "id": f"player_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "created_at": datetime.now().isoformat(),

            # 境界
            "realm": {
                "id": "mortal",
                "name": "凡人",
                "sub_realm": "未入门",
                "sub_realm_index": 0
            },

            # 经验
            "exp": {
                "current": 0,
                "to_next_level": mortal_realm['exp_to_next'],
                "total": 0
            },

            # 一级属性（可分配点数）
            "primary_attributes": {
                "strength": 10,
                "agility": 10,
                "constitution": 10,
                "spirit": 10,
                "perception": 10,
                "luck": 10
            },

            # 可用属性点
            "attribute_points": 0,

            # 二级属性（计算得出）
            "derived_attributes": {
                "hp": mortal_realm['base_hp'],
                "hp_max": mortal_realm['base_hp'],
                "mp": mortal_realm['base_mp'],
                "mp_max": mortal_realm['base_mp'],
                "attack": mortal_realm['base_attack'],
                "defense": mortal_realm['base_defense'],
                "speed": 100,
                "crit_rate": 0.05,
                "crit_damage": 1.5,
                "dodge_rate": 0.05
            },

            # 五行亲和
            "element_affinity": {
                "metal": 0,
                "wood": 0,
                "water": 0,
                "fire": 0,
                "earth": 0
            },

            # 技能（初始技能在game.py中根据配置添加）
            "skills": [],

            # 装备
            "equipment": {
                "weapon": None,
                "head": None,
                "body": None,
                "legs": None,
                "feet": None,
                "accessory": [None, None],
                "storage": None
            },

            # 功法
            "cultivation_methods": [],

            # Buff/Debuff
            "buffs": [],

            # 状态
            "status": {
                "is_alive": True,
                "is_in_combat": False,
                "is_cultivating": False,
                "current_location": "新手村",
                "current_scene": "新手村"
            },

            # 货币
            "currency": {
                "gold": 100,           # 金币（凡人用）
                "spirit_stones": 0,    # 灵石
                "high_spirit_stones": 0  # 上品灵石
            },

            # 统计
            "statistics": {
                "monsters_killed": 0,
                "quests_completed": 0,
                "deaths": 0,
                "total_damage_dealt": 0,
                "total_damage_taken": 0,
                "breakthroughs": 0
            }
        }

        return cls(data)

    @property
    def name(self) -> str:
        return self.data['name']

    @property
    def realm(self) -> dict:
        return self.data['realm']

    @property
    def hp(self) -> int:
        return self.data['derived_attributes']['hp']

    @hp.setter
    def hp(self, value: int):
        max_hp = self.data['derived_attributes']['hp_max']
        self.data['derived_attributes']['hp'] = max(0, min(value, max_hp))
        if self.data['derived_attributes']['hp'] <= 0:
            self.data['status']['is_alive'] = False

    @property
    def mp(self) -> int:
        return self.data['derived_attributes']['mp']

    @mp.setter
    def mp(self, value: int):
        max_mp = self.data['derived_attributes']['mp_max']
        self.data['derived_attributes']['mp'] = max(0, min(value, max_mp))

    @property
    def is_alive(self) -> bool:
        return self.data['status']['is_alive']

    def add_exp(self, amount: int) -> dict:
        """增加经验值，返回升级信息"""
        result = {
            "exp_gained": amount,
            "leveled_up": False,
            "new_realm": None,
            "new_sub_realm": None
        }

        self.data['exp']['current'] += amount
        self.data['exp']['total'] += amount

        # 检查升级（这里只是标记，实际升级逻辑在rules.py）
        if self.data['exp']['current'] >= self.data['exp']['to_next_level']:
            result['leveled_up'] = True

        return result

    def to_dict(self) -> dict:
        return copy.deepcopy(self.data)

    def get_combat_stats(self) -> dict:
        """获取战斗相关属性"""
        derived = self.data['derived_attributes']
        return {
            "hp": derived['hp'],
            "hp_max": derived['hp_max'],
            "mp": derived['mp'],
            "mp_max": derived['mp_max'],
            "attack": derived['attack'],
            "defense": derived['defense'],
            "speed": derived['speed'],
            "crit_rate": derived['crit_rate'],
            "crit_damage": derived['crit_damage'],
            "dodge_rate": derived['dodge_rate']
        }

    def get_status_summary(self) -> str:
        """获取状态摘要（用于AI上下文）"""
        realm = self.data['realm']
        derived = self.data['derived_attributes']
        status = self.data['status']
        currency = self.data['currency']

        # 位置显示：如果location和scene相同，只显示一个
        location = status['current_location']
        scene = status['current_scene']
        if location == scene:
            location_str = location
        else:
            location_str = f"{location} - {scene}"

        return f"""【{self.name}】
境界：{realm['name']} {realm['sub_realm']}
生命：{derived['hp']}/{derived['hp_max']}
法力：{derived['mp']}/{derived['mp_max']}
攻击：{derived['attack']} | 防御：{derived['defense']} | 速度：{derived['speed']}
位置：{location_str}
金币：{currency['gold']} | 灵石：{currency['spirit_stones']}
"""


class NPC:
    """NPC数据类"""

    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def create(cls,
               npc_id: str,
               name: str,
               npc_type: str,
               realm_id: str = "mortal",
               **kwargs) -> "NPC":
        """创建NPC"""
        data = {
            "id": npc_id,
            "name": name,
            "type": npc_type,  # friendly, hostile, neutral, merchant, quest_giver
            "realm": {
                "id": realm_id,
                "sub_realm_index": 0
            },
            "attributes": kwargs.get("attributes", {}),
            "location": kwargs.get("location", "未知"),
            "dialogue_state": {},
            "inventory": kwargs.get("inventory", []),
            "is_alive": True,
            "respawn_time": kwargs.get("respawn_time"),  # None表示不重生
            "loot_table": kwargs.get("loot_table", []),
            "exp_reward": kwargs.get("exp_reward", 0),
            "description": kwargs.get("description", ""),
            "personality": kwargs.get("personality", ""),  # 用于AI生成对话
        }
        return cls(data)

    def to_dict(self) -> dict:
        return copy.deepcopy(self.data)


class Inventory:
    """物品栏管理"""

    def __init__(self, data: dict):
        self.data = data
        if "items" not in self.data:
            self.data["items"] = []
        if "max_slots" not in self.data:
            self.data["max_slots"] = 50

    def add_item(self, item: dict, count: int = 1) -> bool:
        """添加物品"""
        # 检查是否可堆叠
        if item.get("stackable", False):
            for existing in self.data["items"]:
                if existing["id"] == item["id"]:
                    existing["count"] = existing.get("count", 1) + count
                    return True

        # 检查空间
        if len(self.data["items"]) >= self.data["max_slots"]:
            return False

        new_item = copy.deepcopy(item)
        new_item["count"] = count
        self.data["items"].append(new_item)
        return True

    def remove_item(self, item_id: str, count: int = 1) -> bool:
        """移除物品"""
        for i, item in enumerate(self.data["items"]):
            if item["id"] == item_id:
                if item.get("count", 1) > count:
                    item["count"] -= count
                    return True
                elif item.get("count", 1) == count:
                    self.data["items"].pop(i)
                    return True
                else:
                    return False
        return False

    def get_item(self, item_id: str) -> Optional[dict]:
        """获取物品"""
        for item in self.data["items"]:
            if item["id"] == item_id:
                return item
        return None

    def has_item(self, item_id: str, count: int = 1) -> bool:
        """检查是否拥有足够数量的物品"""
        item = self.get_item(item_id)
        if item:
            return item.get("count", 1) >= count
        return False

    def to_dict(self) -> dict:
        return copy.deepcopy(self.data)


class StoryLog:
    """剧情日志"""

    def __init__(self, data: dict):
        self.data = data
        if "entries" not in self.data:
            self.data["entries"] = []
        if "summaries" not in self.data:
            self.data["summaries"] = []

    def add_entry(self, content: str, entry_type: str = "narrative") -> None:
        """添加剧情条目"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,  # narrative, dialogue, combat, system
            "content": content
        }
        self.data["entries"].append(entry)

        # 保留最近100条详细记录
        if len(self.data["entries"]) > 100:
            # 将旧条目压缩成摘要
            old_entries = self.data["entries"][:50]
            summary = self._create_summary(old_entries)
            self.data["summaries"].append(summary)
            self.data["entries"] = self.data["entries"][50:]

    def _create_summary(self, entries: list) -> dict:
        """创建摘要（简单版本，后续可用AI生成）"""
        return {
            "timestamp": datetime.now().isoformat(),
            "period_start": entries[0]["timestamp"],
            "period_end": entries[-1]["timestamp"],
            "entry_count": len(entries),
            "content": f"[{len(entries)}条记录的摘要，包含主要事件]"
        }

    def get_recent_context(self, count: int = 20) -> str:
        """获取最近的剧情上下文（用于AI）"""
        recent = self.data["entries"][-count:]
        return "\n".join([e["content"] for e in recent])

    def get_full_context(self) -> str:
        """获取完整上下文（摘要 + 详细记录）"""
        parts = []

        # 添加摘要
        for summary in self.data["summaries"]:
            parts.append(f"[历史摘要] {summary['content']}")

        # 添加详细记录
        for entry in self.data["entries"]:
            parts.append(entry["content"])

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return copy.deepcopy(self.data)


class Quest:
    """任务数据类"""

    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def create(cls,
               quest_id: str,
               name: str,
               description: str,
               quest_type: str = "main",
               **kwargs) -> "Quest":
        """创建任务"""
        data = {
            "id": quest_id,
            "name": name,
            "description": description,
            "type": quest_type,  # main, side, daily, hidden
            "status": "available",  # available, active, completed, failed
            "objectives": kwargs.get("objectives", []),
            "rewards": kwargs.get("rewards", {}),
            "prerequisites": kwargs.get("prerequisites", []),
            "giver_npc": kwargs.get("giver_npc"),
            "deadline": kwargs.get("deadline"),
            "progress": {},
            "accepted_at": None,
            "completed_at": None
        }
        return cls(data)

    def accept(self) -> bool:
        """接受任务"""
        if self.data["status"] == "available":
            self.data["status"] = "active"
            self.data["accepted_at"] = datetime.now().isoformat()
            return True
        return False

    def update_progress(self, objective_id: str, progress: int) -> None:
        """更新任务进度"""
        self.data["progress"][objective_id] = progress

    def check_completion(self) -> bool:
        """检查是否完成"""
        for obj in self.data["objectives"]:
            obj_id = obj["id"]
            required = obj.get("required", 1)
            current = self.data["progress"].get(obj_id, 0)
            if current < required:
                return False
        return True

    def complete(self) -> dict:
        """完成任务，返回奖励"""
        if self.check_completion():
            self.data["status"] = "completed"
            self.data["completed_at"] = datetime.now().isoformat()
            return self.data["rewards"]
        return {}

    def to_dict(self) -> dict:
        return copy.deepcopy(self.data)
