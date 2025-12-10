"""
主游戏循环
整合所有模块，处理玩家输入，驱动游戏进行
"""
import random
from typing import Optional, Tuple
from pathlib import Path

from .state import GameState, Character, Inventory, StoryLog, NPC
from .rules import RulesEngine
from .memory import MemoryManager
from .ai import AIClient, MockAIClient


class Game:
    """主游戏类"""

    def __init__(self,
                 data_dir: str = "data",
                 config_dir: str = "config",
                 use_mock_ai: bool = False,
                 api_key: Optional[str] = None):
        """
        初始化游戏

        Args:
            data_dir: 数据目录
            config_dir: 配置目录
            use_mock_ai: 是否使用模拟AI（测试用）
            api_key: API密钥
        """
        self.data_dir = Path(data_dir)
        self.config_dir = Path(config_dir)

        # 加载配置
        self.state = GameState(data_dir)
        self.config = self.state.load_config(self.config_dir / "cultivation.yaml")
        self.skills_config = self.state.load_config(self.config_dir / "skills.yaml")
        self.monsters_config = self.state.load_config(self.config_dir / "monsters.yaml")

        # 初始化规则引擎
        self.rules = RulesEngine(self.config)

        # 加载世界设定
        world_setting = self._load_world_setting()
        rules_summary = self._load_rules_summary()

        # 初始化记忆管理器
        self.memory = MemoryManager(self.state, world_setting, rules_summary)

        # 初始化AI客户端
        if use_mock_ai:
            self.ai = MockAIClient()
        else:
            self.ai = AIClient(api_key=api_key)

        # 游戏状态
        self.is_running = False
        self.in_combat = False
        self.combat_enemies = []
        self.combat_round = 0

        # 命令解析器
        self.commands = {
            'status': self.cmd_status,
            'look': self.cmd_look,
            'inventory': self.cmd_inventory,
            'skills': self.cmd_skills,
            'move': self.cmd_move,
            'talk': self.cmd_talk,
            'attack': self.cmd_attack,
            'skill': self.cmd_skill,
            'use': self.cmd_use,
            'flee': self.cmd_flee,
            'cultivate': self.cmd_cultivate,
            'breakthrough': self.cmd_breakthrough,
            'addpoint': self.cmd_addpoint,
            'help': self.cmd_help,
            'save': self.cmd_save,
            'quit': self.cmd_quit,
        }

        # 命令别名
        self.aliases = {
            's': 'status',
            'l': 'look',
            'i': 'inventory',
            'inv': 'inventory',
            'go': 'move',
            't': 'talk',
            'a': 'attack',
            'k': 'skill',
            'u': 'use',
            'f': 'flee',
            'run': 'flee',
            'c': 'cultivate',
            'b': 'breakthrough',
            'ap': 'addpoint',
            'h': 'help',
            '?': 'help',
            'q': 'quit',
            'exit': 'quit',
        }

    def _load_world_setting(self) -> str:
        """加载世界设定"""
        world_file = self.data_dir / "world.md"
        if world_file.exists():
            return world_file.read_text(encoding='utf-8')
        return "这是一个充满灵气的仙侠世界..."  # 默认设定

    def _load_rules_summary(self) -> str:
        """加载规则摘要"""
        return """核心规则：
- 境界从凡人到渡劫期，每个大境界有多个小境界
- 战斗伤害 = 攻击 * 技能倍率 - 防御 * 0.5
- 五行相克：金克木、木克土、土克水、水克火、火克金
- 境界压制：高一个大境界，闪避率-2%"""

    def start(self) -> None:
        """启动游戏"""
        self.is_running = True
        self._print_welcome()

        # 检查是否有存档
        char_data = self.state.get('character')
        if char_data:
            self._print(f"\n欢迎回来，{char_data.get('name', '修士')}！")
            self.character = Character(char_data)
        else:
            self._create_character()

        # 显示当前状态
        self.cmd_status([])

        # 主循环
        self._game_loop()

    def _game_loop(self) -> None:
        """主游戏循环"""
        while self.is_running:
            try:
                # 获取玩家输入
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # 解析并执行
                self._process_input(user_input)

            except KeyboardInterrupt:
                self._print("\n\n使用 'quit' 命令保存并退出游戏。")
            except Exception as e:
                self._print(f"\n发生错误: {e}")

    def _process_input(self, user_input: str) -> None:
        """处理玩家输入"""
        # 分割命令和参数
        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 检查别名
        cmd = self.aliases.get(cmd, cmd)

        # 检查是否是系统命令
        if cmd in self.commands:
            self.commands[cmd](args.split() if args else [])
        else:
            # 作为自由行动交给AI处理
            self._handle_free_action(user_input)

    def _handle_free_action(self, action: str) -> None:
        """处理自由行动"""
        # 构建上下文
        context = self.memory.build_context()

        # 让AI生成叙事
        self._print("\n...")
        narrative = self.ai.generate_narrative(context, action)
        self._print(f"\n{narrative}")

        # 记录到剧情日志
        story_log = StoryLog(self.state.get('story_log', {}))
        story_log.add_entry(f"玩家：{action}")
        story_log.add_entry(narrative)
        self.state.set('story_log', story_log.to_dict())

    # ==================== 命令处理 ====================

    def cmd_status(self, args: list) -> None:
        """显示角色状态"""
        char = self.character
        self._print(char.get_status_summary())

    def cmd_look(self, args: list) -> None:
        """查看周围环境"""
        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})

        if not current_scene:
            # 如果没有场景数据，生成一个
            current_scene = self._generate_default_scene()

        # 生成场景描述
        description = self.ai.generate_scene_description(current_scene)
        self._print(f"\n{description}")

        # 显示可互动对象
        if current_scene.get('features'):
            self._print(f"\n你注意到：{', '.join(current_scene['features'])}")

        if current_scene.get('exits'):
            self._print(f"可前往：{', '.join(current_scene['exits'])}")

        # 显示NPC（只显示当前场景的NPC）
        npcs_data = self.state.get('npcs', {})
        char_scene = self.character.data['status']['current_scene']
        present_npcs = [n for n in npcs_data.get('npcs', {}).values()
                       if n.get('location') == char_scene and n.get('is_alive', True)]
        if present_npcs:
            npc_names = [n['name'] for n in present_npcs]
            self._print(f"这里有：{', '.join(npc_names)}")

    def cmd_inventory(self, args: list) -> None:
        """查看物品栏"""
        inv_data = self.state.get('inventory', {})
        inventory = Inventory(inv_data)

        items = inventory.data.get('items', [])
        if not items:
            self._print("\n你的物品栏是空的。")
            return

        self._print("\n【物品栏】")
        for item in items:
            count = item.get('count', 1)
            quality = item.get('quality', 'common')
            quality_name = self._get_quality_name(quality)
            self._print(f"  - {item['name']} x{count} ({quality_name})")

    def cmd_skills(self, args: list) -> None:
        """查看技能"""
        skills = self.character.data.get('skills', [])

        if not skills:
            self._print("\n你还没有学会任何技能。")
            return

        self._print("\n【技能列表】")
        for skill in skills:
            mp_cost = skill.get('mp_cost', 0)
            damage = skill.get('damage_multiplier', 1.0)
            self._print(f"  - {skill['name']}: {skill.get('description', '')} "
                       f"(消耗{mp_cost}法力, {damage*100:.0f}%伤害)")

    def cmd_move(self, args: list) -> None:
        """移动到其他位置"""
        if not args:
            self._print("\n请指定目的地。用法: move <地点>")
            return

        # 战斗中不能移动
        if self.in_combat:
            self._print("\n战斗中无法移动！")
            return

        destination = " ".join(args)

        # 检查是否可以移动
        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})
        exits = current_scene.get('exits', [])

        if destination not in exits:
            self._print(f"\n无法前往 {destination}。可前往：{', '.join(exits)}")
            return

        # 执行移动
        self.character.data['status']['current_scene'] = destination
        self.state.set('character', self.character.to_dict())

        # 更新场景
        new_scene = self._get_or_create_scene(destination)
        world_state['current_scene'] = new_scene
        self.state.set('world', world_state)

        self._print(f"\n你来到了 {destination}。")

        # 检查随机遇敌
        monsters = self._check_random_encounter(destination)
        if monsters:
            self._trigger_encounter(monsters)
        else:
            self.cmd_look([])

    def cmd_talk(self, args: list) -> None:
        """与NPC对话"""
        if not args:
            self._print("\n请指定对话对象。用法: talk <NPC名字> <说的话>")
            return

        # 解析参数
        npc_name = args[0]
        dialogue = " ".join(args[1:]) if len(args) > 1 else "你好"

        # 查找NPC
        npcs_data = self.state.get('npcs', {})
        npc = None
        for n in npcs_data.get('npcs', {}).values():
            if n['name'] == npc_name:
                npc = n
                break

        if not npc:
            self._print(f"\n这里没有叫 {npc_name} 的人。")
            return

        # 构建上下文并生成对话
        context = self.memory.build_context(focus_area='dialogue')
        response = self.ai.generate_dialogue(context, npc, dialogue)

        self._print(f"\n你对{npc_name}说：「{dialogue}」")
        self._print(f"{npc_name}回应道：「{response}」")

        # 记录对话
        story_log = StoryLog(self.state.get('story_log', {}))
        story_log.add_entry(f"玩家对{npc_name}说：「{dialogue}」", "dialogue")
        story_log.add_entry(f"{npc_name}：「{response}」", "dialogue")
        self.state.set('story_log', story_log.to_dict())

    def cmd_attack(self, args: list) -> None:
        """攻击目标"""
        if not args:
            # 战斗中没指定目标，默认攻击第一个敌人
            if self.in_combat and self.combat_enemies:
                target = self.combat_enemies[0]
                self._execute_attack(target)
                return
            self._print("\n请指定攻击目标。用法: attack <目标>")
            return

        target_name = " ".join(args)

        # 战斗中优先查找当前战斗的敌人
        if self.in_combat:
            target = None
            for enemy in self.combat_enemies:
                if enemy['name'] == target_name and enemy.get('is_alive', True):
                    target = enemy
                    break
            if target:
                self._execute_attack(target)
                return
            else:
                self._print(f"\n战斗中找不到目标：{target_name}")
                return

        # 非战斗中，查找NPC
        npcs_data = self.state.get('npcs', {})
        target = None
        for npc_id, npc in npcs_data.get('npcs', {}).items():
            if npc['name'] == target_name and npc.get('is_alive', True):
                target = npc
                target['_id'] = npc_id
                break

        if not target:
            self._print(f"\n找不到目标：{target_name}")
            return

        # 进入战斗
        self._start_combat([target])

    def cmd_use(self, args: list) -> None:
        """使用物品"""
        if not args:
            self._print("\n请指定物品。用法: use <物品名>")
            return

        item_name = " ".join(args)

        # 查找物品
        inv_data = self.state.get('inventory', {})
        inventory = Inventory(inv_data)

        item = None
        for i in inventory.data.get('items', []):
            if i['name'] == item_name:
                item = i
                break

        if not item:
            self._print(f"\n你没有 {item_name}。")
            return

        # 使用物品
        result = self.rules.use_consumable(self.character.data, item)

        if result['success']:
            self._print(f"\n{result['message']}")
            # 移除消耗品
            if item.get('consumable', True):
                inventory.remove_item(item['id'])
            self.state.set('inventory', inventory.to_dict())
            self.state.set('character', self.character.to_dict())
        else:
            self._print(f"\n无法使用：{result['message']}")

    def cmd_skill(self, args: list) -> None:
        """使用技能"""
        if not args:
            self._print("\n请指定技能名称。用法: skill <技能名> [目标]")
            self._print("查看技能列表: skills")
            return

        skill_name = args[0]
        target_name = " ".join(args[1:]) if len(args) > 1 else None

        # 查找技能
        skill = None
        for s in self.character.data.get('skills', []):
            if s['name'] == skill_name:
                skill = s
                break

        if not skill:
            self._print(f"\n你没有学会技能：{skill_name}")
            return

        # 被动技能不能主动使用
        if skill.get('type') == 'passive':
            self._print(f"\n{skill_name} 是被动技能，无法主动使用。")
            return

        # 检查是否在战斗中
        if not self.in_combat:
            # 非战斗中只能使用部分技能
            if 'damage_multiplier' in skill:
                self._print("\n攻击型技能只能在战斗中使用。")
                return

            # 使用非伤害技能（如恢复技能）
            result = self.rules.use_skill(self.character.data, skill, self.character.data)
            if result['success']:
                self._print(f"\n使用了 {skill['name']}！")
                for effect in result.get('effects', []):
                    self._print(f"  - {effect}")
                self.state.set('character', self.character.to_dict())
            else:
                self._print(f"\n无法使用：{result['message']}")
            return

        # 战斗中使用技能
        if 'damage_multiplier' in skill and not target_name:
            # 默认攻击第一个敌人
            if self.combat_enemies:
                target = self.combat_enemies[0]
            else:
                self._print("\n没有可攻击的目标。")
                return
        elif target_name:
            # 查找指定目标
            target = None
            for enemy in self.combat_enemies:
                if enemy['name'] == target_name:
                    target = enemy
                    break
            if not target:
                self._print(f"\n找不到目标：{target_name}")
                return
        else:
            # 自我施法（如buff）
            target = self.character.data

        # 使用技能
        result = self.rules.use_skill(self.character.data, skill, target)

        if result['success']:
            # 构建战斗日志
            combat_log = [{
                "actor": self.character.name,
                "action": f"使用 {skill['name']}",
                "result": "，".join(result.get('effects', ['成功']))
            }]

            context = self.memory.build_combat_context(self.combat_enemies, self.combat_round)
            narrative = self.ai.generate_combat_narration(context, combat_log)
            self._print(f"\n{narrative}")

            # 检查目标死亡
            if result.get('target_killed'):
                self._handle_enemy_death(target)

            # 敌人反击
            if self.in_combat and target in self.combat_enemies and target.get('is_alive', True):
                self._enemy_turn(target)

            self._update_combat_state()
            self.state.set('character', self.character.to_dict())
        else:
            self._print(f"\n技能使用失败：{result['message']}")

    def cmd_flee(self, args: list) -> None:
        """尝试逃跑"""
        if not self.in_combat:
            self._print("\n你没有在战斗中。")
            return

        # 计算逃跑成功率（基于速度差）
        player_speed = self.character.data['derived_attributes'].get('speed', 100)

        # 获取敌人平均速度
        enemy_speeds = []
        for enemy in self.combat_enemies:
            enemy_speeds.append(enemy.get('derived_attributes', {}).get('speed', 100))
        avg_enemy_speed = sum(enemy_speeds) / len(enemy_speeds) if enemy_speeds else 100

        # 基础成功率 50%，速度越快成功率越高
        base_rate = 0.5
        speed_bonus = (player_speed - avg_enemy_speed) / 200  # 速度差每100增加50%
        flee_rate = min(0.95, max(0.1, base_rate + speed_bonus))

        if random.random() < flee_rate:
            self._print("\n『你成功逃离了战斗！』")
            self._end_combat(victory=False)
        else:
            self._print("\n『逃跑失败！』")
            # 敌人趁机攻击
            for enemy in self.combat_enemies:
                if enemy.get('is_alive', True):
                    self._enemy_turn(enemy)
                    if not self.character.data.get('status', {}).get('is_alive', True):
                        break

    def cmd_addpoint(self, args: list) -> None:
        """分配属性点"""
        available = self.character.data.get('attribute_points', 0)

        if not args:
            self._print(f"\n可用属性点：{available}")
            self._print("属性：力量(str) 敏捷(agi) 体质(con) 神识(spr) 悟性(per) 气运(luk)")
            self._print("用法: addpoint <属性> <点数>")
            self._print("例如: addpoint str 5")
            return

        if len(args) < 2:
            self._print("\n用法: addpoint <属性> <点数>")
            return

        attr_map = {
            'str': 'strength', 'strength': 'strength', '力量': 'strength',
            'agi': 'agility', 'agility': 'agility', '敏捷': 'agility',
            'con': 'constitution', 'constitution': 'constitution', '体质': 'constitution',
            'spr': 'spirit', 'spirit': 'spirit', '神识': 'spirit',
            'per': 'perception', 'perception': 'perception', '悟性': 'perception',
            'luk': 'luck', 'luck': 'luck', '气运': 'luck'
        }

        attr_names = {
            'strength': '力量', 'agility': '敏捷', 'constitution': '体质',
            'spirit': '神识', 'perception': '悟性', 'luck': '气运'
        }

        attr_key = attr_map.get(args[0].lower())
        if not attr_key:
            self._print(f"\n未知属性：{args[0]}")
            return

        try:
            points = int(args[1])
        except ValueError:
            self._print("\n点数必须是数字。")
            return

        if points <= 0:
            self._print("\n点数必须大于0。")
            return

        if points > available:
            self._print(f"\n属性点不足！可用：{available}，需要：{points}")
            return

        # 分配属性点
        self.character.data['primary_attributes'][attr_key] += points
        self.character.data['attribute_points'] -= points

        # 重新计算二级属性
        self.rules.recalculate_attributes(self.character.data)

        self.state.set('character', self.character.to_dict())
        self._print(f"\n成功将 {points} 点属性点分配到 {attr_names[attr_key]}！")
        self._print(f"当前 {attr_names[attr_key]}：{self.character.data['primary_attributes'][attr_key]}")
        self._print(f"剩余属性点：{self.character.data['attribute_points']}")

    def cmd_cultivate(self, args: list) -> None:
        """开始修炼"""
        self.character.data['status']['is_cultivating'] = True

        # 计算获得的经验（基础值提高，并受悟性影响更大）
        perception = self.character.data['primary_attributes'].get('perception', 10)
        base_exp = 25  # 提高基础经验
        bonus = 1 + perception * 0.03  # 悟性加成提高到3%每点

        # 检查被动技能加成
        for skill in self.character.data.get('skills', []):
            if skill.get('type') == 'passive':
                exp_bonus = skill.get('effects', {}).get('exp_bonus', 0)
                bonus += exp_bonus

        # 随机波动
        exp_gained = int(base_exp * bonus * random.uniform(0.8, 1.2))

        result = self.character.add_exp(exp_gained)

        # 生成修炼描述
        context = self.memory.build_context(focus_area='cultivation')
        narrative = self.ai.generate_narrative(
            context,
            "盘膝打坐，运转功法修炼",
            {"exp_gained": exp_gained}
        )

        self._print(f"\n{narrative}")
        self._print(f"\n『获得 {exp_gained} 点修为』")

        if result['leveled_up']:
            self._print("『修为已足够突破，可以尝试突破了』")

        self.character.data['status']['is_cultivating'] = False
        self.state.set('character', self.character.to_dict())

    def cmd_breakthrough(self, args: list) -> None:
        """尝试突破境界"""
        can_break, msg = self.rules.can_breakthrough(self.character.data)

        if not can_break:
            self._print(f"\n{msg}")
            return

        # 执行突破（可以选择带成功率的版本）
        result = self.rules.perform_breakthrough(self.character.data)

        if result['success']:
            # 生成突破描述
            context = self.memory.build_context(focus_area='cultivation')
            narrative = self.ai.generate_narrative(
                context,
                f"突破到{result['new_realm']}",
                result
            )
            self._print(f"\n{narrative}")
            self._print(f"\n『{result['message']}』")
            self._print(f"『获得 {result['attribute_points_gained']} 点属性点』")
        else:
            self._print(f"\n{result['message']}")

        self.state.set('character', self.character.to_dict())

    def cmd_help(self, args: list) -> None:
        """显示帮助"""
        self._print("""
【基础命令】
  status (s)      - 查看角色状态
  look (l)        - 查看周围环境
  inventory (i)   - 查看物品栏
  skills          - 查看技能列表
  move <地点>     - 移动到其他地点

【战斗命令】
  attack (a) <目标>     - 普通攻击
  skill (k) <技能> [目标] - 使用技能
  flee (f)              - 尝试逃跑

【互动命令】
  talk (t) <NPC> <话>   - 与NPC对话
  use (u) <物品>        - 使用物品

【修炼命令】
  cultivate (c)   - 打坐修炼（获取经验）
  breakthrough    - 尝试突破境界
  addpoint (ap)   - 分配属性点

【系统命令】
  save            - 保存游戏
  quit (q)        - 保存并退出
  help (h)        - 显示帮助

【自由行动】
  直接输入任何行动描述，AI会帮你叙述结果。
  例如："四处查看有没有可疑的东西"
        "向老者打听此地的历史"
""")

    def cmd_save(self, args: list) -> None:
        """保存游戏"""
        self.state.save_all()
        self._print("\n游戏已保存。")

    def cmd_quit(self, args: list) -> None:
        """退出游戏"""
        self.state.save_all()
        self._print("\n游戏已保存。再见！")
        self.is_running = False

    # ==================== 战斗系统 ====================

    def _start_combat(self, enemies: list) -> None:
        """开始战斗"""
        self.in_combat = True
        self.combat_round = 1
        self.character.data['status']['is_in_combat'] = True

        # 为敌人初始化战斗属性（如果没有的话）
        for enemy in enemies:
            self._init_enemy_combat_stats(enemy)

        self.combat_enemies = enemies

        enemy_names = ", ".join([e['name'] for e in enemies])
        self._print(f"\n『战斗开始！敌人：{enemy_names}』")

        # 决定行动顺序
        all_participants = [self.character.data] + enemies
        self.combat_order = self.rules.calculate_combat_order(all_participants)

        self._show_combat_status()

    def _init_enemy_combat_stats(self, enemy: dict) -> None:
        """为敌人初始化战斗属性"""
        if 'derived_attributes' in enemy:
            return  # 已有战斗属性

        # 根据敌人境界计算属性
        realm_id = enemy.get('realm', {}).get('id', 'mortal')
        sub_realm_index = enemy.get('realm', {}).get('sub_realm_index', 0)

        try:
            realm_info = self.rules.get_realm_info(realm_id, sub_realm_index)
        except (ValueError, IndexError):
            # 默认使用凡人属性
            realm_info = self.rules.get_realm_info('mortal', 0)

        enemy['derived_attributes'] = {
            'hp': realm_info['base_hp'],
            'hp_max': realm_info['base_hp'],
            'mp': realm_info['base_mp'],
            'mp_max': realm_info['base_mp'],
            'attack': realm_info['base_attack'],
            'defense': realm_info['base_defense'],
            'speed': 100,
            'crit_rate': 0.05,
            'crit_damage': 1.5,
            'dodge_rate': 0.05
        }

        # 更新境界名称（如果只有id）
        if 'name' not in enemy.get('realm', {}):
            enemy['realm']['name'] = realm_info['name']

    def _execute_attack(self, target: dict) -> None:
        """执行攻击"""
        # 计算伤害
        damage_result = self.rules.calculate_damage(
            self.character.data,
            target,
            attacker_element=self.character.data.get('element'),
            defender_element=target.get('element')
        )

        # 应用伤害
        apply_result = self.rules.apply_damage(target, damage_result.final_damage)

        # 构建战斗日志
        combat_log = [{
            "actor": self.character.name,
            "action": "普通攻击",
            "result": f"造成{damage_result.final_damage}伤害" +
                     ("（暴击）" if damage_result.is_crit else "") +
                     ("（闪避）" if damage_result.is_dodged else "")
        }]

        # 生成战斗叙述
        context = self.memory.build_combat_context(self.combat_enemies, self.combat_round)
        narrative = self.ai.generate_combat_narration(context, combat_log)
        self._print(f"\n{narrative}")

        # 检查目标是否死亡
        if apply_result['is_dead']:
            self._handle_enemy_death(target)

        # 敌人反击
        if not apply_result['is_dead'] and self.in_combat:
            self._enemy_turn(target)

        # 更新状态
        self._update_combat_state()

    def _enemy_turn(self, enemy: dict) -> None:
        """敌人回合"""
        if not enemy.get('is_alive', True):
            return

        # 敌人攻击玩家
        damage_result = self.rules.calculate_damage(
            enemy,
            self.character.data,
            attacker_element=enemy.get('element'),
            defender_element=self.character.data.get('element')
        )

        apply_result = self.rules.apply_damage(self.character.data, damage_result.final_damage)

        combat_log = [{
            "actor": enemy['name'],
            "action": "反击",
            "result": f"造成{damage_result.final_damage}伤害" +
                     ("（暴击）" if damage_result.is_crit else "") +
                     ("（闪避）" if damage_result.is_dodged else "")
        }]

        context = self.memory.build_combat_context(self.combat_enemies, self.combat_round)
        narrative = self.ai.generate_combat_narration(context, combat_log)
        self._print(f"\n{narrative}")

        if apply_result['is_dead']:
            self._handle_player_death()

    def _handle_enemy_death(self, enemy: dict) -> None:
        """处理敌人死亡"""
        self._print(f"\n『{enemy['name']} 被击败！』")

        # 获取经验
        exp_reward = enemy.get('exp_reward', 10)
        self.character.add_exp(exp_reward)
        self._print(f"『获得 {exp_reward} 点修为』")

        # 掉落物品
        loot_table = enemy.get('loot_table', [])
        luck_bonus = self.character.data['primary_attributes'].get('luck', 10) * 0.005
        drops = self.rules.generate_loot(loot_table, luck_bonus)

        if drops:
            inv_data = self.state.get('inventory', {})
            inventory = Inventory(inv_data)
            for item in drops:
                inventory.add_item(item)
                item_name = item["name"]
                item_count = item.get("count", 1)
                self._print(f"『获得 {item_name} x{item_count}』")
            self.state.set('inventory', inventory.to_dict())

        # 从战斗列表移除
        self.combat_enemies = [e for e in self.combat_enemies if e.get('is_alive', True)]

        # 检查战斗是否结束
        if not self.combat_enemies:
            self._end_combat(victory=True)

        # 更新NPC状态
        npcs_data = self.state.get('npcs', {})
        if enemy.get('_id') and enemy['_id'] in npcs_data.get('npcs', {}):
            npcs_data['npcs'][enemy['_id']]['is_alive'] = False
            self.state.set('npcs', npcs_data)

        # 更新统计
        self.character.data['statistics']['monsters_killed'] += 1

    def _handle_player_death(self) -> None:
        """处理玩家死亡"""
        self._print("\n『你被击败了...』")

        # 更新统计
        self.character.data['statistics']['deaths'] += 1

        # 复活（简单处理：回到满血，回到安全地点）
        self.character.data['derived_attributes']['hp'] = self.character.data['derived_attributes']['hp_max']
        self.character.data['status']['is_alive'] = True
        self.character.data['status']['current_scene'] = "新手村"

        self._end_combat(victory=False)
        self._print("\n你在新手村的客栈中醒来...")

    def _end_combat(self, victory: bool) -> None:
        """结束战斗"""
        self.in_combat = False
        self.combat_enemies = []
        self.combat_round = 0
        self.character.data['status']['is_in_combat'] = False

        if victory:
            self._print("\n『战斗胜利！』")
        else:
            self._print("\n『战斗结束』")

        self.state.set('character', self.character.to_dict())

    def _update_combat_state(self) -> None:
        """更新战斗状态"""
        if self.in_combat:
            self._show_combat_status()

    def _show_combat_status(self) -> None:
        """显示战斗状态"""
        char = self.character.data['derived_attributes']
        self._print(f"\n【你】HP: {char['hp']}/{char['hp_max']} | MP: {char['mp']}/{char['mp_max']}")

        for enemy in self.combat_enemies:
            if enemy.get('is_alive', True):
                e_attr = enemy.get('derived_attributes', {})
                self._print(f"【{enemy['name']}】HP: {e_attr.get('hp', '?')}/{e_attr.get('hp_max', '?')}")

    # ==================== 辅助方法 ====================

    def _create_character(self) -> None:
        """创建新角色"""
        self._print("\n=== 创建新角色 ===")
        name = input("请输入你的名字: ").strip()

        if not name:
            name = "无名修士"

        self.character = Character.create_new(name, self.config)

        # 添加初始技能
        starter_skill_ids = self.skills_config.get('starter_skills', [])
        all_skills = (
            self.skills_config.get('basic_skills', []) +
            self.skills_config.get('passive_skills', [])
        )
        for skill in all_skills:
            if skill['id'] in starter_skill_ids:
                self.character.data['skills'].append(skill)

        self.state.set('character', self.character.to_dict())

        # 初始化物品栏
        initial_inventory = {
            "items": [
                {"id": "healing_pill_low", "name": "下品回血丹", "count": 5,
                 "stackable": True, "consumable": True, "quality": "common",
                 "effects": {"heal_hp": 50}},
                {"id": "mana_pill_low", "name": "下品回蓝丹", "count": 3,
                 "stackable": True, "consumable": True, "quality": "common",
                 "effects": {"heal_mp": 30}},
            ],
            "max_slots": 50
        }
        self.state.set('inventory', initial_inventory)

        # 初始化世界状态
        initial_world = {
            "current_scene": {
                "name": "新手村",
                "type": "settlement",
                "description": "一个宁静的小村庄，灵气稀薄，适合凡人居住。",
                "features": ["客栈", "杂货铺", "村长家", "练武场"],
                "exits": ["村外小路", "后山"],
                "atmosphere": "宁静祥和",
                "danger_level": "安全"
            }
        }
        self.state.set('world', initial_world)

        # 初始化NPC
        initial_npcs = {
            "npcs": {
                "village_elder": {
                    "id": "village_elder",
                    "name": "王老",
                    "type": "quest_giver",
                    "realm": {"id": "qi_refining", "name": "炼气期"},
                    "location": "新手村",
                    "description": "新手村的村长，一位和蔼的老者，曾是修士。",
                    "personality": "慈祥、话多、爱回忆往事",
                    "is_alive": True
                },
                "shop_owner": {
                    "id": "shop_owner",
                    "name": "李掌柜",
                    "type": "merchant",
                    "realm": {"id": "mortal", "name": "凡人"},
                    "location": "新手村",
                    "description": "杂货铺的老板，精明但不奸诈。",
                    "personality": "精明、健谈、爱八卦",
                    "is_alive": True,
                    "inventory": []
                }
            }
        }
        self.state.set('npcs', initial_npcs)

        self.state.save_all()
        self._print(f"\n角色 {name} 创建成功！")

    def _generate_default_scene(self) -> dict:
        """生成默认场景"""
        return {
            "name": self.character.data['status']['current_scene'],
            "type": "unknown",
            "description": "一片未知的区域。",
            "features": [],
            "exits": ["返回"],
            "atmosphere": "普通",
            "danger_level": "未知"
        }

    def _get_or_create_scene(self, scene_name: str) -> dict:
        """获取或创建场景"""
        # 这里可以扩展为从配置加载或AI生成
        scenes = {
            "新手村": {
                "name": "新手村",
                "type": "settlement",
                "description": "一个宁静的小村庄，炊烟袅袅，鸡犬相闻。村子虽小，却五脏俱全。",
                "features": ["客栈", "杂货铺", "村长家", "练武场"],
                "exits": ["村外小路", "后山"],
                "atmosphere": "宁静祥和",
                "danger_level": "安全"
            },
            "村外小路": {
                "name": "村外小路",
                "type": "road",
                "description": "一条蜿蜒的土路，两旁长满野草。偶尔能看到野兔从草丛中窜过。",
                "features": ["路边野花", "远处的树林", "倒塌的石碑"],
                "exits": ["新手村", "荒野"],
                "atmosphere": "平静中带着一丝不安",
                "danger_level": "低"
            },
            "后山": {
                "name": "后山",
                "type": "wilderness",
                "description": "村子后面的小山，树木葱郁，山间灵气比村中浓郁几分。据村民说，山中有野兽出没。",
                "features": ["山洞入口", "灵草", "奇怪的脚印", "古老的石阶"],
                "exits": ["新手村", "山洞"],
                "atmosphere": "神秘幽深",
                "danger_level": "中"
            },
            "山洞": {
                "name": "山洞",
                "type": "dungeon",
                "description": "一个幽深的山洞，洞口笼罩着淡淡的雾气。洞内传来阵阵凉意和低沉的咆哮声。",
                "features": ["石钟乳", "地下水潭", "兽骨堆", "幽暗的深处"],
                "exits": ["后山"],
                "atmosphere": "阴森恐怖",
                "danger_level": "高"
            },
            "荒野": {
                "name": "荒野",
                "type": "wilderness",
                "description": "一望无际的荒野，杂草丛生，荆棘遍地。远处似乎有狼嚎声传来。",
                "features": ["废弃的营地", "狼群痕迹", "远处的山脉"],
                "exits": ["村外小路"],
                "atmosphere": "荒凉危险",
                "danger_level": "中"
            }
        }

        return scenes.get(scene_name, {
            "name": scene_name,
            "type": "unknown",
            "description": f"你来到了{scene_name}，这是一片未知的区域。",
            "features": [],
            "exits": ["新手村"],  # 默认可以返回新手村
            "atmosphere": "未知",
            "danger_level": "未知"
        })

    def _get_quality_name(self, quality: str) -> str:
        """获取品质中文名"""
        quality_names = {
            "common": "凡品",
            "uncommon": "灵品",
            "rare": "玄品",
            "epic": "地品",
            "legendary": "天品",
            "mythic": "仙品",
            "divine": "神品"
        }
        return quality_names.get(quality, "未知")

    def _get_monster_by_id(self, monster_id: str) -> dict:
        """根据ID获取怪物配置"""
        # 遍历所有怪物类别
        for category in ['starter_monsters', 'backhill_monsters', 'wilderness_monsters']:
            monsters = self.monsters_config.get(category, [])
            for monster in monsters:
                if monster.get('id') == monster_id:
                    return monster.copy()  # 返回副本避免修改原配置
        return None

    def _check_random_encounter(self, scene_name: str) -> list:
        """检查是否触发随机遇敌"""
        spawn_data = self.monsters_config.get('spawn_locations', {}).get(scene_name)
        if not spawn_data:
            return []

        # 检查是否触发遭遇
        encounter_rate = spawn_data.get('encounter_rate', 0)
        if random.random() > encounter_rate:
            return []  # 未触发遭遇

        # 确定出现哪些怪物
        encountered_monsters = []
        for spawn_info in spawn_data.get('monsters', []):
            spawn_chance = spawn_info.get('spawn_chance', 0)
            if random.random() < spawn_chance:
                monster_id = spawn_info['id']
                max_count = spawn_info.get('max_count', 1)
                count = random.randint(1, max_count)

                monster_template = self._get_monster_by_id(monster_id)
                if monster_template:
                    for _ in range(count):
                        monster = monster_template.copy()
                        monster['_runtime_id'] = f"{monster_id}_{random.randint(1000, 9999)}"
                        monster['is_alive'] = True
                        encountered_monsters.append(monster)

        return encountered_monsters

    def _trigger_encounter(self, monsters: list) -> None:
        """触发遭遇战"""
        if not monsters:
            return

        # 显示遭遇信息
        if len(monsters) == 1:
            self._print(f"\n『危险！你遭遇了 {monsters[0]['name']}！』")
        else:
            names = {}
            for m in monsters:
                names[m['name']] = names.get(m['name'], 0) + 1
            name_str = "、".join([f"{name}x{count}" if count > 1 else name
                                  for name, count in names.items()])
            self._print(f"\n『危险！你遭遇了 {name_str}！』")

        # 显示怪物描述
        shown = set()
        for monster in monsters:
            if monster['name'] not in shown:
                self._print(f"【{monster['name']}】{monster.get('description', '')}")
                shown.add(monster['name'])

        # 开始战斗
        self._start_combat(monsters)

    def _print(self, text: str) -> None:
        """输出文本"""
        print(text)

    def _print_welcome(self) -> None:
        """打印欢迎信息"""
        self._print("""
╔════════════════════════════════════════════╗
║                                            ║
║           仙 途 · 文 字 修 仙              ║
║                                            ║
║        一念成仙，一念成魔                  ║
║                                            ║
╚════════════════════════════════════════════╝

输入 'help' 查看命令列表
""")
