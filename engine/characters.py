"""
角色管理器 - 管理 NPC 的加载、查询、状态

功能：
- 加载 config/npcs.yaml 配置
- 管理 NPC 运行时状态
- 提供场景 NPC 查询
- 为 AI 提供 NPC 上下文
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import yaml
import copy


@dataclass
class NPCScheduleSlot:
    """NPC 日程时段"""
    location: str
    activity: str  # work, meditate, rest, sleep, teach, etc.
    description: str = ""
    interruptible: bool = True


@dataclass
class NPCSchedule:
    """NPC 日程表"""
    morning: NPCScheduleSlot
    afternoon: NPCScheduleSlot
    evening: NPCScheduleSlot
    night: NPCScheduleSlot

    def get_slot(self, slot_name: str) -> Optional[NPCScheduleSlot]:
        """获取指定时段"""
        return getattr(self, slot_name, None)


@dataclass
class Relationship:
    """关系数值"""
    trust: int = 0       # 信任
    affection: int = 0   # 好感
    respect: int = 0     # 敬重
    fear: int = 0        # 畏惧

    def to_dict(self) -> dict:
        return {
            "trust": self.trust,
            "affection": self.affection,
            "respect": self.respect,
            "fear": self.fear
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        return cls(
            trust=data.get("trust", 0),
            affection=data.get("affection", 0),
            respect=data.get("respect", 0),
            fear=data.get("fear", 0)
        )


@dataclass
class NPCData:
    """NPC 数据"""
    id: str
    name: str
    nickname: str = ""
    gender: str = "unknown"
    initial_age: int = 20
    lifespan_base: int = 80

    role: str = ""
    faction: str = ""
    home_location: str = ""

    appearance: str = ""
    personality_core: dict = field(default_factory=dict)
    decision_weights: dict = field(default_factory=dict)

    schedule: Optional[NPCSchedule] = None
    initial_relationship: Relationship = field(default_factory=Relationship)

    # 运行时状态
    current_location: str = ""
    current_activity: str = ""
    is_alive: bool = True

    def get_display_name(self) -> str:
        """获取显示名称"""
        return self.nickname if self.nickname else self.name


class CharacterManager:
    """
    角色管理器

    管理所有 NPC 的配置和运行时状态。
    """

    def __init__(self, config_path: str = "config/npcs.yaml"):
        """
        初始化角色管理器

        Args:
            config_path: NPC 配置文件路径
        """
        self.config_path = Path(config_path)
        self.npcs: Dict[str, NPCData] = {}
        self._relationship_defaults: dict = {}

        self._load_config()

    def _load_config(self):
        """加载配置"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"NPC配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 加载关系默认值
        self._relationship_defaults = config.get('relationship_defaults', {})

        # 加载 NPC
        for npc_id, npc_data in config.get('npcs', {}).items():
            self.npcs[npc_id] = self._parse_npc(npc_id, npc_data)

    def _parse_npc(self, npc_id: str, data: dict) -> NPCData:
        """解析 NPC 数据"""
        # 解析日程
        schedule = None
        if 'schedule' in data:
            sched_data = data['schedule']
            schedule = NPCSchedule(
                morning=self._parse_schedule_slot(sched_data.get('morning', {})),
                afternoon=self._parse_schedule_slot(sched_data.get('afternoon', {})),
                evening=self._parse_schedule_slot(sched_data.get('evening', {})),
                night=self._parse_schedule_slot(sched_data.get('night', {}))
            )

        # 解析初始关系
        rel_data = data.get('initial_relationship', {})
        relationship = Relationship.from_dict(rel_data)

        return NPCData(
            id=data.get('id', npc_id),
            name=data.get('name', npc_id),
            nickname=data.get('nickname', ''),
            gender=data.get('gender', 'unknown'),
            initial_age=data.get('initial_age', 20),
            lifespan_base=data.get('lifespan_base', 80),
            role=data.get('role', ''),
            faction=data.get('faction', ''),
            home_location=data.get('home_location', ''),
            appearance=data.get('appearance', ''),
            personality_core=data.get('personality_core', {}),
            decision_weights=data.get('decision_weights', {}),
            schedule=schedule,
            initial_relationship=relationship,
            current_location=data.get('home_location', ''),
            current_activity='idle',
            is_alive=True
        )

    def _parse_schedule_slot(self, data: dict) -> NPCScheduleSlot:
        """解析日程时段"""
        return NPCScheduleSlot(
            location=data.get('location', ''),
            activity=data.get('activity', 'idle'),
            description=data.get('description', ''),
            interruptible=data.get('interruptible', True)
        )

    def get_npc(self, npc_id: str) -> Optional[NPCData]:
        """获取 NPC"""
        return self.npcs.get(npc_id)

    def get_npc_by_name(self, name: str) -> Optional[NPCData]:
        """按名称/昵称查找 NPC"""
        for npc in self.npcs.values():
            if npc.name == name or npc.nickname == name:
                return npc
        return None

    def all_npcs(self) -> List[NPCData]:
        """获取所有 NPC"""
        return list(self.npcs.values())

    def get_npcs_at_location(self, location_id: str) -> List[NPCData]:
        """获取当前在某地点的 NPC"""
        return [
            npc for npc in self.npcs.values()
            if npc.current_location == location_id and npc.is_alive
        ]

    def get_npcs_by_faction(self, faction: str) -> List[NPCData]:
        """按门派/势力筛选 NPC"""
        return [npc for npc in self.npcs.values() if npc.faction == faction]

    def update_npc_location(self, npc_id: str, location: str) -> bool:
        """更新 NPC 位置"""
        npc = self.npcs.get(npc_id)
        if npc:
            npc.current_location = location
            return True
        return False

    def update_npc_activity(self, npc_id: str, activity: str) -> bool:
        """更新 NPC 活动"""
        npc = self.npcs.get(npc_id)
        if npc:
            npc.current_activity = activity
            return True
        return False

    def build_npc_context(self, npc_id: str) -> dict:
        """
        构建 NPC 上下文（用于 AI）

        Args:
            npc_id: NPC ID

        Returns:
            上下文字典
        """
        npc = self.npcs.get(npc_id)
        if not npc:
            return {}

        # 获取表面性格描述
        surface_traits = npc.personality_core.get('surface', [])
        personality_desc = '；'.join(surface_traits) if surface_traits else '性格不详'

        return {
            "id": npc.id,
            "name": npc.name,
            "nickname": npc.nickname,
            "display_name": npc.get_display_name(),
            "role": npc.role,
            "faction": npc.faction,
            "appearance": npc.appearance,
            "personality": personality_desc,
            "current_location": npc.current_location,
            "current_activity": npc.current_activity,
            "decision_weights": npc.decision_weights
        }

    def build_scene_npcs_context(self, location_id: str) -> List[dict]:
        """
        构建场景 NPC 上下文列表

        Args:
            location_id: 地点 ID

        Returns:
            NPC 上下文列表
        """
        npcs = self.get_npcs_at_location(location_id)
        return [self.build_npc_context(npc.id) for npc in npcs]

    def to_dict(self) -> dict:
        """序列化为字典（用于存档）"""
        return {
            npc_id: {
                "current_location": npc.current_location,
                "current_activity": npc.current_activity,
                "is_alive": npc.is_alive
            }
            for npc_id, npc in self.npcs.items()
        }

    def load_state(self, state: dict) -> None:
        """从存档加载状态"""
        for npc_id, npc_state in state.items():
            if npc_id in self.npcs:
                npc = self.npcs[npc_id]
                npc.current_location = npc_state.get('current_location', npc.home_location)
                npc.current_activity = npc_state.get('current_activity', 'idle')
                npc.is_alive = npc_state.get('is_alive', True)
