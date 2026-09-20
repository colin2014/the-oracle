"""Playful two-word names for student accounts ("Jumping Chameleon", "Crazy Crab").

Students never type a name: they pick one happy word and one animal from these
fixed lists, so no real name can enter the system. 25 + 25 = 50 words, giving 625
combinations. The pair becomes both the display name and the login username.
"""

HAPPY_WORDS = [
    "Jumping", "Crazy", "Happy", "Dancing", "Giggling", "Sparkly", "Bouncy", "Zippy", "Cheerful",
    "Sunny", "Wiggly", "Cheeky", "Silly", "Snazzy", "Bubbly", "Groovy", "Jolly", "Perky", "Speedy",
    "Funky", "Merry", "Twirling", "Skipping", "Laughing", "Zooming",
]

ANIMALS = [
    "Chameleon", "Crab", "Penguin", "Llama", "Otter", "Panda", "Koala", "Sloth", "Fox", "Owl",
    "Hedgehog", "Dolphin", "Giraffe", "Octopus", "Flamingo", "Gecko", "Badger", "Walrus", "Puffin",
    "Lemur", "Narwhal", "Platypus", "Capybara", "Meerkat", "Axolotl",
]

_HAPPY_SET = set(HAPPY_WORDS)
_ANIMAL_SET = set(ANIMALS)


def is_valid_pair(happy, animal):
    return happy in _HAPPY_SET and animal in _ANIMAL_SET


def display_name(happy, animal):
    return f"{happy} {animal}"


def username_for(happy, animal):
    """'Jumping', 'Chameleon' -> 'jumping-chameleon' (matches the login username rules)."""
    return f"{happy}-{animal}".lower()
