import random
import time
from pprint import pformat
from itertools import chain
from collections import OrderedDict
import http.client
import json
import re
import sys
import io

import discord
from discord.utils import get, find

from .bot_tracker import bot, reloader


ADMINS = {
    'Autumn': 106584132900941824,
}

KNOWN_CHANNELS = {
    '_test': 243230995954925568,
    '#pub': 113883966976688129,
    '#real-thing': 220368686479835136,
    '#after-dark': 241751939874947072,
}
KNOWN_CHANNELS_RE = re.compile(r'^(?P<channel>%s) <(?P<message>.*)$' % '|'.join(KNOWN_CHANNELS))

MAX_DICE = 100
DICEROLL_PATTERN = re.compile(r'(?P<dice>\d+)d(?P<sides>\d+)(?:\s*\+\s*(?P<offset>\d+))?$')

DEFAULT_8BALL_CHOICES = [
    "It is certain",
    "It is decidedly so",
    "Without a doubt",
    "Yes, definitely",
    "You may rely on it",
    "As I see it, yes",
    "Most likely",
    "Outlook good",
    "Yes",
    "Signs point to yes",
    # "Reply hazy try again",
    # "Ask again later",
    "Better not tell you now",
    # "Cannot predict now",
    # "Concentrate and ask again",
    "Don't count on it",
    "My reply is no",
    "My sources say no",
    "Outlook not so good",
    "Very doubtful",
]
GLOBAL_8BALL_CHOICES = DEFAULT_8BALL_CHOICES[:]
MAX_8BALL_CHOICES = 20
FORTUNE_COOKIE_CATEGORIES = [
    'all',
    'computers',
    'cookie',
    'definitions',
    'miscellaneous',
    'people',
    'platitudes',
    'politics',
    'science',
    'wisdom',
]
FORTUNE_COOKIE_ADVERBS = [
    'happily',
    'wonderously',

    'methodically',
    'carefully',
    'subserviantly',

    'stressefully',
    'manically',
]
PLAY_MESSAGES = [
    "For you, {user}, I'd love to play that game.",
    "Anything for you, darling {user}.",
    "I think I have that one, {user}...",
]
STOP_MESSAGES = [
    "Oh... okay.",
    "Let me find a save point, {user}.",
    "Perfect!  I'm at a stopping place.",
]
FRIENDSHIPS = {}  # Active 'friendship' games being played with other users
GENDERS = {
    'autumn': 'f',
    'laelia': 'f',
    'Egeria': 'f',
}
FRIENDSHIP_ICONS = {
    None: "👫",
    'm': "👫",
    'f': "👭",
}
PERSONAL_PRONOUNS = {
    None: 'they',
    'm': 'he',
    'f': 'she',
}
PRONOUNS = {
    None: 'them',
    'm': 'him',
    'f': 'her',
}
REACTION_LETTERS = {
    'a': '🇦',
    'b': '🇧',
    'c': '🇨',
    'd': '🇩',
    'e': '🇪',
    'f': '🇫',
    'g': '🇬',
    'h': '🇭',
    'i': '🇮',
    'j': '🇯',
    'k': '🇰',
    'l': '🇱',
    'm': '🇲',
    'n': '🇳',
    'o': '🇴',
    'p': '🇵',
    'q': '🇶',
    'r': '🇷',
    's': '🇸',
    't': '🇹',
    'u': '🇺',
    'v': '🇻',
    'w': '🇼',
    'x': '🇽',
    'y': '🇾',
    'z': '🇿',
    ',': '☄',
    '.': '🌟',
    '!': '❗',
    '?': '❓',
    ' ': '💘',
    '1': ':one:',
    '2': ':two:',
    '3': ':three:',
    '4': ':four:',
    '5': ':five:',
    '6': ':six:',
    '7': ':seven:',
    '8': ':eight:',
    '9': ':nine:',
    '0': ':zero:',
}


API_LIBRARY = {
    'fortunecookie': {
        'hostname': 'www.yerkee.com',
        # 'headers': {},
        'endpoint': '/api/fortune/{category}',
    },
}



def _request_to_external_api(api_name, endpoint=None, **endpoint_kwargs):
    api_details = API_LIBRARY[api_name]
    connection = http.client.HTTPConnection(api_details['hostname'])

    if endpoint:
        endpoint = api_details['endpoints'][endpoint]
    else:
        endpoint = api_details['endpoint']
    endpoint = endpoint.format(**endpoint_kwargs)
    headers = api_details.get('headers', {})
    connection.request("GET", endpoint, headers=headers)

    response = connection.getresponse()
    data = response.read()
    return data.decode("utf-8")


FRIENDSHIP_GAMES = []
class FriendshipGame:
    name = None
    user = None

class FriendshipShiritori(FriendshipGame):
    command = 'shiritori'
    name = 'Shiritori'
    help_url = 'https://shiritorigame.com/help/'

    def __init__(self, user):
        self.user = user

FRIENDSHIP_GAMES.append(FriendshipShiritori)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}#{bot.user.id}')


@bot.command(pass_context=True)
async def reload(ctx):
    await ctx.send("🕐 Reloading, wait just a few seconds...")
    reloader.should_reload = True

@bot.command(pass_context=True, aliases=['`', '```'])
async def debug(ctx):
    line = ctx.message.content
    line = re.sub(r'^/\S+', '', line).strip(' `')

    try:
        result = eval(line, {'bot': bot, 'say': say}, locals())
    except Exception as e:
        result = e
    await ctx.channel.send(f'```\n{result!r}\n```')


@bot.command(pass_context=True, aliases=['r',  'dice'])
async def roll(ctx, ndn : str):
    """Rolls dice in NdN format, with results sorted from high to low."""
    user = ctx.message.author.mention

    match = DICEROLL_PATTERN.match(ndn)
    if not match:
        await ctx.send("{user} made a bad roll, try ``NdN`` or ``NdN+N``.".format(user=user))
        return

    dice = int(match.group('dice'))
    sides = int(match.group('sides'))
    offset = int(match.group('offset') or 0)

    if dice == 0:
        await ctx.send("🎲 Aayy, check it out, {user} wasting our time by asking me to roll 0 dice.".format(**{
            'user': user,
        }))
        return

    if dice > MAX_DICE:
        await ctx.send("🎲 Attention everybody @here.  We're having an intervension for {user}, who"
                " thinks {personal_pronoun} wants to roll **{dice}** dice. Convince {pronoun} that"
                " {personal_pronoun}'s batshit crazy.  What would you even do with that many dice?"
                "\n\nJust think about the total cubic volume {dice} would take up, even if they"
                " were those silly micro ones. You're lucky I've got the patience to even count"
                " {max_dice} of them for you, but {too_many_dice} is where I draw the line."
                "\n\nTry again.".format(**{
            'user': user,
            'personal_pronoun': PERSONAL_PRONOUNS[GENDERS.get(ctx.message.author.name)],
            'pronoun': PRONOUNS[GENDERS.get(ctx.message.author.name)],
            'dice': dice,
            'max_dice': MAX_DICE,
            'too_many_dice': MAX_DICE + 1,
        }))
        return


    total = 0
    roll_string = io.StringIO()
    first_roll = True

    def get_die_roll():
        if sides == 0:
            return '?'
        return random.randint(1, sides)

    for roll in (get_die_roll() for r in range(dice)):
        if roll != '?':
            total += roll
        if roll == sides:
            roll = '__**{}**__'.format(roll)
        if not first_roll:
            roll = ', {}'.format(roll)
        else:
            roll = str(roll)

        roll_string.write(roll)
        first_roll = False

    if sides:
        full_total = total + offset
    else:
        full_total = '?'

    total_string = '' if dice == 1 else '{}{} = '.format(
        full_total,
        '' if not offset else ' ({}+{})'.format(total, offset),
    )

    message = "🎲 {user} rolled {total}{rolls}".format(**{
        'user': user,
        'rolls': roll_string.getvalue(),
        'total': total_string,
    })
    await ctx.send(message)

@bot.group(pass_context=True, aliases=['8', '8ball'])
async def eightball(ctx):
    """Divines a message from the holy 8ball.  (/8ball, /8)"""
    if ctx.invoked_subcommand is None:
        if len(GLOBAL_8BALL_CHOICES):
            await ctx.send("🎱 {user}: {result}".format(**{
                'user': ctx.message.author.mention,
                'result': random.choice(GLOBAL_8BALL_CHOICES)
            }))
        else:
            await ctx.send('🎱 Sorry {user}, but no choices are loaded.  Add one via ``/8ball add '
                          '"Custom choice."``  Or you can ``/8ball reset`` to the default list.'.format(**{
                'user': ctx.message.author.mention,
            }))

@eightball.command(name='add', pass_context=True)
async def eightball_add(ctx, *, choice : str):
    await ctx.send("🎱 {user} added magic 8 ball choice: ``{choice}``".format(**{
        'user': ctx.message.author.mention,
        'choice': choice,
    }))

    if len(GLOBAL_8BALL_CHOICES) >= MAX_8BALL_CHOICES:
        await ctx.send("The list is getting kind of full, so the choice ``{choice}`` got removed.  Sorry.".format(**{
            'choice': GLOBAL_8BALL_CHOICES.pop(0),
        }))
    GLOBAL_8BALL_CHOICES.append(choice)

@eightball.command(name='remove', pass_context=True)
async def eightball_remove(ctx, *, choice : str):
    if choice in GLOBAL_8BALL_CHOICES:
        i = GLOBAL_8BALL_CHOICES.index(choice)
        await ctx.send("🎱 {user} removed magic 8 ball choice: ``{choice}``".format(**{
            'user': ctx.message.author.mention,
            'choice': GLOBAL_8BALL_CHOICES.pop(i),
        }))
    else:
        await ctx.send("🎱 {user}, that's not a current choice!".format(**{
            'user': ctx.message.author.mention,
        }))

@eightball.command(name='clear', pass_context=True)
async def eightball_clear(ctx):
    GLOBAL_8BALL_CHOICES[:] = []
    await ctx.send("🎱 {user} cleared all magic 8 ball choices!".format(**{
        'user': ctx.message.author.mention,
    }))

@eightball.command(name='reset', pass_context=True)
async def eightball_reset(ctx):
    GLOBAL_8BALL_CHOICES[:] = DEFAULT_8BALL_CHOICES[:]
    await ctx.send("🎱 {user} reset all magic 8 ball choices to the default {n_choices}.".format(**{
        'user': ctx.message.author.mention,
        'n_choices': len(DEFAULT_8BALL_CHOICES),
    }))

@eightball.command(name='list', pass_context=True)
async def eightball_list(ctx, *choices : str):
    if len(GLOBAL_8BALL_CHOICES):
        await ctx.send("🎱 {user}: Here's the current list of choices:".format(**{
            'user': ctx.message.author.mention,
        }))
        await ctx.send("```{}```".format("\n".join(GLOBAL_8BALL_CHOICES)))
    else:
        await ctx.send("🎱 {user}: There are no choices currently loaded.".format(**{
            'user': ctx.message.author.mention,
        }))

def can_decorate(s):
    chars = set(s.lower())
    return all([
        len(chars) == len(s),
        chars.issubset(set('abcdefghijklmnopqrstuvwxyz1234567890,.!? ')),
    ])


@eightball.command(name='pick', pass_context=True)
async def eightball_pick(ctx, *choices : str):
    random_scale = random.choice(range(10)) / 10
    choice = random.choice(choices)
    if can_decorate(choice):
        await bot.get_command('decorate').callback(ctx, ctx.message.author, choice)
    else:
        await ctx.send("🎱 {user}: ``{choice}``".format(**{
            'user': ctx.message.author.mention,
            'choice': choice,
        }))


@bot.command(pass_context=True, aliases=['*'])
async def decorate(ctx, mention, *emojis):
    s = ' '.join(emojis).lower()
    letters = set(s)

    target = mention
    if mention == 'me':
        target = ctx.message.author
    elif mention == 'aly':
        target = bot.user
    elif isinstance(mention, str):
        mention = mention.lower()
        target = find(lambda u: mention in u.name.lower(), bot.users)

    if not target and len(mention) >= 4:
        mention = mention[2:-1]  # <@ ... >
        if mention[0] == '!':
            mention = mention[1:]  # <@! ... >
        try:
            mention = int(mention)
        except:
            mention = 0
        target = get(bot.users, id=int(mention))

    if not target:
        target = ctx.message.author
        s = 'um, who?'

    message = await ctx.message.channel.history().get(author=target)
    if not message:
        await ctx.send("`Uumm, for what?`")
        return
    if not can_decorate(s):
        print(f'{s!r}')
        await ctx.send('`UM.  No repeat characters, please.  Come on, keep up 👏👏`')
        return

    await message.add_reaction('🎖')
    for letter in s:
        await message.add_reaction(REACTION_LETTERS.get(letter))


def _get_fortune(category='all'):
    error = None
    try:
        payload = _request_to_external_api('fortunecookie', category=category)
        fortune = json.loads(payload)['fortune']
    except Exception as e:
        fortune = None
        error = str(e)
        print(type(e), str(e))
    return fortune, error


@bot.command(pass_context=True, aliases=['cookie'])
async def fortune(ctx, category='all'):
    """Requests a fortune cookie."""
    if category not in FORTUNE_COOKIE_CATEGORIES:
        await ctx.send("🔮 {user}: Sorry, bad cookie category, pal.  Try nothing at all, or one of"
                      " these:\n{category_list}".format(**{
            'user': ctx.message.author.mention,
            'category_list': '\n'.join(FORTUNE_COOKIE_CATEGORIES),
        }))
        return

    await ctx.send("🔮 {user}: {adverb} baking your cookie...".format(**{
        'user': ctx.message.author.mention,
        'adverb': random.choice(FORTUNE_COOKIE_ADVERBS).capitalize(),
    }))
    fortune, error = _get_fortune(category)
    if not error:
        await ctx.send("🔮 {user}: ``{fortune}``".format(**{
            'user': ctx.message.author.mention,
            'fortune': fortune,
        }))
    else:
        await ctx.send("🔮 {user}: Uh oh, cookie burned: ``{error}``".format(**{
            'user': ctx.message.author.mention,
            'error': error,
        }))

@bot.command(name='ha', pass_context=True, aliases=['HA', 'hA', 'Ha', 'lulu'])
async def lulu_laugh(ctx):
    laugh = ''
    for i in range(0, 25):
        laugh += random.choice('Hh')
        laugh += random.choice('Aa')
    await ctx.send(laugh)

@bot.command(pass_context=True)
async def play(ctx, *, game : str):
    """Set the 'Playing' status to the provided game name (in quotations)."""
    await ctx.send("🎮 {message}".format(**{
        'message': random.choice(PLAY_MESSAGES).format(user=ctx.message.author.mention),
    }))
    await bot.change_presence(game=discord.Game(name=game))

@bot.command(pass_context=True)
async def stop(ctx):
    """Clears the 'Playing' status."""
    await ctx.send("🎮 {message}".format(**{
        'message': random.choice(STOP_MESSAGES).format(user=ctx.message.author.mention),
    }))
    await bot.change_presence(game=None)

def get_friendship_icon(user):
    return FRIENDSHIP_ICONS[GENDERS.get(user.name)]

@bot.group(pass_context=True, aliases=['ship'])
async def friendship(ctx):
    if ctx.invoked_subcommand is None:
        if ctx.message.author in FRIENDSHIPS:
            await ctx.send("{icon} {user}, we're still playing these games:\n\n{games_list}".format(**{
                'icon': get_friendship_icon(ctx.message.author),
                'user': ctx.message.author.mention,
                'games_list': '\n'.join(FRIENDSHIPS[ctx.message.author].keys())
            }))
        else:
            await ctx.send("{icon} {user}, I can play these games:\n\n{games_list}".format(**{
                'icon': get_friendship_icon(ctx.message.author),
                'user': ctx.message.author.mention,
                'games_list': '\n'.join([
                    '{game.command} ({game.help_url})'.format(game=GameClass) \
                        for GameClass in FRIENDSHIP_GAMES
                ]),
            }))

@friendship.group(name='stopall', pass_context=True)
async def friendship_stopall(ctx):
    del FRIENDSHIPS[ctx.message.author]
    await ctx.send("{icon} {user}, friendship over, no more games.".format(**{
        'icon': get_friendship_icon(ctx.message.author),
        'user': ctx.message.author.mention,
    }))

async def _friendship_check_already_playing(GameClass, user):
    if user in FRIENDSHIPS:
        game = FRIENDSHIPS[user].get(GameClass.command)
        if game:
            await ctx.send("{icon} {user}, we're already playing {game}!  Pay attention~!".format(**{
                'icon': get_friendship_icon(user),
                'user': user.mention,
                'game': game.name,
            }))
            return game
    return None

async def _friendship_game_starter(GameClass, ctx):
    if not await _friendship_check_already_playing(GameClass, ctx.message.author):
        game = GameClass(ctx.message.author)
        FRIENDSHIPS.setdefault(game.user, {})
        FRIENDSHIPS[game.user][GameClass.command] = game
        await ctx.send("{icon} {user} {name}?  Let's do it!".format(**{
            'icon': get_friendship_icon(game.user),
            'user': ctx.message.author.mention,
            'name': game.name,
        }))

async def _friendship_game_stopper(GameClass, ctx):
    del FRIENDSHIPS[ctx.message.author][GameClass.command]
    await ctx.send("{icon} {user}, ending {game}.".format(**{
        'icon': get_friendship_icon(ctx.message.author),
        'user': ctx.message.author.mention,
        'game': GameClass.name,
    }))

@friendship.group(name=FriendshipShiritori.command, pass_context=True)
async def friendship_shiritori(ctx):
    if ctx.invoked_subcommand == friendship_shiritori:
        await _friendship_game_starter(FriendshipShiritori, ctx)

@friendship_shiritori.command(name='stop', pass_context=True)
async def friendship_shiritori_stop(ctx):
    await _friendship_game_stopper(FriendshipShiritori, ctx)

@bot.event
async def on_message(message):
    puppet_mode = KNOWN_CHANNELS_RE.match(message.content)
    if message.author.id in ADMINS.values() and puppet_mode:
        await bot.get_channel(KNOWN_CHANNELS[puppet_mode.group('channel')]).send(
            puppet_mode.group('message').strip())
    else:
        await bot.process_commands(message)

#     intercept = True
#     if message.author == bot.user:
#         intercept = False
#     elif message.author not in FRIENDSHIPS:
#         intercept = False
#     else:
#         games = FRIENDSHIPS[message.author]
#         if not games:
#             intercept = False
#
#     if not intercept:
#         await bot.process_commands(message)
#     else:
#         ctx.send("Game interaction expected")
