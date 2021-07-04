#!/usr/bin/env python3

import discord
from discord.ext import commands
import os
import logging
import pandas as pd
import typing
import datetime
import requests
import random
import asyncio
import html
import sys
import configparser
from constants import NAME
from filters import *
from cogs.trivia import TriviaCommands
from cogs.mw_cog import MWCommands
from cogs.wiki import WikiCommands
from cogs.weather import WeatherCommands
from cogs.resources import ResourcesCommands
from cogs.unicode import UnicodeCommands
from cogs.images import ImageCommands


logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True


class OwnerCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        # back-me-up list
        self.bmu_list = (
            "PollardsRho",
            "xoxo",
            "Neyo708",
            "Button{R}",
            "49PES",
            "DanTheCurrencyExchangeMan",
        )
        self.standard_channels = (
            "general",
            "academic-help",
            "🤖bot-commands",
            "bot-commands",
        )
        self.filters = (
            ComboFilter(
                (
                    WatchedChannelFilter(self.standard_channels),
                    RecentJoinFilter(),
                    A2AFilter(),
                )
            ),
            ComboFilter(
                (
                    WatchedChannelFilter(self.standard_channels),
                    MentionOrReply(),
                    IsThankYou(),
                )
            ),
            ComboFilter(
                (
                    WatchedChannelFilter(self.standard_channels),
                    MentionOrReply(),
                    IsScold(),
                )
            ),
            ComboFilter(
                (
                    WatchedChannelFilter(self.standard_channels),
                    AnyoneAgree(self.bmu_list),
                )
            ),
            ComboFilter(
                (WatchedChannelFilter(self.standard_channels), ForeignLangFilter())
            ),
        )

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("Nano Is Ready!")
        game = discord.Game("with Sakamoto")
        await self.client.change_presence(status=discord.Status.idle, activity=game)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if (
            hasattr(msg, "author")
            and hasattr(msg.author, "name")
            and msg.author.name == "Nano"
        ):
            return

        for f in self.filters:
            if await f.matches(msg):
                logging.debug(f"{msg.content} matched {f}...")
                await f.respond(msg)
            else:
                logging.debug(f"{msg.content} did not match {f}...")

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
                            if joined is None or (
                                msg.created_at - joined
                            ) <= datetime.timedelta(hours=1):
                                row = {
                                    "id": msg.id,
                                    "content": msg.clean_content,
                                    "server": msg.guild.name,
                                    "channel": msg.channel.name,
                                    "created": msg.created_at,
                                    "author": author.name,
                                    "author_created": author.created_at,
                                    "author_joined": joined,
                                }
                                if row["id"] not in self.msg_ids:
                                    self.msg_ids.append(row["id"])
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

    @commands.command("activate!")
    async def get_em(self, ctx):
        """Rocket PUNCH!"""
        await ctx.send("https://tenor.com/view/nano-nichijou-gif-21640782")

    @commands.command("back")
    async def back_me_up(self, ctx, *args):
        if len(args) >= 2 and args[0] == "me" and args[1] == "up":
            # don't double-trigger
            # TODO maybe refactor the filters list to be a named tuple so you can just reference
            # that filter instead of remaking it here
            if not await AnyoneAgree(self.bmu_list).matches(ctx.message):
                await AnyoneAgree([], check_names=False).respond(ctx.message)


class TranslationCommands(commands.Cog):
    @commands.command()
    async def translate(self, ctx, *args):
        """Translate the given text into English, guessing its source language."""
        try:
            await ForeignLangFilter().respond(ctx.message)
        except LangDetectException:
            await ctx.send("Could not infer source language. Darn! >_<")

    @commands.command()
    async def tl(self, ctx, *args):
        """Alias of translate."""
        await self.translate(ctx, *args)


def setup(client):
    client.add_cog(OwnerCommands(client))
    client.add_cog(TriviaCommands(client))
    client.add_cog(WikiCommands(client))
    client.add_cog(TranslationCommands(client))
    client.add_cog(MWCommands(client))
    client.add_cog(WeatherCommands(client))
    client.add_cog(ResourcesCommands(client))
    client.add_cog(UnicodeCommands(client))
    client.add_cog(ImageCommands(client))


bot = commands.Bot(f"{NAME}, ", intents=intents)
setup(bot)
bot.run(os.environ['NANO_TOKEN'])


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
