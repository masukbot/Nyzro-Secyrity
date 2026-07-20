"""
Rinox Sentinel - Entry Point
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.bot import RinoxBot

def main():
    """Run the bot"""
    load_dotenv()
    
    bot = RinoxBot()
    
    try:
        bot.run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
