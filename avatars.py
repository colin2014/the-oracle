"""Fixed catalog of student profile-picture avatars.

Deliberately a closed set of built-in options — never a free-text value,
uploaded file, or external URL/image — so a student can express a little
personality (Kahoot-style) without any path to entering personal information.

Each avatar is a standard Unicode emoji character, not a downloaded/embedded
image file: the actual glyph artwork is rendered by the visitor's own OS or
browser font, which is already properly licensed on their device. Nothing is
scraped, redistributed, or bundled here — just a character code point plus a
label, so there is no licensing or attribution question for this codebase.
"""

AVATAR_CATALOG = [
    {"key": "fox", "label": "Fox", "emoji": "\U0001F98A"},
    {"key": "bear", "label": "Bear", "emoji": "\U0001F43B"},
    {"key": "panda", "label": "Panda", "emoji": "\U0001F43C"},
    {"key": "koala", "label": "Koala", "emoji": "\U0001F428"},
    {"key": "bunny", "label": "Bunny", "emoji": "\U0001F430"},
    {"key": "wolf", "label": "Wolf", "emoji": "\U0001F43A"},
    {"key": "cat", "label": "Cat", "emoji": "\U0001F431"},
    {"key": "dog", "label": "Dog", "emoji": "\U0001F436"},
    {"key": "lion", "label": "Lion", "emoji": "\U0001F981"},
    {"key": "tiger", "label": "Tiger", "emoji": "\U0001F42F"},
    {"key": "frog", "label": "Frog", "emoji": "\U0001F438"},
    {"key": "owl", "label": "Owl", "emoji": "\U0001F989"},
    {"key": "penguin", "label": "Penguin", "emoji": "\U0001F427"},
    {"key": "turtle", "label": "Turtle", "emoji": "\U0001F422"},
    {"key": "dolphin", "label": "Dolphin", "emoji": "\U0001F42C"},
    {"key": "unicorn", "label": "Unicorn", "emoji": "\U0001F984"},
    {"key": "octopus", "label": "Octopus", "emoji": "\U0001F419"},
    {"key": "robot", "label": "Robot", "emoji": "\U0001F916"},
    {"key": "alien", "label": "Alien", "emoji": "\U0001F47D"},
    {"key": "ghost", "label": "Ghost", "emoji": "\U0001F47B"},
]

AVATAR_BY_KEY = {a["key"]: a for a in AVATAR_CATALOG}
AVATAR_KEYS = set(AVATAR_BY_KEY.keys())


def default_avatar_for(user_id):
    """Deterministic (not random) so re-running a backfill is idempotent and
    a given user always lands on the same default until they change it."""
    return AVATAR_CATALOG[user_id % len(AVATAR_CATALOG)]["key"]
