"""
事件总线 - 轻量级发布/订阅系统

功能：
- 同步事件发布/订阅
- 支持事件优先级
- World/Time/NPC/Event 系统间通信
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件处理优先级"""
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class EventHandler:
    """事件处理器包装"""
    callback: Callable[[Any], None]
    priority: EventPriority = EventPriority.NORMAL
    once: bool = False  # 是否只触发一次


@dataclass
class Event:
    """事件数据"""
    type: str
    data: Any = None
    source: str = ""  # 事件来源
    timestamp: int = 0  # 游戏时间 tick


class EventBus:
    """
    事件总线

    轻量级同步事件系统，用于游戏各系统间通信。

    使用示例：
        bus = EventBus()

        # 订阅
        bus.subscribe("day_ended", lambda e: print(f"日结算: {e.data}"))

        # 发布
        bus.publish("day_ended", {"day": 5})

        # 带优先级订阅
        bus.subscribe("combat_start", handler, priority=EventPriority.HIGH)

        # 一次性订阅
        bus.subscribe_once("player_died", respawn_handler)
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._event_history: List[Event] = []  # 最近事件历史
        self._history_limit = 100

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Event], None],
        priority: EventPriority = EventPriority.NORMAL
    ) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数，接收 Event 对象
            priority: 处理优先级
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        handler = EventHandler(callback=callback, priority=priority)
        self._handlers[event_type].append(handler)

        # 按优先级排序（高优先级在前）
        self._handlers[event_type].sort(
            key=lambda h: h.priority.value,
            reverse=True
        )

    def subscribe_once(
        self,
        event_type: str,
        callback: Callable[[Event], None],
        priority: EventPriority = EventPriority.NORMAL
    ) -> None:
        """订阅一次性事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        handler = EventHandler(callback=callback, priority=priority, once=True)
        self._handlers[event_type].append(handler)
        self._handlers[event_type].sort(
            key=lambda h: h.priority.value,
            reverse=True
        )

    def unsubscribe(
        self,
        event_type: str,
        callback: Callable[[Event], None]
    ) -> bool:
        """
        取消订阅

        Args:
            event_type: 事件类型
            callback: 要取消的回调函数

        Returns:
            是否成功取消
        """
        if event_type not in self._handlers:
            return False

        original_len = len(self._handlers[event_type])
        self._handlers[event_type] = [
            h for h in self._handlers[event_type]
            if h.callback != callback
        ]
        return len(self._handlers[event_type]) < original_len

    def publish(
        self,
        event_type: str,
        data: Any = None,
        source: str = "",
        timestamp: int = 0
    ) -> int:
        """
        发布事件

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
            timestamp: 游戏时间戳

        Returns:
            触发的处理器数量
        """
        event = Event(
            type=event_type,
            data=data,
            source=source,
            timestamp=timestamp
        )

        # 记录历史
        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history = self._event_history[-self._history_limit:]

        if event_type not in self._handlers:
            return 0

        handlers_to_remove = []
        triggered = 0

        for handler in self._handlers[event_type]:
            try:
                handler.callback(event)
                triggered += 1

                if handler.once:
                    handlers_to_remove.append(handler)

            except Exception as e:
                logger.error(f"[EventBus] 处理器执行失败 ({event_type}): {e}")

        # 移除一次性处理器
        for handler in handlers_to_remove:
            self._handlers[event_type].remove(handler)

        return triggered

    def has_subscribers(self, event_type: str) -> bool:
        """检查是否有订阅者"""
        return event_type in self._handlers and len(self._handlers[event_type]) > 0

    def get_subscriber_count(self, event_type: str) -> int:
        """获取订阅者数量"""
        if event_type not in self._handlers:
            return 0
        return len(self._handlers[event_type])

    def get_recent_events(self, count: int = 10) -> List[Event]:
        """获取最近的事件"""
        return self._event_history[-count:]

    def clear_event_type(self, event_type: str) -> None:
        """清除某类型的所有订阅"""
        if event_type in self._handlers:
            self._handlers[event_type] = []

    def clear_all(self) -> None:
        """清除所有订阅"""
        self._handlers = {}


# 全局事件总线实例（可选使用）
_global_bus: Optional[EventBus] = None


def get_global_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


# ============ 预定义事件类型 ============
class GameEvents:
    """游戏事件类型常量"""
    # 时间事件
    TIME_ADVANCED = "time_advanced"
    SLOT_CHANGED = "slot_changed"
    DAY_ENDED = "day_ended"
    MONTH_ENDED = "month_ended"
    YEAR_ENDED = "year_ended"

    # 玩家事件
    PLAYER_MOVED = "player_moved"
    PLAYER_ACTION = "player_action"
    PLAYER_DIED = "player_died"
    PLAYER_LEVELED = "player_leveled"

    # NPC 事件
    NPC_SCHEDULE_EXECUTED = "npc_schedule_executed"
    NPC_LOCATION_CHANGED = "npc_location_changed"
    NPC_STATE_CHANGED = "npc_state_changed"

    # 关系事件
    RELATIONSHIP_CHANGED = "relationship_changed"
    MEMORY_ADDED = "memory_added"

    # 剧情事件
    EVENT_TRIGGERED = "event_triggered"
    FLAG_CHANGED = "flag_changed"
    QUEST_UPDATED = "quest_updated"

    # 战斗事件
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    COMBAT_ROUND = "combat_round"
