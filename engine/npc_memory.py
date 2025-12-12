"""
NPC 记忆系统 - 管理 NPC 对玩家互动的记忆

功能：
- 核心记忆（core）：永久存储的关键事件
- 近期记忆（recent）：最近的互动细节
- 摘要记忆（summaries）：压缩后的记忆
- 记忆检索与相关性排序
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

from .event_bus import EventBus, GameEvents


logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """单条记忆"""
    id: str
    content: str
    emotion: str = ""           # 情感标签
    importance: int = 5         # 重要性 1-10
    game_day: int = 0           # 游戏天数
    game_year: float = 0.0      # 游戏年份
    location: str = ""          # 发生地点
    tags: List[str] = field(default_factory=list)
    is_core: bool = False       # 是否为核心记忆


@dataclass
class MemorySummary:
    """记忆摘要"""
    id: str
    content: str
    period_start: int           # 开始天数
    period_end: int             # 结束天数
    source_count: int           # 来源记忆数量
    key_events: List[str] = field(default_factory=list)


class NPCMemoryStore:
    """
    单个 NPC 的记忆存储

    三层记忆结构：
    - core: 永久记忆（关键转折点）
    - recent: 近期记忆（详细互动）
    - summaries: 摘要记忆（压缩的历史）
    """

    # 配置
    MAX_RECENT_MEMORIES = 20
    SUMMARY_THRESHOLD = 15      # 超过此数量触发摘要
    CORE_IMPORTANCE_THRESHOLD = 8  # 重要性>=8自动成为核心记忆

    def __init__(self, npc_id: str):
        self.npc_id = npc_id
        self.core: List[Memory] = []
        self.recent: List[Memory] = []
        self.summaries: List[MemorySummary] = []
        self._memory_counter = 0

    def add_memory(
        self,
        content: str,
        emotion: str = "",
        importance: int = 5,
        game_day: int = 0,
        game_year: float = 0.0,
        location: str = "",
        tags: Optional[List[str]] = None
    ) -> Memory:
        """
        添加新记忆

        Args:
            content: 记忆内容
            emotion: 情感标签
            importance: 重要性 1-10
            game_day: 游戏天数
            game_year: 游戏年份
            location: 发生地点
            tags: 标签列表

        Returns:
            创建的记忆对象
        """
        self._memory_counter += 1
        memory_id = f"{self.npc_id}_mem_{self._memory_counter}"

        is_core = importance >= self.CORE_IMPORTANCE_THRESHOLD

        memory = Memory(
            id=memory_id,
            content=content,
            emotion=emotion,
            importance=importance,
            game_day=game_day,
            game_year=game_year,
            location=location,
            tags=tags or [],
            is_core=is_core
        )

        if is_core:
            self.core.append(memory)
            logger.info(
                f"[Memory] {self.npc_id} 核心记忆: {content[:30]}... "
                f"(重要性:{importance})"
            )
        else:
            self.recent.append(memory)

        # 检查是否需要压缩
        if len(self.recent) > self.MAX_RECENT_MEMORIES:
            self._trigger_compression_needed()

        return memory

    def _trigger_compression_needed(self):
        """标记需要压缩"""
        logger.debug(
            f"[Memory] {self.npc_id} 近期记忆过多 "
            f"({len(self.recent)}), 需要压缩"
        )

    def should_summarize(self) -> bool:
        """检查是否应该进行摘要"""
        return len(self.recent) >= self.SUMMARY_THRESHOLD

    def compress_memories(
        self,
        summary_content: str,
        memories_to_compress: Optional[List[Memory]] = None
    ) -> MemorySummary:
        """
        压缩记忆

        Args:
            summary_content: 摘要内容（由 AI 生成或模板）
            memories_to_compress: 要压缩的记忆（默认压缩旧的 recent）

        Returns:
            创建的摘要
        """
        if memories_to_compress is None:
            # 默认压缩最旧的一半
            compress_count = len(self.recent) // 2
            memories_to_compress = self.recent[:compress_count]
            self.recent = self.recent[compress_count:]

        if not memories_to_compress:
            return None

        # 创建摘要
        summary_id = f"{self.npc_id}_sum_{len(self.summaries) + 1}"
        summary = MemorySummary(
            id=summary_id,
            content=summary_content,
            period_start=memories_to_compress[0].game_day,
            period_end=memories_to_compress[-1].game_day,
            source_count=len(memories_to_compress),
            key_events=[m.content[:50] for m in memories_to_compress if m.importance >= 6]
        )

        self.summaries.append(summary)

        logger.info(
            f"[Memory] {self.npc_id} 压缩 {len(memories_to_compress)} 条记忆 "
            f"-> 摘要 (第{summary.period_start}-{summary.period_end}天)"
        )

        return summary

    def retrieve_relevant(
        self,
        query: str = "",
        k: int = 5,
        include_core: bool = True,
        include_recent: bool = True,
        include_summaries: bool = True
    ) -> List[Memory]:
        """
        检索相关记忆

        Args:
            query: 查询关键词（简单匹配）
            k: 返回数量
            include_core: 是否包含核心记忆
            include_recent: 是否包含近期记忆
            include_summaries: 是否包含摘要

        Returns:
            相关记忆列表
        """
        candidates = []

        if include_core:
            candidates.extend(self.core)

        if include_recent:
            candidates.extend(self.recent)

        # 如果有查询词，进行简单匹配
        if query:
            query_lower = query.lower()
            scored = []
            for mem in candidates:
                score = 0
                if query_lower in mem.content.lower():
                    score += 5
                for tag in mem.tags:
                    if query_lower in tag.lower():
                        score += 2
                if mem.emotion and query_lower in mem.emotion.lower():
                    score += 1
                # 重要性加权
                score += mem.importance / 2
                scored.append((score, mem))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [mem for _, mem in scored[:k]]
        else:
            # 无查询词，按重要性和时间排序
            candidates.sort(
                key=lambda m: (m.importance, m.game_day),
                reverse=True
            )
            return candidates[:k]

    def get_recent_context(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近记忆上下文（用于 AI）

        Args:
            count: 数量

        Returns:
            记忆上下文列表
        """
        recent = self.recent[-count:] if self.recent else []
        return [
            {
                "content": m.content,
                "emotion": m.emotion,
                "importance": m.importance,
                "day": m.game_day
            }
            for m in recent
        ]

    def get_core_context(self) -> List[Dict[str, Any]]:
        """获取核心记忆上下文"""
        return [
            {
                "content": m.content,
                "emotion": m.emotion,
                "importance": m.importance,
                "day": m.game_day
            }
            for m in self.core
        ]

    def to_dict(self) -> dict:
        """序列化"""
        return {
            "npc_id": self.npc_id,
            "memory_counter": self._memory_counter,
            "core": [
                {
                    "id": m.id,
                    "content": m.content,
                    "emotion": m.emotion,
                    "importance": m.importance,
                    "game_day": m.game_day,
                    "game_year": m.game_year,
                    "location": m.location,
                    "tags": m.tags,
                    "is_core": m.is_core
                }
                for m in self.core
            ],
            "recent": [
                {
                    "id": m.id,
                    "content": m.content,
                    "emotion": m.emotion,
                    "importance": m.importance,
                    "game_day": m.game_day,
                    "game_year": m.game_year,
                    "location": m.location,
                    "tags": m.tags,
                    "is_core": m.is_core
                }
                for m in self.recent
            ],
            "summaries": [
                {
                    "id": s.id,
                    "content": s.content,
                    "period_start": s.period_start,
                    "period_end": s.period_end,
                    "source_count": s.source_count,
                    "key_events": s.key_events
                }
                for s in self.summaries
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPCMemoryStore":
        """从字典创建"""
        store = cls(data["npc_id"])
        store._memory_counter = data.get("memory_counter", 0)

        for m_data in data.get("core", []):
            mem = Memory(
                id=m_data["id"],
                content=m_data["content"],
                emotion=m_data.get("emotion", ""),
                importance=m_data.get("importance", 5),
                game_day=m_data.get("game_day", 0),
                game_year=m_data.get("game_year", 0.0),
                location=m_data.get("location", ""),
                tags=m_data.get("tags", []),
                is_core=True
            )
            store.core.append(mem)

        for m_data in data.get("recent", []):
            mem = Memory(
                id=m_data["id"],
                content=m_data["content"],
                emotion=m_data.get("emotion", ""),
                importance=m_data.get("importance", 5),
                game_day=m_data.get("game_day", 0),
                game_year=m_data.get("game_year", 0.0),
                location=m_data.get("location", ""),
                tags=m_data.get("tags", []),
                is_core=False
            )
            store.recent.append(mem)

        for s_data in data.get("summaries", []):
            summary = MemorySummary(
                id=s_data["id"],
                content=s_data["content"],
                period_start=s_data["period_start"],
                period_end=s_data["period_end"],
                source_count=s_data["source_count"],
                key_events=s_data.get("key_events", [])
            )
            store.summaries.append(summary)

        return store


class NPCMemoryManager:
    """
    NPC 记忆管理器

    管理所有 NPC 的记忆系统。
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self._stores: Dict[str, NPCMemoryStore] = {}

    def get_store(self, npc_id: str) -> NPCMemoryStore:
        """获取或创建 NPC 记忆存储"""
        if npc_id not in self._stores:
            self._stores[npc_id] = NPCMemoryStore(npc_id)
        return self._stores[npc_id]

    def add_memory(
        self,
        npc_id: str,
        content: str,
        emotion: str = "",
        importance: int = 5,
        game_day: int = 0,
        game_year: float = 0.0,
        location: str = "",
        tags: Optional[List[str]] = None
    ) -> Memory:
        """
        为 NPC 添加记忆

        Args:
            npc_id: NPC ID
            content: 记忆内容
            emotion: 情感标签
            importance: 重要性
            game_day: 游戏天数
            game_year: 游戏年份
            location: 地点
            tags: 标签

        Returns:
            创建的记忆
        """
        store = self.get_store(npc_id)
        memory = store.add_memory(
            content=content,
            emotion=emotion,
            importance=importance,
            game_day=game_day,
            game_year=game_year,
            location=location,
            tags=tags
        )

        # 发布事件
        if self.event_bus:
            self.event_bus.publish(
                GameEvents.MEMORY_ADDED,
                data={
                    "npc_id": npc_id,
                    "memory_id": memory.id,
                    "content": content,
                    "importance": importance,
                    "is_core": memory.is_core
                },
                source="memory_manager"
            )

        return memory

    def retrieve_relevant(
        self,
        npc_id: str,
        query: str = "",
        k: int = 5
    ) -> List[Memory]:
        """检索 NPC 的相关记忆"""
        store = self.get_store(npc_id)
        return store.retrieve_relevant(query, k)

    def should_summarize(self, npc_id: str) -> bool:
        """检查 NPC 是否需要摘要"""
        store = self.get_store(npc_id)
        return store.should_summarize()

    def compress_memories(
        self,
        npc_id: str,
        summary_content: str
    ) -> Optional[MemorySummary]:
        """压缩 NPC 的记忆"""
        store = self.get_store(npc_id)
        return store.compress_memories(summary_content)

    def build_context(self, npc_id: str) -> Dict[str, Any]:
        """
        构建 NPC 记忆上下文（用于 AI）

        Args:
            npc_id: NPC ID

        Returns:
            记忆上下文
        """
        store = self.get_store(npc_id)

        return {
            "core_memories": store.get_core_context(),
            "recent_memories": store.get_recent_context(5),
            "memory_stats": {
                "core_count": len(store.core),
                "recent_count": len(store.recent),
                "summary_count": len(store.summaries)
            }
        }

    def to_dict(self) -> dict:
        """序列化"""
        return {
            npc_id: store.to_dict()
            for npc_id, store in self._stores.items()
        }

    def load_state(self, state: dict) -> None:
        """加载状态"""
        for npc_id, store_data in state.items():
            self._stores[npc_id] = NPCMemoryStore.from_dict(store_data)
