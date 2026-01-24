-- 修仙游戏数据库结构
-- 创建时间: 2026-01-20

-- ============================================
-- 角色基础信息
-- ============================================
CREATE TABLE IF NOT EXISTS character (
    id INTEGER PRIMARY KEY DEFAULT 1,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    realm TEXT NOT NULL,              -- 境界：炼气一层、筑基初期等
    realm_progress INTEGER DEFAULT 0, -- 境界进度 0-100
    spiritual_root TEXT NOT NULL,     -- 灵根：水木双灵根
    lifespan_used INTEGER DEFAULT 0,  -- 已用寿元（年）
    lifespan_max INTEGER DEFAULT 100, -- 寿元上限（年）
    location TEXT,                    -- 当前位置
    faction TEXT,                     -- 所属势力
    identity TEXT,                    -- 身份：外门弟子等
    contribution_points INTEGER DEFAULT 0, -- 贡献点
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 游戏时间
-- ============================================
CREATE TABLE IF NOT EXISTS game_time (
    id INTEGER PRIMARY KEY DEFAULT 1,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    total_days INTEGER DEFAULT 0  -- 游戏总天数（从开始算）
);

-- ============================================
-- 物品栏
-- ============================================
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,          -- 灵石/丹药/法器/功法/符箓/材料/杂物
    grade TEXT,                       -- 品级：下品/中品/上品/极品
    quantity INTEGER DEFAULT 1,
    attribute TEXT,                   -- 属性：金木水火土
    is_equipped INTEGER DEFAULT 0,    -- 是否装备中
    is_bound INTEGER DEFAULT 0,       -- 是否已炼化绑定
    durability INTEGER DEFAULT 100,   -- 耐久度
    notes TEXT,                       -- 备注/特殊效果
    source TEXT,                      -- 来源：签到/购买/战利品等
    acquired_day INTEGER,             -- 获得时的游戏天数
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 功法与术法
-- ============================================
CREATE TABLE IF NOT EXISTS techniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,               -- 功法/术法/被动
    grade TEXT,                       -- 下品/中品/上品
    attribute TEXT,                   -- 属性
    proficiency INTEGER DEFAULT 0,    -- 熟练度 0-100
    is_main INTEGER DEFAULT 0,        -- 是否主修功法
    max_level TEXT,                   -- 最高可修炼境界
    current_level TEXT,               -- 当前修炼层数
    effects TEXT,                     -- 效果描述
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 词条系统
-- ============================================
CREATE TABLE IF NOT EXISTS enchantments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,               -- 词条名：锋利、吸血、坚韧等
    grade TEXT NOT NULL,              -- 白/绿/蓝/紫/金/红
    effect_type TEXT,                 -- 攻击/防御/辅助/特效
    effect_value TEXT,                -- 效果数值描述
    attached_to INTEGER,              -- 附加到的物品ID（inventory表）
    attached_type TEXT,               -- item/technique/body
    source TEXT,                      -- 来源
    acquired_day INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- NPC关系
-- ============================================
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_name TEXT NOT NULL,
    npc_realm TEXT,                   -- NPC境界
    faction TEXT,                     -- 所属势力
    attitude INTEGER DEFAULT 0,       -- 好感度 -100到100
    relationship TEXT,                -- 关系描述：友善/中立/敌对/师徒等
    first_met_day INTEGER,            -- 首次相遇的游戏天数
    notes TEXT,
    is_alive INTEGER DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 金手指系统状态
-- ============================================
CREATE TABLE IF NOT EXISTS golden_finger (
    id INTEGER PRIMARY KEY DEFAULT 1,
    system_type TEXT NOT NULL,        -- 选择的金手指类型

    -- 签到系统
    signin_streak INTEGER DEFAULT 0,  -- 连续签到天数
    signin_total INTEGER DEFAULT 0,   -- 总签到天数
    last_signin_day INTEGER,          -- 上次签到的游戏天数

    -- 炼化抽奖
    lottery_tickets INTEGER DEFAULT 0, -- 抽奖次数

    -- 词条抽附
    enchant_used_today INTEGER DEFAULT 0, -- 今日是否已使用
    enchant_last_day INTEGER,         -- 上次使用的游戏天数

    -- 每日任务
    daily_task_1 TEXT,
    daily_task_1_done INTEGER DEFAULT 0,
    daily_task_2 TEXT,
    daily_task_2_done INTEGER DEFAULT 0,
    daily_task_3 TEXT,
    daily_task_3_done INTEGER DEFAULT 0,
    daily_task_refresh_day INTEGER,   -- 任务刷新的游戏天数

    -- 系统商店
    shop_refresh_day INTEGER,         -- 商店刷新的游戏天数
    shop_items TEXT,                  -- JSON格式的当前商品列表

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 事件日志（重要事件记录）
-- ============================================
CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_day INTEGER NOT NULL,        -- 发生时的游戏天数
    event_type TEXT,                  -- 战斗/突破/机缘/交易/任务等
    importance TEXT DEFAULT '普通',   -- 普通/重要/关键
    summary TEXT NOT NULL,            -- 事件摘要
    details TEXT,                     -- 详细描述
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 已知情报
-- ============================================
CREATE TABLE IF NOT EXISTS intelligence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,                    -- 人物/势力/地点/秘闻
    title TEXT NOT NULL,
    content TEXT,
    source TEXT,                      -- 情报来源
    reliability TEXT DEFAULT '未知',  -- 可靠度：确认/可能/传闻/未知
    acquired_day INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 灵石专用表（货币）
-- ============================================
CREATE TABLE IF NOT EXISTS currency (
    id INTEGER PRIMARY KEY DEFAULT 1,
    spirit_stone_low INTEGER DEFAULT 0,    -- 下品灵石
    spirit_stone_mid INTEGER DEFAULT 0,    -- 中品灵石
    spirit_stone_high INTEGER DEFAULT 0,   -- 上品灵石
    spirit_stone_supreme INTEGER DEFAULT 0, -- 极品灵石
    mortal_silver INTEGER DEFAULT 0,       -- 凡人银两
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 价格参考表（三轴定价体系）
-- ============================================
CREATE TABLE IF NOT EXISTS price_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,           -- 丹药/法器/功法/符箓/灵药/材料
    sub_category TEXT,                -- 细分类：炼器材料/战斗符等
    realm TEXT NOT NULL,              -- 炼气期/筑基期/金丹期
    quality TEXT NOT NULL,            -- 下品/中品/上品/极品
    color TEXT,                       -- 灰/白/绿/蓝/紫/金/红
    item_name TEXT NOT NULL,          -- 物品名称
    price_low INTEGER NOT NULL,       -- 最低价格
    price_high INTEGER NOT NULL,      -- 最高价格
    unit TEXT DEFAULT '下品灵石',     -- 计价单位
    notes TEXT,                       -- 备注说明
    UNIQUE(category, realm, quality, item_name)
);

CREATE INDEX IF NOT EXISTS idx_price_category ON price_reference(category);
CREATE INDEX IF NOT EXISTS idx_price_realm ON price_reference(realm);
CREATE INDEX IF NOT EXISTS idx_price_quality ON price_reference(quality);

-- ============================================
-- 索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_inventory_type ON inventory(item_type);
CREATE INDEX IF NOT EXISTS idx_inventory_equipped ON inventory(is_equipped);
CREATE INDEX IF NOT EXISTS idx_event_log_day ON event_log(game_day);
CREATE INDEX IF NOT EXISTS idx_relationships_attitude ON relationships(attitude);
