"""
规则引擎模块
负责所有游戏逻辑判定：战斗、升级、技能、物品等
"""
import random
import math
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class DamageResult:
    """伤害计算结果"""
    base_damage: int
    final_damage: int
    is_crit: bool
    is_dodged: bool
    element_bonus: float
    damage_type: str  # physical, magical, true


@dataclass
class CombatAction:
    """战斗行动"""
    action_type: str  # attack, skill, item, flee, defend
    source: dict
    target: dict
    skill_id: Optional[str] = None
    item_id: Optional[str] = None


class RulesEngine:
    """规则引擎"""

    def __init__(self, config: dict):
        self.config = config
        self.realms = {r['id']: r for r in config['realms']}
        self.elements = {e['id']: e for e in config['elements']}
        self.combat_config = config['combat']

    # ==================== 境界系统 ====================

    def get_realm_info(self, realm_id: str, sub_realm_index: int = 0) -> dict:
        """获取境界信息及计算后的属性"""
        realm = self.realms.get(realm_id)
        if not realm:
            raise ValueError(f"Unknown realm: {realm_id}")

        multiplier = realm.get('multiplier_per_sub', 1.0) ** sub_realm_index

        return {
            "id": realm['id'],
            "name": realm['name'],
            "sub_realm": realm['sub_realms'][sub_realm_index],
            "sub_realm_index": sub_realm_index,
            "base_hp": int(realm['base_hp'] * multiplier),
            "base_mp": int(realm['base_mp'] * multiplier),
            "base_attack": int(realm['base_attack'] * multiplier),
            "base_defense": int(realm['base_defense'] * multiplier),
            "exp_to_next": int(realm['exp_to_next'] * multiplier)
        }

    def can_breakthrough(self, character: dict) -> Tuple[bool, str]:
        """检查是否可以突破"""
        exp = character['exp']
        realm = character['realm']

        if exp['current'] < exp['to_next_level']:
            return False, f"经验不足，需要 {exp['to_next_level']} 点"

        # 获取当前境界配置
        realm_config = self.realms[realm['id']]
        sub_realms = realm_config['sub_realms']

        # 检查是否是当前境界的最后一个小境界
        if realm['sub_realm_index'] >= len(sub_realms) - 1:
            # 需要突破到下一个大境界
            realm_ids = list(self.realms.keys())
            current_idx = realm_ids.index(realm['id'])
            if current_idx >= len(realm_ids) - 1:
                return False, "已达最高境界"

            # 可以突破到下一大境界
            return True, "可以突破到下一大境界"
        else:
            # 小境界突破
            return True, "可以突破到下一小境界"

    def perform_breakthrough(self, character: dict) -> dict:
        """执行突破，返回结果"""
        can_break, msg = self.can_breakthrough(character)
        if not can_break:
            return {"success": False, "message": msg}

        realm = character['realm']
        realm_config = self.realms[realm['id']]
        sub_realms = realm_config['sub_realms']

        # 扣除经验
        character['exp']['current'] -= character['exp']['to_next_level']

        old_realm_name = f"{realm['name']} {realm['sub_realm']}"

        if realm['sub_realm_index'] >= len(sub_realms) - 1:
            # 大境界突破
            realm_ids = list(self.realms.keys())
            current_idx = realm_ids.index(realm['id'])
            new_realm_id = realm_ids[current_idx + 1]
            new_realm_config = self.realms[new_realm_id]

            character['realm'] = {
                "id": new_realm_id,
                "name": new_realm_config['name'],
                "sub_realm": new_realm_config['sub_realms'][0],
                "sub_realm_index": 0
            }

            # 大境界突破给额外属性点
            character['attribute_points'] = character.get('attribute_points', 0) + 10
        else:
            # 小境界突破
            new_sub_index = realm['sub_realm_index'] + 1
            character['realm']['sub_realm'] = sub_realms[new_sub_index]
            character['realm']['sub_realm_index'] = new_sub_index

            # 小境界突破给少量属性点
            character['attribute_points'] = character.get('attribute_points', 0) + 3

        # 更新下一级所需经验
        new_realm_info = self.get_realm_info(
            character['realm']['id'],
            character['realm']['sub_realm_index']
        )
        character['exp']['to_next_level'] = new_realm_info['exp_to_next']

        # 重新计算属性
        self.recalculate_attributes(character)

        new_realm_name = f"{character['realm']['name']} {character['realm']['sub_realm']}"

        # 更新统计
        character['statistics']['breakthroughs'] = character['statistics'].get('breakthroughs', 0) + 1

        return {
            "success": True,
            "old_realm": old_realm_name,
            "new_realm": new_realm_name,
            "attribute_points_gained": 10 if realm['sub_realm_index'] >= len(sub_realms) - 1 else 3,
            "message": f"突破成功！从 {old_realm_name} 晋升为 {new_realm_name}"
        }

    def recalculate_attributes(self, character: dict) -> None:
        """重新计算角色所有属性"""
        realm_info = self.get_realm_info(
            character['realm']['id'],
            character['realm']['sub_realm_index']
        )

        primary = character['primary_attributes']
        derived = character['derived_attributes']

        # 获取属性效果配置
        attr_config = {a['id']: a['effects'] for a in self.config['attributes']['primary']}

        # 基础值来自境界
        base_hp = realm_info['base_hp']
        base_mp = realm_info['base_mp']
        base_attack = realm_info['base_attack']
        base_defense = realm_info['base_defense']

        # 一级属性加成
        bonus_hp = primary['constitution'] * attr_config['constitution']['hp']
        bonus_mp = primary['spirit'] * attr_config['spirit']['mp']
        bonus_attack = primary['strength'] * attr_config['strength']['attack']
        bonus_defense = primary['constitution'] * attr_config['constitution']['defense']
        bonus_speed = primary['agility'] * attr_config['agility']['speed']

        # TODO: 装备加成
        equip_bonus = self._calculate_equipment_bonus(character)

        # 最终值
        hp_max = int(base_hp + bonus_hp + equip_bonus.get('hp', 0))
        mp_max = int(base_mp + bonus_mp + equip_bonus.get('mp', 0))

        # 保持当前HP/MP比例
        hp_ratio = derived['hp'] / derived['hp_max'] if derived['hp_max'] > 0 else 1
        mp_ratio = derived['mp'] / derived['mp_max'] if derived['mp_max'] > 0 else 1

        derived['hp_max'] = hp_max
        derived['mp_max'] = mp_max
        derived['hp'] = int(hp_max * hp_ratio)
        derived['mp'] = int(mp_max * mp_ratio)

        derived['attack'] = int(base_attack + bonus_attack + equip_bonus.get('attack', 0))
        derived['defense'] = int(base_defense + bonus_defense + equip_bonus.get('defense', 0))
        derived['speed'] = int(100 + bonus_speed + equip_bonus.get('speed', 0))

        # 暴击和闪避
        derived['crit_rate'] = min(
            0.75,  # 上限
            0.05 + primary['agility'] * attr_config['agility']['crit_rate'] + equip_bonus.get('crit_rate', 0)
        )
        derived['dodge_rate'] = min(
            0.60,  # 上限
            0.05 + primary['agility'] * attr_config['agility']['dodge_rate'] + equip_bonus.get('dodge_rate', 0)
        )
        derived['crit_damage'] = min(
            5.0,  # 上限
            1.5 + equip_bonus.get('crit_damage', 0)
        )

    def _calculate_equipment_bonus(self, character: dict) -> dict:
        """计算装备加成"""
        bonus = {}
        equipment = character.get('equipment', {})

        for slot, item in equipment.items():
            if item and isinstance(item, dict):
                for stat, value in item.get('stats', {}).items():
                    bonus[stat] = bonus.get(stat, 0) + value

        return bonus

    # ==================== 战斗系统 ====================

    def calculate_damage(self,
                         attacker: dict,
                         defender: dict,
                         skill: Optional[dict] = None,
                         attacker_element: Optional[str] = None,
                         defender_element: Optional[str] = None) -> DamageResult:
        """计算伤害"""
        atk_stats = attacker['derived_attributes']
        def_stats = defender['derived_attributes']

        # 技能倍率
        skill_multiplier = 1.0
        mp_cost = 0
        damage_type = "physical"

        if skill:
            skill_multiplier = skill.get('damage_multiplier', 1.0)
            mp_cost = skill.get('mp_cost', 0)
            damage_type = skill.get('damage_type', 'physical')

        # 检查法力是否足够
        if mp_cost > atk_stats.get('mp', 0):
            return DamageResult(
                base_damage=0,
                final_damage=0,
                is_crit=False,
                is_dodged=False,
                element_bonus=0,
                damage_type=damage_type
            )

        # 闪避判定
        dodge_chance = def_stats.get('dodge_rate', 0.05)
        # 境界压制：攻击者境界每高一级，闪避-2%
        realm_diff = self._get_realm_level(attacker) - self._get_realm_level(defender)
        if realm_diff > 0:
            dodge_chance = max(0, dodge_chance - realm_diff * 0.02)

        is_dodged = random.random() < dodge_chance
        if is_dodged:
            return DamageResult(
                base_damage=0,
                final_damage=0,
                is_crit=False,
                is_dodged=True,
                element_bonus=0,
                damage_type=damage_type
            )

        # 基础伤害计算
        attack_value = atk_stats['attack']
        if damage_type == "magical":
            attack_value += atk_stats.get('spell_power', 0)

        base_damage = attack_value * skill_multiplier

        # 防御减伤
        defense_value = def_stats['defense']
        if damage_type == "true":
            defense_value = 0  # 真实伤害无视防御

        damage_reduction = defense_value * self.combat_config['damage_formula']['defense_factor']
        damage_after_def = base_damage - damage_reduction

        # 最低伤害保证
        min_damage = base_damage * self.combat_config['damage_formula']['min_damage_percent']
        damage_after_def = max(damage_after_def, min_damage)

        # 五行克制
        element_bonus = 0.0
        if attacker_element and defender_element:
            element_bonus = self._calculate_element_bonus(attacker_element, defender_element)

        damage_with_element = damage_after_def * (1 + element_bonus)

        # 暴击判定
        crit_chance = atk_stats.get('crit_rate', 0.05)
        is_crit = random.random() < crit_chance

        final_damage = damage_with_element
        if is_crit:
            crit_multiplier = atk_stats.get('crit_damage', 1.5)
            final_damage *= crit_multiplier

        # 随机浮动 ±10%
        final_damage *= random.uniform(0.9, 1.1)

        return DamageResult(
            base_damage=int(base_damage),
            final_damage=int(final_damage),
            is_crit=is_crit,
            is_dodged=False,
            element_bonus=element_bonus,
            damage_type=damage_type
        )

    def _get_realm_level(self, character: dict) -> int:
        """获取境界等级（用于比较）"""
        realm = character.get('realm', {})
        if not realm:
            return 0  # 无境界信息，视为凡人

        realm_ids = list(self.realms.keys())
        realm_id = realm.get('id', 'mortal')

        try:
            base_level = realm_ids.index(realm_id) * 10
        except ValueError:
            base_level = 0  # 未知境界，视为凡人

        sub_level = realm.get('sub_realm_index', 0)
        return base_level + sub_level

    def _calculate_element_bonus(self, attacker_element: str, defender_element: str) -> float:
        """计算五行克制加成"""
        if attacker_element not in self.elements:
            return 0.0

        element = self.elements[attacker_element]

        if element.get('strong_against') == defender_element:
            return self.config['element_damage_bonus']  # 克制，加伤
        elif element.get('weak_against') == defender_element:
            return -self.config['element_damage_reduction']  # 被克，减伤

        return 0.0

    def apply_damage(self, target: dict, damage: int) -> dict:
        """应用伤害到目标"""
        old_hp = target['derived_attributes']['hp']
        target['derived_attributes']['hp'] = max(0, old_hp - damage)
        new_hp = target['derived_attributes']['hp']

        is_dead = new_hp <= 0
        if is_dead:
            # 兼容NPC和玩家的不同数据结构
            if 'status' in target:
                target['status']['is_alive'] = False
            else:
                target['is_alive'] = False

        return {
            "old_hp": old_hp,
            "new_hp": new_hp,
            "damage_taken": old_hp - new_hp,
            "is_dead": is_dead
        }

    def heal(self, target: dict, amount: int) -> dict:
        """治疗"""
        old_hp = target['derived_attributes']['hp']
        max_hp = target['derived_attributes']['hp_max']
        target['derived_attributes']['hp'] = min(max_hp, old_hp + amount)
        new_hp = target['derived_attributes']['hp']

        return {
            "old_hp": old_hp,
            "new_hp": new_hp,
            "healed": new_hp - old_hp
        }

    def calculate_combat_order(self, participants: list) -> list:
        """计算战斗顺序"""
        def get_initiative(p):
            speed = p['derived_attributes'].get('speed', 100)
            return speed + random.randint(1, 20)

        return sorted(participants, key=get_initiative, reverse=True)

    # ==================== 物品系统 ====================

    def can_use_item(self, character: dict, item: dict) -> Tuple[bool, str]:
        """检查是否可以使用物品"""
        # 检查等级/境界要求
        if 'required_realm' in item:
            char_level = self._get_realm_level(character)
            realm_ids = list(self.realms.keys())
            required_level = realm_ids.index(item['required_realm']) * 10
            if char_level < required_level:
                return False, f"需要达到 {self.realms[item['required_realm']]['name']} 才能使用"

        return True, "可以使用"

    def use_consumable(self, character: dict, item: dict) -> dict:
        """使用消耗品"""
        can_use, msg = self.can_use_item(character, item)
        if not can_use:
            return {"success": False, "message": msg}

        effects = []
        item_effects = item.get('effects', {})

        # 恢复生命
        if 'heal_hp' in item_effects:
            result = self.heal(character, item_effects['heal_hp'])
            effects.append(f"恢复 {result['healed']} 点生命")

        # 恢复法力
        if 'heal_mp' in item_effects:
            old_mp = character['derived_attributes']['mp']
            max_mp = character['derived_attributes']['mp_max']
            character['derived_attributes']['mp'] = min(max_mp, old_mp + item_effects['heal_mp'])
            healed = character['derived_attributes']['mp'] - old_mp
            effects.append(f"恢复 {healed} 点法力")

        # 增加经验
        if 'exp' in item_effects:
            character['exp']['current'] += item_effects['exp']
            character['exp']['total'] += item_effects['exp']
            effects.append(f"获得 {item_effects['exp']} 点经验")

        # 添加Buff
        if 'buff' in item_effects:
            self._add_buff(character, item_effects['buff'])
            effects.append(f"获得增益效果: {item_effects['buff']['name']}")

        return {
            "success": True,
            "item_name": item['name'],
            "effects": effects,
            "message": f"使用了 {item['name']}: " + "，".join(effects)
        }

    def _add_buff(self, character: dict, buff: dict) -> None:
        """添加Buff"""
        # 检查是否已存在同类Buff
        existing = None
        for i, b in enumerate(character['buffs']):
            if b['id'] == buff['id']:
                existing = i
                break

        if existing is not None:
            # 检查是否可叠加
            if buff.get('stackable', False):
                max_stacks = buff.get('max_stacks', 5)
                current_stacks = character['buffs'][existing].get('stacks', 1)
                if current_stacks < max_stacks:
                    character['buffs'][existing]['stacks'] = current_stacks + 1
                # 刷新持续时间
                character['buffs'][existing]['duration'] = buff['duration']
            else:
                # 不可叠加，刷新持续时间
                character['buffs'][existing]['duration'] = buff['duration']
        else:
            # 添加新Buff
            new_buff = buff.copy()
            new_buff['stacks'] = 1
            character['buffs'].append(new_buff)

    def process_buffs(self, character: dict) -> list:
        """处理Buff tick，返回事件列表"""
        events = []
        remaining_buffs = []

        for buff in character['buffs']:
            buff['duration'] -= 1

            # 处理Buff效果
            if buff.get('type') == 'dot':
                damage = buff.get('damage_per_tick', 0) * buff.get('stacks', 1)
                self.apply_damage(character, damage)
                events.append(f"受到 {buff['name']} 造成的 {damage} 点伤害")

            elif buff.get('type') == 'hot':
                heal = buff.get('heal_per_tick', 0) * buff.get('stacks', 1)
                self.heal(character, heal)
                events.append(f"{buff['name']} 恢复了 {heal} 点生命")

            # 保留未过期的Buff
            if buff['duration'] > 0:
                remaining_buffs.append(buff)
            else:
                events.append(f"效果 {buff['name']} 已结束")

        character['buffs'] = remaining_buffs
        return events

    # ==================== 技能系统 ====================

    def can_use_skill(self, character: dict, skill: dict) -> Tuple[bool, str]:
        """检查是否可以使用技能"""
        # 检查法力
        mp_cost = skill.get('mp_cost', 0)
        if character['derived_attributes']['mp'] < mp_cost:
            return False, f"法力不足，需要 {mp_cost} 点法力"

        # 检查冷却（如果有冷却系统的话）
        # TODO: 实现冷却系统

        return True, "可以使用"

    def use_skill(self, character: dict, skill: dict, target: dict) -> dict:
        """使用技能"""
        can_use, msg = self.can_use_skill(character, skill)
        if not can_use:
            return {"success": False, "message": msg}

        # 扣除法力
        mp_cost = skill.get('mp_cost', 0)
        character['derived_attributes']['mp'] -= mp_cost

        result = {
            "success": True,
            "skill_name": skill['name'],
            "mp_cost": mp_cost,
            "effects": []
        }

        # 伤害技能
        if 'damage_multiplier' in skill:
            damage_result = self.calculate_damage(
                character, target, skill,
                character.get('element'),
                target.get('element')
            )

            if damage_result.is_dodged:
                result['effects'].append("目标闪避了攻击")
            else:
                apply_result = self.apply_damage(target, damage_result.final_damage)
                crit_text = "暴击！" if damage_result.is_crit else ""
                result['effects'].append(
                    f"{crit_text}对目标造成 {damage_result.final_damage} 点{damage_result.damage_type}伤害"
                )
                if apply_result['is_dead']:
                    result['effects'].append("目标已被击杀")
                    result['target_killed'] = True

            result['damage_result'] = damage_result

        # 治疗技能
        if 'heal_amount' in skill:
            heal_result = self.heal(target, skill['heal_amount'])
            result['effects'].append(f"为目标恢复 {heal_result['healed']} 点生命")

        # 添加Buff
        if 'apply_buff' in skill:
            self._add_buff(target, skill['apply_buff'])
            result['effects'].append(f"为目标添加了 {skill['apply_buff']['name']} 效果")

        return result

    # ==================== 掉落系统 ====================

    def generate_loot(self, loot_table: list, luck_bonus: float = 0) -> list:
        """生成掉落物品"""
        drops = []

        for entry in loot_table:
            drop_chance = entry.get('chance', 1.0) * (1 + luck_bonus)
            if random.random() < drop_chance:
                item = entry['item'].copy()

                # 随机数量
                min_count = entry.get('min_count', 1)
                max_count = entry.get('max_count', 1)
                item['count'] = random.randint(min_count, max_count)

                drops.append(item)

        return drops

    # ==================== 突破失败系统（可选） ====================

    def attempt_breakthrough_with_chance(self, character: dict, success_rate: float = 1.0) -> dict:
        """带成功率的突破尝试"""
        can_break, msg = self.can_breakthrough(character)
        if not can_break:
            return {"success": False, "message": msg}

        # 悟性影响成功率
        perception = character['primary_attributes'].get('perception', 10)
        attr_config = {a['id']: a['effects'] for a in self.config['attributes']['primary']}
        perception_bonus = perception * attr_config['perception'].get('skill_learn_rate', 0.01)

        final_rate = min(1.0, success_rate + perception_bonus)

        if random.random() < final_rate:
            return self.perform_breakthrough(character)
        else:
            # 突破失败
            # 可以设计惩罚：损失部分经验、受伤等
            exp_loss = int(character['exp']['current'] * 0.1)  # 损失10%当前经验
            character['exp']['current'] -= exp_loss

            return {
                "success": False,
                "message": f"突破失败！损失 {exp_loss} 点经验。继续修炼吧...",
                "exp_lost": exp_loss
            }
