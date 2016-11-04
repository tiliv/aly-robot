bot = None
reloader = None

def register(bot_, reloader_):
    global bot, reloader
    bot = bot_
    reloader = reloader_
