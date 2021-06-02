#!/usr/bin/env python3

"""Cog to support trivia puzzles."""
from discord.ext import commands
import requests
import logging
import random
import html
import asyncio
from constants import NAME


class TriviaCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.qs_with_answers = {}
        self.answer_choices = "🇦🇧🇨🇩"

    @ commands.Cog.listener()
    async def on_ready(self):
        r = requests.get("https://opentdb.com/api_token.php?command=request")
        r.raise_for_status()
        self.token = r.json()['token']

    @commands.Cog.listener()
    async def on_reaction_add(self, rxn, user):
        msg = rxn.message
        if user.name == NAME:
            return
        elif msg.id in self.qs_with_answers:
            correct_char = self.answer_choices[self.qs_with_answers[msg.id]]
            if str(rxn) == correct_char:
                del self.qs_with_answers[msg.id]
                await msg.channel.send("Correct, good job {}!".format(user.mention))

    @ commands.command()
    async def trivia(self, ctx):
        # TODO support more features
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
            text = f"{html.unescape(q['question'])}"
            for choice, answer in zip(self.answer_choices, answers):
                text += f'\n{choice} → {html.unescape(answer)}'

            msg = await ctx.send(text)
            self.qs_with_answers[msg.id] = correct_answer_num
            await asyncio.gather(*[msg.add_reaction(c) for c in self.answer_choices])
