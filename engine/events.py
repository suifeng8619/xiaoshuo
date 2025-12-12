"""
事件管理器 - 管理事件池、触发检查、效果执行

功能：
- 加载 config/events.yaml 事件配置
- 检查事件触发条件
- 选择并执行事件
- 管理事件冷却和调度
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import random
import logging

from .event_bus import EventBus, GameEvents


logger = logging.getLogger(__name__)


class EventTier(Enum):
    """事件层级"""
    DAILY = "daily"
    OPPORTUNITY = "opportunity"
    CRITICAL = "critical"


@dataclass
class EventWindow:
    """事件触发窗口"""
    time_slots: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    year_min: float = 0
    year_max: float = 9999


@dataclass
class EventEffect:
    """事件效果"""
    set_flags: List[str] = field(default_factory=list)
    clear_flags: List[str] = field(default_factory=list)
    relationship: Dict[str, Dict[str, int]] = field(default_factory=dict)
    player: Dict[str, Any] = field(default_factory=dict)
    add_clue: Optional[Dict[str, Any]] = None
    schedule_followup: Optional[Dict[str, Any]] = None


@dataclass
class EventChoice:
    """事件选项"""
    id: str
    label: str
    description: str
    effects: EventEffect


@dataclass
class EventData:
    """事件数据"""
    id: str
    name: str
    tier: EventTier
    storyline: str = ""
    repeatable: bool = False
    interrupt: bool = False

    window: EventWindow = field(default_factory=EventWindow)
    conditions: Dict[str, Any] = field(default_factory=dict)
    effects: EventEffect = field(default_factory=EventEffect)
    choices: List[EventChoice] = field(default_factory=list)

    cooldown: int = 0  # 冷却天数
    narrative: Dict[str, Any] = field(default_factory=dict)
    expiry: Optional[Dict[str, Any]] = None

    # 运行时状态
    triggered_count: int = 0
    last_triggered_day: int = -999
    scheduled_day: int = -1  # 调度触发日


class EventManager:
    """
    事件管理器

    管理事件池的加载、触发检查和效果执行。
    """

    def __init__(
        self,
        config_path: str = "config/events.yaml",
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化事件管理器

        Args:
            config_path: 事件配置文件路径
            event_bus: 事件总线
        """
        self.config_path = Path(config_path)
        self.event_bus = event_bus

        self.events: Dict[str, EventData] = {}
        self.story_phases: Dict[str, Dict[str, Any]] = {}
        self.clues: Dict[str, Dict[str, Any]] = {}

        # 索引
        self._daily_pool: List[str] = []
        self._opportunity_pool: List[str] = []
        self._critical_pool: List[str] = []

        self._load_config()

    def _load_config(self):
        """加载配置"""
        if not self.config_path.exists():
            logger.warning(f"事件配置文件不存在: {self.config_path}")
            return

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 加载事件
        for event_id, event_data in config.get('events', {}).items():
            event = self._parse_event(event_id, event_data)
            self.events[event_id] = event

            # 按层级索引
            if event.tier == EventTier.DAILY:
                self._daily_pool.append(event_id)
            elif event.tier == EventTier.OPPORTUNITY:
                self._opportunity_pool.append(event_id)
            elif event.tier == EventTier.CRITICAL:
                self._critical_pool.append(event_id)

        # 加载剧情阶段
        self.story_phases = config.get('story_phases', {})

        # 加载线索
        self.clues = config.get('clues', {})

        logger.info(
            f"[EventManager] 加载 {len(self.events)} 个事件 "
            f"(daily:{len(self._daily_pool)}, "
            f"opportunity:{len(self._opportunity_pool)}, "
            f"critical:{len(self._critical_pool)})"
        )

    def _parse_event(self, event_id: str, data: dict) -> EventData:
        """解析事件数据"""
        # 解析窗口
        window_data = data.get('window', {})
        window = EventWindow(
            time_slots=window_data.get('time_slots', []),
            locations=window_data.get('locations', []),
            year_min=window_data.get('time', {}).get('year_min', 0),
            year_max=window_data.get('time', {}).get('year_max', 9999)
        )

        # 解析效果
        effects = self._parse_effects(data.get('effects', {}))

        # 解析选项
        choices = []
        for choice_data in data.get('choices', []):
            choice = EventChoice(
                id=choice_data['id'],
                label=choice_data['label'],
                description=choice_data.get('description', ''),
                effects=self._parse_effects(choice_data.get('effects', {}))
            )
            choices.append(choice)

        # 解析层级
        tier_str = data.get('tier', 'daily')
        tier = EventTier(tier_str)

        return EventData(
            id=data.get('id', event_id),
            name=data.get('name', event_id),
            tier=tier,
            storyline=data.get('storyline', ''),
            repeatable=data.get('repeatable', False),
            interrupt=data.get('interrupt', False),
            window=window,
            conditions=data.get('conditions', {}),
            effects=effects,
            choices=choices,
            cooldown=data.get('cooldown', 0),
            narrative=data.get('narrative', {}),
            expiry=data.get('expiry')
        )

    def _parse_effects(self, data: dict) -> EventEffect:
        """解析事件效果"""
        return EventEffect(
            set_flags=data.get('set_flags', []),
            clear_flags=data.get('clear_flags', []),
            relationship=data.get('relationship', {}),
            player=data.get('player', {}),
            add_clue=data.get('add_clue'),
            schedule_followup=data.get('schedule_followup')
        )

    def get_event(self, event_id: str) -> Optional[EventData]:
        """获取事件"""
        return self.events.get(event_id)

    def check_triggers(
        self,
        world_state: Any,
        flags: Set[str],
        current_day: int,
        current_year: float,
        current_slot: str,
        player_location: str,
        npc_locations: Dict[str, str],
        relationships: Dict[str, Dict[str, int]]
    ) -> List[EventData]:
        """
        检查可触发的事件

        Args:
            world_state: 世界状态
            flags: 当前标记集合
            current_day: 当前天数
            current_year: 当前年份
            current_slot: 当前时段
            player_location: 玩家位置
            npc_locations: NPC位置字典
            relationships: 关系数据

        Returns:
            可触发的事件列表
        """
        triggered = []

        for event in self.events.values():
            if self._can_trigger(
                event, flags, current_day, current_year,
                current_slot, player_location, npc_locations,
                relationships
            ):
                triggered.append(event)

        return triggered

    def _can_trigger(
        self,
        event: EventData,
        flags: Set[str],
        current_day: int,
        current_year: float,
        current_slot: str,
        player_location: str,
        npc_locations: Dict[str, str],
        relationships: Dict[str, Dict[str, int]]
    ) -> bool:
        """检查单个事件是否可触发"""
        # 检查是否已触发（非重复事件）
        if not event.repeatable and event.triggered_count > 0:
            return False

        # 检查冷却
        if event.cooldown > 0:
            if current_day - event.last_triggered_day < event.cooldown:
                return False

        # 检查时间窗口
        if event.window.year_min > current_year:
            return False
        if event.window.year_max < current_year:
            return False

        # 检查时段
        if event.window.time_slots:
            if current_slot not in event.window.time_slots:
                return False

        # 检查地点
        if event.window.locations:
            if player_location not in event.window.locations:
                return False

        # 检查条件
        conditions = event.conditions

        # 检查必需标记
        flags_required = conditions.get('flags_required', [])
        for flag in flags_required:
            if flag not in flags:
                return False

        # 检查排除标记
        flags_absent = conditions.get('flags_absent', [])
        for flag in flags_absent:
            if flag in flags:
                return False

        # 检查 NPC 存活
        npc_alive = conditions.get('npc_alive', [])
        # 简化处理：假设配置的 NPC 都存活
        # 实际应该检查 CharacterManager

        # 检查 NPC 位置
        npc_at_location = conditions.get('npc_at_location', {})
        for npc_id, required_loc in npc_at_location.items():
            if required_loc == 'same_as_player':
                if npc_locations.get(npc_id) != player_location:
                    return False
            else:
                if npc_locations.get(npc_id) != required_loc:
                    return False

        # 检查关系条件
        rel_conditions = conditions.get('relationship', {})
        for npc_id, req in rel_conditions.items():
            npc_rel = relationships.get(npc_id, {})
            for dim, threshold in req.items():
                if isinstance(threshold, str):
                    # 解析 ">=75" 格式
                    if threshold.startswith('>='):
                        val = int(threshold[2:])
                        if npc_rel.get(dim, 0) < val:
                            return False
                    elif threshold.startswith('>'):
                        val = int(threshold[1:])
                        if npc_rel.get(dim, 0) <= val:
                            return False
                else:
                    if npc_rel.get(dim, 0) < threshold:
                        return False

        # 检查随机概率
        random_chance = conditions.get('random_chance', 1.0)
        if random.random() > random_chance:
            return False

        return True

    def select_event(
        self,
        candidates: List[EventData],
        prefer_tier: Optional[EventTier] = None
    ) -> Optional[EventData]:
        """
        从候选事件中选择一个

        Args:
            candidates: 候选事件列表
            prefer_tier: 优先选择的层级

        Returns:
            选中的事件
        """
        if not candidates:
            return None

        # 按层级优先级排序：critical > opportunity > daily
        tier_priority = {
            EventTier.CRITICAL: 3,
            EventTier.OPPORTUNITY: 2,
            EventTier.DAILY: 1
        }

        # 分组
        critical = [e for e in candidates if e.tier == EventTier.CRITICAL]
        opportunity = [e for e in candidates if e.tier == EventTier.OPPORTUNITY]
        daily = [e for e in candidates if e.tier == EventTier.DAILY]

        # 优先触发 critical
        if critical:
            return random.choice(critical)

        # 然后 opportunity
        if opportunity:
            return random.choice(opportunity)

        # 最后 daily
        if daily:
            return random.choice(daily)

        return None

    def execute_event(
        self,
        event: EventData,
        choice_id: Optional[str] = None,
        current_day: int = 0
    ) -> Dict[str, Any]:
        """
        执行事件

        Args:
            event: 要执行的事件
            choice_id: 选择的选项ID（如果有选项）
            current_day: 当前天数

        Returns:
            执行结果
        """
        result = {
            "event_id": event.id,
            "event_name": event.name,
            "effects": {},
            "choice_made": choice_id
        }

        # 确定要应用的效果
        effects = event.effects
        if choice_id and event.choices:
            for choice in event.choices:
                if choice.id == choice_id:
                    effects = choice.effects
                    break

        # 应用效果
        result["effects"]["set_flags"] = effects.set_flags
        result["effects"]["clear_flags"] = effects.clear_flags
        result["effects"]["relationship"] = effects.relationship
        result["effects"]["player"] = effects.player
        result["effects"]["add_clue"] = effects.add_clue
        result["effects"]["schedule_followup"] = effects.schedule_followup

        # 更新事件状态
        event.triggered_count += 1
        event.last_triggered_day = current_day

        # 发布事件
        if self.event_bus:
            self.event_bus.publish(
                GameEvents.EVENT_TRIGGERED,
                data={
                    "event_id": event.id,
                    "event_name": event.name,
                    "tier": event.tier.value,
                    "storyline": event.storyline,
                    "effects": result["effects"]
                },
                source="event_manager"
            )

        logger.info(f"[EventManager] 触发事件: {event.name} ({event.id})")

        return result

    def get_events_by_tier(self, tier: EventTier) -> List[EventData]:
        """按层级获取事件列表"""
        if tier == EventTier.DAILY:
            return [self.events[eid] for eid in self._daily_pool]
        elif tier == EventTier.OPPORTUNITY:
            return [self.events[eid] for eid in self._opportunity_pool]
        elif tier == EventTier.CRITICAL:
            return [self.events[eid] for eid in self._critical_pool]
        return []

    def get_events_by_storyline(self, storyline: str) -> List[EventData]:
        """按剧情线获取事件"""
        return [e for e in self.events.values() if e.storyline == storyline]

    def schedule_event(self, event_id: str, trigger_day: int) -> bool:
        """调度事件"""
        event = self.events.get(event_id)
        if event:
            event.scheduled_day = trigger_day
            return True
        return False

    def check_scheduled_events(self, current_day: int) -> List[EventData]:
        """检查到期的调度事件"""
        triggered = []
        for event in self.events.values():
            if event.scheduled_day > 0 and event.scheduled_day <= current_day:
                triggered.append(event)
                event.scheduled_day = -1  # 清除调度
        return triggered

    def get_narrative(self, event: EventData) -> Dict[str, Any]:
        """获取事件叙事内容"""
        return event.narrative

    def to_dict(self) -> dict:
        """序列化为字典（用于存档）"""
        return {
            event_id: {
                "triggered_count": event.triggered_count,
                "last_triggered_day": event.last_triggered_day,
                "scheduled_day": event.scheduled_day
            }
            for event_id, event in self.events.items()
            if event.triggered_count > 0 or event.scheduled_day > 0
        }

    def load_state(self, state: dict) -> None:
        """从存档加载状态"""
        for event_id, event_state in state.items():
            if event_id in self.events:
                event = self.events[event_id]
                event.triggered_count = event_state.get('triggered_count', 0)
                event.last_triggered_day = event_state.get('last_triggered_day', -999)
                event.scheduled_day = event_state.get('scheduled_day', -1)
