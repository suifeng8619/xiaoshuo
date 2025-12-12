"""
关系系统 - 管理玩家与 NPC 间的多维度关系

功能：
- 多维度关系数值（trust/affection/respect/fear）
- 每日/每月衰减
- 变化限制（守护栏）
- 关系事件追踪
"""

from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .event_bus import EventBus, GameEvents


logger = logging.getLogger(__name__)


class RelationshipDimension(Enum):
    """关系维度"""
    TRUST = "trust"           # 信任
    AFFECTION = "affection"   # 好感
    RESPECT = "respect"       # 敬重
    FEAR = "fear"             # 畏惧


@dataclass
class RelationshipChange:
    """关系变化记录"""
    dimension: str
    old_value: int
    new_value: int
    delta: int
    reason: str
    day: int


@dataclass
class NPCRelationship:
    """NPC 关系数据"""
    npc_id: str
    trust: int = 0
    affection: int = 0
    respect: int = 0
    fear: int = 0

    # 追踪数据
    days_since_interaction: int = 0
    total_interactions: int = 0
    change_history: List[RelationshipChange] = field(default_factory=list)

    def get(self, dimension: str) -> int:
        """获取维度值"""
        return getattr(self, dimension, 0)

    def set(self, dimension: str, value: int) -> None:
        """设置维度值"""
        setattr(self, dimension, value)

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "trust": self.trust,
            "affection": self.affection,
            "respect": self.respect,
            "fear": self.fear,
            "days_since_interaction": self.days_since_interaction,
            "total_interactions": self.total_interactions
        }

    @classmethod
    def from_dict(cls, npc_id: str, data: dict) -> "NPCRelationship":
        """从字典创建"""
        return cls(
            npc_id=npc_id,
            trust=data.get("trust", 0),
            affection=data.get("affection", 0),
            respect=data.get("respect", 0),
            fear=data.get("fear", 0),
            days_since_interaction=data.get("days_since_interaction", 0),
            total_interactions=data.get("total_interactions", 0)
        )


class RelationshipSystem:
    """
    关系系统

    管理玩家与所有 NPC 的关系。
    """

    # 关系值范围
    MIN_VALUE = -100
    MAX_VALUE = 100

    # 单次变化限制
    SINGLE_CHANGE_MAX = {
        "trust": 15,
        "affection": 10,
        "respect": 10,
        "fear": 20
    }

    # 每月衰减率
    MONTHLY_DECAY_RATES = {
        "trust": 0.5,
        "affection": 0.3,
        "respect": 0.2,
        "fear": 1.0
    }

    # 每日衰减率 = 月衰减 / 30
    DAILY_DECAY_RATES = {
        k: v / 30 for k, v in MONTHLY_DECAY_RATES.items()
    }

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        初始化关系系统

        Args:
            event_bus: 事件总线
        """
        self.event_bus = event_bus
        self._relationships: Dict[str, NPCRelationship] = {}
        self._history_limit = 50  # 每个 NPC 保留最近50条变化记录

    def init_relationship(
        self,
        npc_id: str,
        initial_values: Optional[Dict[str, int]] = None
    ) -> NPCRelationship:
        """
        初始化 NPC 关系

        Args:
            npc_id: NPC ID
            initial_values: 初始值字典

        Returns:
            创建的关系对象
        """
        if npc_id in self._relationships:
            return self._relationships[npc_id]

        rel = NPCRelationship(npc_id=npc_id)

        if initial_values:
            for dim, val in initial_values.items():
                rel.set(dim, self._clamp(val))

        self._relationships[npc_id] = rel
        return rel

    def get_relationship(self, npc_id: str) -> Optional[NPCRelationship]:
        """获取关系数据"""
        return self._relationships.get(npc_id)

    def get_value(self, npc_id: str, dimension: str) -> int:
        """获取关系维度值"""
        rel = self._relationships.get(npc_id)
        return rel.get(dimension) if rel else 0

    def apply_change(
        self,
        npc_id: str,
        dimension: str,
        delta: int,
        reason: str = "",
        current_day: int = 0,
        bypass_limit: bool = False
    ) -> int:
        """
        应用关系变化

        Args:
            npc_id: NPC ID
            dimension: 关系维度
            delta: 变化量
            reason: 变化原因
            current_day: 当前天数
            bypass_limit: 是否绕过单次变化限制

        Returns:
            实际变化量
        """
        rel = self._relationships.get(npc_id)
        if not rel:
            rel = self.init_relationship(npc_id)

        old_value = rel.get(dimension)

        # 应用单次变化限制
        if not bypass_limit:
            max_change = self.SINGLE_CHANGE_MAX.get(dimension, 10)
            delta = max(-max_change, min(max_change, delta))

        new_value = self._clamp(old_value + delta)
        actual_delta = new_value - old_value

        if actual_delta != 0:
            rel.set(dimension, new_value)

            # 记录历史
            change = RelationshipChange(
                dimension=dimension,
                old_value=old_value,
                new_value=new_value,
                delta=actual_delta,
                reason=reason,
                day=current_day
            )
            rel.change_history.append(change)

            # 限制历史长度
            if len(rel.change_history) > self._history_limit:
                rel.change_history = rel.change_history[-self._history_limit:]

            # 发布事件
            if self.event_bus:
                self.event_bus.publish(
                    GameEvents.RELATIONSHIP_CHANGED,
                    data={
                        "npc_id": npc_id,
                        "dimension": dimension,
                        "old_value": old_value,
                        "new_value": new_value,
                        "delta": actual_delta,
                        "reason": reason
                    },
                    source="relationship_system"
                )

            logger.debug(
                f"[Relationship] {npc_id}.{dimension}: "
                f"{old_value} -> {new_value} ({actual_delta:+d}) [{reason}]"
            )

        return actual_delta

    def apply_changes(
        self,
        npc_id: str,
        changes: Dict[str, int],
        reason: str = "",
        current_day: int = 0
    ) -> Dict[str, int]:
        """
        应用多个维度的变化

        Args:
            npc_id: NPC ID
            changes: {dimension: delta} 变化字典
            reason: 变化原因
            current_day: 当前天数

        Returns:
            实际变化量字典
        """
        results = {}
        for dimension, delta in changes.items():
            actual = self.apply_change(
                npc_id, dimension, delta, reason, current_day
            )
            results[dimension] = actual
        return results

    def record_interaction(self, npc_id: str) -> None:
        """
        记录交互（重置未交互天数）

        Args:
            npc_id: NPC ID
        """
        rel = self._relationships.get(npc_id)
        if rel:
            rel.days_since_interaction = 0
            rel.total_interactions += 1

    def apply_daily_decay(self, current_day: int = 0) -> Dict[str, Dict[str, float]]:
        """
        应用每日衰减

        Args:
            current_day: 当前天数

        Returns:
            衰减结果 {npc_id: {dimension: decay_amount}}
        """
        results = {}

        for npc_id, rel in self._relationships.items():
            # 增加未交互天数
            rel.days_since_interaction += 1

            npc_decay = {}
            for dimension, daily_rate in self.DAILY_DECAY_RATES.items():
                current = rel.get(dimension)

                # 只对正值衰减（fear 除外，fear 向0衰减）
                if dimension == "fear":
                    if current > 0:
                        decay = min(daily_rate, current)
                        rel.set(dimension, current - decay)
                        npc_decay[dimension] = -decay
                    elif current < 0:
                        decay = min(daily_rate, -current)
                        rel.set(dimension, current + decay)
                        npc_decay[dimension] = decay
                else:
                    if current > 0:
                        decay = min(daily_rate, current)
                        rel.set(dimension, int(current - decay))
                        npc_decay[dimension] = -decay

            if npc_decay:
                results[npc_id] = npc_decay

        return results

    def apply_monthly_decay(self, current_day: int = 0) -> Dict[str, Dict[str, float]]:
        """
        应用每月衰减（在月结算时调用）

        Args:
            current_day: 当前天数

        Returns:
            衰减结果
        """
        results = {}

        for npc_id, rel in self._relationships.items():
            npc_decay = {}

            # 根据未交互天数计算额外衰减
            extra_decay_factor = 1.0
            if rel.days_since_interaction > 14:
                extra_decay_factor = 1.5  # 超过两周未互动，衰减加速
            if rel.days_since_interaction > 30:
                extra_decay_factor = 2.0  # 超过一月，衰减翻倍

            for dimension, monthly_rate in self.MONTHLY_DECAY_RATES.items():
                current = rel.get(dimension)
                decay = monthly_rate * extra_decay_factor

                if dimension == "fear":
                    # fear 向0衰减
                    if current > 0:
                        actual_decay = min(decay, current)
                        rel.set(dimension, int(current - actual_decay))
                        npc_decay[dimension] = -actual_decay
                    elif current < 0:
                        actual_decay = min(decay, -current)
                        rel.set(dimension, int(current + actual_decay))
                        npc_decay[dimension] = actual_decay
                else:
                    # 其他维度只从正值衰减
                    if current > 0:
                        actual_decay = min(decay, current)
                        rel.set(dimension, int(current - actual_decay))
                        npc_decay[dimension] = -actual_decay

            if npc_decay:
                results[npc_id] = npc_decay
                logger.debug(
                    f"[Relationship] 月衰减 {npc_id}: {npc_decay} "
                    f"(未互动{rel.days_since_interaction}天)"
                )

        return results

    def get_relationship_level(self, npc_id: str) -> str:
        """
        获取关系等级描述

        Args:
            npc_id: NPC ID

        Returns:
            关系等级描述
        """
        rel = self._relationships.get(npc_id)
        if not rel:
            return "陌生"

        # 综合评分
        score = (
            rel.trust * 0.3 +
            rel.affection * 0.4 +
            rel.respect * 0.2 +
            rel.fear * -0.1
        )

        if score >= 80:
            return "挚交"
        elif score >= 60:
            return "密友"
        elif score >= 40:
            return "友善"
        elif score >= 20:
            return "熟识"
        elif score >= 0:
            return "点头之交"
        elif score >= -20:
            return "疏远"
        elif score >= -50:
            return "敌意"
        else:
            return "仇视"

    def get_all_relationships(self) -> Dict[str, NPCRelationship]:
        """获取所有关系数据"""
        return self._relationships.copy()

    def _clamp(self, value: int) -> int:
        """限制值在有效范围内"""
        return max(self.MIN_VALUE, min(self.MAX_VALUE, value))

    def to_dict(self) -> dict:
        """序列化"""
        return {
            npc_id: rel.to_dict()
            for npc_id, rel in self._relationships.items()
        }

    def load_state(self, state: dict) -> None:
        """加载状态"""
        for npc_id, rel_data in state.items():
            self._relationships[npc_id] = NPCRelationship.from_dict(npc_id, rel_data)

    def build_context(self, npc_id: str) -> Dict[str, Any]:
        """
        构建关系上下文（用于 AI）

        Args:
            npc_id: NPC ID

        Returns:
            关系上下文字典
        """
        rel = self._relationships.get(npc_id)
        if not rel:
            return {
                "level": "陌生",
                "trust": 0,
                "affection": 0,
                "respect": 0,
                "fear": 0,
                "days_since_interaction": 0
            }

        return {
            "level": self.get_relationship_level(npc_id),
            "trust": rel.trust,
            "affection": rel.affection,
            "respect": rel.respect,
            "fear": rel.fear,
            "days_since_interaction": rel.days_since_interaction,
            "total_interactions": rel.total_interactions
        }
