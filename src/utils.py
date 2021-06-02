#!/usr/bin/env python3

"""Utility functions."""


def user_joined(user):
    """Gets joined_at if it exists, otherwise returning None."""
    if hasattr(user, 'joined_at'):
        return user.joined_at
    else:
        return None
