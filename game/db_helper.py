#!/usr/bin/env python3
"""
修仙游戏数据库操作助手
用于初始化、查询、更新游戏数据
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "xiuxian.db"


def get_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)


def init_new_game(name: str, spiritual_root: str, golden_finger: str,
                  origin: str, age: int = 16):
    """
    初始化新游戏
    """
    conn = get_connection()
    cur = conn.cursor()

    # 清空所有表
    tables = ['character', 'game_time', 'currency', 'inventory',
              'techniques', 'enchantments', 'relationships',
              'golden_finger', 'event_log', 'intelligence']
    for table in tables:
        cur.execute(f"DELETE FROM {table}")

    # 初始化角色
    cur.execute("""
        INSERT INTO character (id, name, age, realm, spiritual_root,
                               lifespan_max, location, identity)
        VALUES (1, ?, ?, '凡人', ?, 100, ?, ?)
    """, (name, age, spiritual_root, origin, '凡人'))

    # 初始化时间（第1天）
    cur.execute("""
        INSERT INTO game_time (id, year, month, day, total_days)
        VALUES (1, 1, 1, 1, 1)
    """)

    # 初始化货币（白手起家）
    cur.execute("""
        INSERT INTO currency (id, spirit_stone_low, mortal_silver)
        VALUES (1, 0, 0)
    """)

    # 初始化金手指
    cur.execute("""
        INSERT INTO golden_finger (id, system_type)
        VALUES (1, ?)
    """, (golden_finger,))

    conn.commit()
    conn.close()
    print(f"新游戏初始化完成：{name}")


def get_status():
    """获取当前状态摘要"""
    conn = get_connection()
    cur = conn.cursor()

    # 角色信息
    cur.execute("SELECT * FROM character WHERE id = 1")
    char = cur.fetchone()

    # 时间
    cur.execute("SELECT * FROM game_time WHERE id = 1")
    time = cur.fetchone()

    # 货币
    cur.execute("SELECT * FROM currency WHERE id = 1")
    currency = cur.fetchone()

    # 金手指
    cur.execute("SELECT system_type FROM golden_finger WHERE id = 1")
    gf = cur.fetchone()

    conn.close()

    if not char:
        return "无存档"

    status = f"""
【状态】
姓名：{char[1]} | 境界：{char[3]}（进度{char[4]}%）
灵根：{char[5]} | 寿元：{char[6]}/{char[7]}年
位置：{char[8]}
时间：第{time[4]}天（{time[1]}年{time[2]}月{time[3]}日）
灵石：{currency[1]}块
金手指：{gf[0] if gf else '无'}
"""
    return status


def update_realm(realm: str, progress: int = 0):
    """更新境界"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE character SET realm = ?, realm_progress = ?, updated_at = ?
        WHERE id = 1
    """, (realm, progress, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def update_progress(progress: int):
    """更新境界进度"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE character SET realm_progress = ?, updated_at = ?
        WHERE id = 1
    """, (progress, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def advance_day(days: int = 1):
    """推进游戏时间"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT year, month, day, total_days FROM game_time WHERE id = 1")
    year, month, day, total = cur.fetchone()

    for _ in range(days):
        total += 1
        day += 1
        if day > 30:  # 简化为每月30天
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1

    cur.execute("""
        UPDATE game_time SET year = ?, month = ?, day = ?, total_days = ?
        WHERE id = 1
    """, (year, month, day, total))

    # 更新角色已用寿元
    cur.execute("""
        UPDATE character SET lifespan_used = lifespan_used + ?
        WHERE id = 1
    """, (days / 365,))

    conn.commit()
    conn.close()
    return total


def add_spirit_stones(amount: int):
    """增加灵石"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE currency SET spirit_stone_low = spirit_stone_low + ?, updated_at = ?
        WHERE id = 1
    """, (amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def add_item(name: str, item_type: str, grade: str = None,
             quantity: int = 1, attribute: str = None,
             notes: str = None, source: str = None):
    """添加物品"""
    conn = get_connection()
    cur = conn.cursor()

    # 获取当前游戏天数
    cur.execute("SELECT total_days FROM game_time WHERE id = 1")
    day = cur.fetchone()[0]

    # 检查是否已有同名物品（可堆叠）
    cur.execute("""
        SELECT id, quantity FROM inventory
        WHERE item_name = ? AND item_type = ?
    """, (name, item_type))
    existing = cur.fetchone()

    if existing and item_type in ['灵石', '丹药', '符箓', '材料']:
        # 可堆叠物品，增加数量
        cur.execute("""
            UPDATE inventory SET quantity = quantity + ?
            WHERE id = ?
        """, (quantity, existing[0]))
    else:
        # 新物品
        cur.execute("""
            INSERT INTO inventory (item_name, item_type, grade, quantity,
                                   attribute, notes, source, acquired_day)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, item_type, grade, quantity, attribute, notes, source, day))

    conn.commit()
    conn.close()


def remove_item(name: str, quantity: int = 1):
    """移除物品"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, quantity FROM inventory WHERE item_name = ?
    """, (name,))
    item = cur.fetchone()

    if item:
        if item[1] <= quantity:
            cur.execute("DELETE FROM inventory WHERE id = ?", (item[0],))
        else:
            cur.execute("""
                UPDATE inventory SET quantity = quantity - ?
                WHERE id = ?
            """, (quantity, item[0]))

    conn.commit()
    conn.close()


def get_inventory():
    """获取物品栏"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT item_name, item_type, grade, quantity, notes
        FROM inventory ORDER BY item_type, grade
    """)
    items = cur.fetchall()
    conn.close()
    return items


def add_technique(name: str, tech_type: str, grade: str = None,
                  attribute: str = None, effects: str = None,
                  source: str = None, is_main: int = 0):
    """添加功法/术法"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO techniques (name, type, grade, attribute, effects, source, is_main)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, tech_type, grade, attribute, effects, source, is_main))
    conn.commit()
    conn.close()


def update_technique_proficiency(name: str, proficiency: int):
    """更新术法熟练度"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE techniques SET proficiency = ? WHERE name = ?
    """, (proficiency, name))
    conn.commit()
    conn.close()


def add_relationship(npc_name: str, npc_realm: str = None,
                     faction: str = None, attitude: int = 0,
                     relationship: str = '中立', notes: str = None):
    """添加NPC关系"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT total_days FROM game_time WHERE id = 1")
    day = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO relationships (npc_name, npc_realm, faction, attitude,
                                   relationship, first_met_day, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (npc_name, npc_realm, faction, attitude, relationship, day, notes))
    conn.commit()
    conn.close()


def update_relationship(npc_name: str, attitude_change: int):
    """更新NPC好感度"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE relationships
        SET attitude = MIN(100, MAX(-100, attitude + ?)), updated_at = ?
        WHERE npc_name = ?
    """, (attitude_change, datetime.now().isoformat(), npc_name))
    conn.commit()
    conn.close()


def log_event(event_type: str, summary: str,
              details: str = None, importance: str = '普通'):
    """记录事件"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT total_days FROM game_time WHERE id = 1")
    day = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO event_log (game_day, event_type, importance, summary, details)
        VALUES (?, ?, ?, ?, ?)
    """, (day, event_type, importance, summary, details))
    conn.commit()
    conn.close()


def update_signin(streak: int, total: int):
    """更新签到状态"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT total_days FROM game_time WHERE id = 1")
    day = cur.fetchone()[0]

    cur.execute("""
        UPDATE golden_finger
        SET signin_streak = ?, signin_total = ?, last_signin_day = ?
        WHERE id = 1
    """, (streak, total, day))
    conn.commit()
    conn.close()


def add_enchantment(name: str, grade: str, effect_type: str,
                    effect_value: str, source: str = None):
    """添加词条"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT total_days FROM game_time WHERE id = 1")
    day = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO enchantments (name, grade, effect_type, effect_value,
                                  source, acquired_day)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, grade, effect_type, effect_value, source, day))
    conn.commit()
    conn.close()


def get_recent_events(limit: int = 10):
    """获取最近事件"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT game_day, event_type, summary FROM event_log
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    events = cur.fetchall()
    conn.close()
    return events


if __name__ == "__main__":
    # 测试
    print(get_status())
