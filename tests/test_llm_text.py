import pytest

from open_rag_engine.llm_text import ThinkFilter, strip_think


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("<think>plan</think>\nAnswer [1].", "Answer [1]."),
        ("planning without an opening tag\n</think>\n\nAnswer [1].", "Answer [1]."),
        ("Answer [1].", "Answer [1]."),
        ("<think>cut off before the end", ""),
    ],
)
def test_strip_think(raw: str, clean: str):
    assert strip_think(raw) == clean


def stream(tokens: list[str]) -> str:
    f = ThinkFilter()
    return "".join(f.feed(t) for t in tokens)


def test_think_filter_hides_a_leading_block_split_across_tokens():
    assert stream(["<thi", "nk>I should", " cite [2]</th", "ink>\n", "It is [1]", "."]) == "It is [1]."


def test_think_filter_passes_plain_answers_through():
    assert stream(["It ", "draws ", "1.2 kW [1]."]) == "It draws 1.2 kW [1]."


def test_think_filter_does_not_mistake_a_short_answer_for_a_tag():
    assert stream(["<b", ">bold</b>"]) == "<b>bold</b>"
