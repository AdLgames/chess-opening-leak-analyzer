"""Rating bands, so a club player is compared against club players.

The book folds every game together, which means "the database scores 54% here" is really
"everyone from 800 to 2800 scores 54% here". Those are different games. A line that is
excellent once both sides know the theory can be a poor practical choice at 1400, and a
line that scores well at 1400 precisely because it is easy to meet badly may be nothing at
master level. Telling a 1400 they are 6% below a number set largely by players two classes
above them is not a useful thing to tell them.

Bands are coarse on purpose. Narrow bands cut the number of games behind each move, and the
whole analysis rests on having enough games to say anything — a comparison against the right
population with eight games behind it is worse than one against a slightly wrong population
with eight hundred.
"""
from __future__ import annotations

# (name, lower, upper). Upper is exclusive except for the top band.
BANDS: tuple[tuple[str, int, int], ...] = (
    ("u1200", 0, 1200),
    ("1200-1600", 1200, 1600),
    ("1600-2000", 1600, 2000),
    ("2000-2400", 2000, 2400),
    ("2400+", 2400, 10000),
)

# What the book calls the everyone-together rows. Books built before bands existed contain
# only these, which is why it is a real value rather than NULL.
ALL = "all"

LABELS = {
    "u1200": "under 1200",
    "1200-1600": "1200–1600",
    "1600-2000": "1600–2000",
    "2000-2400": "2000–2400",
    "2400+": "2400 and up",
    ALL: "all ratings",
}


def band_for(rating: int | float | None) -> str:
    """The band a rating falls in, or `ALL` when there is no rating to go on."""
    if rating is None:
        return ALL
    try:
        value = float(rating)
    except (TypeError, ValueError):
        return ALL
    if value <= 0:
        return ALL
    for name, low, high in BANDS:
        if low <= value < high:
            return name
    return BANDS[-1][0]


def label(band: str) -> str:
    return LABELS.get(band, band)


def neighbours(band: str) -> list[str]:
    """The band itself, then its neighbours outward, then everyone.

    Used to widen the comparison when the player's own band is too thin to say anything.
    Widening outward keeps the population as close as possible for as long as possible,
    rather than jumping straight to a number set by everybody.
    """
    if band == ALL:
        return [ALL]
    names = [b[0] for b in BANDS]
    try:
        i = names.index(band)
    except ValueError:
        return [ALL]
    out = [band]
    for step in range(1, len(names)):
        for j in (i - step, i + step):
            if 0 <= j < len(names) and names[j] not in out:
                out.append(names[j])
    out.append(ALL)
    return out
