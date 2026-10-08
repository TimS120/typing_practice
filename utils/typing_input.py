"""Compare typed text with optional Enter presses at visual wrap points."""


def normalize_wrapped_input(target: str, typed: str, boundaries: set[int]) -> tuple[str, list[int]]:
    """Return canonical input and its original character offsets for highlighting.

    Each visual wrap permits one Enter, either alongside its separating
    whitespace or replacing one separator. Saved newlines remain literal.
    """
    separators = {}
    for boundary in boundaries:
        position = boundary - 1
        while position >= 0 and target[position].isspace() and target[position] not in "\r\n":
            separators[position] = boundary
            position -= 1
    result = []
    offsets = []
    used_wraps = set()
    for offset, char in enumerate(typed):
        position = len(result)
        expected = target[position] if position < len(target) else ""
        if char == "\n" and expected != "\n":
            boundary = separators.get(position, position if position in boundaries else None)
            if boundary is not None and boundary not in used_wraps:
                used_wraps.add(boundary)
                if position in separators:
                    # With a following space/tab, Enter is additional; otherwise
                    # it stands in for that separator in the saved text.
                    following = typed[offset + 1:offset + 2]
                    if following != expected:
                        result.append(expected)
                        offsets.append(offset)
                continue
        result.append(char)
        offsets.append(offset)
    return "".join(result), offsets
