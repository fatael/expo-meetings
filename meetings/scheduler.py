"""The scheduling engine.

Two steps, both independent of Django so they can be tested and reused on their own:

1. ``select_requests`` decides WHICH requests are granted when demand exceeds supply.
   It is an optimisation model (OR-Tools CP-SAT) that is fair across visitors: a visitor's
   first meeting is worth more than anyone's second, the second more than anyone's third,
   and so on. Within that, higher-priority requests are preferred.

2. ``assign_slots`` decides WHEN each granted meeting takes place. Because nobody is
   granted more meetings than there are slots, a conflict-free timetable always exists
   (edge colouring of a bipartite graph, König's theorem), and this step finds it exactly.
"""
from collections import defaultdict

from ortools.sat.python import cp_model

LEVEL_WEIGHT = 1000  # value of moving a visitor up one "round"
MAX_PRIORITY_BONUS = 50  # must stay well below LEVEL_WEIGHT


def select_requests(requests, n_slots, max_per_visitor=None, time_limit=30, workers=8):
    """Choose the requests to grant.

    ``requests`` is a list of ``(visitor, exhibitor, rank)`` with rank 1 = first priority.
    Returns the set of indexes into ``requests`` that are granted.
    """
    if not requests or n_slots <= 0:
        return set()
    visitor_cap = n_slots if max_per_visitor is None else min(n_slots, max_per_visitor)
    if visitor_cap <= 0:
        return set()

    by_visitor, by_exhibitor = defaultdict(list), defaultdict(list)
    for i, (visitor, exhibitor, _rank) in enumerate(requests):
        by_visitor[visitor].append(i)
        by_exhibitor[exhibitor].append(i)

    model = cp_model.CpModel()
    grant = [model.NewBoolVar(f"g{i}") for i in range(len(requests))]
    objective = []

    for i, (_v, _e, rank) in enumerate(requests):
        objective.append(max(1, MAX_PRIORITY_BONUS - rank) * grant[i])

    for visitor, idxs in by_visitor.items():
        cap = min(visitor_cap, len(idxs))
        total = sum(grant[i] for i in idxs)
        model.Add(total <= cap)
        # level[k] is true when the visitor has at least k+1 meetings.
        levels = [model.NewBoolVar(f"l{visitor}_{k}") for k in range(cap)]
        model.Add(sum(levels) == total)
        for k in range(cap - 1):
            model.AddImplication(levels[k + 1], levels[k])
        for k, level in enumerate(levels):
            objective.append(LEVEL_WEIGHT * (visitor_cap - k) * level)

    for idxs in by_exhibitor.values():
        model.Add(sum(grant[i] for i in idxs) <= n_slots)

    model.Maximize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("The scheduling engine could not find a solution in the time allowed.")
    return {i for i in range(len(requests)) if solver.Value(grant[i])}


def assign_slots(pairs, n_slots):
    """Give every (visitor, exhibitor) pair a slot index so that nobody is double-booked.

    Requires that no visitor and no exhibitor appears in more than ``n_slots`` pairs.
    Returns a dict ``{(visitor, exhibitor): slot_index}``.
    """
    # used[node][slot] = the node on the other side of the meeting held in that slot
    used = defaultdict(dict)

    def free(node):
        taken = used[node]
        for slot in range(n_slots):
            if slot not in taken:
                return slot
        raise ValueError(f"{node!r} has more meetings than there are slots")

    for visitor, exhibitor in pairs:
        v, e = ("v", visitor), ("e", exhibitor)
        a, b = free(v), free(e)
        if a in used[e]:
            # Slot a is busy on the exhibitor's side: swap a and b along the alternating
            # chain that starts at the exhibitor. In a bipartite graph it never reaches v.
            chain, node, slot = [], e, a
            while slot in used[node]:
                other = used[node][slot]
                chain.append((node, other, slot))
                node, slot = other, (b if slot == a else a)
            for x, y, slot in chain:
                del used[x][slot]
                del used[y][slot]
            for x, y, slot in chain:
                swapped = b if slot == a else a
                used[x][swapped] = y
                used[y][swapped] = x
        used[v][a] = e
        used[e][a] = v

    result = {}
    for (side, visitor), taken in used.items():
        if side == "v":
            for slot, (_side, exhibitor) in taken.items():
                result[(visitor, exhibitor)] = slot
    return result


def schedule(requests, n_slots, max_per_visitor=None, time_limit=30, workers=8):
    """Full run. Returns ``{request_index: slot_index}`` for the granted requests."""
    granted = sorted(select_requests(requests, n_slots, max_per_visitor, time_limit, workers))
    pairs = [(requests[i][0], requests[i][1]) for i in granted]
    slot_of = assign_slots(pairs, n_slots)
    return {i: slot_of[(requests[i][0], requests[i][1])] for i in granted}


def suggested_cap(n_requests, n_visitors, n_exhibitors, n_slots):
    """A reasonable ceiling on meetings per visitor, from the demand/supply ratio."""
    if not n_visitors or not n_slots:
        return 0
    supply = n_exhibitors * n_slots
    fair_share = supply // n_visitors
    average_demand = -(-n_requests // n_visitors)  # ceiling division
    return max(1, min(n_slots, fair_share, max(average_demand, 1)))
