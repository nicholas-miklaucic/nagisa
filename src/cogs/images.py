#!/usr/bin/env python3

"""Cog to let people search using Google Images and show the first result."""

from discord.ext import commands
import discord
import requests
from bs4 import BeautifulSoup


class ImageCommands(commands.Cog):
    """Images search. (Not Google because they killed API access...)"""
    def __init__(self, client):
        self.client = client

    def search(self, q):
        """Get an image URL for the given query and number of images."""
        url = "https://www.google.com/search"
        params = {
            'q': q,
            'tbm': 'isch'
        }
        soup = BeautifulSoup(requests.get(url, params=params).text)
        return soup.select('a div img')[0]['src']

    @commands.command(name='img')
    async def img(self, ctx, *args):
        """Return the first image that comes up in the search results for the given query."""
        async with ctx.typing():
            query = ' '.join(args)
            emb = discord.Embed()
            emb.set_image(url=self.search(query))

        await ctx.send(embed=emb)
