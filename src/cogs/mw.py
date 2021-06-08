#!/usr/bin/env python3
import discord

"""This file provides Python bindings for the Merriam-Webster Dictionary API that correctly deal
with the API's use of markup."""
import re
import requests
from urllib.parse import quote


def to_small_caps(text: str) -> str:
    """Converts text to small caps."""
    # TODO implement Unicode small caps later
    return text.upper()


def to_italics(text: str) -> str:
    """Converts text to Markdown italics. Doesn't work for text with asterisks."""
    return f"*{text}*"


def to_bold(text: str) -> str:
    """Converts text to Markdown bold. Doesn't work for text with asterisks."""
    return f"**{text}**"


SUPERSCRIPT_NUMS = {str(i): chr(8304 + i) for i in range(10)}
# fix annoying edge cases
SUPERSCRIPT_NUMS["1"] = "\u00b9"
SUPERSCRIPT_NUMS["2"] = "\u00b2"
SUPERSCRIPT_NUMS["3"] = "\u00b3"
SUPERSCRIPT_NUMS["+"] = "\u207a"
SUPERSCRIPT_NUMS["-"] = "\u207b"
SUPERSCRIPT_TRANS = str.maketrans(SUPERSCRIPT_NUMS)

SUBSCRIPT_NUMS = {str(i): chr(8320 + i) for i in range(10)}
SUBSCRIPT_NUMS["+"] = "\u208a"
SUBSCRIPT_NUMS["-"] = "\u208b"
SUBSCRIPT_TRANS = str.maketrans(SUBSCRIPT_NUMS)


def to_subscript(text: str) -> str:
    """Given a numeric string, converts it to the Unicode subscript version."""
    return text.translate(SUBSCRIPT_TRANS)


def to_superscript(text: str) -> str:
    """Given a string, converts it to the Unicode superscript version."""
    return text.translate(SUPERSCRIPT_TRANS)


def replace_mw_punctuation(text: str) -> str:
    """Given input from the MW API, replaces the self-contained punctuation markup with its proper form.
    For instance, {ldquo} is replaced with the left quote character.
    """
    return (
        text.replace("{ldquo}", "\u201c")
        .replace("{rdquo}", "\u201d")
        .replace("{bc}", "**:** ")
    )


TOKEN_TO_FUNC = {
    "b": to_bold,
    "inf": to_subscript,
    "it": to_italics,
    "sc": to_small_caps,
    "sup": to_superscript,
    "phrase": lambda x: to_bold(to_italics(x)),
    "parahw": lambda x: to_bold(to_small_caps(x)),
    "gloss": lambda x: f"[{x}]",
    "wi": to_italics,
    "qword": to_italics,
}

MW_GROUP_RE = re.compile(r"{(.+?)}(.*?){\/.*?}")


def mw_to_markdown(text: str) -> str:
    """Given input from the MW API, translates the markup to Markdown."""
    new_text = replace_mw_punctuation(text)

    def replace(match):
        if match.group(1) in TOKEN_TO_FUNC:
            return TOKEN_TO_FUNC[match.group(1)](match.group(2))
        else:
            # one of the tags we don't search for, probably a link: just remove
            return ""

    subbed = re.sub(MW_GROUP_RE, replace, new_text)
    # now deal with single-quote markup like sx and a_link
    return re.sub(r"{[^}|]+\|([^}|]*)[^}]*}", r"\1", subbed)


BASEURL = "https://dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}"


def define(word):
    j = requests.get(BASEURL.format(quote(word), os.environ['MW_DICT_KEY'])).json()
    if j and isinstance(j[0], str):
        # gave us a list of suggestions back, try first one
        return define(j[0])
    elif not j:
        return []
    else:
        defs = []
        for definition in j:
            if definition["meta"]["id"].split(":")[0] == word:
                defs.append(definition)
        return defs
