"""Map generation, seed ranges and cheapest-path tables (spec §1.1, §1.7, §1.8)."""

import numpy as np
import pytest

from tlr.costs import CostModel
from tlr.mapgen import (HAZARD, WALL, _connected_non_walls, compute_statics, generate_instance,
                        instance_from_ascii)
from tlr.utils import SEED_BASE, deep_update, instance_seed


def test_same_seed_same_instance_different_seed_different(cfg):
    a = generate_instance(cfg, instance_seed("test", 0))
    b = generate_instance(cfg, instance_seed("test", 0))
    c = generate_instance(cfg, instance_seed("test", 1))
    assert a.to_bytes() == b.to_bytes()
    assert a.to_bytes() != c.to_bytes()


@pytest.mark.parametrize("L,density", [(10, 0.06), (8, 0.04), (8, 0.08), (12, 0.04), (12, 0.08)])
def test_generated_instances_satisfy_spec(cfg, L, density):
    c2 = deep_update(cfg, {"env": {"grid_size": L, "victim_density": density}})
    for k in range(25):
        inst = generate_instance(c2, instance_seed("calibration", k))
        assert inst.L == L
        assert _connected_non_walls(inst.grid, L, inst.base)
        assert inst.grid[inst.base] == 0                       # base is plain free (not wall, not hazard)
        assert inst.meta["walls_placed"] == inst.meta["walls_target"] == round(0.15 * L * L + 1e-9)
        V = int(np.floor(density * L * L + 0.5))
        assert inst.n_victims == V
        assert len(set(inst.victim_cells.tolist())) == V      # distinct cells
        assert (inst.grid[inst.victim_cells] != WALL).all()
        assert int(inst.victim_heavy.sum()) == int(np.floor(0.5 * V + 0.5))
        br, bc = inst.rc(inst.base)
        for cell in inst.victim_cells:                         # never visible from the base at t = 0
            r, c = inst.rc(cell)
            assert max(abs(r - br), abs(c - bc)) >= 2
        assert int((inst.grid == HAZARD).sum()) == inst.meta["hazards"]


def test_p_heavy_zero_shares_layout_and_positions(cfg):
    """A3 pairing: same seed -> same layout and victim cells; p_heavy = 0 makes every victim light."""
    c0 = deep_update(cfg, {"env": {"p_heavy": 0.0}})
    for k in range(20):
        s = instance_seed("train", k)
        a, b = generate_instance(cfg, s), generate_instance(c0, s)
        assert np.array_equal(a.grid, b.grid) and a.base == b.base
        assert np.array_equal(a.victim_cells, b.victim_cells)
        assert not b.victim_heavy.any() and a.victim_heavy.sum() == 3


def test_seed_ranges_disjoint():
    lo_hi = {}
    for split in SEED_BASE:
        lo_hi[split] = (instance_seed(split, 0, 0), instance_seed(split, 9_999, 99))
    spans = sorted(lo_hi.values())
    for (a_lo, a_hi), (b_lo, _) in zip(spans, spans[1:]):
        assert a_hi < b_lo
    with pytest.raises(ValueError):
        instance_seed("test", 0, 100)


def test_hazard_path_costs_and_asymmetry(cfg):
    cm = CostModel.from_config(cfg)
    # Top row is a corridor B(0,0) -> ~(0,1) -> .(0,2); the rest connects through column 1.
    inst = instance_from_ascii(["B~.",
                                "#.#",
                                "#.#"])
    st = compute_statics(inst, cm, [1, 2])
    b, h, e = 0, 1, 2
    assert st.dist[b, h] == 2 and st.dist[b, e] == 3      # entering the hazard costs 2, then 1
    assert st.dist[h, b] == 1 and st.dist[e, b] == 3      # leaving the hazard is cheap: d is not symmetric
    assert st.steps[b, e] == 2
    assert st.dist[b, 3] >= 10**6                          # wall cell is unreachable


def test_first_move_tables_consistent(cfg):
    """For every reachable pair: first step lies on a cheapest path and step counts are consistent."""
    cm = CostModel.from_config(cfg)
    for k in range(5):
        inst = generate_instance(cfg, instance_seed("validation", k))
        st = compute_statics(inst, cm, [1, 2])
        free = np.flatnonzero(st.free)
        for a in free:
            assert st.dist[a, a] == 0 and st.first_move[a, a] == -1
            for b in free:
                if a == b:
                    continue
                m = st.first_move[a, b]
                assert 0 <= m <= 3
                nxt = st.move_target[a, m]
                assert nxt >= 0
                assert st.entry_cost[nxt] + st.dist[nxt, b] == st.dist[a, b]
                assert st.steps[a, b] == st.steps[nxt, b] + 1
                # Deterministic tie-break: no earlier action index is also on a cheapest path.
                for m2 in range(m):
                    n2 = st.move_target[a, m2]
                    if n2 >= 0:
                        assert st.entry_cost[n2] + st.dist[n2, b] > st.dist[a, b]
