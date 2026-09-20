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
    # Extra options so a whole year group can each hold a unique avatar
    # (the profile page enforces one avatar per person).
    {"key": "monkey", "label": "Monkey", "emoji": "\U0001F435"},
    {"key": "chicken", "label": "Chicken", "emoji": "\U0001F414"},
    {"key": "pig", "label": "Pig", "emoji": "\U0001F437"},
    {"key": "cow", "label": "Cow", "emoji": "\U0001F42E"},
    {"key": "horse", "label": "Horse", "emoji": "\U0001F434"},
    {"key": "zebra", "label": "Zebra", "emoji": "\U0001F993"},
    {"key": "giraffe", "label": "Giraffe", "emoji": "\U0001F992"},
    {"key": "elephant", "label": "Elephant", "emoji": "\U0001F418"},
    {"key": "rhino", "label": "Rhino", "emoji": "\U0001F98F"},
    {"key": "kangaroo", "label": "Kangaroo", "emoji": "\U0001F998"},
    {"key": "hedgehog", "label": "Hedgehog", "emoji": "\U0001F994"},
    {"key": "otter", "label": "Otter", "emoji": "\U0001F9A6"},
    {"key": "sloth", "label": "Sloth", "emoji": "\U0001F9A5"},
    {"key": "flamingo", "label": "Flamingo", "emoji": "\U0001F9A9"},
    {"key": "parrot", "label": "Parrot", "emoji": "\U0001F99C"},
    {"key": "peacock", "label": "Peacock", "emoji": "\U0001F99A"},
    {"key": "bat", "label": "Bat", "emoji": "\U0001F987"},
    {"key": "crocodile", "label": "Crocodile", "emoji": "\U0001F40A"},
    {"key": "lizard", "label": "Lizard", "emoji": "\U0001F98E"},
    {"key": "snake", "label": "Snake", "emoji": "\U0001F40D"},
    {"key": "whale", "label": "Whale", "emoji": "\U0001F433"},
    {"key": "shark", "label": "Shark", "emoji": "\U0001F988"},
    {"key": "fish", "label": "Fish", "emoji": "\U0001F420"},
    {"key": "crab", "label": "Crab", "emoji": "\U0001F980"},
    {"key": "lobster", "label": "Lobster", "emoji": "\U0001F99E"},
    {"key": "squid", "label": "Squid", "emoji": "\U0001F991"},
    {"key": "snail", "label": "Snail", "emoji": "\U0001F40C"},
    {"key": "butterfly", "label": "Butterfly", "emoji": "\U0001F98B"},
    {"key": "bee", "label": "Bee", "emoji": "\U0001F41D"},
    {"key": "ladybug", "label": "Ladybug", "emoji": "\U0001F41E"},
    {"key": "dinosaur", "label": "Dinosaur", "emoji": "\U0001F995"},
    {"key": "trex", "label": "T-Rex", "emoji": "\U0001F996"},
    {"key": "deer", "label": "Deer", "emoji": "\U0001F98C"},
    {"key": "duck", "label": "Duck", "emoji": "\U0001F986"},
    {"key": "swan", "label": "Swan", "emoji": "\U0001F9A2"},
    {"key": "eagle", "label": "Eagle", "emoji": "\U0001F985"},
    {"key": "mouse", "label": "Mouse", "emoji": "\U0001F42D"},
    {"key": "hamster", "label": "Hamster", "emoji": "\U0001F439"},
    {"key": "beaver", "label": "Beaver", "emoji": "\U0001F9AB"},
    {"key": "badger", "label": "Badger", "emoji": "\U0001F9A1"},
    {"key": "llama", "label": "Llama", "emoji": "\U0001F999"},
    {"key": "camel", "label": "Camel", "emoji": "\U0001F42A"},
    {"key": "raccoon", "label": "Raccoon", "emoji": "\U0001F99D"},
    {"key": "dragon", "label": "Dragon", "emoji": "\U0001F409"},
]

AVATAR_BY_KEY = {a["key"]: a for a in AVATAR_CATALOG}
AVATAR_KEYS = set(AVATAR_BY_KEY.keys())


def default_avatar_for(user_id):
    """Deterministic (not random) so re-running a backfill is idempotent and
    a given user always lands on the same default until they change it."""
    return AVATAR_CATALOG[user_id % len(AVATAR_CATALOG)]["key"]
