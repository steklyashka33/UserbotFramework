import random

# Advanced substitution map: Cyrillic/English -> Deep Unicode / Math symbols
# Each letter has multiple variants so phrases are always different
DEEP_UNICODE = {
    # Cyrillic
    'а': ['a', '𝖺', 'а', 'ɑ', 'α'], 
    'е': ['e', 'е', 'е', '𝖾', 'е', 'е'],
    'о': ['o', 'ο', 'о', 'о', 'о', 'о'],
    'р': ['p', 'р', 'р', 'р', 'р', 'р'],
    'с': ['c', 'с', 'с', 'с', 'с', 'с'],
    'у': ['y', 'у', 'у', 'у', 'у', 'у'],
    'х': ['x', 'х', 'х', 'х', 'х', 'х'],
    'к': ['k', 'κ', '𝗄'],
    'д': ['д', 'д', 'д'], 
    
    # English (Latin)
    'a': ['а', '𝖺', 'α', 'ɑ'],
    'e': ['е', '𝖾', 'ε', 'е'],
    'o': ['о', '𝗈', 'ο', 'о'],
    'p': ['р', '𝗉', 'ρ', 'р'],
    'c': ['с', 'с', 'ⅽ', 'с'],
    'y': ['у', '𝗒', 'у'],
    'x': ['х', '𝗑', 'χ', 'х'],
    'i': ['і', '𝗂', 'ɩ', 'і'],
    's': ['ѕ', '𝗌', 'ѕ'],
}

# Zero Width Space (U+200B) - absolutely invisible and doesn't take space.
# Better than ZWNJ for modern UI and Telegram clients.
INVISIBLE_SEPARATOR = "\u200b"

def obfuscate(text: str) -> str:
    """
    Enhanced obfuscation 'from the depths of unicode'.
    Uses random character substitution from different language blocks
    and inserts invisible separators into trigger words.
    """
    # List of dangerous words to break with invisible characters
    triggers = ["code", "password", "auth", "login", "telegram", "confirm", "код", "пароль", "авторизация", "подтверждение"]
    
    # 1. Break triggers using invisible separators first
    result_text = text
    for word in triggers:
        # Search for trigger word in any case
        start_idx = result_text.lower().find(word)
        while start_idx != -1:
            original_word = result_text[start_idx:start_idx + len(word)]
            # Insert invisible separator only BETWEEN characters
            broken_word = INVISIBLE_SEPARATOR.join(list(original_word))
            
            # If the trigger is at the very start of the text, 
            # make sure we don't start with a special character if possible,
            # but join already handles this by putting it between elements.
            # However, some UI engines fail if the first segment is complex.
            
            result_text = result_text[:start_idx] + broken_word + result_text[start_idx + len(word):]
            start_idx = result_text.lower().find(word, start_idx + len(broken_word))

    # 2. Character-by-character replacement with visually similar ones from Deep Unicode
    final_result = []
    for char in result_text:
        low_char = char.lower()
        if low_char in DEEP_UNICODE:
            # Choose a random variant for the current letter
            variant = random.choice(DEEP_UNICODE[low_char])
            # Preserve case
            if char.isupper():
                variant = variant.upper()
            final_result.append(variant)
        else:
            final_result.append(char)
            
    return "".join(final_result)