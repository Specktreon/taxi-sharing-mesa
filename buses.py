"""Bus lines and bus agents (optional public transport, parameter `buses`).

Each line is a straight row or column driven back and forth. A bus enters the
next district after cell_minutes of that district (taxi speed, congestion
applies). At a stop it lets riders off, then takes waiting passengers who are
heading the way it drives, up to BUS_CAPACITY; it stands boarding_minutes only
when someone boarded or alighted. Riders board at the start of that stop and
finish alighting at its end, as in taxis.
"""

import mesa

from config import (BUS_CAPACITY, BUS_MIN_TRIP, BUS_STOP_SPACING, BUS_WALK_MAX,
                    BUSES_PER_LINE)
from routing import manhattan


class BusLine:
    """A straight bus line: its cells in driving order and its stops."""

    def __init__(self, line_id, name, cells):
        self.line_id = line_id
        self.name = name
        self.cells = cells
        positions = list(range(0, len(cells), BUS_STOP_SPACING))
        if positions[-1] != len(cells) - 1:
            positions.append(len(cells) - 1)  # stops at both ends
        self.stop_index = {cells[i]: i for i in positions}  # stop -> position
        self.waiting = {cell: [] for cell in self.stop_index}  # queue per stop


def make_bus_lines(width, height):
    """Rows h//4, h//2, 3h//4 (H1-H3) and columns w//4, w//2, 3w//4 (V1-V3)."""
    lines = []
    for i, y in enumerate((height // 4, height // 2, 3 * height // 4), 1):
        lines.append(BusLine(len(lines), f"H{i}", [(x, y) for x in range(width)]))
    for i, x in enumerate((width // 4, width // 2, 3 * width // 4), 1):
        lines.append(BusLine(len(lines), f"V{i}", [(x, y) for y in range(height)]))
    return lines


def choose_bus_trip(lines, origin, destination):
    """(line, boarding stop, alighting stop) with the least total walking, or
    None. Only trips of at least BUS_MIN_TRIP districts use the bus. Both stops
    must be on the same line (no transfers), different, and each within
    BUS_WALK_MAX districts. Ties: lower line id, then stop order."""
    if manhattan(origin, destination) < BUS_MIN_TRIP:
        return None
    best = None
    for line in lines:
        near_origin = [s for s in line.stop_index if manhattan(origin, s) <= BUS_WALK_MAX]
        near_dest = [s for s in line.stop_index
                     if manhattan(destination, s) <= BUS_WALK_MAX]
        for board in near_origin:
            for alight in near_dest:
                if board == alight:
                    continue
                key = (manhattan(origin, board) + manhattan(alight, destination),
                       line.line_id, line.stop_index[board], line.stop_index[alight])
                if best is None or key < best[0]:
                    best = (key, line, board, alight)
    return None if best is None else best[1:]


def initial_positions(line):
    """BUSES_PER_LINE (position, direction) pairs spread evenly over the
    back-and-forth cycle of the line."""
    last = len(line.cells) - 1
    cycle = 2 * last
    result = []
    for k in range(BUSES_PER_LINE):
        phase = k * cycle // BUSES_PER_LINE
        result.append((phase, 1) if phase < last else (cycle - phase, -1))
    return result


class BusAgent(mesa.Agent):
    """A bus driving back and forth along one line."""

    def __init__(self, model, line, index, direction):
        super().__init__(model)
        self.line = line
        self.index = index  # position along line.cells
        self.direction = direction  # +1 or -1 along line.cells
        self.capacity = BUS_CAPACITY
        self.onboard = []
        self.alighting = []  # riders leaving during the current stop
        self.dwell = 0
        self.progress = 0  # minutes driven towards the next cell
        self.distance = 0  # districts driven
        self.passenger_distance = 0  # passenger-districts carried

    def move(self):
        """One minute: stand at a stop, or drive towards the next cell."""
        now = self.model.minute
        if self.dwell > 0:
            self.dwell -= 1
            if self.dwell == 0:
                self.finish_stop(now + 1)
            return
        next_cell = self.line.cells[self.index + self.direction]
        self.progress += 1
        if self.progress < self.model.cell_minutes[next_cell]:
            return
        self.progress = 0
        self.index += self.direction
        self.model.grid.move_agent(self, next_cell)
        for p in self.onboard:
            self.model.grid.move_agent(p, next_cell)
        self.distance += 1
        self.passenger_distance += len(self.onboard)
        if self.index in (0, len(self.line.cells) - 1):
            self.direction = -self.direction  # turn at the end of the line
        self.serve_stop(now + 1)

    def serve_stop(self, minute):
        """Riders for this stop get off, then waiting passengers heading the
        bus's way board in arrival order while seats are free."""
        here = self.line.stop_index.get(self.pos)
        if here is None:
            return
        self.alighting = [p for p in self.onboard if p.alight_stop == self.pos]
        for p in self.alighting:
            self.onboard.remove(p)
        boarded = False
        queue = self.line.waiting[self.pos]
        for p in list(queue):
            if len(self.onboard) >= self.capacity:
                break
            if (self.line.stop_index[p.alight_stop] - here) * self.direction > 0:
                queue.remove(p)
                p.board_bus(self, minute)
                self.onboard.append(p)
                boarded = True
        if self.alighting or boarded:
            self.dwell = self.model.boarding_minutes
        if self.dwell == 0:
            self.finish_stop(minute)

    def finish_stop(self, minute):
        for p in self.alighting:
            p.leave_bus(minute)
        self.alighting = []
