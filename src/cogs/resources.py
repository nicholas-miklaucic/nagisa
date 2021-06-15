#!/usr/bin/env python3

"""Simple cog to show a list of resources on the server."""
from discord.ext import commands
import discord
import json
import typing

res = ""
with open('resources/resources.json', 'r') as infile:
    res = json.load(infile)

class ResourcesCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def help_list(self, ctx):
        await ctx.send("Available resource headings (use `Nano, resources {header}`):\n" +
                       '\n'.join(res.keys()))

    @commands.command(name='resources')
    async def help(self, ctx, subj: typing.Optional[str]):
        """Show a list of helpful free online resources. subj can be:
         - general, math, or writing, to show those pages
         - list to show all page headers
         - nothing to show all resources"""
        if subj is None:
            for subj in res:
                await self.help(ctx, subj)
        elif subj.lower() in res:
            emb = discord.Embed(
                title=f'Resources: {subj.capitalize()}',
            )
            for field in res[subj]:
                emb.add_field(**field)

            await ctx.send(embed=emb)
        elif subj.lower() == 'list':
            await self.help_list(ctx)
        else:
            await ctx.send("Couldn't find any list of resources under that name.")
            await self.help_list(ctx)
