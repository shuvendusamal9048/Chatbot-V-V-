def detect_language(text: str) -> str:
    if not text:
        return "en-IN"

    # Count Devanagari (Hindi) and Odia characters
    devanagari_count = 0
    odia_count = 0

    for char in text:
        codepoint = ord(char)
        if 0x0900 <= codepoint <= 0x097F:
            devanagari_count += 1
        elif 0x0B00 <= codepoint <= 0x0B7F:
            odia_count += 1

    if odia_count > 0:
        return "or-IN"
    elif devanagari_count > 0:
        return "hi-IN"
    else:
        return "en-IN"