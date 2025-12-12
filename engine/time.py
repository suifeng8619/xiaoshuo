"""
游戏时间系统

时间单位定义（参考 docs/design/06_specifications.md）：
- 1 时辰 = 1 tick（最小单位，对应现实2小时）
- 1 时段 = 2 时辰（morning/afternoon/evening/night）
- 1 日 = 8 时辰 = 4 时段
- 1 月 = 30 日 = 240 tick
- 1 季 = 3 月 = 720 tick
- 1 年 = 12 月 = 2880 tick
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class TimeSlot(Enum):
    """时段枚举"""
    MORNING = "morning"      # 第1-2时辰 (05:00-09:00)
    AFTERNOON = "afternoon"  # 第3-4时辰 (09:00-13:00)
    EVENING = "evening"      # 第5-6时辰 (13:00-17:00)
    NIGHT = "night"          # 第7-8时辰 (17:00-21:00)


# 时间常量
TICKS_PER_SLOT = 2      # 每时段 2 时辰
SLOTS_PER_DAY = 4       # 每日 4 时段
TICKS_PER_DAY = 8       # 每日 8 时辰
DAYS_PER_MONTH = 30     # 每月 30 日
MONTHS_PER_YEAR = 12    # 每年 12 月
TICKS_PER_MONTH = TICKS_PER_DAY * DAYS_PER_MONTH  # 240
TICKS_PER_YEAR = TICKS_PER_MONTH * MONTHS_PER_YEAR  # 2880

# 时段顺序
SLOT_ORDER = [TimeSlot.MORNING, TimeSlot.AFTERNOON, TimeSlot.EVENING, TimeSlot.NIGHT]


@dataclass
class GameTime:
    """
    游戏时间类

    使用 absolute_tick 作为内部存储，year/month/day/slot/tick_in_slot 作为视图。
    """
    year: int = 1
    month: int = 1
    day: int = 1
    tick_in_day: int = 0  # 0-7，当日第几个时辰

    def __post_init__(self):
        """验证并规范化时间"""
        self._normalize()

    def _normalize(self):
        """规范化时间，处理溢出"""
        # 将所有字段转为 absolute_tick 再重新分解
        total = self.to_absolute_tick()
        self._set_from_absolute_tick(total)

    def _set_from_absolute_tick(self, absolute_tick: int):
        """从绝对 tick 设置时间字段"""
        if absolute_tick < 0:
            absolute_tick = 0

        # 计算年
        self.year = absolute_tick // TICKS_PER_YEAR + 1
        remainder = absolute_tick % TICKS_PER_YEAR

        # 计算月
        self.month = remainder // TICKS_PER_MONTH + 1
        remainder = remainder % TICKS_PER_MONTH

        # 计算日
        self.day = remainder // TICKS_PER_DAY + 1
        self.tick_in_day = remainder % TICKS_PER_DAY

    def to_absolute_tick(self) -> int:
        """转换为绝对 tick（从游戏开始的总时辰数）"""
        return (
            (self.year - 1) * TICKS_PER_YEAR +
            (self.month - 1) * TICKS_PER_MONTH +
            (self.day - 1) * TICKS_PER_DAY +
            self.tick_in_day
        )

    @classmethod
    def from_absolute_tick(cls, absolute_tick: int) -> "GameTime":
        """从绝对 tick 创建 GameTime"""
        gt = cls()
        gt._set_from_absolute_tick(absolute_tick)
        return gt

    def current_slot(self) -> TimeSlot:
        """获取当前时段"""
        slot_index = self.tick_in_day // TICKS_PER_SLOT
        return SLOT_ORDER[slot_index]

    def slot_remaining_ticks(self) -> int:
        """当前时段剩余时辰数"""
        tick_in_slot = self.tick_in_day % TICKS_PER_SLOT
        return TICKS_PER_SLOT - tick_in_slot

    def advance_ticks(self, n: int) -> Tuple[int, int, int]:
        """
        推进 n 个时辰

        Returns:
            (days_passed, months_passed, years_passed): 跨越的日/月/年数
        """
        if n <= 0:
            return (0, 0, 0)

        old_day = self.day
        old_month = self.month
        old_year = self.year

        new_tick = self.to_absolute_tick() + n
        self._set_from_absolute_tick(new_tick)

        # 计算跨越数量
        days_passed = (new_tick // TICKS_PER_DAY) - ((new_tick - n) // TICKS_PER_DAY)
        months_passed = (
            (self.year - 1) * MONTHS_PER_YEAR + (self.month - 1)
        ) - (
            (old_year - 1) * MONTHS_PER_YEAR + (old_month - 1)
        )
        years_passed = self.year - old_year

        return (days_passed, months_passed, years_passed)

    def copy(self) -> "GameTime":
        """创建副本"""
        return GameTime(
            year=self.year,
            month=self.month,
            day=self.day,
            tick_in_day=self.tick_in_day
        )

    def __str__(self) -> str:
        """格式化输出：第X年X月X日 时段"""
        slot = self.current_slot()
        slot_names = {
            TimeSlot.MORNING: "晨",
            TimeSlot.AFTERNOON: "午",
            TimeSlot.EVENING: "暮",
            TimeSlot.NIGHT: "夜"
        }
        return f"第{self.year}年{self.month}月{self.day}日 {slot_names[slot]}"

    def __repr__(self) -> str:
        return f"GameTime(year={self.year}, month={self.month}, day={self.day}, tick_in_day={self.tick_in_day})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, GameTime):
            return False
        return self.to_absolute_tick() == other.to_absolute_tick()

    def __lt__(self, other) -> bool:
        if not isinstance(other, GameTime):
            return NotImplemented
        return self.to_absolute_tick() < other.to_absolute_tick()

    def __le__(self, other) -> bool:
        if not isinstance(other, GameTime):
            return NotImplemented
        return self.to_absolute_tick() <= other.to_absolute_tick()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "tick_in_day": self.tick_in_day,
            "absolute_tick": self.to_absolute_tick()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameTime":
        """从字典反序列化"""
        if "absolute_tick" in data:
            return cls.from_absolute_tick(data["absolute_tick"])
        return cls(
            year=data.get("year", 1),
            month=data.get("month", 1),
            day=data.get("day", 1),
            tick_in_day=data.get("tick_in_day", 0)
        )
