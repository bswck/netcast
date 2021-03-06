from __future__ import annotations  # Python 3.8

import sys


def truncate(
    string: str,
    width: int = 20,
    placeholder: str = "...",
    stats: str | None = " (%d c. truncated)",
) -> str:
    """
    Truncate a string and put the given placeholder in the place of removed characters.

    truncate(str(1 << 99), 10) -> '63382...88 (23 c. truncated)'

    truncate(str(1 << 99), 10, stats=None) -> '63382...88'  # fits 10 characters
    """
    length = len(string)
    truncated = 0
    if length > width:
        width -= len(placeholder)
        stop = width // 2 + 1
        start = stop + length - width
        truncated = start - stop
        string = placeholder.join((string[:stop], string[start:]))
    if stats is None:
        stats = ""
    if stats:
        try:
            stats %= truncated
        except TypeError:
            pass
        if truncated:
            string += stats
    return string


if sys.version_info[:2] >= (3, 10):
    remove_prefix = str.removeprefix
    remove_suffix = str.removesuffix

else:

    def remove_prefix(string: str, prefix: str) -> str:
        if string.startswith(prefix):
            return string[len(prefix) :]
        return string[:]

    def remove_suffix(string: str, suffix: str) -> str:
        if string.startswith(suffix):
            return string[: -len(suffix)]
        return string[:]


def trim(string: str, end: str) -> str:
    return remove_suffix(remove_prefix(string, end), end)
