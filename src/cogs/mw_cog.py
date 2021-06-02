#!/usr/bin/env python3

"""Cog to interact with the Merriam-Webster dictionary."""
from discord.ext import commands
from .mw import define, mw_to_markdown
import discord
from constants import NAME


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


class MWCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.definitions = {}

    @commands.Cog.listener()
    async def on_reaction_add(self, rxn, user):
        msg = rxn.message
        if user.name == NAME:
            return
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
