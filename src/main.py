"""
Main entry point for the refactored Discord bot.
Uses the new feature-based architecture with OOP patterns.
"""

import asyncio
import os
from dotenv import load_dotenv

from .core.bot import run_bot

async def main():
    """Main function to run the bot"""
    # Load environment variables
    load_dotenv()

    print("🤖 Starting Discord Bot with new architecture...")
    print("📦 Features: Calendar, Polls, Reminders, Users")
    print("🔧 OOP Patterns: Command Hierarchy, Service Layer, Dependency Injection")
    print("=" * 60)

    # Run the bot
    await run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()