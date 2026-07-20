"""
Rinox Sentinel - AI-Powered Discord Security Bot
Main Bot Entry Point
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncpg
import redis.asyncio as redis
from aiohttp import web

from .config import BotConfig
from .database import DatabaseManager, SQLiteDatabase
from .cache import CacheManager
from .ai_manager import AIManager
from .security_engine import SecurityEngine
from ..utils.rate_limiter import RateLimiter
from ..automation.autoclean import AutoCleanTask

# Configure logging
if sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("rinox.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("Rinox")

class RinoxBot(commands.Bot):
    """Main bot class for Rinox Sentinel"""
    
    def __init__(self):
        # Intents
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        
        super().__init__(
            command_prefix="!",  # Fallback prefix
            intents=intents,
            help_command=None,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                users=True
            )
        )
        
        # Core components
        self.config = BotConfig()
        self.db: Optional[DatabaseManager] = None
        self.cache: Optional[CacheManager] = None
        self.ai: Optional[AIManager] = None
        self.security: Optional[SecurityEngine] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.auto_clean: Optional[AutoCleanTask] = None
        
        self.logger = logger

        # Status tracking
        self.start_time = datetime.utcnow()
        self.guild_settings: Dict[int, Dict[str, Any]] = {}
        
    async def setup_hook(self):
        """Initialize all components"""
        logger.info("🚀 Rinox Sentinel initializing...")
        
        # Initialize database
        await self._init_database()
        
        # Initialize cache
        await self._init_cache()
        
        # Initialize AI manager
        await self._init_ai()
        if self.ai:
            self.ai.set_router_db(self.db)
        
        # Initialize security engine
        await self._init_security()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(self.cache)
        
        # Initialize auto-clean
        self.auto_clean = AutoCleanTask(self)
        
        # Load cogs
        await self._load_cogs()
        
        # Sync commands
        await self.tree.sync()
        logger.info("✅ Slash commands synced globally")
        
        # Start background tasks
        try:
            self.status_update.start()
        except Exception as e:
            logger.warning(f"Could not start status_update task: {e}")
        try:
            self.cache_cleanup.start()
        except Exception as e:
            logger.warning(f"Could not start cache_cleanup task: {e}")
        try:
            self.auto_clean_loop.start()
        except Exception as e:
            logger.warning(f"Could not start auto_clean_loop task: {e}")
        # Start healthcheck HTTP server for Railway
        asyncio.create_task(self._start_healthcheck())
        
        logger.info("🛡️ Rinox Sentinel is ready!")
        
    async def _init_database(self):
        """Initialize database with PostgreSQL or SQLite fallback"""
        try:
            pool = await asyncpg.create_pool(
                dsn=os.getenv("DATABASE_URL", "postgresql://localhost/rinox"),
                min_size=2,
                max_size=10
            )
            self.db = DatabaseManager(pool)
            await self.db.init_tables()
            self.db._db_type = "postgres"
            logger.info("✅ PostgreSQL connected")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL failed: {e}")
            logger.info("🔄 Falling back to SQLite...")
            self.db = SQLiteDatabase()
            await self.db.init_tables()
            self.db._db_type = "sqlite"
            logger.info("✅ SQLite connected (fallback mode)")
            
    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True
            )
            self.cache = CacheManager(redis_client)
            logger.info("✅ Cache connected")
        except Exception as e:
            logger.warning(f"⚠️ Cache connection failed: {e}")
            self.cache = None
            
    async def _init_ai(self):
        """Initialize AI manager"""
        self.ai = AIManager(self.cache)
        await self.ai.load_providers()
        logger.info("✅ AI Manager initialized")
        
    async def _init_security(self):
        """Initialize security engine"""
        self.security = SecurityEngine(self.ai, self.cache)
        logger.info("✅ Security Engine initialized")
        
    async def _load_cogs(self):
        """Load all cogs"""
        cogs = [
            "src.cogs.ai_commands",
            "src.cogs.security_commands", 
            "src.cogs.moderation_commands",
            "src.cogs.logging_commands",
            "src.cogs.automation_commands",
            "src.cogs.utility_commands",
            "src.cogs.setup_commands",
            "src.cogs.analytics_commands",
            "src.cogs.backup_commands",
            "src.cogs.events",
            "src.cogs.ai_route_commands",
            "src.cogs.autoclean_commands",
            "src.cogs.ai_features_commands",
            "src.cogs.management_commands",
            "src.cogs.announcement_commands"
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load {cog}: {e}")
                
    @tasks.loop(minutes=5)
    async def status_update(self):
        """Update bot status"""
        if not self.ws:
            return
        guild_count = len(self.guilds)
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{guild_count} servers | /setup"
        )
        await self.change_presence(activity=activity)
        
    @tasks.loop(seconds=60)
    async def auto_clean_loop(self):
        """Run auto-clean every 60 seconds"""
        if self.auto_clean:
            await self.auto_clean.run()

    @tasks.loop(hours=1)
    async def cache_cleanup(self):
        """Clean up expired cache entries"""
        if self.cache:
            await self.cache.cleanup()

    async def _start_healthcheck(self):
        """Lightweight HTTP server for Railway healthcheck"""
        async def health(request):
            return web.Response(text="ok", status=200)

        app = web.Application()
        app.router.add_get("/", health)
        app.router.add_get("/health", health)

        port = int(os.getenv("PORT", 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"✅ Healthcheck server started on port {port}")
            
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🤖 Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        
    async def on_guild_join(self, guild: discord.Guild):
        """Handle guild join"""
        logger.info(f"➕ Joined guild: {guild.name} (ID: {guild.id})")
        # Create default settings
        if self.db:
            await self.db.create_guild_settings(guild.id)
            
    async def on_guild_remove(self, guild: discord.Guild):
        """Handle guild leave"""
        logger.info(f"➖ Left guild: {guild.name} (ID: {guild.id})")
        
    async def close(self):
        """Clean shutdown"""
        logger.info("🛑 Shutting down Rinox Sentinel...")
        if self.db:
            await self.db.close()
        if self.cache:
            await self.cache.close()
        await super().close()
        
    def run_bot(self):
        """Run the bot"""
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.error("❌ DISCORD_TOKEN not found in environment!")
            sys.exit(1)
        super().run(token, reconnect=True)


if __name__ == "__main__":
    bot = RinoxBot()
    bot.run_bot()
