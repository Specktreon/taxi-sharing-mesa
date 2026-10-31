"""Grid routing helpers.

Taxis drive on a regular grid without diagonal moves. The route between two
districts is the "x first, then y" Manhattan path, which is always a shortest
path in districts (it does not avoid congestion). Entering a district costs
minutes_per_district x its congestion factor; planning sums these costs along
the same path (TaxiModel.travel_time) and the actual movement happens one cell
at a time in TaxiAgent.move().
"""

from config import (CENTER_FACTOR, CONGESTION_CENTER_SIZE, CONGESTION_MODES,
                    RING_FACTOR)


def manhattan(a, b):
    """Grid distance (number of districts) between two cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_towards(current, target):
    """Next cell on the x-first path from current to target."""
    x, y = current
    tx, ty = target
    if x != tx:
        return (x + (1 if tx > x else -1), y)
    if y != ty:
        return (x, y + (1 if ty > y else -1))
    return current


def grid_path(start, end):
    """Cells visited when driving from start to end (start excluded)."""
    cells = []
    current = start
    while current != end:
        current = step_towards(current, end)
        cells.append(current)
    return cells


def travel_time(a, b, minutes_per_district):
    """Travel time in minutes between two districts without congestion."""
    return manhattan(a, b) * minutes_per_district


def congestion_center(width, height):
    """Lower-left cell (x0, y0) of the central congested square."""
    return ((width - CONGESTION_CENTER_SIZE) // 2,
            (height - CONGESTION_CENTER_SIZE) // 2)


def congestion_factor(cell, width, height, mode):
    """Integer factor on the time to enter `cell`: CENTER_FACTOR inside the
    central square, RING_FACTOR in the ring of cells around it, else 1."""
    if mode not in CONGESTION_MODES:
        raise ValueError(f"congestion must be one of {CONGESTION_MODES}")
    if mode == "off":
        return 1
    x0, y0 = congestion_center(width, height)
    last = CONGESTION_CENTER_SIZE - 1
    # Chebyshev distance from the cell to the central square (0 = inside).
    dx = max(x0 - cell[0], 0, cell[0] - (x0 + last))
    dy = max(y0 - cell[1], 0, cell[1] - (y0 + last))
    ring = max(dx, dy)
    return CENTER_FACTOR if ring == 0 else RING_FACTOR if ring == 1 else 1
