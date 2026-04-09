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
    Enhanced selective obfuscation for UserbotFramework.
    Only applies character substitution and invisible separators to identified 'trigger' words.
    """
    triggers = ["code", "password", "auth", "login", "telegram", "confirm", "код", "пароль", "авторизация", "подтверждение", "miyobi"]
    
    import re
    
    def replace_word(match):
        word = match.group(0)
        # 1. Insert invisible separators
        broken = INVISIBLE_SEPARATOR.join(list(word))
        
        # 2. Substitute characters
        substituted = []
        for char in broken:
            low_char = char.lower()
            if low_char in DEEP_UNICODE:
                if random.random() > 0.5:
                    variant = random.choice(DEEP_UNICODE[low_char])
                    substituted.append(variant.upper() if char.isupper() else variant)
                else:
                    substituted.append(char)
            else:
                substituted.append(char)
        return "".join(substituted)

    pattern = re.compile("|".join(re.escape(word) for word in triggers), re.IGNORECASE)
    return pattern.sub(replace_word, text)