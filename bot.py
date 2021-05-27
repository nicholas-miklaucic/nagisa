#!/usr/bin/env python3

import discord
from discord.ext import commands
from secrets import TOKEN
import logging
import pandas as pd
import typing
import datetime
import spacy

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True

a2a_nlp = spacy.load("textcat_demo/training/model-best")


def user_joined(user):
    """Gets joined_at if it exists, otherwise returning None."""
    if hasattr(user, 'joined_at'):
        return user.joined_at
    else:
        return None


class MessageFilter():
    """Specific way of filtering messages and handling them accordingly."""

    def matches(self, message):
        raise NotImplementedError()

    async def respond(self, message):
        pass


class WatchedChannelFilter(MessageFilter):
    """Filter for general and academic-help channels only."""

    def matches(self, message):
        return any([message.channel.name.startswith(pref) for pref in
                    ['general', 'academic-help', '🤖bot-commands', 'bot-commands']])


class RecentJoinFilter(MessageFilter):
    def matches(self, message):
        joined = user_joined(message.author)
        return joined is not None and (message.created_at - joined) < datetime.timedelta(minutes=5)


class A2AFilter(MessageFilter):
    """Filter for ask-to-ask messages."""

    def matches(self, message):
        cats = a2a_nlp(message.content.lower()).cats
        return cats['BAD'] * 100 > cats['GOOD']

    async def respond(self, message):
        if message.guild.name == "Homework Help Voice":
            await message.add_reaction('<:snoo_disapproval:808077416501215232>')
        else:
            await message.add_reaction("🤨")


class MentionOrReply(MessageFilter):

    def matches(self, message):
        return ((hasattr(message, 'reference') and message.reference is not None and message.reference.author.name == "Nagisa") or
                any(member.name == 'Nagisa' for member in message.mentions))


class IsThankYou(MessageFilter):

    def matches(self, message):
        return any(word in message.content.lower() for word in
                   ("thank", "thanks", "good bot"))

    async def respond(self, message):
        await message.add_reaction("🥰")


class ComboFilter(MessageFilter):

    def __init__(self, filters):
        self.filters = filters

    def matches(self, message):
        return all([f.matches(message) for f in self.filters])

    async def respond(self, message):
        for f in self.filters:
            await f.respond(message)


class OwnerCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.filters = (
            ComboFilter([WatchedChannelFilter(), RecentJoinFilter(), A2AFilter()]),
            ComboFilter([WatchedChannelFilter(), MentionOrReply(), IsThankYou()])
        )

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("OwnerCommands Is Ready")
        game = discord.Game("with spacetime")
        await self.client.change_presence(status=discord.Status.idle, activity=game)

    @commands.Cog.listener()
    async def on_message(self, msg):
        for f in self.filters:
            if f.matches(msg):
                logging.info(f"{msg.content} matched {f}...")
                await f.respond(msg)
            else:
                logging.info(f"{msg.content} did not match {f}...")

    @commands.command()
    @commands.is_owner()
    async def servers(self, ctx):
        activeservers = self.client.guilds
        for guild in activeservers:
            await ctx.send(guild.name)
            logging.info(guild.name)

    @commands.command()
    @commands.is_owner()
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

    @commands.command()
    @commands.is_owner()
    async def write(self, ctx, filename: typing.Optional[str] = "messages"):
        async with ctx.typing():
            msg_df = pd.DataFrame(self.msgs)
            msg_df.to_csv(filename + ".csv", index=False)
            await ctx.send(f"Done! Logged {len(self.msgs)} messages!")


def setup(client):
    client.add_cog(OwnerCommands(client))


bot = commands.Bot('Nagisa, ', intents=intents)
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
