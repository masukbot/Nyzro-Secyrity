"""
Rinox Sentinel - Database Manager
PostgreSQL with SQLite automatic fallback
"""

import asyncpg
import aiosqlite
import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("Rinox.Database")


class DatabaseManager:
    """Manages all database operations"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self._db_type = "postgres"
        self._conn = None

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id BIGINT PRIMARY KEY,
                    ai_provider TEXT DEFAULT 'openai',
                    ai_model TEXT DEFAULT 'gpt-4o',
                    ai_api_key TEXT,
                    ai_base_url TEXT,
                    temperature REAL DEFAULT 0.3,
                    max_tokens INTEGER DEFAULT 4096,
                    vision_enabled BOOLEAN DEFAULT TRUE,
                    ocr_enabled BOOLEAN DEFAULT TRUE,
                    streaming_enabled BOOLEAN DEFAULT TRUE,
                    security_config JSONB DEFAULT '{}',
                    moderation_config JSONB DEFAULT '{}',
                    enabled_features JSONB DEFAULT '["image_scan", "message_scan", "attachment_scan", "url_scan"]',
                    whitelist JSONB DEFAULT '[]',
                    blacklist JSONB DEFAULT '[]',
                    custom_prompts JSONB DEFAULT '{}',
                    language TEXT DEFAULT 'en',
                    premium BOOLEAN DEFAULT FALSE,
                    log_channel_id BIGINT,
                    appeal_channel_id BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS moderation_logs (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    moderator_id BIGINT,
                    action_type TEXT NOT NULL,
                    reason TEXT,
                    evidence JSONB DEFAULT '[]',
                    duration INTEGER,
                    ai_confidence REAL,
                    risk_score INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id BIGINT,
                    channel_id BIGINT,
                    message_id BIGINT,
                    content TEXT,
                    threat_level INTEGER DEFAULT 0,
                    risk_score INTEGER DEFAULT 0,
                    ai_confidence REAL,
                    action_taken TEXT,
                    evidence JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_warnings (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    moderator_id BIGINT,
                    reason TEXT,
                    weight INTEGER DEFAULT 1,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_usage (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    endpoint TEXT,
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    latency_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    backup_name TEXT NOT NULL,
                    backup_data JSONB NOT NULL,
                    size_bytes INTEGER,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    messages_scanned INTEGER DEFAULT 0,
                    threats_detected INTEGER DEFAULT 0,
                    actions_taken INTEGER DEFAULT 0,
                    false_positives INTEGER DEFAULT 0,
                    ai_calls INTEGER DEFAULT 0,
                    avg_risk_score REAL DEFAULT 0,
                    UNIQUE(guild_id, date)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    list_type TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_id BIGINT,
                    item_value TEXT,
                    reason TEXT,
                    added_by BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    task_type TEXT NOT NULL,
                    task_data JSONB DEFAULT '{}',
                    next_run TIMESTAMP NOT NULL,
                    interval_hours INTEGER DEFAULT 24,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Feature-based AI providers
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS feature_providers (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    feature TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT,
                    priority INTEGER DEFAULT 0,
                    enabled BOOLEAN DEFAULT TRUE,
                    max_daily INTEGER DEFAULT 0,
                    daily_used INTEGER DEFAULT 0,
                    last_reset DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(guild_id, feature, provider)
                )
            """)

            # Channel AI modes
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_ai_modes (
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    feature TEXT NOT NULL,
                    config JSONB DEFAULT '{}',
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (guild_id, channel_id)
                )
            """)

            # Auto-clean settings
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_clean (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    delay_seconds INTEGER NOT NULL,
                    filter_type TEXT DEFAULT 'all',
                    whitelist_roles JSONB DEFAULT '[]',
                    whitelist_users JSONB DEFAULT '[]',
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(guild_id, channel_id)
                )
            """)

            logger.info("✅ PostgreSQL tables initialized")

    async def create_guild_settings(self, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO guild_settings (guild_id)
                VALUES ($1)
                ON CONFLICT (guild_id) DO NOTHING
            """, guild_id)

    async def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            return dict(row) if row else None

    async def update_guild_settings(self, guild_id: int, **kwargs):
        if not kwargs:
            return
        columns = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join([f"{col} = ${i+2}" for i, col in enumerate(columns)])
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE guild_settings
                SET {set_clause}, updated_at = NOW()
                WHERE guild_id = $1
                """,
                guild_id, *values
            )

    async def log_moderation(self, guild_id: int, user_id: int,
                           action_type: str, **kwargs):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO moderation_logs
                (guild_id, user_id, moderator_id, action_type, reason,
                 evidence, duration, ai_confidence, risk_score)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, guild_id, user_id, kwargs.get('moderator_id'),
                action_type, kwargs.get('reason'),
                json.dumps(kwargs.get('evidence', [])),
                kwargs.get('duration'), kwargs.get('ai_confidence'),
                kwargs.get('risk_score'))

    async def log_security_event(self, guild_id: int, event_type: str, **kwargs):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO security_events
                (guild_id, event_type, user_id, channel_id, message_id,
                 content, threat_level, risk_score, ai_confidence,
                 action_taken, evidence)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, guild_id, event_type, kwargs.get('user_id'),
                kwargs.get('channel_id'), kwargs.get('message_id'),
                kwargs.get('content'), kwargs.get('threat_level', 0),
                kwargs.get('risk_score', 0), kwargs.get('ai_confidence'),
                kwargs.get('action_taken'), json.dumps(kwargs.get('evidence', {})))

    async def add_warning(self, guild_id: int, user_id: int,
                         reason: str, moderator_id: int = None,
                         weight: int = 1, expires_at: datetime = None):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_warnings
                (guild_id, user_id, moderator_id, reason, weight, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, guild_id, user_id, moderator_id, reason, weight, expires_at)

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM user_warnings
                WHERE guild_id = $1 AND user_id = $2 AND active = TRUE
                ORDER BY created_at DESC
            """, guild_id, user_id)
            return [dict(row) for row in rows]

    async def get_analytics(self, guild_id: int, days: int = 7) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM analytics
                WHERE guild_id = $1 AND date >= CURRENT_DATE - $2::integer
                ORDER BY date DESC
            """, guild_id, days)
            return [dict(row) for row in rows]

    async def update_analytics(self, guild_id: int, **kwargs):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO analytics (guild_id, date, messages_scanned,
                    threats_detected, actions_taken, false_positives,
                    ai_calls, avg_risk_score)
                VALUES ($1, CURRENT_DATE, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (guild_id, date) DO UPDATE SET
                    messages_scanned = analytics.messages_scanned + EXCLUDED.messages_scanned,
                    threats_detected = analytics.threats_detected + EXCLUDED.threats_detected,
                    actions_taken = analytics.actions_taken + EXCLUDED.actions_taken,
                    false_positives = analytics.false_positives + EXCLUDED.false_positives,
                    ai_calls = analytics.ai_calls + EXCLUDED.ai_calls,
                    avg_risk_score = (analytics.avg_risk_score + EXCLUDED.avg_risk_score) / 2
            """, guild_id,
                kwargs.get('messages_scanned', 0),
                kwargs.get('threats_detected', 0),
                kwargs.get('actions_taken', 0),
                kwargs.get('false_positives', 0),
                kwargs.get('ai_calls', 0),
                kwargs.get('avg_risk_score', 0))

    async def create_backup(self, guild_id: int, backup_name: str,
                           backup_data: Dict, size_bytes: int,
                           created_by: int):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO backups (guild_id, backup_name, backup_data, size_bytes, created_by)
                VALUES ($1, $2, $3, $4, $5)
            """, guild_id, backup_name, json.dumps(backup_data),
                size_bytes, created_by)

    async def get_backups(self, guild_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM backups
                WHERE guild_id = $1
                ORDER BY created_at DESC
            """, guild_id)
            return [dict(row) for row in rows]

    # ==================== FEATURE PROVIDERS ====================

    async def set_feature_provider(self, guild_id: int, feature: str, provider: str,
                                    model: str = None, priority: int = 0, max_daily: int = 0):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO feature_providers (guild_id, feature, provider, model, priority, max_daily)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (guild_id, feature, provider) DO UPDATE SET
                    model = EXCLUDED.model,
                    priority = EXCLUDED.priority,
                    max_daily = EXCLUDED.max_daily,
                    enabled = TRUE
            """, guild_id, feature, provider, model, priority, max_daily)

    async def remove_feature_provider(self, guild_id: int, feature: str, provider: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM feature_providers
                WHERE guild_id = $1 AND feature = $2 AND provider = $3
            """, guild_id, feature, provider)

    async def get_feature_providers(self, guild_id: int, feature: str) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM feature_providers
                WHERE guild_id = $1 AND feature = $2 AND enabled = TRUE
                ORDER BY priority ASC
            """, guild_id, feature)
            return [dict(r) for r in rows]

    async def get_all_feature_configs(self, guild_id: int) -> Dict[str, List[Dict]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM feature_providers
                WHERE guild_id = $1 AND enabled = TRUE
                ORDER BY feature, priority ASC
            """, guild_id)
            configs = {}
            for r in rows:
                d = dict(r)
                configs.setdefault(d["feature"], []).append(d)
            return configs

    async def increment_daily_usage(self, guild_id: int, feature: str, provider: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE feature_providers SET
                    daily_used = daily_used + 1,
                    last_reset = CURRENT_DATE
                WHERE guild_id = $1 AND feature = $2 AND provider = $3
            """, guild_id, feature, provider)
            row = await conn.fetchrow("""
                SELECT daily_used, max_daily FROM feature_providers
                WHERE guild_id = $1 AND feature = $2 AND provider = $3
            """, guild_id, feature, provider)
            if row:
                return row["daily_used"], row["max_daily"]
            return 0, 0

    async def reset_daily_usage(self, guild_id: int, feature: str, provider: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE feature_providers SET daily_used = 0, last_reset = CURRENT_DATE
                WHERE guild_id = $1 AND feature = $2 AND provider = $3
            """, guild_id, feature, provider)

    # ==================== CHANNEL AI MODES ====================

    async def set_channel_ai_mode(self, guild_id: int, channel_id: int, feature: str, config: dict = None):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO channel_ai_modes (guild_id, channel_id, feature, config)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, channel_id) DO UPDATE SET
                    feature = EXCLUDED.feature,
                    config = EXCLUDED.config,
                    enabled = TRUE
            """, guild_id, channel_id, feature, json.dumps(config or {}))

    async def remove_channel_ai_mode(self, guild_id: int, channel_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM channel_ai_modes
                WHERE guild_id = $1 AND channel_id = $2
            """, guild_id, channel_id)

    async def get_channel_ai_mode(self, guild_id: int, channel_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM channel_ai_modes
                WHERE guild_id = $1 AND channel_id = $2 AND enabled = TRUE
            """, guild_id, channel_id)
            return dict(row) if row else None

    async def get_all_channel_ai_modes(self, guild_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM channel_ai_modes
                WHERE guild_id = $1 AND enabled = TRUE
            """, guild_id)
            return [dict(r) for r in rows]

    # ==================== AUTO CLEAN ====================

    async def set_auto_clean(self, guild_id: int, channel_id: int, delay_seconds: int,
                              filter_type: str = "all", whitelist_roles: list = None,
                              whitelist_users: list = None):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO auto_clean (guild_id, channel_id, delay_seconds, filter_type,
                    whitelist_roles, whitelist_users)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (guild_id, channel_id) DO UPDATE SET
                    delay_seconds = EXCLUDED.delay_seconds,
                    filter_type = EXCLUDED.filter_type,
                    whitelist_roles = EXCLUDED.whitelist_roles,
                    whitelist_users = EXCLUDED.whitelist_users,
                    enabled = TRUE
            """, guild_id, channel_id, delay_seconds, filter_type,
                json.dumps(whitelist_roles or []),
                json.dumps(whitelist_users or []))

    async def remove_auto_clean(self, guild_id: int, channel_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM auto_clean
                WHERE guild_id = $1 AND channel_id = $2
            """, guild_id, channel_id)

    async def get_auto_clean(self, guild_id: int, channel_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM auto_clean
                WHERE guild_id = $1 AND channel_id = $2 AND enabled = TRUE
            """, guild_id, channel_id)
            return dict(row) if row else None

    async def get_all_auto_clean(self, guild_id: int = None) -> List[Dict]:
        async with self.pool.acquire() as conn:
            if guild_id:
                rows = await conn.fetch("""
                    SELECT * FROM auto_clean WHERE guild_id = $1 AND enabled = TRUE
                """, guild_id)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM auto_clean WHERE enabled = TRUE
                """)
            return [dict(r) for r in rows]

    async def close(self):
        await self.pool.close()


class SQLiteDatabase:
    """SQLite fallback database (same interface as DatabaseManager)"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "rinox.db"
        )
        self._conn: Optional[aiosqlite.Connection] = None
        self._db_type = "sqlite"

    async def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    async def init_tables(self):
        conn = await self._get_conn()
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                ai_provider TEXT DEFAULT 'openai',
                ai_model TEXT DEFAULT 'gpt-4o',
                ai_api_key TEXT,
                ai_base_url TEXT,
                temperature REAL DEFAULT 0.3,
                max_tokens INTEGER DEFAULT 4096,
                vision_enabled INTEGER DEFAULT 1,
                ocr_enabled INTEGER DEFAULT 1,
                streaming_enabled INTEGER DEFAULT 1,
                security_config TEXT DEFAULT '{}',
                moderation_config TEXT DEFAULT '{}',
                enabled_features TEXT DEFAULT '["image_scan", "message_scan", "attachment_scan", "url_scan"]',
                whitelist TEXT DEFAULT '[]',
                blacklist TEXT DEFAULT '[]',
                custom_prompts TEXT DEFAULT '{}',
                language TEXT DEFAULT 'en',
                premium INTEGER DEFAULT 0,
                log_channel_id INTEGER,
                appeal_channel_id INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER,
                action_type TEXT NOT NULL,
                reason TEXT,
                evidence TEXT DEFAULT '[]',
                duration INTEGER,
                ai_confidence REAL,
                risk_score INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                content TEXT,
                threat_level INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                ai_confidence REAL,
                action_taken TEXT,
                evidence TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER,
                reason TEXT,
                weight INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS ai_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                endpoint TEXT,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                latency_ms INTEGER,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                backup_name TEXT NOT NULL,
                backup_data TEXT NOT NULL,
                size_bytes INTEGER,
                created_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                date TEXT DEFAULT (date('now')),
                messages_scanned INTEGER DEFAULT 0,
                threats_detected INTEGER DEFAULT 0,
                actions_taken INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                ai_calls INTEGER DEFAULT 0,
                avg_risk_score REAL DEFAULT 0,
                UNIQUE(guild_id, date)
            );

            CREATE TABLE IF NOT EXISTS lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                list_type TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER,
                item_value TEXT,
                reason TEXT,
                added_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                task_data TEXT DEFAULT '{}',
                next_run TEXT NOT NULL,
                interval_hours INTEGER DEFAULT 24,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS feature_providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                priority INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                max_daily INTEGER DEFAULT 0,
                daily_used INTEGER DEFAULT 0,
                last_reset TEXT DEFAULT (date('now')),
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(guild_id, feature, provider)
            );

            CREATE TABLE IF NOT EXISTS channel_ai_modes (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                config TEXT DEFAULT '{}',
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (guild_id, channel_id)
            );

            CREATE TABLE IF NOT EXISTS auto_clean (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                delay_seconds INTEGER NOT NULL,
                filter_type TEXT DEFAULT 'all',
                whitelist_roles TEXT DEFAULT '[]',
                whitelist_users TEXT DEFAULT '[]',
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(guild_id, channel_id)
            );
        """)
        await conn.commit()
        logger.info("✅ SQLite tables initialized")

    async def create_guild_settings(self, guild_id: int):
        conn = await self._get_conn()
        await conn.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
            (guild_id,)
        )
        await conn.commit()

    async def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        conn = await self._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    async def update_guild_settings(self, guild_id: int, **kwargs):
        if not kwargs:
            return
        columns = list(kwargs.keys())
        values = list(kwargs.values())
        set_clause = ", ".join([f"{col} = ?" for col in columns])
        conn = await self._get_conn()
        await conn.execute(
            f"UPDATE guild_settings SET {set_clause}, updated_at = datetime('now') WHERE guild_id = ?",
            (*values, guild_id)
        )
        await conn.commit()

    async def log_moderation(self, guild_id: int, user_id: int,
                           action_type: str, **kwargs):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO moderation_logs
            (guild_id, user_id, moderator_id, action_type, reason,
             evidence, duration, ai_confidence, risk_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, user_id, kwargs.get('moderator_id'),
              action_type, kwargs.get('reason'),
              json.dumps(kwargs.get('evidence', [])),
              kwargs.get('duration'), kwargs.get('ai_confidence'),
              kwargs.get('risk_score')))
        await conn.commit()

    async def log_security_event(self, guild_id: int, event_type: str, **kwargs):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO security_events
            (guild_id, event_type, user_id, channel_id, message_id,
             content, threat_level, risk_score, ai_confidence,
             action_taken, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, event_type, kwargs.get('user_id'),
              kwargs.get('channel_id'), kwargs.get('message_id'),
              kwargs.get('content'), kwargs.get('threat_level', 0),
              kwargs.get('risk_score', 0), kwargs.get('ai_confidence'),
              kwargs.get('action_taken'), json.dumps(kwargs.get('evidence', {}))))
        await conn.commit()

    async def add_warning(self, guild_id: int, user_id: int,
                         reason: str, moderator_id: int = None,
                         weight: int = 1, expires_at: datetime = None):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO user_warnings
            (guild_id, user_id, moderator_id, reason, weight, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, user_id, moderator_id, reason, weight,
              expires_at.isoformat() if expires_at else None))
        await conn.commit()

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM user_warnings
            WHERE guild_id = ? AND user_id = ? AND active = 1
            ORDER BY created_at DESC
        """, (guild_id, user_id))
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def get_analytics(self, guild_id: int, days: int = 7) -> List[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM analytics
            WHERE guild_id = ? AND date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        """, (guild_id, days))
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def update_analytics(self, guild_id: int, **kwargs):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO analytics (guild_id, date, messages_scanned,
                threats_detected, actions_taken, false_positives,
                ai_calls, avg_risk_score)
            VALUES (?, date('now'), ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, date) DO UPDATE SET
                messages_scanned = analytics.messages_scanned + excluded.messages_scanned,
                threats_detected = analytics.threats_detected + excluded.threats_detected,
                actions_taken = analytics.actions_taken + excluded.actions_taken,
                false_positives = analytics.false_positives + excluded.false_positives,
                ai_calls = analytics.ai_calls + excluded.ai_calls,
                avg_risk_score = (analytics.avg_risk_score + excluded.avg_risk_score) / 2.0
        """, (guild_id,
              kwargs.get('messages_scanned', 0),
              kwargs.get('threats_detected', 0),
              kwargs.get('actions_taken', 0),
              kwargs.get('false_positives', 0),
              kwargs.get('ai_calls', 0),
              kwargs.get('avg_risk_score', 0)))
        await conn.commit()

    async def create_backup(self, guild_id: int, backup_name: str,
                           backup_data: Dict, size_bytes: int,
                           created_by: int):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO backups (guild_id, backup_name, backup_data, size_bytes, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, backup_name, json.dumps(backup_data), size_bytes, created_by))
        await conn.commit()

    async def get_backups(self, guild_id: int) -> List[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM backups
            WHERE guild_id = ?
            ORDER BY created_at DESC
        """, (guild_id,))
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ==================== FEATURE PROVIDERS ====================

    async def set_feature_provider(self, guild_id: int, feature: str, provider: str,
                                    model: str = None, priority: int = 0, max_daily: int = 0):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO feature_providers (guild_id, feature, provider, model, priority, max_daily)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, feature, provider) DO UPDATE SET
                model = excluded.model,
                priority = excluded.priority,
                max_daily = excluded.max_daily,
                enabled = 1
        """, (guild_id, feature, provider, model, priority, max_daily))
        await conn.commit()

    async def remove_feature_provider(self, guild_id: int, feature: str, provider: str):
        conn = await self._get_conn()
        await conn.execute(
            "DELETE FROM feature_providers WHERE guild_id = ? AND feature = ? AND provider = ?",
            (guild_id, feature, provider)
        )
        await conn.commit()

    async def get_feature_providers(self, guild_id: int, feature: str) -> List[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM feature_providers
            WHERE guild_id = ? AND feature = ? AND enabled = 1
            ORDER BY priority ASC
        """, (guild_id, feature))
        return [self._row_to_dict(r) for r in await cursor.fetchall()]

    async def get_all_feature_configs(self, guild_id: int) -> Dict[str, List[Dict]]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM feature_providers
            WHERE guild_id = ? AND enabled = 1
            ORDER BY feature, priority ASC
        """, (guild_id,))
        configs = {}
        for r in await cursor.fetchall():
            d = self._row_to_dict(r)
            configs.setdefault(d["feature"], []).append(d)
        return configs

    async def increment_daily_usage(self, guild_id: int, feature: str, provider: str):
        conn = await self._get_conn()
        await conn.execute("""
            UPDATE feature_providers SET
                daily_used = daily_used + 1,
                last_reset = date('now')
            WHERE guild_id = ? AND feature = ? AND provider = ?
        """, (guild_id, feature, provider))
        await conn.commit()
        cursor = await conn.execute("""
            SELECT daily_used, max_daily FROM feature_providers
            WHERE guild_id = ? AND feature = ? AND provider = ?
        """, (guild_id, feature, provider))
        row = await cursor.fetchone()
        if row:
            return row[0], row[1]
        return 0, 0

    async def reset_daily_usage(self, guild_id: int, feature: str, provider: str):
        conn = await self._get_conn()
        await conn.execute("""
            UPDATE feature_providers SET daily_used = 0, last_reset = date('now')
            WHERE guild_id = ? AND feature = ? AND provider = ?
        """, (guild_id, feature, provider))
        await conn.commit()

    # ==================== CHANNEL AI MODES ====================

    async def set_channel_ai_mode(self, guild_id: int, channel_id: int, feature: str, config: dict = None):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO channel_ai_modes (guild_id, channel_id, feature, config)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, channel_id) DO UPDATE SET
                feature = excluded.feature,
                config = excluded.config,
                enabled = 1
        """, (guild_id, channel_id, feature, json.dumps(config or {})))
        await conn.commit()

    async def remove_channel_ai_mode(self, guild_id: int, channel_id: int):
        conn = await self._get_conn()
        await conn.execute(
            "DELETE FROM channel_ai_modes WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id)
        )
        await conn.commit()

    async def get_channel_ai_mode(self, guild_id: int, channel_id: int) -> Optional[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM channel_ai_modes
            WHERE guild_id = ? AND channel_id = ? AND enabled = 1
        """, (guild_id, channel_id))
        row = await cursor.fetchone()
        return self._row_to_dict(row) if row else None

    async def get_all_channel_ai_modes(self, guild_id: int) -> List[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM channel_ai_modes
            WHERE guild_id = ? AND enabled = 1
        """, (guild_id,))
        return [self._row_to_dict(r) for r in await cursor.fetchall()]

    # ==================== AUTO CLEAN ====================

    async def set_auto_clean(self, guild_id: int, channel_id: int, delay_seconds: int,
                              filter_type: str = "all", whitelist_roles: list = None,
                              whitelist_users: list = None):
        conn = await self._get_conn()
        await conn.execute("""
            INSERT INTO auto_clean (guild_id, channel_id, delay_seconds, filter_type,
                whitelist_roles, whitelist_users)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, channel_id) DO UPDATE SET
                delay_seconds = excluded.delay_seconds,
                filter_type = excluded.filter_type,
                whitelist_roles = excluded.whitelist_roles,
                whitelist_users = excluded.whitelist_users,
                enabled = 1
        """, (guild_id, channel_id, delay_seconds, filter_type,
              json.dumps(whitelist_roles or []),
              json.dumps(whitelist_users or [])))
        await conn.commit()

    async def remove_auto_clean(self, guild_id: int, channel_id: int):
        conn = await self._get_conn()
        await conn.execute(
            "DELETE FROM auto_clean WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id)
        )
        await conn.commit()

    async def get_auto_clean(self, guild_id: int, channel_id: int) -> Optional[Dict]:
        conn = await self._get_conn()
        cursor = await conn.execute("""
            SELECT * FROM auto_clean
            WHERE guild_id = ? AND channel_id = ? AND enabled = 1
        """, (guild_id, channel_id))
        row = await cursor.fetchone()
        return self._row_to_dict(row) if row else None

    async def get_all_auto_clean(self, guild_id: int = None) -> List[Dict]:
        conn = await self._get_conn()
        if guild_id:
            cursor = await conn.execute(
                "SELECT * FROM auto_clean WHERE guild_id = ? AND enabled = 1", (guild_id,))
        else:
            cursor = await conn.execute("SELECT * FROM auto_clean WHERE enabled = 1")
        return [self._row_to_dict(r) for r in await cursor.fetchall()]

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _row_to_dict(self, row: aiosqlite.Row) -> Dict[str, Any]:
        d = dict(row)
        for key, value in d.items():
            if isinstance(value, str):
                if key in ("security_config", "moderation_config", "enabled_features",
                          "whitelist", "blacklist", "custom_prompts",
                          "evidence", "backup_data", "task_data",
                          "config", "whitelist_roles", "whitelist_users"):
                    try:
                        d[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
        return d