#!/usr/bin/env python3

import discord
from discord.ext import commands
from secrets import TOKEN, MW_DICT_KEY
import logging
import pandas as pd
import typing
import datetime
import spacy
import wikipedia
import requests
import random
import asyncio
import html
from urllib.parse import quote
from langdetect import detect_langs, LangDetectException
from googletrans import Translator
from iso639 import to_name

from mw import mw_to_markdown

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True

nlp = spacy.load('en_core_web_sm')
a2a_nlp = spacy.load("textcat_demo/training/model-best")

NAME = "Nano"


BASEURL = "https://dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}"


def define(word):
    j = requests.get(BASEURL.format(quote(word), MW_DICT_KEY)).json()
    if j and isinstance(j[0], str):
        # gave us a list of suggestions back, try first one
        return define(j[0])
    elif not j:
        return []
    else:
        defs = []
        for definition in j:
            if definition['meta']['id'].split(':')[0] == word:
                defs.append(definition)
        return defs


def get_all_senses(tree):
    """Given a JSON definition tree, recurse, returning an ordered list of all of the senses."""
    senses = []
    if isinstance(tree, list):
        # check for single sense
        if len(tree) == 2 and tree[0] == 'sense':
            senses.append(tree)
        elif len(tree) == 2 and tree[0] == 'bs':
            # these are weird idk why
            _, sense_dict = tree
            if 'sense' in sense_dict:
                senses.append(['sense', sense_dict['sense']])
        else:
            # otherwise, check sublists
            for el in tree:
                senses += get_all_senses(el)
    elif isinstance(tree, dict):
        # map type like sseq, recurse on values
        for value in tree.values():
            senses += get_all_senses(value)
    return senses


def def_to_embed(dfn):
    """Given a definition as a dictionary in JSON, outputs a Discord embed."""
    logging.info(repr(dfn) + '\n\n\n')
    embed = discord.Embed(
        title=dfn['meta']['id'].split(':')[0],
        description=dfn['hwi'].get('prs', ({},))[0].get('mw', ''),
        type='rich'
    )

    text = []
    for d in dfn['def']:
        senses = get_all_senses(d)
        for _, sense in senses:
            dt = sense['dt']
            dt_text = [txt for (kw, txt) in dt if kw == 'text'][0]
            if 'sn' in sense and sense['sn'][0].isdigit() and text:  # starts new definition
                embed.add_field(name='Definition', value='\n'.join(text), inline=False)
                text = []
            text.append('**' + sense.get('sn', '1') + '** ' + mw_to_markdown(dt_text))

    if text:
        embed.add_field(name='Definition', value='\n'.join(text), inline=False)
    return embed


def user_joined(user):
    """Gets joined_at if it exists, otherwise returning None."""
    if hasattr(user, 'joined_at'):
        return user.joined_at
    else:
        return None


class MessageFilter():
    """Specific way of filtering messages and handling them accordingly."""

    async def matches(self, message):
        raise NotImplementedError()

    async def respond(self, message):
        pass


class WatchedChannelFilter(MessageFilter):
    """Filter for general and academic-help channels only."""

    def __init__(self, channel_prefs):
        self.channel_prefs = channel_prefs

    async def matches(self, message):
        return (type(message.channel) == discord.DMChannel or
                any([message.channel.name.startswith(pref) for pref in self.channel_prefs]))


class RecentJoinFilter(MessageFilter):
    async def matches(self, message):
        joined = user_joined(message.author)
        return joined is not None and (message.created_at - joined) < datetime.timedelta(minutes=5)


class A2AFilter(MessageFilter):
    """Filter for ask-to-ask messages."""

    async def matches(self, message):
        cats = a2a_nlp(message.content.lower()).cats
        return cats['BAD'] * 100 > cats['GOOD']

    async def respond(self, message):
        if message.guild.name == "Homework Help Voice":
            await message.add_reaction('<:snoo_disapproval:808077416501215232>')
        else:
            await message.add_reaction("🤨")


class MentionOrReply(MessageFilter):

    async def matches(self, message):
        if message.author.name == NAME:
            return False
        elif hasattr(message, 'reference') and message.reference is not None:
            ref = message.reference.message_id
            ref_msg = await message.channel.fetch_message(ref)
            if ref_msg.author.name == NAME:
                logging.info(ref_msg)
                logging.info(ref_msg, ref_msg.author)
                logging.info(message)
                logging.info(message.channel)
                logging.info(message.reference)
                return True
        else:
            return any(member.name == 'Nano' for member in message.mentions)


class IsThankYou(MessageFilter):

    async def matches(self, message):
        return any(word in message.content.lower() for word in
                   ("thank", "thanks", "good bot"))

    async def respond(self, message):
        await message.add_reaction("🥰")


class IsScold(MessageFilter):

    async def matches(self, message):
        return any(word in message.content.lower() for word in
                   ("bad bot",))

    async def respond(self, message):
        await message.reply("https://tenor.com/view/nichijou-nano-silly-stupid-gif-20046613")


class AnyoneAgree(MessageFilter):

    def __init__(self, names, check_names=True):
        self.names = names
        self.check_names = check_names

    async def matches(self, message):
        return (message.author is not None and
                (not self.check_names or message.author.name in self.names) and
                "back me up" in message.content.lower())

    async def respond(self, message):
        await message.reply(f"I completely agree with {message.author.display_name} on this one")


class ForeignLangFilter(MessageFilter):
    translator = Translator()

    async def matches(self, message):
        if len(message.content) <= 30:
            return False
        else:
            langs = detect_langs(message.content)
            if langs and langs[0].lang == 'en':
                # most likely match, continue
                return False
            else:
                return any([lang.lang != 'en' and lang.prob > 0.99 for lang in langs])

    async def respond(self, message):
        translated = self.translator.translate(message.content)
        await message.reply(f"Translated from {to_name(translated.src)}: {translated.text}")


class ComboFilter(MessageFilter):

    def __init__(self, filters):
        self.filters = filters

    async def matches(self, message):
        matches = []
        for f in self.filters:
            does_match = await f.matches(message)
            matches.append(does_match)
        return all(matches)

    async def respond(self, message):
        for f in self.filters:
            await f.respond(message)


class OwnerCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        # back-me-up list
        self.bmu_list = ('PollardsRho', 'xoxo', 'Neyo708', 'Button{R}',
                         '49PES', 'DanTheCurrencyExchangeMan')
        self.standard_channels = ('general', 'academic-help', '🤖bot-commands', 'bot-commands')
        self.filters = (
            ComboFilter((WatchedChannelFilter(self.standard_channels),
                         RecentJoinFilter(), A2AFilter())),
            ComboFilter((WatchedChannelFilter(self.standard_channels),
                         MentionOrReply(), IsThankYou())),
            ComboFilter((WatchedChannelFilter(self.standard_channels),
                         MentionOrReply(), IsScold())),
            ComboFilter((WatchedChannelFilter(self.standard_channels),
                         AnyoneAgree(self.bmu_list))),
            ComboFilter((WatchedChannelFilter(self.standard_channels),
                         ForeignLangFilter()))
        )
        self.token = ""
        self.qs_with_answers = {}
        self.answer_choices = "🇦🇧🇨🇩"
        self.definitions = {}

    @ commands.Cog.listener()
    async def on_ready(self):
        logging.info("OwnerCommands Is Ready")
        game = discord.Game("with Sakamoto")
        r = requests.get("https://opentdb.com/api_token.php?command=request")
        r.raise_for_status()
        self.token = r.json()['token']
        await self.client.change_presence(status=discord.Status.idle, activity=game)

    @ commands.Cog.listener()
    async def on_message(self, msg):
        if hasattr(msg, 'author') and hasattr(msg.author, 'name') and msg.author.name == 'Nano':
            logging.info("not replying to self message")
            return

        for f in self.filters:
            if (await f.matches(msg)):
                logging.debug(f"{msg.content} matched {f}...")
                await f.respond(msg)
            else:
                logging.debug(f"{msg.content} did not match {f}...")

    @ commands.Cog.listener()
    async def on_reaction_add(self, rxn, user):
        msg = rxn.message
        if user.name == NAME:
            return
        elif msg.id in self.qs_with_answers:
            correct_char = self.answer_choices[self.qs_with_answers[msg.id]]
            if str(rxn) == correct_char:
                del self.qs_with_answers[msg.id]
                await msg.channel.send("Correct, good job {}!".format(user.mention))
        elif msg.id in self.definitions:
            i, defs = self.definitions[msg.id]
            if str(rxn) == '⬅':
                new_i = (i - 1) % len(defs)
            elif str(rxn) == '\u27a1':
                new_i = (i + 1) % len(defs)
            else:
                new_i = i

            if new_i != i:
                self.definitions[msg.id] = (new_i, defs)
                await msg.edit(embed=defs[new_i].set_footer(text=f'{new_i+1}/{len(defs)}'))

    @ commands.command()
    @ commands.is_owner()
    async def servers(self, ctx):
        activeservers = self.client.guilds
        for guild in activeservers:
            await ctx.send(guild.name)
            logging.info(guild.name)

    @ commands.command()
    @ commands.is_owner()
    async def scrape(self, ctx, limit: typing.Optional[int] = 200):
        self.msgs = []
        async with ctx.typing():
            num_msgs = 0
            guild = ctx.guild
            logging.info(f"Scraping {guild.name}...")
            for channel in guild.text_channels:
                logging.info(f"Channel {channel.name}")
                if self.is_watched_channel(channel):
                    logging.info("Matched, scraping messages...")
                    async for msg in channel.history(limit=limit):
                        if not msg.is_system():
                            author = msg.author
                            joined = user_joined(guild.get_member(author.id))
                            if joined is None or (msg.created_at - joined) <= datetime.timedelta(hours=1):
                                row = {
                                    'id': msg.id,
                                    'content': msg.clean_content,
                                    'server': msg.guild.name,
                                    'channel': msg.channel.name,
                                    'created': msg.created_at,
                                    'author': author.name,
                                    'author_created': author.created_at,
                                    'author_joined': joined
                                }
                                if row['id'] not in self.msg_ids:
                                    self.msg_ids.append(row['id'])
                                    self.msgs.append(row)
                                    num_msgs += 1
                    else:
                        logging.info("Not a match, moving on")
            logging.info("Done!")
        await ctx.send(f"Done! Scraped {num_msgs} messages")

    @ commands.command()
    @ commands.is_owner()
    async def write(self, ctx, filename: typing.Optional[str] = "messages"):
        async with ctx.typing():
            msg_df = pd.DataFrame(self.msgs)
            msg_df.to_csv(filename + ".csv", index=False)
        await ctx.send(f"Done! Logged {len(self.msgs)} messages!")

    @ commands.command()
    async def wiki(self, ctx, sentences: typing.Optional[int] = 2, *args):
        async with ctx.typing():
            if not args:
                search_term = str(sentences)
                sentences = 2
            else:
                search_term = ' '.join(args)
            logging.info(search_term)
            searched = wikipedia.search(f'{search_term}')
            if searched:
                suggested = searched[0]
            else:
                suggested = wikipedia.suggest(search_term)

            logging.info(suggested)
            try:
                text = wikipedia.summary(suggested, sentences=sentences,
                                         auto_suggest=False).replace('\n', '\n\n')
            except wikipedia.exceptions.DisambiguationError:
                text = "Your query wasn't specific enough."
            except wikipedia.exceptions.PageError:
                text = "Page not found, try again."
        await ctx.send(text)

    @ commands.command("activate!")
    async def get_em(self, ctx):
        await ctx.send("https://tenor.com/view/nano-nichijou-gif-21640782")

    @ commands.command()
    async def trivia(self, ctx):
        r = requests.get(f"https://opentdb.com/api.php?amount=1&type=multiple&token={self.token}")
        json = r.json()
        logging.info(json)
        if json['response_code'] != 0:
            await ctx.send("There was an error!")
        else:
            q = json['results'][0]
            logging.info(q)
            cor_answer = q['correct_answer']
            inc_answers = q['incorrect_answers']
            num_ans = len(inc_answers) + 1
            answers = inc_answers
            correct_answer_num = random.randrange(num_ans)
            answers.insert(correct_answer_num, cor_answer)
            text = f"""{html.unescape(q['question'])}
🇦 → {html.unescape(answers[0])}
🇧 → {html.unescape(answers[1])}
🇨 → {html.unescape(answers[2])}
🇩 → {html.unescape(answers[3])}"""
            msg = await ctx.send(text)
            self.qs_with_answers[msg.id] = correct_answer_num
            await asyncio.gather(*[msg.add_reaction(c) for c in self.answer_choices])

    @ commands.command()
    async def define(self, ctx, *args):
        async with ctx.typing():
            word = ' '.join(args)
            text = [def_to_embed(d) for d in define(word)]
            text = [emb for emb in text if emb.fields]
        if text:
            msg = await ctx.send(embed=text[0].set_footer(text=f'1/{len(text)}'))
            self.definitions[msg.id] = (0, text)
            await msg.add_reaction("⬅")
            await msg.add_reaction("\u27a1")
        else:
            await ctx.send("Couldn't find definition. Sorry! >_<")

    @ commands.command("back")
    async def back_me_up(self, ctx, *args):
        if len(args) >= 2 and args[0] == "me" and args[1] == "up":
            # don't double-trigger
            # TODO maybe refactor the filters list to be a named tuple so you can just reference
            # that filter instead of remaking it here
            if not await AnyoneAgree(self.bmu_list).matches(ctx.message):
                await AnyoneAgree([], check_names=False).respond(ctx.message)

    @commands.command()
    async def translate(self, ctx, *args):
        try:
            await ForeignLangFilter().respond(ctx.message)
        except LangDetectException:
            await ctx.send("Could not infer source language. Darn! >_<")


def setup(client):
    client.add_cog(OwnerCommands(client))


bot = commands.Bot(f'{NAME}, ', intents=intents)
setup(bot)
bot.run(TOKEN)


# @client.event
# async def on_ready():
#     print('We have logged in as {0.user}'.format(client))


# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     if message.content.startswith('$hello'):
#         await message.channel.send('Hello!')

# await client.start(TOKEN)
# sleep(3)
# await client.close()
