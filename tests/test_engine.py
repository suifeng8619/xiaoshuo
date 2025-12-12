"""
引擎核心模块单元测试

覆盖：
- TimeSystem：时间推进、时段变化、日/月/年结算
- EventBus：订阅、发布、优先级、一次性事件
- EventManager：事件触发、选择、执行
- RelationshipSystem：关系变化、衰减、限制
"""

import pytest
from engine.time import GameTime, TimeSlot
from engine.time_system import TimeSystem
from engine.event_bus import EventBus, EventPriority, GameEvents
from engine.events import EventManager, EventTier
from engine.relationships import RelationshipSystem


class TestTimeSystem:
    """时间系统测试"""

    def test_initial_time(self):
        """测试初始时间"""
        ts = TimeSystem()
        t = ts.current_time
        assert t.year == 1
        assert t.month == 1
        assert t.day == 1
        assert t.tick_in_day == 0

    def test_advance_single_tick(self):
        """测试单时辰推进"""
        ts = TimeSystem()
        event = ts.advance(1)
        assert event.ticks_advanced == 1
        assert ts.current_time.tick_in_day == 1

    def test_advance_cross_day(self):
        """测试跨日推进"""
        ts = TimeSystem()
        event = ts.advance(8)  # 1天 = 8时辰
        assert event.days_passed == 1
        assert ts.current_time.day == 2
        assert ts.current_time.tick_in_day == 0

    def test_advance_cross_month(self):
        """测试跨月推进"""
        ts = TimeSystem()
        event = ts.advance(30 * 8)  # 30天
        assert event.months_passed == 1
        assert ts.current_time.month == 2

    def test_time_slot_morning(self):
        """测试早晨时段"""
        ts = TimeSystem()
        assert ts.current_slot == TimeSlot.MORNING

    def test_time_slot_afternoon(self):
        """测试下午时段"""
        ts = TimeSystem()
        ts.advance(2)
        assert ts.current_slot == TimeSlot.AFTERNOON

    def test_day_end_hook(self):
        """测试日结算钩子"""
        ts = TimeSystem()
        called = []

        def on_day_end(event):
            called.append(event.event_type)

        ts.register_hook("day_ended", on_day_end)
        ts.advance(8)

        assert len(called) == 1
        assert called[0] == "day_ended"


class TestEventBus:
    """事件总线测试"""

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event.data)

        bus.subscribe("test_event", handler)
        bus.publish("test_event", data="hello")

        assert len(received) == 1
        assert received[0] == "hello"

    def test_priority_order(self):
        """测试优先级顺序"""
        bus = EventBus()
        order = []

        def low_handler(event):
            order.append("low")

        def high_handler(event):
            order.append("high")

        bus.subscribe("test", low_handler, EventPriority.LOW)
        bus.subscribe("test", high_handler, EventPriority.HIGH)
        bus.publish("test")

        assert order == ["high", "low"]

    def test_subscribe_once(self):
        """测试一次性订阅"""
        bus = EventBus()
        count = [0]

        def handler(event):
            count[0] += 1

        bus.subscribe_once("test", handler)
        bus.publish("test")
        bus.publish("test")

        assert count[0] == 1

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EventBus()
        count = [0]

        def handler(event):
            count[0] += 1

        bus.subscribe("test", handler)
        bus.publish("test")
        bus.unsubscribe("test", handler)
        bus.publish("test")

        assert count[0] == 1


class TestEventManager:
    """事件管理器测试"""

    def test_load_events(self):
        """测试加载事件配置"""
        em = EventManager()
        assert len(em.events) > 0

    def test_events_by_tier(self):
        """测试按层级获取事件"""
        em = EventManager()
        daily = em.get_events_by_tier(EventTier.DAILY)
        opportunity = em.get_events_by_tier(EventTier.OPPORTUNITY)
        critical = em.get_events_by_tier(EventTier.CRITICAL)

        assert len(daily) > 0
        assert len(opportunity) > 0
        assert len(critical) > 0

    def test_event_selection_priority(self):
        """测试事件选择优先级（critical > opportunity > daily）"""
        em = EventManager()
        daily = em.get_events_by_tier(EventTier.DAILY)
        critical = em.get_events_by_tier(EventTier.CRITICAL)

        # 混合候选
        candidates = [daily[0], critical[0]]
        selected = em.select_event(candidates)

        assert selected.tier == EventTier.CRITICAL

    def test_event_execute(self):
        """测试事件执行"""
        em = EventManager()
        event = em.get_event("daily_cultivation_insight")
        if event:
            result = em.execute_event(event, current_day=1)
            assert result["event_id"] == "daily_cultivation_insight"
            assert event.triggered_count == 1


class TestRelationshipSystem:
    """关系系统测试"""

    def test_init_relationship(self):
        """测试初始化关系"""
        rs = RelationshipSystem()
        rel = rs.init_relationship("test_npc", {
            "trust": 50,
            "affection": 30
        })
        assert rel.trust == 50
        assert rel.affection == 30

    def test_apply_change(self):
        """测试应用关系变化"""
        rs = RelationshipSystem()
        rs.init_relationship("npc", {"trust": 50})
        delta = rs.apply_change("npc", "trust", 10, "test")
        assert delta == 10
        assert rs.get_value("npc", "trust") == 60

    def test_change_limit(self):
        """测试单次变化限制"""
        rs = RelationshipSystem()
        rs.init_relationship("npc", {"trust": 50})
        # 尝试变化50，但被限制到15
        delta = rs.apply_change("npc", "trust", 50, "test")
        assert delta == 15
        assert rs.get_value("npc", "trust") == 65

    def test_value_clamp(self):
        """测试值范围限制"""
        rs = RelationshipSystem()
        rs.init_relationship("npc", {"trust": 95})
        # 尝试增加20，但会被限制在100
        rs.apply_change("npc", "trust", 20, "test", bypass_limit=True)
        assert rs.get_value("npc", "trust") == 100

    def test_daily_decay(self):
        """测试每日衰减"""
        rs = RelationshipSystem()
        rs.init_relationship("npc", {"trust": 50, "affection": 30})

        initial_trust = rs.get_value("npc", "trust")
        rs.apply_daily_decay()

        # 衰减后值应该变小
        assert rs.get_value("npc", "trust") < initial_trust

    def test_record_interaction(self):
        """测试记录互动"""
        rs = RelationshipSystem()
        rs.init_relationship("npc", {})

        # 模拟几天未互动
        for _ in range(5):
            rs.apply_daily_decay()

        rel = rs.get_relationship("npc")
        assert rel.days_since_interaction == 5

        # 记录互动后重置
        rs.record_interaction("npc")
        assert rel.days_since_interaction == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
