#!/usr/bin/env python3
"""
配置文件验证脚本

用法:
    python scripts/validate_configs.py

验证内容:
- config/world.yaml: 地点和连接配置
- config/npcs.yaml: NPC 配置
- config/events.yaml: 事件配置

返回码:
- 0: 验证通过
- 1: 验证失败
"""

import sys
from pathlib import Path
import yaml

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engine.validator import ConfigValidator


def load_yaml(path: Path) -> dict:
    """加载 YAML 文件"""
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def validate_yaml_syntax(path: Path) -> bool:
    """验证 YAML 语法"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True
    except yaml.YAMLError as e:
        print(f"❌ YAML 语法错误 ({path}): {e}")
        return False


def main():
    config_dir = project_root / "config"

    print("=" * 50)
    print("配置文件验证")
    print("=" * 50)
    print()

    all_valid = True
    errors = []

    # 检查配置文件存在性
    required_files = [
        "world.yaml",
        "npcs.yaml",
        "events.yaml"
    ]

    for filename in required_files:
        filepath = config_dir / filename
        if not filepath.exists():
            print(f"❌ 缺少配置文件: {filepath}")
            all_valid = False
        else:
            print(f"✓ 找到配置文件: {filepath}")

    if not all_valid:
        print()
        print("❌ 配置文件缺失，验证中止")
        return 1

    print()

    # 验证 YAML 语法
    print("检查 YAML 语法...")
    for filename in required_files:
        filepath = config_dir / filename
        if not validate_yaml_syntax(filepath):
            all_valid = False
        else:
            print(f"  ✓ {filename}")

    if not all_valid:
        print()
        print("❌ YAML 语法错误，验证中止")
        return 1

    print()

    # 加载配置
    print("加载配置文件...")
    world_config = load_yaml(config_dir / "world.yaml")
    npcs_config = load_yaml(config_dir / "npcs.yaml")
    events_config = load_yaml(config_dir / "events.yaml")

    print(f"  - 地点: {len(world_config.get('locations', {}))} 个")
    print(f"  - NPC: {len(npcs_config.get('npcs', {}))} 个")
    print(f"  - 事件: {len(events_config.get('events', {}))} 个")
    print()

    # 运行验证
    print("运行交叉引用验证...")
    validator = ConfigValidator()
    is_valid, validation_errors = validator.run_all_validations(
        world_config,
        npcs_config,
        events_config
    )

    if validation_errors:
        all_valid = False
        for error in validation_errors:
            print(f"  ❌ {error}")
    else:
        print("  ✓ 所有引用有效")

    print()

    # 额外检查：NPC 日程覆盖
    print("检查 NPC 日程完整性...")
    npcs = npcs_config.get('npcs', {})
    for npc_id, npc_data in npcs.items():
        schedule = npc_data.get('schedule', {})
        required_slots = ['morning', 'afternoon', 'evening', 'night']
        missing = [s for s in required_slots if s not in schedule]
        if missing:
            print(f"  ⚠ NPC '{npc_id}' 日程缺少时段: {missing}")
        else:
            print(f"  ✓ NPC '{npc_id}' 日程完整")

    print()

    # 额外检查：事件层级分布
    print("检查事件层级分布...")
    events = events_config.get('events', {})
    tiers = {'daily': 0, 'opportunity': 0, 'critical': 0}
    for event_data in events.values():
        tier = event_data.get('tier', 'daily')
        if tier in tiers:
            tiers[tier] += 1

    for tier, count in tiers.items():
        status = "✓" if count > 0 else "⚠"
        print(f"  {status} {tier}: {count} 个事件")

    print()

    # 结果
    print("=" * 50)
    if all_valid:
        print("✅ 所有配置验证通过")
        return 0
    else:
        print("❌ 配置验证失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
