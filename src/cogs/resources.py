#!/usr/bin/env python3

"""Simple cog to show a list of resources on the server."""
from discord.ext import commands
import discord


class ResourcesCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    def resources(self, ctx):
        emb = discord.Embed(
            title='Resources',
            description='Useful sites to know about for homework help'
        )

        emb.add_field(name='General', value="""
[Khan Academy](https://www.khanacademy.org/)
[]
""")
