"""
记忆管理模块
负责为AI构建上下文，管理长期/短期记忆
"""
from typing import Optional
from datetime import datetime


class MemoryManager:
    """记忆管理器 - 为AI构建合适的上下文"""

    def __init__(self, state_manager, world_setting: str, rules_summary: str):
        self.state = state_manager
        self.world_setting = world_setting
        self.rules_summary = rules_summary

        # Token预算（Claude的上下文窗口）
        self.max_context_tokens = 180000  # 保守估计
        self.reserved_for_response = 4000

    def build_context(self,
                      include_full_history: bool = False,
                      focus_area: Optional[str] = None) -> str:
        """
        构建AI上下文

        Args:
            include_full_history: 是否包含完整历史
            focus_area: 焦点区域（combat, dialogue, exploration等）

        Returns:
            格式化的上下文字符串
        """
        sections = []

        # 1. 系统设定（永远包含）
        sections.append(self._build_system_prompt(focus_area))

        # 2. 世界观（压缩版）
        sections.append(self._build_world_context())

        # 3. 角色状态（当前）
        sections.append(self._build_character_context())

        # 4. 当前场景
        sections.append(self._build_scene_context())

        # 5. 相关NPC
        sections.append(self._build_npc_context())

        # 6. 活跃任务
        sections.append(self._build_quest_context())

        # 7. 剧情历史（根据需要压缩）
        if include_full_history:
            sections.append(self._build_full_story_context())
        else:
            sections.append(self._build_recent_story_context())

        # 8. 关系网络（如果相关）
        if focus_area in ['dialogue', 'social']:
            sections.append(self._build_relationship_context())

        return "\n\n".join(filter(None, sections))

    def _build_system_prompt(self, focus_area: Optional[str] = None) -> str:
        """构建系统提示"""
        base_prompt = """# 你的角色
你是一个仙侠世界的游戏主持人（GM），负责：
1. 描述场景、环境、NPC的言行
2. 推动剧情发展
3. 扮演NPC与玩家对话
4. 根据玩家行动给出合理的世界反馈

# 重要规则
- 你不能替玩家做决定或行动
- 所有数值计算由游戏系统完成，你只负责叙事
- 保持世界观一致性
- NPC的行为要符合其性格和立场
- 战斗描述要配合系统给出的伤害数值
- 不要编造系统没有的物品、技能或NPC

# 输出格式
- 环境描写用【】标注
- NPC对话用「」标注
- 系统提示用『』标注
- 保持叙事简洁有力，避免冗长"""

        focus_prompts = {
            'combat': """
# 当前焦点：战斗
- 根据系统计算的伤害数值描述战斗场面
- 描述招式的视觉效果
- 注意描述战斗节奏和紧张感
- 战斗结果由系统判定，你只负责描写""",

            'dialogue': """
# 当前焦点：对话
- 扮演NPC，保持其性格一致
- 对话要有信息量，推动剧情或透露线索
- 注意NPC与玩家的关系和态度
- 可以适当加入NPC的小动作和表情""",

            'exploration': """
# 当前焦点：探索
- 详细描述环境细节
- 暗示可能的互动点
- 营造氛围（危险/神秘/宁静等）
- 适时给出环境线索""",

            'cultivation': """
# 当前焦点：修炼
- 描述修炼时的身体感受和灵气运转
- 突破时要有仪式感
- 可以加入心境描写
- 注意修炼环境的影响"""
        }

        if focus_area and focus_area in focus_prompts:
            base_prompt += focus_prompts[focus_area]

        return base_prompt

    def _build_world_context(self) -> str:
        """构建世界观上下文"""
        return f"""# 世界设定
{self.world_setting}

# 规则摘要
{self.rules_summary}"""

    def _build_character_context(self) -> str:
        """构建角色上下文"""
        char_data = self.state.get('character', {})
        if not char_data:
            return ""

        realm = char_data.get('realm', {})
        derived = char_data.get('derived_attributes', {})
        primary = char_data.get('primary_attributes', {})
        status = char_data.get('status', {})
        currency = char_data.get('currency', {})

        # 装备摘要
        equipment = char_data.get('equipment', {})
        equipped_items = []
        for slot, item in equipment.items():
            if item:
                if isinstance(item, dict):
                    equipped_items.append(f"{slot}: {item.get('name', '未知')}")
                elif isinstance(item, list):
                    for i in item:
                        if i:
                            equipped_items.append(f"{slot}: {i.get('name', '未知')}")

        equip_str = "、".join(equipped_items) if equipped_items else "无"

        # 技能摘要
        skills = char_data.get('skills', [])
        skill_names = [s.get('name', '未知') for s in skills[:5]]  # 只显示前5个
        skill_str = "、".join(skill_names) if skill_names else "无"
        if len(skills) > 5:
            skill_str += f"...等{len(skills)}个技能"

        # Buff摘要
        buffs = char_data.get('buffs', [])
        buff_str = "、".join([b.get('name', '未知') for b in buffs]) if buffs else "无"

        return f"""# 玩家角色状态
【{char_data.get('name', '无名')}】
境界：{realm.get('name', '?')} {realm.get('sub_realm', '?')}
生命：{derived.get('hp', 0)}/{derived.get('hp_max', 0)}
法力：{derived.get('mp', 0)}/{derived.get('mp_max', 0)}
攻击：{derived.get('attack', 0)} | 防御：{derived.get('defense', 0)} | 速度：{derived.get('speed', 0)}
暴击：{derived.get('crit_rate', 0)*100:.1f}% | 闪避：{derived.get('dodge_rate', 0)*100:.1f}%

经验：{char_data.get('exp', {}).get('current', 0)}/{char_data.get('exp', {}).get('to_next_level', 0)}
可用属性点：{char_data.get('attribute_points', 0)}

位置：{status.get('current_location', '未知')} - {status.get('current_scene', '未知')}
状态：{'战斗中' if status.get('is_in_combat') else '修炼中' if status.get('is_cultivating') else '正常'}

装备：{equip_str}
技能：{skill_str}
增益/减益：{buff_str}

金币：{currency.get('gold', 0)} | 灵石：{currency.get('spirit_stones', 0)}"""

    def _build_scene_context(self) -> str:
        """构建当前场景上下文"""
        world_state = self.state.get('world', {})
        current_scene = world_state.get('current_scene', {})

        if not current_scene:
            return ""

        return f"""# 当前场景
{current_scene.get('name', '未知场景')}

{current_scene.get('description', '无描述')}

可见物品/特征：{', '.join(current_scene.get('features', ['无']))}
可前往：{', '.join(current_scene.get('exits', ['无']))}
环境氛围：{current_scene.get('atmosphere', '普通')}
危险等级：{current_scene.get('danger_level', '安全')}"""

    def _build_npc_context(self) -> str:
        """构建NPC上下文"""
        npcs_data = self.state.get('npcs', {})
        world_state = self.state.get('world', {})

        # 获取当前位置
        char_data = self.state.get('character', {})
        current_location = char_data.get('status', {}).get('current_location', '')
        current_scene = char_data.get('status', {}).get('current_scene', '')

        # 筛选当前场景的NPC
        present_npcs = []
        for npc_id, npc in npcs_data.get('npcs', {}).items():
            npc_location = npc.get('location', '')
            # 支持多种匹配方式：完整位置、场景名、或位置名
            if npc_location in [f"{current_location}-{current_scene}",
                               current_scene,
                               current_location]:
                present_npcs.append(npc)

        if not present_npcs:
            return ""

        npc_descriptions = []
        for npc in present_npcs[:5]:  # 最多显示5个
            desc = f"""【{npc.get('name', '未知')}】
类型：{npc.get('type', '未知')}
境界：{npc.get('realm', {}).get('name', '?')}
性格：{npc.get('personality', '未知')}
描述：{npc.get('description', '无')}"""
            npc_descriptions.append(desc)

        return "# 当前场景NPC\n" + "\n\n".join(npc_descriptions)

    def _build_quest_context(self) -> str:
        """构建任务上下文"""
        quests_data = self.state.get('quests', {})
        active_quests = [q for q in quests_data.get('quests', [])
                        if q.get('status') == 'active']

        if not active_quests:
            return ""

        quest_texts = []
        for quest in active_quests[:3]:  # 最多显示3个
            objectives = quest.get('objectives', [])
            progress = quest.get('progress', {})

            obj_texts = []
            for obj in objectives:
                current = progress.get(obj['id'], 0)
                required = obj.get('required', 1)
                status = "✓" if current >= required else f"{current}/{required}"
                obj_texts.append(f"  - {obj.get('description', '未知')}: {status}")

            quest_texts.append(f"""【{quest.get('name', '未知任务')}】
{quest.get('description', '')}
目标：
{chr(10).join(obj_texts)}""")

        return "# 进行中的任务\n" + "\n\n".join(quest_texts)

    def _build_recent_story_context(self, count: int = 15) -> str:
        """构建最近剧情上下文"""
        story_data = self.state.get('story_log', {})
        entries = story_data.get('entries', [])[-count:]

        if not entries:
            return ""

        story_texts = [e.get('content', '') for e in entries]
        return "# 最近发生的事\n" + "\n".join(story_texts)

    def _build_full_story_context(self) -> str:
        """构建完整剧情上下文（包含摘要）"""
        story_data = self.state.get('story_log', {})

        parts = []

        # 添加摘要
        summaries = story_data.get('summaries', [])
        if summaries:
            summary_texts = [s.get('content', '') for s in summaries]
            parts.append("## 历史摘要\n" + "\n".join(summary_texts))

        # 添加详细记录
        entries = story_data.get('entries', [])
        if entries:
            entry_texts = [e.get('content', '') for e in entries]
            parts.append("## 详细记录\n" + "\n".join(entry_texts))

        if not parts:
            return ""

        return "# 剧情历史\n" + "\n\n".join(parts)

    def _build_relationship_context(self) -> str:
        """构建关系网络上下文"""
        rel_data = self.state.get('relationships', {})

        if not rel_data:
            return ""

        char_name = self.state.get('character', {}).get('name', '玩家')
        relationships = rel_data.get('relationships', {})

        if not relationships:
            return ""

        rel_texts = []
        for npc_id, rel in relationships.items():
            attitude = rel.get('attitude', 0)
            if attitude > 50:
                status = "友好"
            elif attitude > 0:
                status = "中立偏好"
            elif attitude > -50:
                status = "中立偏恶"
            else:
                status = "敌对"

            rel_texts.append(f"- {rel.get('npc_name', npc_id)}: {status} ({attitude})")

        return f"# {char_name}的人际关系\n" + "\n".join(rel_texts)

    def build_combat_context(self, enemies: list, round_number: int) -> str:
        """构建战斗专用上下文"""
        sections = []

        # 基础上下文
        sections.append(self._build_system_prompt('combat'))

        # 玩家状态
        sections.append(self._build_character_context())

        # 敌人状态
        enemy_texts = []
        for enemy in enemies:
            derived = enemy.get('derived_attributes', {})
            enemy_texts.append(f"""【{enemy.get('name', '未知')}】
境界：{enemy.get('realm', {}).get('name', '?')}
生命：{derived.get('hp', 0)}/{derived.get('hp_max', 0)}
状态：{'存活' if enemy.get('is_alive', True) else '已死亡'}""")

        sections.append("# 敌人\n" + "\n\n".join(enemy_texts))

        # 战斗信息
        sections.append(f"# 战斗信息\n当前回合：{round_number}")

        return "\n\n".join(sections)

    def summarize_story(self, entries: list, ai_client) -> str:
        """使用AI生成剧情摘要"""
        content = "\n".join([e.get('content', '') for e in entries])

        prompt = f"""请将以下剧情内容压缩成简短摘要（100字以内），保留关键事件和重要信息：

{content}

摘要："""

        # 这里需要调用AI
        # summary = ai_client.generate(prompt, max_tokens=200)
        # return summary

        # 临时返回简单摘要
        return f"[包含{len(entries)}个事件的剧情摘要]"

    def get_context_for_action(self, action_type: str, **kwargs) -> str:
        """根据行动类型获取上下文"""
        focus_map = {
            'attack': 'combat',
            'skill': 'combat',
            'defend': 'combat',
            'flee': 'combat',
            'talk': 'dialogue',
            'ask': 'dialogue',
            'look': 'exploration',
            'search': 'exploration',
            'move': 'exploration',
            'cultivate': 'cultivation',
            'breakthrough': 'cultivation'
        }

        focus = focus_map.get(action_type, None)
        return self.build_context(focus_area=focus)
