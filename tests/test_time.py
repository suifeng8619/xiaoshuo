"""
GameTime 单元测试
"""

import pytest
from engine.time import (
    GameTime, TimeSlot,
    TICKS_PER_DAY, TICKS_PER_MONTH, TICKS_PER_YEAR,
    TICKS_PER_SLOT
)


class TestTimeConstants:
    """测试时间常量"""

    def test_ticks_per_day(self):
        """8 ticks = 1 日"""
        assert TICKS_PER_DAY == 8

    def test_ticks_per_month(self):
        """240 ticks = 1 月"""
        assert TICKS_PER_MONTH == 240

    def test_ticks_per_year(self):
        """2880 ticks = 1 年"""
        assert TICKS_PER_YEAR == 2880


class TestGameTimeBasic:
    """测试 GameTime 基本功能"""

    def test_default_init(self):
        """默认初始化为第1年1月1日 morning"""
        gt = GameTime()
        assert gt.year == 1
        assert gt.month == 1
        assert gt.day == 1
        assert gt.tick_in_day == 0
        assert gt.current_slot() == TimeSlot.MORNING

    def test_to_absolute_tick_start(self):
        """初始时间的绝对tick为0"""
        gt = GameTime()
        assert gt.to_absolute_tick() == 0

    def test_from_absolute_tick_zero(self):
        """从0创建应为初始时间"""
        gt = GameTime.from_absolute_tick(0)
        assert gt.year == 1
        assert gt.month == 1
        assert gt.day == 1
        assert gt.tick_in_day == 0

    def test_from_absolute_tick_one_day(self):
        """8 tick = 第2日"""
        gt = GameTime.from_absolute_tick(8)
        assert gt.day == 2
        assert gt.tick_in_day == 0

    def test_from_absolute_tick_one_month(self):
        """240 tick = 第2月"""
        gt = GameTime.from_absolute_tick(240)
        assert gt.month == 2
        assert gt.day == 1

    def test_from_absolute_tick_one_year(self):
        """2880 tick = 第2年"""
        gt = GameTime.from_absolute_tick(2880)
        assert gt.year == 2
        assert gt.month == 1
        assert gt.day == 1


class TestTimeSlots:
    """测试时段功能"""

    def test_slot_morning(self):
        """tick 0-1 是 morning"""
        gt = GameTime(tick_in_day=0)
        assert gt.current_slot() == TimeSlot.MORNING
        gt = GameTime(tick_in_day=1)
        assert gt.current_slot() == TimeSlot.MORNING

    def test_slot_afternoon(self):
        """tick 2-3 是 afternoon"""
        gt = GameTime(tick_in_day=2)
        assert gt.current_slot() == TimeSlot.AFTERNOON
        gt = GameTime(tick_in_day=3)
        assert gt.current_slot() == TimeSlot.AFTERNOON

    def test_slot_evening(self):
        """tick 4-5 是 evening"""
        gt = GameTime(tick_in_day=4)
        assert gt.current_slot() == TimeSlot.EVENING

    def test_slot_night(self):
        """tick 6-7 是 night"""
        gt = GameTime(tick_in_day=6)
        assert gt.current_slot() == TimeSlot.NIGHT

    def test_slot_remaining_at_start(self):
        """时段开始时剩余2时辰"""
        gt = GameTime(tick_in_day=0)
        assert gt.slot_remaining_ticks() == 2

    def test_slot_remaining_mid(self):
        """时段中间剩余1时辰"""
        gt = GameTime(tick_in_day=1)
        assert gt.slot_remaining_ticks() == 1


class TestAdvanceTicks:
    """测试时间推进"""

    def test_advance_within_day(self):
        """在日内推进"""
        gt = GameTime()
        days, months, years = gt.advance_ticks(3)
        assert gt.tick_in_day == 3
        assert gt.day == 1
        assert days == 0

    def test_advance_cross_day(self):
        """跨日推进"""
        gt = GameTime()
        days, months, years = gt.advance_ticks(10)  # 跨1日
        assert gt.day == 2
        assert gt.tick_in_day == 2
        assert days == 1

    def test_advance_cross_day_resets_slot(self):
        """跨日后时段重置"""
        gt = GameTime(tick_in_day=7)  # night 最后一个 tick
        gt.advance_ticks(1)  # 跨日
        assert gt.day == 2
        assert gt.tick_in_day == 0
        assert gt.current_slot() == TimeSlot.MORNING

    def test_advance_cross_month(self):
        """跨月推进"""
        gt = GameTime(day=30, tick_in_day=7)  # 月末最后一个 tick
        days, months, years = gt.advance_ticks(1)
        assert gt.month == 2
        assert gt.day == 1
        assert days == 1
        assert months == 1

    def test_advance_cross_year(self):
        """跨年推进"""
        gt = GameTime(month=12, day=30, tick_in_day=7)  # 年末
        days, months, years = gt.advance_ticks(1)
        assert gt.year == 2
        assert gt.month == 1
        assert gt.day == 1
        assert years == 1

    def test_advance_zero(self):
        """推进0不变化"""
        gt = GameTime()
        old_tick = gt.to_absolute_tick()
        gt.advance_ticks(0)
        assert gt.to_absolute_tick() == old_tick

    def test_advance_negative(self):
        """负数推进不变化"""
        gt = GameTime(day=5)
        old_tick = gt.to_absolute_tick()
        gt.advance_ticks(-3)
        assert gt.to_absolute_tick() == old_tick


class TestSerialization:
    """测试序列化"""

    def test_to_dict(self):
        """序列化为字典"""
        gt = GameTime(year=2, month=3, day=15, tick_in_day=5)
        d = gt.to_dict()
        assert d["year"] == 2
        assert d["month"] == 3
        assert d["day"] == 15
        assert d["tick_in_day"] == 5
        assert "absolute_tick" in d

    def test_from_dict(self):
        """从字典反序列化"""
        d = {"year": 2, "month": 3, "day": 15, "tick_in_day": 5}
        gt = GameTime.from_dict(d)
        assert gt.year == 2
        assert gt.month == 3
        assert gt.day == 15
        assert gt.tick_in_day == 5

    def test_from_dict_with_absolute(self):
        """从 absolute_tick 反序列化"""
        d = {"absolute_tick": 100}
        gt = GameTime.from_dict(d)
        assert gt.to_absolute_tick() == 100


class TestComparison:
    """测试比较运算"""

    def test_equal(self):
        """相等比较"""
        gt1 = GameTime(year=1, month=2, day=3)
        gt2 = GameTime(year=1, month=2, day=3)
        assert gt1 == gt2

    def test_less_than(self):
        """小于比较"""
        gt1 = GameTime(day=1)
        gt2 = GameTime(day=2)
        assert gt1 < gt2

    def test_copy(self):
        """复制独立于原对象"""
        gt1 = GameTime(day=5)
        gt2 = gt1.copy()
        gt2.advance_ticks(10)
        assert gt1.day == 5  # 原对象不变
        assert gt2.day != 5  # 副本改变


class TestStringFormat:
    """测试字符串格式化"""

    def test_str_format(self):
        """__str__ 格式"""
        gt = GameTime(year=1, month=3, day=15, tick_in_day=0)
        s = str(gt)
        assert "第1年" in s
        assert "3月" in s
        assert "15日" in s
        assert "晨" in s
