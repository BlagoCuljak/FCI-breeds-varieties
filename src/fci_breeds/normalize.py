"""Conservative enrichment; source labels always remain authoritative."""

# Sizes are breed-specific: a name such as Miniature Spitz is also a named variety.
SIZES = {
    172: {
        "standard": "Standard",
        "medium size": "Medium size",
        "miniature": "Miniature",
        "toy": "Toy",
    },
    148: {"standard": "Standard", "miniature": "Miniature", "rabbit dachshund": "Rabbit"},
}
COATS = {
    "smooth-haired": "Smooth-haired",
    "long-haired": "Long-haired",
    "wire-haired": "Wire-haired",
    "short-haired": "Short-haired",
    "rough-haired": "Rough-haired",
    "hairless": "Hairless",
    "powder puff": "Powder puff",
    "double coat": "Double coat",
    "long and harsh outer coat": "Long and harsh outer coat",
    "long and wavy": "Long and wavy",
    "shorter and curly": "Shorter and curly",
}
COLORS = {
    "black",
    "white",
    "brown",
    "grey",
    "fawn",
    "other colours",
    "brindle",
    "brindled",
    "harlequin",
    "merle",
    "blue",
    "pearl-white",
    "black and tan",
    "ruby",
    "blenheim",
    "tricolour",
    "parti-colour",
    "orange",
    "grey shaded",
    "ash",
    "liver",
    "ash-brown",
    "cifra (merle)",
    "white-orange",
    "chestnut roan",
}


def typed_fields(fci_id: int, labels: list[str]) -> dict:
    single = labels[0].casefold() if len(labels) == 1 else ""
    return {
        "size": SIZES.get(fci_id, {}).get(single),
        "coat": COATS.get(single),
        "colors": labels if labels and all(s.casefold() in COLORS for s in labels) else [],
    }
