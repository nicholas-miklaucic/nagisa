#!/usr/bin/env python3

"""File to do plaintext Unicode search."""

from discord.ext import commands
import discord
import pandas as pd
import tabulate
import unicodedata
from fuzzywuzzy import process

UDATA = "https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt"
df = pd.read_csv(
    UDATA,
    sep=';',
    names=['code', 'name', 'category', 'combining_class', 'bidi_category', 'digit10', 'digit',
           'numeric', 'mirrored', 'old_name', 'comment', 'upper', 'lower', 'title'],
    index_col=False)


class UnicodeCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(name='unicode')
    async def unicode(self, ctx, *args):
        """Returns a table of Unicode code points that best match the given plaintext search.
        If the first argument is a number, shows that many results."""
        if args and args[0].isnumeric():
            limit = int(args[0])
            query = ' '.join(args[1:])
        else:
            limit = 3
            query = ' '.join(args)
        print(limit, query)
        results = process.extract(query, df['name'], limit=limit)
        output = [('Name', 'Code', 'Character')]
        for name, score, i in results:
            output.append((name, df.loc[i, 'code'], unicodedata.lookup(name)))

        await ctx.send('```\n' + tabulate.tabulate(output, tablefmt='simple') + '\n```')
