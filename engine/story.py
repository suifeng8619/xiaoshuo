"""
剧情系统 - 管理标记、剧情阶段、线索

功能：
- Flag set/clear/check 操作
- 复合条件判断
- 剧情阶段（StoryPhase）管理
- 线索收集与追踪
"""

from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .event_bus import EventBus, GameEvents


logger = logging.getLogger(__name__)


@dataclass
class Clue:
    """线索"""
    id: str
    name: str
    description: str
    storyline: str
    weight: int = 1
    discovered: bool = False
    discovered_day: int = -1


@dataclass
class StorylineProgress:
    """剧情线进度"""
    storyline: str
    current_phase: int = 0
    clues_collected: List[str] = field(default_factory=list)
    clue_weight_total: int = 0


class FlagManager:
    """
    标记管理器

    管理游戏中的布尔标记，用于追踪事件状态、解锁条件等。
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self._flags: Set[str] = set()
        self._flag_history: List[Dict[str, Any]] = []  # 标记变更历史

    def set_flag(self, flag: str, source: str = "") -> bool:
        """
        设置标记

        Args:
            flag: 标记名称
            source: 来源（用于调试）

        Returns:
            是否是新设置的（之前不存在）
        """
        is_new = flag not in self._flags
        self._flags.add(flag)

        if is_new:
            self._flag_history.append({
                "action": "set",
                "flag": flag,
                "source": source
            })

            if self.event_bus:
                self.event_bus.publish(
                    GameEvents.FLAG_CHANGED,
                    data={"flag": flag, "action": "set", "source": source},
                    source="flag_manager"
                )

            logger.debug(f"[FlagManager] 设置标记: {flag} (来源: {source})")

        return is_new

    def clear_flag(self, flag: str, source: str = "") -> bool:
        """
        清除标记

        Args:
            flag: 标记名称
            source: 来源

        Returns:
            是否成功清除（之前存在）
        """
        if flag in self._flags:
            self._flags.remove(flag)

            self._flag_history.append({
                "action": "clear",
                "flag": flag,
                "source": source
            })

            if self.event_bus:
                self.event_bus.publish(
                    GameEvents.FLAG_CHANGED,
                    data={"flag": flag, "action": "clear", "source": source},
                    source="flag_manager"
                )

            logger.debug(f"[FlagManager] 清除标记: {flag} (来源: {source})")
            return True

        return False

    def has_flag(self, flag: str) -> bool:
        """检查标记是否存在"""
        return flag in self._flags

    def has_all_flags(self, flags: List[str]) -> bool:
        """检查是否所有标记都存在"""
        return all(f in self._flags for f in flags)

    def has_any_flag(self, flags: List[str]) -> bool:
        """检查是否任一标记存在"""
        return any(f in self._flags for f in flags)

    def get_all_flags(self) -> Set[str]:
        """获取所有标记"""
        return self._flags.copy()

    def check_condition(self, condition: Dict[str, Any]) -> bool:
        """
        检查复合条件

        支持的条件格式:
        - {"all": ["flag1", "flag2"]} - 所有标记都存在
        - {"any": ["flag1", "flag2"]} - 任一标记存在
        - {"none": ["flag1", "flag2"]} - 所有标记都不存在
        - {"flag": "flag_name"} - 单个标记存在

        Args:
            condition: 条件字典

        Returns:
            条件是否满足
        """
        if "all" in condition:
            return self.has_all_flags(condition["all"])

        if "any" in condition:
            return self.has_any_flag(condition["any"])

        if "none" in condition:
            return not self.has_any_flag(condition["none"])

        if "flag" in condition:
            return self.has_flag(condition["flag"])

        # 支持嵌套条件
        if "and" in condition:
            return all(self.check_condition(c) for c in condition["and"])

        if "or" in condition:
            return any(self.check_condition(c) for c in condition["or"])

        if "not" in condition:
            return not self.check_condition(condition["not"])

        return True

    def to_dict(self) -> dict:
        """序列化"""
        return {"flags": list(self._flags)}

    def load_state(self, state: dict) -> None:
        """加载状态"""
        self._flags = set(state.get("flags", []))


class StoryManager:
    """
    剧情管理器

    管理剧情阶段和线索系统。
    """

    def __init__(
        self,
        flag_manager: FlagManager,
        event_bus: Optional[EventBus] = None
    ):
        self.flags = flag_manager
        self.event_bus = event_bus

        # 剧情线进度
        self._storylines: Dict[str, StorylineProgress] = {}

        # 线索
        self._clues: Dict[str, Clue] = {}

        # 剧情阶段配置（从 events.yaml 加载）
        self._phase_config: Dict[str, Dict[str, Any]] = {}

    def init_storyline(self, storyline: str) -> None:
        """初始化剧情线"""
        if storyline not in self._storylines:
            self._storylines[storyline] = StorylineProgress(storyline=storyline)

    def get_storyline_phase(self, storyline: str) -> int:
        """获取剧情线当前阶段"""
        progress = self._storylines.get(storyline)
        return progress.current_phase if progress else 0

    def advance_storyline(self, storyline: str, to_phase: Optional[int] = None) -> bool:
        """
        推进剧情线阶段

        Args:
            storyline: 剧情线名称
            to_phase: 目标阶段（默认+1）

        Returns:
            是否成功推进
        """
        self.init_storyline(storyline)
        progress = self._storylines[storyline]

        old_phase = progress.current_phase
        new_phase = to_phase if to_phase is not None else old_phase + 1

        if new_phase > old_phase:
            progress.current_phase = new_phase

            if self.event_bus:
                self.event_bus.publish(
                    GameEvents.QUEST_UPDATED,
                    data={
                        "storyline": storyline,
                        "old_phase": old_phase,
                        "new_phase": new_phase
                    },
                    source="story_manager"
                )

            logger.info(
                f"[StoryManager] 剧情线推进: {storyline} "
                f"phase {old_phase} -> {new_phase}"
            )
            return True

        return False

    def register_clue(
        self,
        clue_id: str,
        name: str,
        description: str,
        storyline: str,
        weight: int = 1
    ) -> None:
        """注册线索"""
        self._clues[clue_id] = Clue(
            id=clue_id,
            name=name,
            description=description,
            storyline=storyline,
            weight=weight
        )

    def discover_clue(self, clue_id: str, current_day: int = 0) -> bool:
        """
        发现线索

        Args:
            clue_id: 线索ID
            current_day: 当前天数

        Returns:
            是否是新发现
        """
        clue = self._clues.get(clue_id)
        if not clue:
            logger.warning(f"[StoryManager] 未知线索: {clue_id}")
            return False

        if clue.discovered:
            return False

        clue.discovered = True
        clue.discovered_day = current_day

        # 更新剧情线进度
        self.init_storyline(clue.storyline)
        progress = self._storylines[clue.storyline]
        progress.clues_collected.append(clue_id)
        progress.clue_weight_total += clue.weight

        logger.info(
            f"[StoryManager] 发现线索: {clue.name} "
            f"({clue.storyline} +{clue.weight})"
        )

        return True

    def get_clue_count(self, storyline: str) -> int:
        """获取剧情线已收集的线索数量"""
        progress = self._storylines.get(storyline)
        return len(progress.clues_collected) if progress else 0

    def get_clue_weight(self, storyline: str) -> int:
        """获取剧情线线索权重总和"""
        progress = self._storylines.get(storyline)
        return progress.clue_weight_total if progress else 0

    def get_discovered_clues(self, storyline: Optional[str] = None) -> List[Clue]:
        """获取已发现的线索"""
        clues = []
        for clue in self._clues.values():
            if clue.discovered:
                if storyline is None or clue.storyline == storyline:
                    clues.append(clue)
        return clues

    def load_phase_config(self, config: Dict[str, Dict[str, Any]]) -> None:
        """
        加载剧情阶段配置

        Args:
            config: 从 events.yaml 加载的 story_phases 配置
        """
        self._phase_config = config

        # 初始化所有剧情线
        for storyline in config.keys():
            self.init_storyline(storyline)

    def load_clue_config(self, config: Dict[str, Dict[str, Any]]) -> None:
        """
        加载线索配置

        Args:
            config: 从 events.yaml 加载的 clues 配置
        """
        for storyline, clues in config.items():
            for clue_id, clue_data in clues.items():
                self.register_clue(
                    clue_id=clue_data.get('id', clue_id),
                    name=clue_data.get('name', clue_id),
                    description=clue_data.get('description', ''),
                    storyline=storyline,
                    weight=clue_data.get('weight', 1)
                )

    def check_phase_advance_conditions(
        self,
        storyline: str,
        relationships: Dict[str, Dict[str, int]]
    ) -> bool:
        """
        检查是否可以推进剧情阶段

        Args:
            storyline: 剧情线
            relationships: 关系数据

        Returns:
            是否满足推进条件
        """
        if storyline not in self._phase_config:
            return False

        progress = self._storylines.get(storyline)
        if not progress:
            return False

        phases = list(self._phase_config[storyline].keys())
        current_idx = progress.current_phase

        if current_idx >= len(phases) - 1:
            return False  # 已是最后阶段

        current_phase_key = phases[current_idx]
        phase_data = self._phase_config[storyline][current_phase_key]
        advance_conditions = phase_data.get('advance_conditions', [])

        for condition in advance_conditions:
            if isinstance(condition, dict):
                # 检查 flag 条件
                if 'flag' in condition:
                    if self.flags.has_flag(condition['flag']):
                        return True

                # 检查关系条件
                for key, value in condition.items():
                    if key.startswith('relationship.'):
                        parts = key.split('.')
                        npc_id = parts[1]
                        dim = parts[2]
                        threshold = int(value.replace('>=', ''))
                        if relationships.get(npc_id, {}).get(dim, 0) >= threshold:
                            return True

        return False

    def to_dict(self) -> dict:
        """序列化"""
        return {
            "storylines": {
                sl: {
                    "current_phase": p.current_phase,
                    "clues_collected": p.clues_collected,
                    "clue_weight_total": p.clue_weight_total
                }
                for sl, p in self._storylines.items()
            },
            "discovered_clues": [
                clue.id for clue in self._clues.values() if clue.discovered
            ]
        }

    def load_state(self, state: dict) -> None:
        """加载状态"""
        for sl_name, sl_data in state.get("storylines", {}).items():
            self.init_storyline(sl_name)
            progress = self._storylines[sl_name]
            progress.current_phase = sl_data.get("current_phase", 0)
            progress.clues_collected = sl_data.get("clues_collected", [])
            progress.clue_weight_total = sl_data.get("clue_weight_total", 0)

        for clue_id in state.get("discovered_clues", []):
            if clue_id in self._clues:
                self._clues[clue_id].discovered = True
