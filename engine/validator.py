"""
AI 输出验证器 - 校验 AI 输出的合法性

功能：
- 检查 ID 白名单（NPC、地点、物品、技能）
- 检查硬规则（不允许死亡复活、时间倒流等）
- 违规时降级处理
"""

import re
import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """验证错误"""
    code: str
    message: str
    severity: str = "warning"  # warning, error, critical
    context: str = ""


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    sanitized_content: Optional[str] = None


class AIValidator:
    """
    AI 输出验证器

    校验 AI 生成的内容是否符合游戏规则和世界设定。
    """

    def __init__(self):
        # ID 白名单
        self._valid_npcs: Set[str] = set()
        self._valid_locations: Set[str] = set()
        self._valid_items: Set[str] = set()
        self._valid_skills: Set[str] = set()

        # 禁止词列表
        self._forbidden_patterns: List[Tuple[str, str]] = [
            (r"复活|死而复生|起死回生", "dead_resurrection"),
            (r"时光倒流|回到过去|时间逆转", "time_reversal"),
            (r"瞬间突破|立刻飞升|一步登天", "instant_breakthrough"),
        ]

        # NPC 名称映射（用于检测提及）
        self._npc_names: Dict[str, str] = {}  # {name/nickname: npc_id}

    def register_valid_npcs(self, npcs: Dict[str, Dict[str, Any]]) -> None:
        """
        注册有效的 NPC

        Args:
            npcs: {npc_id: {"name": ..., "nickname": ...}}
        """
        self._valid_npcs.clear()
        self._npc_names.clear()

        for npc_id, data in npcs.items():
            self._valid_npcs.add(npc_id)
            if "name" in data:
                self._npc_names[data["name"]] = npc_id
            if "nickname" in data and data["nickname"]:
                self._npc_names[data["nickname"]] = npc_id

    def register_valid_locations(self, locations: Set[str]) -> None:
        """注册有效的地点 ID"""
        self._valid_locations = locations

    def register_valid_items(self, items: Set[str]) -> None:
        """注册有效的物品 ID"""
        self._valid_items = items

    def register_valid_skills(self, skills: Set[str]) -> None:
        """注册有效的技能 ID"""
        self._valid_skills = skills

    def validate_narrative(self, content: str) -> ValidationResult:
        """
        验证叙事内容

        Args:
            content: AI 生成的叙事内容

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 检查禁止模式
        for pattern, code in self._forbidden_patterns:
            if re.search(pattern, content):
                errors.append(ValidationError(
                    code=code,
                    message=f"检测到禁止内容: {pattern}",
                    severity="error",
                    context=content[:100]
                ))

        # 检查是否提及未知 NPC
        # 简单检查：如果内容中出现「XXX」格式的对话但 XXX 不在白名单中
        dialogue_pattern = r"「([^」]+)」"
        # 这里不检查对话内容，因为那是 NPC 说的话

        is_valid = len(errors) == 0
        sanitized = self._sanitize_content(content, errors) if not is_valid else content

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            sanitized_content=sanitized
        )

    def validate_ai_action(self, action: Dict[str, Any]) -> ValidationResult:
        """
        验证 AI 动作输出

        Args:
            action: AI 输出的动作字典

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 检查地点
        if "location" in action:
            loc = action["location"]
            if loc not in self._valid_locations:
                errors.append(ValidationError(
                    code="invalid_location",
                    message=f"无效的地点 ID: {loc}",
                    severity="error"
                ))

        # 检查 NPC
        if "npc_id" in action:
            npc = action["npc_id"]
            if npc not in self._valid_npcs:
                errors.append(ValidationError(
                    code="invalid_npc",
                    message=f"无效的 NPC ID: {npc}",
                    severity="error"
                ))

        # 检查物品
        if "item_id" in action:
            item = action["item_id"]
            if item not in self._valid_items:
                errors.append(ValidationError(
                    code="invalid_item",
                    message=f"无效的物品 ID: {item}",
                    severity="error"
                ))

        # 检查技能
        if "skill_id" in action:
            skill = action["skill_id"]
            if skill not in self._valid_skills:
                errors.append(ValidationError(
                    code="invalid_skill",
                    message=f"无效的技能 ID: {skill}",
                    severity="error"
                ))

        # 检查关系变化范围
        if "relationship_change" in action:
            for npc_id, changes in action["relationship_change"].items():
                for dim, delta in changes.items():
                    if abs(delta) > 20:
                        warnings.append(ValidationError(
                            code="excessive_relationship_change",
                            message=f"关系变化过大: {npc_id}.{dim} = {delta}",
                            severity="warning"
                        ))

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    def validate_state_change(
        self,
        change_type: str,
        old_state: Any,
        new_state: Any
    ) -> ValidationResult:
        """
        验证状态变化

        Args:
            change_type: 变化类型
            old_state: 旧状态
            new_state: 新状态

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        if change_type == "npc_alive":
            # 检查死亡复活
            if old_state is False and new_state is True:
                errors.append(ValidationError(
                    code="dead_resurrection",
                    message="NPC 不能复活",
                    severity="critical"
                ))

        elif change_type == "game_time":
            # 检查时间倒流
            if new_state < old_state:
                errors.append(ValidationError(
                    code="time_reversal",
                    message="游戏时间不能倒流",
                    severity="critical"
                ))

        elif change_type == "player_realm":
            # 检查境界跳跃（简化：不能跳超过1级）
            if new_state - old_state > 1:
                warnings.append(ValidationError(
                    code="realm_jump",
                    message=f"境界跳跃过大: {old_state} -> {new_state}",
                    severity="warning"
                ))

        is_valid = len([e for e in errors if e.severity == "critical"]) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    def _sanitize_content(
        self,
        content: str,
        errors: List[ValidationError]
    ) -> str:
        """
        清理违规内容

        Args:
            content: 原内容
            errors: 错误列表

        Returns:
            清理后的内容
        """
        sanitized = content

        for error in errors:
            if error.code == "dead_resurrection":
                sanitized = re.sub(
                    r"复活|死而复生|起死回生",
                    "[描述已修正]",
                    sanitized
                )
            elif error.code == "time_reversal":
                sanitized = re.sub(
                    r"时光倒流|回到过去|时间逆转",
                    "[描述已修正]",
                    sanitized
                )
            elif error.code == "instant_breakthrough":
                sanitized = re.sub(
                    r"瞬间突破|立刻飞升|一步登天",
                    "[描述已修正]",
                    sanitized
                )

        return sanitized

    def get_fallback_narrative(self, context: str = "") -> str:
        """
        获取降级叙事（当验证失败时使用）

        Args:
            context: 上下文提示

        Returns:
            安全的降级叙事
        """
        fallbacks = [
            "时光流转，岁月静好。",
            "一切如常，波澜不惊。",
            "日复一日，修行不辍。",
        ]

        import random
        return random.choice(fallbacks)


class ConfigValidator:
    """
    配置文件验证器

    用于验证 config/*.yaml 文件的完整性和一致性。
    """

    def __init__(self):
        self._locations: Set[str] = set()
        self._npcs: Set[str] = set()
        self._events: Set[str] = set()
        self.errors: List[str] = []

    def load_locations(self, locations: Dict[str, Any]) -> None:
        """加载地点配置"""
        self._locations = set(locations.keys())

    def load_npcs(self, npcs: Dict[str, Any]) -> None:
        """加载 NPC 配置"""
        self._npcs = set(npcs.keys())

    def load_events(self, events: Dict[str, Any]) -> None:
        """加载事件配置"""
        self._events = set(events.keys())

    def validate_npc_locations(self, npcs: Dict[str, Any]) -> List[str]:
        """
        验证 NPC 配置中的地点引用

        Args:
            npcs: NPC 配置

        Returns:
            错误列表
        """
        errors = []

        for npc_id, npc_data in npcs.items():
            # 检查 home_location
            home = npc_data.get('home_location', '')
            if home and home not in self._locations:
                errors.append(
                    f"NPC '{npc_id}' 的 home_location '{home}' 不存在"
                )

            # 检查日程中的地点
            schedule = npc_data.get('schedule', {})
            for slot, slot_data in schedule.items():
                loc = slot_data.get('location', '')
                if loc and loc not in self._locations:
                    errors.append(
                        f"NPC '{npc_id}' 日程 {slot} 的地点 '{loc}' 不存在"
                    )

        return errors

    def validate_event_references(self, events: Dict[str, Any]) -> List[str]:
        """
        验证事件配置中的引用

        Args:
            events: 事件配置

        Returns:
            错误列表
        """
        errors = []

        for event_id, event_data in events.items():
            # 检查地点
            window = event_data.get('window', {})
            locations = window.get('locations', [])
            for loc in locations:
                if loc and loc not in self._locations:
                    errors.append(
                        f"事件 '{event_id}' 引用了不存在的地点 '{loc}'"
                    )

            # 检查 NPC
            conditions = event_data.get('conditions', {})
            npc_alive = conditions.get('npc_alive', [])
            for npc in npc_alive:
                if npc not in self._npcs:
                    errors.append(
                        f"事件 '{event_id}' 引用了不存在的 NPC '{npc}'"
                    )

            npc_at_location = conditions.get('npc_at_location', {})
            for npc in npc_at_location.keys():
                if npc not in self._npcs:
                    errors.append(
                        f"事件 '{event_id}' 引用了不存在的 NPC '{npc}'"
                    )

        return errors

    def validate_world_connections(
        self,
        locations: Dict[str, Any],
        connections: List[Dict[str, Any]]
    ) -> List[str]:
        """
        验证世界连接配置

        Args:
            locations: 地点配置
            connections: 连接配置

        Returns:
            错误列表
        """
        errors = []
        location_ids = set(locations.keys())

        for conn in connections:
            from_id = conn.get('from', '')
            to_id = conn.get('to', '')

            if from_id not in location_ids:
                errors.append(f"连接引用了不存在的地点 '{from_id}'")
            if to_id not in location_ids:
                errors.append(f"连接引用了不存在的地点 '{to_id}'")

        return errors

    def run_all_validations(
        self,
        world_config: Dict[str, Any],
        npcs_config: Dict[str, Any],
        events_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        运行所有验证

        Args:
            world_config: 世界配置
            npcs_config: NPC 配置
            events_config: 事件配置

        Returns:
            (是否通过, 错误列表)
        """
        all_errors = []

        # 加载基础数据
        locations = world_config.get('locations', {})
        self.load_locations(locations)
        self.load_npcs(npcs_config.get('npcs', {}))
        self.load_events(events_config.get('events', {}))

        # 验证 NPC 地点引用
        errors = self.validate_npc_locations(npcs_config.get('npcs', {}))
        all_errors.extend(errors)

        # 验证事件引用
        errors = self.validate_event_references(events_config.get('events', {}))
        all_errors.extend(errors)

        # 验证世界连接
        errors = self.validate_world_connections(
            locations,
            world_config.get('connections', [])
        )
        all_errors.extend(errors)

        is_valid = len(all_errors) == 0
        return is_valid, all_errors
