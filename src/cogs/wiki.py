#!/usr/bin/env python3

import typing
import discord
import logging
import wikipedia
import re
from discord.ext import commands

"""Cog to support wikipedia functionality."""


class WikiCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def wiki(self, ctx, sentences: typing.Optional[int] = 2, *args):
        """Get the first sentences of the Wikipedia entry on the given topic. If the first input is
        an number, get that many sentences instead of the default 2."""
        async with ctx.typing():
            if not args:
                search_term = str(sentences)
                sentences = 2
            else:
                search_term = " ".join(args)
            logging.info(search_term)
            searched = wikipedia.search(f"{search_term}")
            if searched:
                suggested = searched[0]
            else:
                suggested = wikipedia.suggest(search_term)

            logging.info(suggested)
            try:
                text = wikipedia.summary(
                    suggested, sentences=sentences, auto_suggest=False
                )
                # MediaWiki has some super messed up formatting problems with TeX, do my best to
                # paper over the gaping maw of the problems with this format
                text = re.sub(r'\n +', '', text)
                text = re.sub(r'(\w+)\{.*\}', r'\1', text)
                text = text.replace('\n', '\n\n')
            except wikipedia.exceptions.DisambiguationError:
                text = "Your query wasn't specific enough."
            except wikipedia.exceptions.PageError:
                text = "Page not found, try again."
        await ctx.send(text)
