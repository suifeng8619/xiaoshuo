"""
主游戏循环
整合所有模块，处理玩家输入，驱动游戏进行
"""
import random
from typing import Optional, Tuple
from pathlib import Path

from .state import GameState, Character, Inventory, StoryLog, NPC, WorldState
from .rules import RulesEngine
from .memory import MemoryManager
from .ai import AIClient, MockAIClient
from .time import GameTime
from .time_system import TimeSystem


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
        self.scenes_config = self.state.load_config(self.config_dir / "scenes.yaml")
        self.quests_config = self.state.load_config(self.config_dir / "quests.yaml")

        # 构建场景索引（按名称和ID都可以查找）
        self.scenes_by_id = {}
        self.scenes_by_name = {}
        for category in ['starter_area', 'advanced_area']:
            for scene in self.scenes_config.get(category, []):
                self.scenes_by_id[scene['id']] = scene
                self.scenes_by_name[scene['name']] = scene

        # 构建任务索引
        self.quests_by_id = {}
        for category in ['starter_quests', 'side_quests', 'daily_quests']:
            for quest in self.quests_config.get(category, []):
                self.quests_by_id[quest['id']] = quest

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

        # 时间系统
        self.time_system: Optional[TimeSystem] = None
        self.world_state: Optional[WorldState] = None

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
            'defend': self.cmd_defend,
            'use': self.cmd_use,
            'flee': self.cmd_flee,
            'search': self.cmd_search,
            'examine': self.cmd_examine,
            'rest': self.cmd_rest,
            'shop': self.cmd_shop,
            'buy': self.cmd_buy,
            'sell': self.cmd_sell,
            'quest': self.cmd_quest,
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
            'd': 'defend',
            'u': 'use',
            'f': 'flee',
            'run': 'flee',
            'e': 'examine',
            'x': 'examine',
            'r': 'rest',
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

        # 初始化时间系统和世界状态
        self._init_time_and_world()

        # 显示当前状态
        self.cmd_status([])

        # 主循环
        self._game_loop()

    def _init_time_and_world(self) -> None:
        """初始化时间系统和世界状态"""
        # 加载或创建世界状态
        world_data = self.state.get('world', {})
        self.world_state = WorldState(world_data)

        # 从世界状态恢复时间
        time_data = self.world_state.current_time
        if time_data and time_data.get('absolute_tick', 0) > 0:
            game_time = GameTime.from_dict(time_data)
        else:
            game_time = GameTime()  # 第1年1月1日晨

        self.time_system = TimeSystem(initial_time=game_time)

        # 注册日结算钩子（后续 Phase 会填充具体逻辑）
        self.time_system.register_hook('day_ended', self._on_day_ended)

        # 同步世界状态
        self._sync_world_state()

    def _on_day_ended(self, event) -> None:
        """日结算钩子（占位，后续填充）"""
        # TODO: Phase 3/4/5 填充：关系衰减、NPC日程、事件检查等
        pass

    def _sync_world_state(self) -> None:
        """同步时间到世界状态并保存"""
        if self.time_system and self.world_state:
            self.world_state.current_time = self.time_system.current_time.to_dict()
            self.state.set('world', self.world_state.to_dict())

    def _advance_time(self, ticks: int) -> None:
        """推进时间并同步状态"""
        if self.time_system and ticks > 0:
            event = self.time_system.advance(ticks)
            self._sync_world_state()
            # 可选：显示时间变化
            if event.days_passed > 0:
                self._print(f"【时间流逝：{event.days_passed} 日】")

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
        # 显示当前时间
        if self.time_system:
            self._print(f"【{self.time_system.current_time}】")

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

        # 更新任务进度（对话类）
        npc_id = npc.get('id', '')
        self._update_quest_progress('talk', npc_id)

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

    def cmd_defend(self, args: list) -> None:
        """防御姿态"""
        if not self.in_combat:
            self._print("\n你没有在战斗中，不需要防御。")
            return

        # 进入防御状态，减少受到的伤害
        self.character.data['status']['is_defending'] = True
        self._print("\n『你摆出防御姿态，准备格挡攻击！』")
        self._print("（下回合受到的伤害减少50%）")

        # 敌人攻击
        for enemy in self.combat_enemies:
            if enemy.get('is_alive', True):
                self._enemy_turn(enemy, player_defending=True)
                if not self.character.data.get('status', {}).get('is_alive', True):
                    break

        # 防御状态在回合结束后解除
        self.character.data['status']['is_defending'] = False
        self._update_combat_state()

    def cmd_search(self, args: list) -> None:
        """搜索当前区域"""
        if self.in_combat:
            self._print("\n战斗中无法搜索！")
            return

        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})
        scene_name = current_scene.get('name', '')
        danger_level = current_scene.get('danger_level', 'safe')

        # 安全区域不会遇敌
        if danger_level == 'safe':
            self._print("\n你仔细搜索了一番，这里很安全，没有发现任何危险。")
            return

        self._print("\n你警惕地搜索着四周...")

        # 搜索时遇敌概率更高
        search_encounter_rates = {
            'low': 0.6,
            'medium': 0.8,
            'high': 0.95,
            'dangerous': 1.0
        }
        encounter_rate = search_encounter_rates.get(danger_level, 0.5)

        if random.random() < encounter_rate:
            monsters = self._force_encounter(scene_name)
            if monsters:
                self._trigger_encounter(monsters)
            else:
                self._print("搜索了一会儿，没有发现什么。")
        else:
            self._print("搜索了一会儿，暂时没有发现敌人的踪迹。")

    def _force_encounter(self, scene_name: str) -> list:
        """强制生成遭遇（用于搜索）"""
        spawn_data = self.monsters_config.get('spawn_locations', {}).get(scene_name)
        if not spawn_data:
            return []

        # 随机选择一种怪物
        monster_spawns = spawn_data.get('monsters', [])
        if not monster_spawns:
            return []

        # 按权重选择
        total_chance = sum(m.get('spawn_chance', 0.1) for m in monster_spawns)
        roll = random.random() * total_chance
        cumulative = 0

        for spawn_info in monster_spawns:
            cumulative += spawn_info.get('spawn_chance', 0.1)
            if roll <= cumulative:
                monster_id = spawn_info['id']
                max_count = spawn_info.get('max_count', 1)
                count = random.randint(1, max_count)

                monster_template = self._get_monster_by_id(monster_id)
                if monster_template:
                    monsters = []
                    for _ in range(count):
                        monster = monster_template.copy()
                        monster['_runtime_id'] = f"{monster_id}_{random.randint(1000, 9999)}"
                        monster['is_alive'] = True
                        monsters.append(monster)
                    return monsters

        return []

    def cmd_examine(self, args: list) -> None:
        """检查场景中的物品或特征"""
        if not args:
            self._print("\n请指定要检查的对象。用法: examine <对象>")
            return

        target_name = " ".join(args)

        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})
        features_detail = current_scene.get('features_detail', [])

        # 查找目标特征
        target_feature = None
        for feature in features_detail:
            if feature['name'] == target_name:
                target_feature = feature
                break

        if not target_feature:
            self._print(f"\n这里没有 {target_name}。")
            return

        # 显示描述
        self._print(f"\n【{target_feature['name']}】")
        self._print(target_feature.get('description', '没什么特别的。'))

        # 检查是否有额外文本
        if 'examine_text' in target_feature:
            self._print(f"\n{target_feature['examine_text']}")

        # 检查是否可以采集
        if target_feature.get('interaction') == 'gather':
            self._handle_gather(target_feature)

        # 检查是否可以搜索
        if target_feature.get('interaction') == 'search':
            self._handle_search_feature(target_feature)

    def _handle_gather(self, feature: dict) -> None:
        """处理采集"""
        gather_items = feature.get('gather_items', [])
        if not gather_items:
            return

        self._print("\n你尝试采集...")

        inv_data = self.state.get('inventory', {})
        inventory = Inventory(inv_data)
        gathered_any = False
        gathered_items = []

        for item_info in gather_items:
            if random.random() < item_info.get('chance', 0.5):
                item = {
                    'id': item_info['id'],
                    'name': item_info['name'],
                    'count': 1,
                    'stackable': True,
                    'quality': 'common'
                }
                inventory.add_item(item)
                self._print(f"『获得 {item['name']} x1』")
                gathered_any = True
                gathered_items.append(item_info['id'])

        if not gathered_any:
            self._print("没有采集到什么有用的东西。")
        else:
            self.state.set('inventory', inventory.to_dict())
            # 更新任务进度（采集类）
            for item_id in gathered_items:
                self._update_quest_progress('gather', item_id)

    def _handle_search_feature(self, feature: dict) -> None:
        """处理搜索特征点"""
        search_items = feature.get('search_items', [])
        if not search_items:
            return

        self._print("\n你仔细搜索...")

        inv_data = self.state.get('inventory', {})
        inventory = Inventory(inv_data)
        found_any = False

        for item_info in search_items:
            if random.random() < item_info.get('chance', 0.3):
                count_range = item_info.get('count', [1, 1])
                if isinstance(count_range, list):
                    count = random.randint(count_range[0], count_range[1])
                else:
                    count = count_range

                item = {
                    'id': item_info['id'],
                    'name': item_info['name'],
                    'count': count,
                    'stackable': True,
                    'quality': 'common'
                }
                inventory.add_item(item)
                item_name = item["name"]
                self._print(f"『发现 {item_name} x{count}』")
                found_any = True

        if not found_any:
            self._print("没有发现什么有价值的东西。")
        else:
            self.state.set('inventory', inventory.to_dict())

    def cmd_rest(self, args: list) -> None:
        """休息恢复"""
        if self.in_combat:
            self._print("\n战斗中无法休息！")
            return

        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})

        # 检查是否是安全区域
        if not current_scene.get('can_rest', False) and current_scene.get('danger_level') != 'safe':
            self._print("\n这里不够安全，无法休息。")
            self._print("提示：返回新手村的客栈可以安全休息。")
            return

        # 恢复生命和法力
        derived = self.character.data['derived_attributes']
        hp_before = derived['hp']
        mp_before = derived['mp']

        derived['hp'] = derived['hp_max']
        derived['mp'] = derived['mp_max']

        hp_healed = derived['hp'] - hp_before
        mp_healed = derived['mp'] - mp_before

        self._print("\n你找了个安全的地方休息...")
        self._print(f"『恢复了 {hp_healed} 点生命，{mp_healed} 点法力』")
        self._print(f"当前状态：HP {derived['hp']}/{derived['hp_max']} | MP {derived['mp']}/{derived['mp_max']}")

        self.state.set('character', self.character.to_dict())

        # 推进时间（休息消耗2时辰=1时段）
        self._advance_time(2)

    def cmd_shop(self, args: list) -> None:
        """查看商店"""
        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})
        scene_name = current_scene.get('name', '')

        # 检查当前场景是否有商店
        if scene_name != '新手村':
            self._print("\n这里没有商店。")
            return

        self._print("\n【杂货铺 - 李掌柜】")
        self._print("「客官，看看有什么需要的？」\n")

        shop_items = self._get_shop_items()
        for i, item in enumerate(shop_items, 1):
            self._print(f"  {i}. {item['name']} - {item['price']} 金币")
            self._print(f"     {item.get('description', '')}")

        self._print(f"\n你的金币：{self.character.data['currency'].get('gold', 0)}")
        self._print("使用 buy <物品名> 购买，sell <物品名> 出售")

    def _get_shop_items(self) -> list:
        """获取商店物品列表"""
        return [
            {
                'id': 'healing_pill_low',
                'name': '下品回血丹',
                'price': 20,
                'description': '恢复50点生命',
                'stackable': True,
                'consumable': True,
                'quality': 'common',
                'effects': {'heal_hp': 50}
            },
            {
                'id': 'healing_pill_mid',
                'name': '中品回血丹',
                'price': 80,
                'description': '恢复150点生命',
                'stackable': True,
                'consumable': True,
                'quality': 'uncommon',
                'effects': {'heal_hp': 150}
            },
            {
                'id': 'mana_pill_low',
                'name': '下品回蓝丹',
                'price': 15,
                'description': '恢复30点法力',
                'stackable': True,
                'consumable': True,
                'quality': 'common',
                'effects': {'heal_mp': 30}
            },
            {
                'id': 'mana_pill_mid',
                'name': '中品回蓝丹',
                'price': 60,
                'description': '恢复100点法力',
                'stackable': True,
                'consumable': True,
                'quality': 'uncommon',
                'effects': {'heal_mp': 100}
            },
            {
                'id': 'antidote',
                'name': '解毒丹',
                'price': 30,
                'description': '解除中毒状态',
                'stackable': True,
                'consumable': True,
                'quality': 'common',
                'effects': {'cure': 'poison'}
            }
        ]

    def cmd_buy(self, args: list) -> None:
        """购买物品"""
        if not args:
            self._print("\n请指定要购买的物品。用法: buy <物品名> [数量]")
            return

        # 检查是否在商店
        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})
        if current_scene.get('name') != '新手村':
            self._print("\n这里没有商店。")
            return

        item_name = args[0]
        count = int(args[1]) if len(args) > 1 else 1

        # 查找物品
        shop_items = self._get_shop_items()
        target_item = None
        for item in shop_items:
            if item['name'] == item_name:
                target_item = item
                break

        if not target_item:
            self._print(f"\n商店没有 {item_name}。")
            return

        total_price = target_item['price'] * count
        gold = self.character.data['currency'].get('gold', 0)

        if gold < total_price:
            self._print(f"\n金币不足！需要 {total_price}，你只有 {gold}。")
            return

        # 扣除金币
        self.character.data['currency']['gold'] = gold - total_price

        # 添加物品
        inv_data = self.state.get('inventory', {})
        inventory = Inventory(inv_data)

        buy_item = target_item.copy()
        buy_item['count'] = count
        inventory.add_item(buy_item)

        self.state.set('inventory', inventory.to_dict())
        self.state.set('character', self.character.to_dict())

        self._print(f"\n『购买了 {item_name} x{count}，花费 {total_price} 金币』")
        self._print(f"剩余金币：{self.character.data['currency']['gold']}")

    def cmd_sell(self, args: list) -> None:
        """出售物品"""
        if not args:
            self._print("\n请指定要出售的物品。用法: sell <物品名> [数量]")
            return

        # 检查是否在商店
        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})
        if current_scene.get('name') != '新手村':
            self._print("\n这里没有商店。")
            return

        item_name = args[0]
        count = int(args[1]) if len(args) > 1 else 1

        # 查找背包物品
        inv_data = self.state.get('inventory', {})
        inventory = Inventory(inv_data)

        target_item = None
        for item in inventory.data.get('items', []):
            if item['name'] == item_name:
                target_item = item
                break

        if not target_item:
            self._print(f"\n你没有 {item_name}。")
            return

        if target_item.get('count', 1) < count:
            self._print(f"\n你只有 {target_item.get('count', 1)} 个 {item_name}。")
            return

        # 计算售价（默认为购买价的一半，或者物品自带的sell_price）
        sell_price = target_item.get('sell_price', target_item.get('price', 10) // 2)
        total_price = sell_price * count

        # 移除物品
        if target_item.get('count', 1) == count:
            inventory.data['items'].remove(target_item)
        else:
            target_item['count'] -= count

        # 增加金币
        self.character.data['currency']['gold'] = self.character.data['currency'].get('gold', 0) + total_price

        self.state.set('inventory', inventory.to_dict())
        self.state.set('character', self.character.to_dict())

        self._print(f"\n『出售了 {item_name} x{count}，获得 {total_price} 金币』")
        self._print(f"当前金币：{self.character.data['currency']['gold']}")

    def cmd_quest(self, args: list) -> None:
        """查看任务"""
        quests_data = self.state.get('quests', {'quests': []})
        active_quests = [q for q in quests_data.get('quests', []) if q.get('status') == 'active']
        completed_quests = [q for q in quests_data.get('quests', []) if q.get('status') == 'completed']

        if not args:
            # 显示任务列表
            self._print("\n【任务列表】")

            if active_quests:
                self._print("\n进行中：")
                for quest in active_quests:
                    self._print(f"  - {quest['name']}")
            else:
                self._print("\n暂无进行中的任务。")

            if completed_quests:
                self._print(f"\n已完成：{len(completed_quests)} 个")

            self._print("\n使用 quest <任务名> 查看详情")
            return

        # 查看具体任务
        quest_name = " ".join(args)
        target_quest = None
        for q in quests_data.get('quests', []):
            if q['name'] == quest_name:
                target_quest = q
                break

        if not target_quest:
            self._print(f"\n没有找到任务：{quest_name}")
            return

        self._print(f"\n【{target_quest['name']}】")
        self._print(f"状态：{target_quest.get('status', 'unknown')}")
        self._print(f"\n{target_quest.get('description', '无描述')}")

        if target_quest.get('objectives'):
            self._print("\n目标：")
            progress = target_quest.get('progress', {})
            for obj in target_quest['objectives']:
                current = progress.get(obj['id'], 0)
                required = obj.get('required', 1)
                status = "✓" if current >= required else f"{current}/{required}"
                self._print(f"  - {obj.get('description', '未知')}: {status}")

        if target_quest.get('rewards'):
            self._print("\n奖励：")
            rewards = target_quest['rewards']
            if rewards.get('exp'):
                self._print(f"  - 经验: {rewards['exp']}")
            if rewards.get('gold'):
                self._print(f"  - 金币: {rewards['gold']}")
            if rewards.get('items'):
                for item in rewards['items']:
                    self._print(f"  - {item['name']} x{item.get('count', 1)}")

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

        # 推进时间（修炼消耗1时辰）
        self._advance_time(1)

        # 更新任务进度（修炼类）
        self._update_quest_progress('cultivate', '')

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

            # 更新任务进度（突破类）
            self._update_quest_progress('breakthrough', '')
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
  attack (a) [目标]     - 普通攻击（不指定则攻击第一个敌人）
  skill (k) <技能> [目标] - 使用技能
  defend (d)            - 防御姿态（受伤减半）
  flee (f)              - 尝试逃跑

【探索命令】
  search          - 搜索区域（主动寻找怪物）
  examine (e) <对象>    - 检查场景中的物品
  rest (r)        - 休息恢复（仅限安全区）

【交易命令】
  shop            - 查看商店
  buy <物品> [数量]     - 购买物品
  sell <物品> [数量]    - 出售物品

【互动命令】
  talk (t) <NPC> <话>   - 与NPC对话
  use (u) <物品>        - 使用物品
  quest           - 查看任务列表

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

    def _enemy_turn(self, enemy: dict, player_defending: bool = False) -> None:
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

        # 如果玩家在防御，伤害减半
        actual_damage = damage_result.final_damage
        if player_defending:
            actual_damage = actual_damage // 2

        apply_result = self.rules.apply_damage(self.character.data, actual_damage)

        defend_text = "（被格挡）" if player_defending else ""
        combat_log = [{
            "actor": enemy['name'],
            "action": "反击",
            "result": f"造成{actual_damage}伤害{defend_text}" +
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

        # 更新任务进度（击杀类）
        enemy_id = enemy.get('id', '')
        self._update_quest_progress('kill', enemy_id)
        self._update_quest_progress('kill', 'any')  # 击杀任意怪物

    def _update_quest_progress(self, objective_type: str, target: str, amount: int = 1) -> None:
        """更新任务进度"""
        quests_data = self.state.get('quests', {'quests': []})
        updated = False

        for quest in quests_data.get('quests', []):
            if quest.get('status') != 'active':
                continue

            for objective in quest.get('objectives', []):
                if objective.get('type') != objective_type:
                    continue

                # 检查目标是否匹配
                obj_target = objective.get('target', '')
                if obj_target and obj_target != target and target != 'any':
                    continue

                # 更新进度
                obj_id = objective['id']
                current = quest.get('progress', {}).get(obj_id, 0)
                required = objective.get('required', 1)

                if current < required:
                    if 'progress' not in quest:
                        quest['progress'] = {}
                    quest['progress'][obj_id] = current + amount
                    updated = True

                    new_progress = quest['progress'][obj_id]
                    obj_desc = objective.get('description', obj_id)
                    if new_progress >= required:
                        self._print(f"『任务目标完成：{obj_desc}』")
                    else:
                        self._print(f"『任务进度：{obj_desc} ({new_progress}/{required})』")

        if updated:
            self.state.set('quests', quests_data)
            # 检查任务是否全部完成
            self._check_quest_completion()

    def _check_quest_completion(self) -> None:
        """检查并处理任务完成"""
        quests_data = self.state.get('quests', {'quests': []})
        completed_any = False

        for quest in quests_data.get('quests', []):
            if quest.get('status') != 'active':
                continue

            # 检查所有目标是否完成
            all_complete = True
            for objective in quest.get('objectives', []):
                obj_id = objective['id']
                current = quest.get('progress', {}).get(obj_id, 0)
                required = objective.get('required', 1)
                if current < required:
                    all_complete = False
                    break

            if all_complete:
                quest['status'] = 'completed'
                completed_any = True
                quest_name = quest['name']
                self._print(f"\n『任务完成：{quest_name}』")

                # 发放奖励
                rewards = quest.get('rewards', {})
                self._grant_quest_rewards(rewards)

                # 检查是否有后续任务
                quest_config = self.quests_by_id.get(quest['id'], {})
                next_quest_id = quest_config.get('next_quest')
                if next_quest_id:
                    self._accept_quest(next_quest_id)

        if completed_any:
            self.state.set('quests', quests_data)

    def _grant_quest_rewards(self, rewards: dict) -> None:
        """发放任务奖励"""
        if not rewards:
            return

        # 经验奖励
        if rewards.get('exp'):
            exp = rewards['exp']
            self.character.add_exp(exp)
            self._print(f"『获得 {exp} 点修为』")

        # 金币奖励
        if rewards.get('gold'):
            gold = rewards['gold']
            self.character.data['currency']['gold'] = self.character.data['currency'].get('gold', 0) + gold
            self._print(f"『获得 {gold} 金币』")

        # 属性点奖励
        if rewards.get('attribute_points'):
            points = rewards['attribute_points']
            self.character.data['attribute_points'] = self.character.data.get('attribute_points', 0) + points
            self._print(f"『获得 {points} 属性点』")

        # 物品奖励
        if rewards.get('items'):
            inv_data = self.state.get('inventory', {})
            inventory = Inventory(inv_data)
            for item_info in rewards['items']:
                item = {
                    'id': item_info['id'],
                    'name': item_info['name'],
                    'count': item_info.get('count', 1),
                    'stackable': True,
                    'quality': item_info.get('quality', 'common')
                }
                # 如果是技能书，添加技能
                if item_info.get('type') == 'skill_book' and item_info.get('skill_id'):
                    self._learn_skill_from_book(item_info['skill_id'])
                else:
                    inventory.add_item(item)
                    item_name = item['name']
                    item_count = item['count']
                    self._print(f"『获得 {item_name} x{item_count}』")
            self.state.set('inventory', inventory.to_dict())

        self.state.set('character', self.character.to_dict())

    def _learn_skill_from_book(self, skill_id: str) -> None:
        """从技能书学习技能"""
        # 查找技能配置
        all_skills = (
            self.skills_config.get('basic_skills', []) +
            self.skills_config.get('qi_refining_skills', []) +
            self.skills_config.get('foundation_skills', []) +
            self.skills_config.get('passive_skills', []) +
            self.skills_config.get('ultimate_skills', [])
        )

        for skill in all_skills:
            if skill['id'] == skill_id:
                # 检查是否已学会
                current_skills = self.character.data.get('skills', [])
                if any(s['id'] == skill_id for s in current_skills):
                    skill_name = skill['name']
                    self._print(f"『你已经学会了 {skill_name}』")
                    return

                self.character.data['skills'].append(skill.copy())
                skill_name = skill['name']
                self._print(f"『学会了新技能：{skill_name}』")
                return

        self._print(f"『无法学习技能：{skill_id}』")

    def _accept_quest(self, quest_id: str) -> None:
        """接取任务"""
        quest_config = self.quests_by_id.get(quest_id)
        if not quest_config:
            return

        quests_data = self.state.get('quests', {'quests': []})

        # 检查是否已接取
        for q in quests_data.get('quests', []):
            if q['id'] == quest_id:
                return

        # 添加任务
        quest_data = {
            'id': quest_config['id'],
            'name': quest_config['name'],
            'type': quest_config.get('type', 'main'),
            'description': quest_config['description'],
            'objectives': quest_config.get('objectives', []),
            'rewards': quest_config.get('rewards', {}),
            'status': 'active',
            'progress': {}
        }
        quests_data['quests'].append(quest_data)
        self.state.set('quests', quests_data)

        quest_name = quest_config['name']
        quest_desc = quest_config['description']
        self._print(f"\n『接取新任务：{quest_name}』")
        self._print(f"  {quest_desc}")

    def _handle_player_death(self) -> None:
        """处理玩家死亡"""
        self._print("\n『你被击败了...』")

        # 更新统计
        self.character.data['statistics']['deaths'] += 1

        # 死亡惩罚
        # 1. 损失一定比例的经验（10%，但不会掉级）
        current_exp = self.character.data.get('exp', 0)
        exp_lost = int(current_exp * 0.1)
        if exp_lost > 0:
            self.character.data['exp'] = max(0, current_exp - exp_lost)
            self._print(f"『损失了 {exp_lost} 点修为』")

        # 2. 损失一定比例的金币（20%）
        current_gold = self.character.data['currency'].get('gold', 0)
        gold_lost = int(current_gold * 0.2)
        if gold_lost > 0:
            self.character.data['currency']['gold'] = current_gold - gold_lost
            self._print(f"『丢失了 {gold_lost} 枚金币』")

        # 3. 有概率掉落背包中的物品（30%概率丢失一件随机物品）
        inv_data = self.state.get('inventory', {})
        items = inv_data.get('items', [])
        if items and random.random() < 0.3:
            lost_item = random.choice(items)
            lost_name = lost_item['name']
            lost_count = min(lost_item.get('count', 1), 1)  # 只丢1个
            if lost_item.get('count', 1) > 1:
                lost_item['count'] -= 1
            else:
                items.remove(lost_item)
            self.state.set('inventory', inv_data)
            self._print(f"『丢失了 {lost_name} x{lost_count}』")

        # 复活：回到满血（但只恢复50%），回到安全地点
        max_hp = self.character.data['derived_attributes']['hp_max']
        self.character.data['derived_attributes']['hp'] = max_hp // 2
        self.character.data['derived_attributes']['mp'] = self.character.data['derived_attributes']['mp_max'] // 2
        self.character.data['status']['is_alive'] = True
        self.character.data['status']['current_scene'] = "新手村"

        # 更新场景
        world_state = self.state.get('world', {})
        world_state['current_scene'] = self._get_or_create_scene("新手村")
        self.state.set('world', world_state)

        self._end_combat(victory=False)
        self._print("\n你在新手村的客栈中悠悠醒来，浑身酸痛，口袋也轻了许多...")
        self._print(f"当前状态：HP {self.character.data['derived_attributes']['hp']}/{max_hp}")

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

        # 初始化任务（自动接取新手任务）
        initial_quests = {"quests": []}
        for quest in self.quests_config.get('starter_quests', []):
            if quest.get('auto_accept'):
                quest_data = {
                    'id': quest['id'],
                    'name': quest['name'],
                    'type': quest.get('type', 'main'),
                    'description': quest['description'],
                    'objectives': quest.get('objectives', []),
                    'rewards': quest.get('rewards', {}),
                    'status': 'active',
                    'progress': {}
                }
                initial_quests['quests'].append(quest_data)
        self.state.set('quests', initial_quests)

        self.state.save_all()
        self._print(f"\n角色 {name} 创建成功！")

        # 显示新手提示
        self._print("\n『新手提示』")
        self._print("  - 输入 help 查看所有命令")
        self._print("  - 输入 quest 查看当前任务")
        self._print("  - 去找村长王老交谈吧！")

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
        """从配置获取场景数据"""
        # 先按名称查找
        scene_config = self.scenes_by_name.get(scene_name)
        if not scene_config:
            # 再按ID查找
            scene_config = self.scenes_by_id.get(scene_name)

        if scene_config:
            # 转换为游戏使用的格式
            features = [f['name'] for f in scene_config.get('features', [])]
            exits = [e['name'] for e in scene_config.get('exits', [])]

            return {
                "id": scene_config['id'],
                "name": scene_config['name'],
                "type": scene_config['type'],
                "description": scene_config['description'],
                "features": features,
                "features_detail": scene_config.get('features', []),
                "exits": exits,
                "exits_detail": scene_config.get('exits', []),
                "atmosphere": scene_config.get('atmosphere', '普通'),
                "danger_level": scene_config.get('danger_level', 'low'),
                "can_rest": scene_config.get('can_rest', False),
                "can_save": scene_config.get('can_save', False)
            }

        # 未知场景
        return {
            "name": scene_name,
            "type": "unknown",
            "description": f"你来到了{scene_name}，这是一片未知的区域。",
            "features": [],
            "exits": ["新手村"],
            "atmosphere": "未知",
            "danger_level": "unknown"
        }

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
