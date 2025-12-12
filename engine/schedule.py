"""
NPC 日程引擎 - 管理 NPC 按时段执行日程

功能：
- 根据时段更新 NPC 位置和活动
- 发布 NPC 状态变更事件
- 支持日程中断检查
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from .characters import CharacterManager, NPCData
from .time import TimeSlot
from .event_bus import EventBus, GameEvents


logger = logging.getLogger(__name__)


@dataclass
class ScheduleResult:
    """日程执行结果"""
    npc_id: str
    slot: str
    old_location: str
    new_location: str
    activity: str
    description: str
    location_changed: bool


class NPCScheduleEngine:
    """
    NPC 日程引擎

    根据时段自动更新 NPC 的位置和活动状态。

    使用示例：
        engine = NPCScheduleEngine(character_manager, event_bus)

        # 当时段变化时调用
        results = engine.execute_slot("morning")

        # 或者针对单个 NPC
        result = engine.execute_npc_slot("atan", "morning")
    """

    def __init__(
        self,
        character_manager: CharacterManager,
        event_bus: Optional[EventBus] = None
    ):
        """
        初始化日程引擎

        Args:
            character_manager: 角色管理器
            event_bus: 事件总线（可选）
        """
        self.characters = character_manager
        self.event_bus = event_bus

    def execute_slot(self, slot_name: str) -> List[ScheduleResult]:
        """
        执行所有 NPC 的指定时段日程

        Args:
            slot_name: 时段名称 (morning/afternoon/evening/night)

        Returns:
            执行结果列表
        """
        results = []

        for npc in self.characters.all_npcs():
            if not npc.is_alive:
                continue

            result = self.execute_npc_slot(npc.id, slot_name)
            if result:
                results.append(result)

        return results

    def execute_npc_slot(
        self,
        npc_id: str,
        slot_name: str
    ) -> Optional[ScheduleResult]:
        """
        执行单个 NPC 的时段日程

        Args:
            npc_id: NPC ID
            slot_name: 时段名称

        Returns:
            执行结果，无日程或NPC不存在返回 None
        """
        npc = self.characters.get_npc(npc_id)
        if not npc or not npc.is_alive:
            return None

        if not npc.schedule:
            return None

        slot = npc.schedule.get_slot(slot_name)
        if not slot:
            return None

        old_location = npc.current_location
        new_location = slot.location
        location_changed = old_location != new_location

        # 更新 NPC 状态
        npc.current_location = new_location
        npc.current_activity = slot.activity

        result = ScheduleResult(
            npc_id=npc_id,
            slot=slot_name,
            old_location=old_location,
            new_location=new_location,
            activity=slot.activity,
            description=slot.description,
            location_changed=location_changed
        )

        # 发布事件
        self._publish_events(npc, result)

        logger.debug(
            f"[Schedule] {npc.name} {slot_name}: "
            f"{old_location} -> {new_location} ({slot.activity})"
        )

        return result

    def _publish_events(self, npc: NPCData, result: ScheduleResult) -> None:
        """发布日程相关事件"""
        if not self.event_bus:
            return

        # 日程执行事件
        self.event_bus.publish(
            GameEvents.NPC_SCHEDULE_EXECUTED,
            data={
                "npc_id": result.npc_id,
                "npc_name": npc.name,
                "slot": result.slot,
                "location": result.new_location,
                "activity": result.activity,
                "description": result.description
            },
            source="schedule_engine"
        )

        # 位置变更事件
        if result.location_changed:
            self.event_bus.publish(
                GameEvents.NPC_LOCATION_CHANGED,
                data={
                    "npc_id": result.npc_id,
                    "npc_name": npc.name,
                    "old_location": result.old_location,
                    "new_location": result.new_location
                },
                source="schedule_engine"
            )

    def execute_time_slot(self, time_slot: TimeSlot) -> List[ScheduleResult]:
        """
        根据 TimeSlot 枚举执行日程

        Args:
            time_slot: TimeSlot 枚举值

        Returns:
            执行结果列表
        """
        slot_name = time_slot.value  # morning, afternoon, etc.
        return self.execute_slot(slot_name)

    def get_npc_schedule_at_slot(
        self,
        npc_id: str,
        slot_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        查询 NPC 在指定时段的日程

        Args:
            npc_id: NPC ID
            slot_name: 时段名称

        Returns:
            日程信息字典
        """
        npc = self.characters.get_npc(npc_id)
        if not npc or not npc.schedule:
            return None

        slot = npc.schedule.get_slot(slot_name)
        if not slot:
            return None

        return {
            "npc_id": npc_id,
            "npc_name": npc.name,
            "slot": slot_name,
            "location": slot.location,
            "activity": slot.activity,
            "description": slot.description,
            "interruptible": slot.interruptible
        }

    def is_npc_interruptible(self, npc_id: str, slot_name: str) -> bool:
        """
        检查 NPC 在指定时段是否可被打断

        Args:
            npc_id: NPC ID
            slot_name: 时段名称

        Returns:
            是否可打断
        """
        npc = self.characters.get_npc(npc_id)
        if not npc or not npc.schedule:
            return True  # 无日程默认可打断

        slot = npc.schedule.get_slot(slot_name)
        if not slot:
            return True

        return slot.interruptible

    def get_npcs_at_location_for_slot(
        self,
        location_id: str,
        slot_name: str
    ) -> List[Dict[str, Any]]:
        """
        查询指定时段在某地点的所有 NPC

        Args:
            location_id: 地点 ID
            slot_name: 时段名称

        Returns:
            NPC 信息列表
        """
        result = []

        for npc in self.characters.all_npcs():
            if not npc.is_alive or not npc.schedule:
                continue

            slot = npc.schedule.get_slot(slot_name)
            if slot and slot.location == location_id:
                result.append({
                    "npc_id": npc.id,
                    "npc_name": npc.name,
                    "activity": slot.activity,
                    "description": slot.description,
                    "interruptible": slot.interruptible
                })

        return result
