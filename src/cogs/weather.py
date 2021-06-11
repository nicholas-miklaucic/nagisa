#!/usr/bin/env python3

from discord.ext import commands
import discord
import os
import requests
import re


class WeatherCommands(commands.Cog):
    KEY = os.environ['OWM_KEY']
    BASE_URL = 'http://api.openweathermap.org/data/2.5/weather'
    ICON_URL = 'http://openweathermap.org/img/wn/{code}@2x.png'

    def __init__(self, client):
        self.client = client

    @staticmethod
    def format_temp(c_temp):
        """Takes in a measurement in Celsius and formats it using both Celsius and Fahrenheit."""
        f_temp = c_temp * 9 / 5 + 32
        return f"{c_temp:.1f} °C ({f_temp:.1f} °F)"

    @commands.command()
    async def weather(self, ctx, *args):
        async with ctx.typing():
            query = ' '.join(args)
            if ',' in query:  # split into list so the comma makes it into the query
                query = query.split(',')
            r = requests.get(self.BASE_URL, timeout=0.5,
                             params={'q': query, 'appid': self.KEY, 'units': 'metric'})
        if r.status_code != requests.codes.ok:
            await ctx.send("Could not complete query. Sorry!")
            r.raise_for_status()
        else:
            j = r.json()
            if type(query) == list:
                q = ', '.join(query)
            else:
                q = query

            embed = discord.Embed(title=f'Weather in {q}', type='rich',
                                  colour=0x000763)
            embed.set_image(url=self.ICON_URL.format(code=j['weather'][0]['icon']))
            embed.add_field(name='Conditions',
                            value=j['weather'][0]['description'].capitalize())
            embed.add_field(name='Feels Like',
                            value=self.format_temp(j['main']['feels_like']))
            embed.set_footer(text='Data courtesy of OpenWeatherMap')
            await ctx.send(embed=embed)
