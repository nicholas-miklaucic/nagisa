#!/usr/bin/env python3

"""This file defines message filters: automated tests that are applied to each message sent,
triggering some corresponding action."""
import discord
from langdetect import detect_langs
from googletrans import Translator, LANGUAGES
from utils import user_joined
import spacy
import datetime
import logging
from constants import NAME
nlp = spacy.load('en_core_web_sm')
a2a_nlp = spacy.load("textcat_demo/training/model-best")


class MessageFilter():
    """Specific way of filtering messages and handling them accordingly."""

    async def matches(self, message):
        raise NotImplementedError()

    async def respond(self, message):
        pass


class WatchedChannelFilter(MessageFilter):
    """Filter for general and academic-help channels only."""

    def __init__(self, channel_prefs):
        self.channel_prefs = channel_prefs

    async def matches(self, message):
        return (type(message.channel) == discord.DMChannel or
                any([message.channel.name.startswith(pref) for pref in self.channel_prefs]))


class RecentJoinFilter(MessageFilter):
    async def matches(self, message):
        joined = user_joined(message.author)
        return joined is not None and (message.created_at - joined) < datetime.timedelta(minutes=5)


class A2AFilter(MessageFilter):
    """Filter for ask-to-ask messages."""

    async def matches(self, message):
        cats = a2a_nlp(message.content.lower()).cats
        return cats['BAD'] * 100 > cats['GOOD']

    async def respond(self, message):
        if message.guild.name == "Homework Help Voice":
            await message.add_reaction('<:snoo_disapproval:808077416501215232>')
        else:
            await message.add_reaction("🤨")


class MentionOrReply(MessageFilter):

    async def matches(self, message):
        if message.author.name == NAME:
            return False
        elif hasattr(message, 'reference') and message.reference is not None:
            ref = message.reference.message_id
            ref_msg = await message.channel.fetch_message(ref)
            if ref_msg.author.name == NAME:
                logging.info(ref_msg)
                logging.info(ref_msg, ref_msg.author)
                logging.info(message)
                logging.info(message.channel)
                logging.info(message.reference)
                return True
        else:
            return any(member.name == 'Nano' for member in message.mentions)


class IsThankYou(MessageFilter):

    async def matches(self, message):
        return any(word in message.content.lower() for word in
                   ("thank", "thanks", "good bot"))

    async def respond(self, message):
        await message.add_reaction("🥰")


class IsScold(MessageFilter):

    async def matches(self, message):
        return any(word in message.content.lower() for word in
                   ("bad bot",))

    async def respond(self, message):
        await message.reply("https://tenor.com/view/nichijou-nano-silly-stupid-gif-20046613")


class AnyoneAgree(MessageFilter):

    def __init__(self, names, check_names=True):
        self.names = names
        self.check_names = check_names

    async def matches(self, message):
        return (message.author is not None and
                (not self.check_names or message.author.name in self.names) and
                "back me up" in message.content.lower())

    async def respond(self, message):
        await message.reply(f"I completely agree with {message.author.display_name} on this one")


class ForeignLangFilter(MessageFilter):
    translator = Translator()

    async def matches(self, message):
        if len(message.content) <= 30:
            return False
        elif message.content.startswith("Nano, "):
            return False
        else:
            langs = detect_langs(message.content)
            if langs and langs[0].lang == 'en':
                # most likely match, continue
                return False
            else:
                return any([lang.lang != 'en' and lang.prob > 0.99 for lang in langs])

    async def respond(self, message):
        if message.content.startswith("Nano, translate"):
            content = message.content[len("Nano, translate"):]
        elif message.content.startswith("Nano, tl"):
            content = message.content[len("Nano, tl"):]
        else:
            content = message.content
        translated = self.translator.translate(content)
        if translated.src != 'en':
            lang = LANGUAGES.get(translated.src.lower(), 'unknown')
            await message.reply(f"Translated from {lang.capitalize()}: {translated.text}")


class ComboFilter(MessageFilter):

    def __init__(self, filters):
        self.filters = filters

    async def matches(self, message):
        matches = []
        for f in self.filters:
            does_match = await f.matches(message)
            matches.append(does_match)
        return all(matches)

    async def respond(self, message):
        for f in self.filters:
            await f.respond(message)
