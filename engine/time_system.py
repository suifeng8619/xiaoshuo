"""
时间系统 - 管理世界时间推进与结算钩子

包装 GameTime，提供：
- advance(action_time_cost): 推进时间
- on_day_end / on_month_end / on_year_end: 结算钩子
- 事件发布：time_advanced, slot_changed, day_ended, month_ended, year_ended
"""

from typing import Callable, List, Optional
from dataclasses import dataclass, field

from engine.time import GameTime, TimeSlot, TICKS_PER_DAY


@dataclass
class TimeEvent:
    """时间事件数据"""
    event_type: str  # time_advanced, slot_changed, day_ended, etc.
    old_time: GameTime
    new_time: GameTime
    ticks_advanced: int
    days_passed: int = 0
    months_passed: int = 0
    years_passed: int = 0


# 钩子函数类型
TimeHook = Callable[[TimeEvent], None]


class TimeSystem:
    """
    时间系统

    管理游戏世界时间的推进，并在关键时间节点触发钩子。
    """

    def __init__(self, initial_time: Optional[GameTime] = None):
        """
        初始化时间系统

        Args:
            initial_time: 初始时间，默认为第1年1月1日晨
        """
        self._time = initial_time.copy() if initial_time else GameTime()

        # 钩子注册表
        self._hooks: dict[str, List[TimeHook]] = {
            "time_advanced": [],
            "slot_changed": [],
            "day_ended": [],
            "month_ended": [],
            "year_ended": [],
        }

    @property
    def current_time(self) -> GameTime:
        """获取当前时间（只读副本）"""
        return self._time.copy()

    @property
    def current_slot(self) -> TimeSlot:
        """获取当前时段"""
        return self._time.current_slot()

    def advance(self, ticks: int) -> TimeEvent:
        """
        推进时间

        Args:
            ticks: 要推进的时辰数

        Returns:
            TimeEvent: 包含时间变化信息的事件对象
        """
        if ticks <= 0:
            return TimeEvent(
                event_type="time_advanced",
                old_time=self._time.copy(),
                new_time=self._time.copy(),
                ticks_advanced=0
            )

        old_time = self._time.copy()
        old_slot = self._time.current_slot()

        # 推进时间
        days_passed, months_passed, years_passed = self._time.advance_ticks(ticks)

        new_time = self._time.copy()
        new_slot = self._time.current_slot()

        # 创建事件
        event = TimeEvent(
            event_type="time_advanced",
            old_time=old_time,
            new_time=new_time,
            ticks_advanced=ticks,
            days_passed=days_passed,
            months_passed=months_passed,
            years_passed=years_passed
        )

        # 触发钩子（按顺序）
        self._trigger_hooks("time_advanced", event)

        # 时段变化
        if old_slot != new_slot:
            slot_event = TimeEvent(
                event_type="slot_changed",
                old_time=old_time,
                new_time=new_time,
                ticks_advanced=ticks,
                days_passed=days_passed
            )
            self._trigger_hooks("slot_changed", slot_event)

        # 日结算
        if days_passed > 0:
            for _ in range(days_passed):
                day_event = TimeEvent(
                    event_type="day_ended",
                    old_time=old_time,
                    new_time=new_time,
                    ticks_advanced=ticks,
                    days_passed=days_passed
                )
                self._trigger_hooks("day_ended", day_event)

        # 月结算
        if months_passed > 0:
            for _ in range(months_passed):
                month_event = TimeEvent(
                    event_type="month_ended",
                    old_time=old_time,
                    new_time=new_time,
                    ticks_advanced=ticks,
                    months_passed=months_passed
                )
                self._trigger_hooks("month_ended", month_event)

        # 年结算
        if years_passed > 0:
            for _ in range(years_passed):
                year_event = TimeEvent(
                    event_type="year_ended",
                    old_time=old_time,
                    new_time=new_time,
                    ticks_advanced=ticks,
                    years_passed=years_passed
                )
                self._trigger_hooks("year_ended", year_event)

        return event

    def register_hook(self, event_type: str, hook: TimeHook):
        """
        注册时间钩子

        Args:
            event_type: 事件类型 (time_advanced, slot_changed, day_ended, month_ended, year_ended)
            hook: 钩子函数
        """
        if event_type not in self._hooks:
            raise ValueError(f"未知事件类型: {event_type}")
        self._hooks[event_type].append(hook)

    def unregister_hook(self, event_type: str, hook: TimeHook):
        """注销时间钩子"""
        if event_type in self._hooks and hook in self._hooks[event_type]:
            self._hooks[event_type].remove(hook)

    def _trigger_hooks(self, event_type: str, event: TimeEvent):
        """触发指定类型的所有钩子"""
        for hook in self._hooks.get(event_type, []):
            try:
                hook(event)
            except Exception as e:
                # 钩子执行失败不应中断时间推进
                print(f"[TimeSystem] 钩子执行失败 ({event_type}): {e}")

    def set_time(self, time: GameTime):
        """
        设置当前时间（用于加载存档）

        Args:
            time: 要设置的时间
        """
        self._time = time.copy()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "current_time": self._time.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeSystem":
        """从字典反序列化"""
        time = GameTime.from_dict(data.get("current_time", {}))
        return cls(initial_time=time)

    def __str__(self) -> str:
        return f"TimeSystem({self._time})"
