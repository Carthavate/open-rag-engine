"""Small helpers for text that comes back from an LLM."""

import re

_THINK = re.compile(r"<think>.*?</think>", flags=re.DOTALL)
OPEN, CLOSE = "<think>", "</think>"


def strip_think(text: str) -> str:
    """Remove reasoning that models like Qwen3 may emit before the answer.

    Handles complete <think>...</think> blocks, reasoning whose opening tag was part of the prompt template
    (only </think> appears), and reasoning cut off before it closed.
    """
    text = _THINK.sub("", text)
    if CLOSE in text:
        text = text.rsplit(CLOSE, 1)[1]
    if OPEN in text:
        text = text.split(OPEN, 1)[0]
    return text.strip()


class ThinkFilter:
    """Hides a leading <think>...</think> block from a token stream; everything after it passes through."""

    def __init__(self) -> None:
        self._buffer = ""
        self._passing = False

    def feed(self, token: str) -> str:
        if self._passing:
            return token
        self._buffer += token
        head = self._buffer.lstrip()
        if not head or (len(head) < len(OPEN) and OPEN.startswith(head)):
            return ""
        if head.startswith(OPEN):
            if CLOSE not in head:
                return ""
            self._passing = True
            return head.split(CLOSE, 1)[1].lstrip()
        self._passing = True
        return self._buffer
