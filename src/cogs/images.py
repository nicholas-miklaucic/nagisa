#!/usr/bin/env python3

"""Cog to let people search using Google Images and show the first result."""

from discord.ext import commands
import discord
import requests

class ImageCommands(commands.Cog):
    """Images search. (Not Google because they killed API access...)"""
    def __init__(self, client):
        self.client = client

    def search(self, q):
        """Gets an image URL for the given query and number of images."""
        params = {
            'count': 1,
            'q': q,
            't': 'images',
            'safesearch': 1,
            'locale': 'en_US',
            'uiv': 4
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        }
        r = requests.get("https://api.qwant.com/api/search/images", params=params, headers=headers)
        resp = r.json().get('data').get('result').get('items')[0]
        return resp['media']

    @commands.command(name='img')
    async def img(self, ctx, *args):
        """Returns the first image that comes up in the search results for the given query."""
        async with ctx.typing():
            query = ' '.join(args)
            emb = discord.Embed()
            emb.set_image(url=self.search(query))

        await ctx.send(embed=emb)
