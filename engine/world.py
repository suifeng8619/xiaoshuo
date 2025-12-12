"""
世界管理器 - 管理地点、连接、旅行时间

功能：
- 加载 config/world.yaml 构建地点图
- 提供地点查询、可达性判断、旅行时间计算
- 与 TimeSystem 对接处理旅行时间消耗
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yaml


@dataclass
class Location:
    """地点数据"""
    id: str
    name: str
    type: str  # sect, city, wild, secret_realm, dwelling
    region: str
    description: str
    spirit_density: float = 1.0
    danger_level: str = "none"  # none, low, medium, high, dangerous
    can_rest: bool = False
    can_save: bool = False
    parent: Optional[str] = None
    npcs: List[str] = None

    def __post_init__(self):
        if self.npcs is None:
            self.npcs = []


@dataclass
class Connection:
    """地点连接"""
    from_id: str
    to_id: str
    travel_time: int  # 时辰
    bidirectional: bool = True


class WorldManager:
    """
    世界管理器

    管理地点图和旅行逻辑。
    """

    def __init__(self, config_path: str = "config/world.yaml"):
        """
        初始化世界管理器

        Args:
            config_path: 世界配置文件路径
        """
        self.config_path = Path(config_path)
        self.locations: Dict[str, Location] = {}
        self.connections: Dict[str, Dict[str, int]] = {}  # {from_id: {to_id: travel_time}}
        self.travel_modifiers: Dict[str, float] = {}
        self.starter_location: str = "player_cave"

        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"世界配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 加载地点
        for loc_id, loc_data in config.get('locations', {}).items():
            self.locations[loc_id] = Location(
                id=loc_data.get('id', loc_id),
                name=loc_data.get('name', loc_id),
                type=loc_data.get('type', 'unknown'),
                region=loc_data.get('region', 'unknown'),
                description=loc_data.get('description', ''),
                spirit_density=loc_data.get('spirit_density', 1.0),
                danger_level=loc_data.get('danger_level', 'none'),
                can_rest=loc_data.get('can_rest', False),
                can_save=loc_data.get('can_save', False),
                parent=loc_data.get('parent'),
                npcs=loc_data.get('npcs', [])
            )

        # 加载连接
        for conn in config.get('connections', []):
            from_id = conn['from']
            to_id = conn['to']
            travel_time = conn.get('travel_time', 1)
            bidirectional = conn.get('bidirectional', True)

            # 添加正向连接
            if from_id not in self.connections:
                self.connections[from_id] = {}
            self.connections[from_id][to_id] = travel_time

            # 添加反向连接
            if bidirectional:
                if to_id not in self.connections:
                    self.connections[to_id] = {}
                self.connections[to_id][from_id] = travel_time

        # 加载旅行修正
        self.travel_modifiers = config.get('travel_modifiers', {
            'walk': 1.0,
            'fly': 0.2,
            'teleport': 0
        })

        # 起始位置
        self.starter_location = config.get('starter_location', 'player_cave')

    def get_location(self, location_id: str) -> Optional[Location]:
        """
        获取地点信息

        Args:
            location_id: 地点 ID

        Returns:
            Location 对象，不存在则返回 None
        """
        return self.locations.get(location_id)

    def get_location_by_name(self, name: str) -> Optional[Location]:
        """
        按名称查找地点

        Args:
            name: 地点名称

        Returns:
            Location 对象，不存在则返回 None
        """
        for loc in self.locations.values():
            if loc.name == name:
                return loc
        return None

    def can_travel(self, from_id: str, to_id: str) -> bool:
        """
        检查两地是否可达

        Args:
            from_id: 起点 ID
            to_id: 终点 ID

        Returns:
            是否可直接到达
        """
        if from_id not in self.connections:
            return False
        return to_id in self.connections[from_id]

    def get_travel_time(self, from_id: str, to_id: str, mode: str = "walk") -> int:
        """
        获取旅行时间

        Args:
            from_id: 起点 ID
            to_id: 终点 ID
            mode: 移动方式 (walk/fly/teleport)

        Returns:
            旅行时间（时辰），不可达返回 -1
        """
        if not self.can_travel(from_id, to_id):
            return -1

        base_time = self.connections[from_id][to_id]
        modifier = self.travel_modifiers.get(mode, 1.0)

        # 瞬移特殊处理
        if modifier == 0:
            return 0

        return max(1, int(base_time * modifier))

    def get_adjacent_locations(self, location_id: str) -> List[str]:
        """
        获取相邻地点列表

        Args:
            location_id: 当前地点 ID

        Returns:
            可直接到达的地点 ID 列表
        """
        if location_id not in self.connections:
            return []
        return list(self.connections[location_id].keys())

    def get_adjacent_with_names(self, location_id: str) -> List[Tuple[str, str, int]]:
        """
        获取相邻地点（含名称和时间）

        Args:
            location_id: 当前地点 ID

        Returns:
            [(location_id, location_name, travel_time), ...]
        """
        result = []
        for adj_id in self.get_adjacent_locations(location_id):
            loc = self.get_location(adj_id)
            if loc:
                time = self.connections[location_id][adj_id]
                result.append((adj_id, loc.name, time))
        return result

    def get_all_locations(self) -> List[Location]:
        """获取所有地点"""
        return list(self.locations.values())

    def get_locations_by_type(self, loc_type: str) -> List[Location]:
        """按类型筛选地点"""
        return [loc for loc in self.locations.values() if loc.type == loc_type]

    def get_locations_with_npc(self, npc_id: str) -> List[Location]:
        """查找某 NPC 可能出现的地点"""
        return [loc for loc in self.locations.values() if npc_id in loc.npcs]

    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """
        查找两地之间的路径（简单 BFS）

        Args:
            from_id: 起点 ID
            to_id: 终点 ID

        Returns:
            路径列表 [from_id, ..., to_id]，不可达返回 None
        """
        if from_id == to_id:
            return [from_id]

        if from_id not in self.locations or to_id not in self.locations:
            return None

        # BFS
        from collections import deque
        visited = {from_id}
        queue = deque([(from_id, [from_id])])

        while queue:
            current, path = queue.popleft()

            for neighbor in self.get_adjacent_locations(current):
                if neighbor == to_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def calculate_path_time(self, path: List[str], mode: str = "walk") -> int:
        """
        计算路径总旅行时间

        Args:
            path: 路径列表
            mode: 移动方式

        Returns:
            总时间（时辰）
        """
        if not path or len(path) < 2:
            return 0

        total = 0
        for i in range(len(path) - 1):
            time = self.get_travel_time(path[i], path[i + 1], mode)
            if time < 0:
                return -1  # 路径不可达
            total += time

        return total

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "locations": {k: vars(v) for k, v in self.locations.items()},
            "starter_location": self.starter_location
        }
