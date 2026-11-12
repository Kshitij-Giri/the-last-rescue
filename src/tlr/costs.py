"""Action set and integer resource-cost model.

Implements: spec §1.2 (actions, costs). All cost values come from the `costs` block of the config.
The cost of a move depends on the cell being ENTERED (hazard cells cost more), so the cost of an action can only be
computed with the map; `action_cost` takes the precomputed per-cell entry cost array.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import numpy as np


class Action(IntEnum):
    """The 8 primitive actions. Integer values are the column indices of Q-tables and masks."""

    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    SEARCH = 4
    RESCUE = 5
    ASSIST = 6
    WAIT = 7


N_ACTIONS = len(Action)
MOVE_ACTIONS = (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT)
# (d_row, d_col) of each move. Row 0 is the top (north) of the grid.
MOVE_DELTAS = {Action.UP: (-1, 0), Action.DOWN: (1, 0), Action.LEFT: (0, -1), Action.RIGHT: (0, 1)}


@dataclass(frozen=True)
class CostModel:
    """Integer costs of every action type (spec §1.2)."""

    move: int
    move_hazard: int
    search: int
    rescue: int
    assist: int
    wait: int

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "CostModel":
        c = cfg["costs"]
        model = cls(int(c["move"]), int(c["move_hazard"]), int(c["search"]), int(c["rescue"]),
                    int(c["assist"]), int(c["wait"]))
        model.validate()
        return model

    def validate(self) -> None:
        """Enforce the assumptions the rest of the code relies on."""
        if self.wait != 0:
            # WAIT must be free so that an agent always has at least one valid action (spec §1.2).
            raise ValueError("WAIT must cost 0")
        for name in ("move", "move_hazard", "search", "rescue", "assist"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must cost >= 1 (integer units)")
        if self.move_hazard < self.move:
            raise ValueError("hazard moves must not be cheaper than normal moves")

    @property
    def c_min(self) -> int:
        """Cheapest costly action (defines dormancy: budget < c_min)."""
        return min(self.move, self.move_hazard, self.search, self.rescue, self.assist)

    @property
    def c_rescue(self) -> int:
        return self.rescue

    @property
    def c_assist(self) -> int:
        return self.assist

    def action_cost(self, action: int, target_entry_cost: int) -> int:
        """Cost of `action`. `target_entry_cost` is the entry cost of the move's target cell (ignored otherwise)."""
        if action <= Action.RIGHT:
            return int(target_entry_cost)
        if action == Action.SEARCH:
            return self.search
        if action == Action.RESCUE:
            return self.rescue
        if action == Action.ASSIST:
            return self.assist
        return self.wait

    def non_move_costs(self) -> np.ndarray:
        """Costs of actions 4..7 (SEARCH, RESCUE, ASSIST, WAIT) as an int array, for fast masking."""
        return np.array([self.search, self.rescue, self.assist, self.wait], dtype=np.int64)
