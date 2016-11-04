#!/usr/bin/env python3

import os
import asyncio
from imp import reload

from discord.ext import commands

description = """The ultimate friendship bot, ALY."""
bot = commands.Bot(command_prefix='/', description=description)

class Reloader:
    should_reload = False
reloader = Reloader()

async def reload_checker():
    global bot_commands

    await bot.wait_until_ready()
    while not bot.is_closed:
        if reloader.should_reload:
            bot.recursively_remove_all_commands()
            bot_commands = reload(bot_commands)
            reloader.should_reload = False
        await asyncio.sleep(2)

from alyr.bot_tracker import register
register(bot, reloader)

from alyr import bot_commands

bot.loop.create_task(reload_checker())
bot.run(os.environ['ALY_TOKEN'])
