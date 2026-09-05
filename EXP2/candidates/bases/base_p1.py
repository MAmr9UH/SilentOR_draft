"""Certified base model for Exp-2 problem 1 (red_star_plastic).
Matches frozen requirements R1-R7. Returns keys: produced (dict '1'..'6'),
allocation (dict 'i,j' for cap_i>=cap_j)."""
import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    cap = data["cap"]; dem = data["dem"]; vcost = data["vcost"]; FIX = data["fixed"]
    n = len(dem)
    m = gp.Model(); m.Params.OutputFlag = 0

    # produced[i]: units of type i produced (integer, >=0)  -- R5, R6
    produced = {i: m.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i}") for i in range(1, n + 1)}
    # allocation[(i,j)]: units of type i used to serve demand class j, only if cap_i>=cap_j -- R2
    alloc = {}
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                alloc[(i, j)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f"alloc_{i}_{j}")
    # open[i]: 1 iff type i produced (for fixed cost) -- R4
    openv = {i: m.addVar(vtype=GRB.BINARY, name=f"open_{i}") for i in range(1, n + 1)}

    # R1 demand satisfaction: each class j fully served by allocations into it
    for j in range(1, n + 1):
        m.addConstr(gp.quicksum(alloc[(i, j)] for i in range(1, n + 1) if (i, j) in alloc)
                    >= dem[j - 1], name=f"demand_{j}")
    # R3 conservation: units of type i used cannot exceed produced
    for i in range(1, n + 1):
        m.addConstr(gp.quicksum(alloc[(i, j)] for j in range(1, n + 1) if (i, j) in alloc)
                    <= produced[i], name=f"conserve_{i}")
    # R4 fixed-cost linking: produced[i] > 0 only if open[i]=1  (big-M = total demand)
    M = sum(dem)
    for i in range(1, n + 1):
        m.addConstr(produced[i] <= M * openv[i], name=f"link_{i}")

    # R7 objective: variable cost + fixed cost
    m.setObjective(gp.quicksum(vcost[i - 1] * produced[i] for i in range(1, n + 1))
                   + FIX * gp.quicksum(openv[i] for i in range(1, n + 1)), GRB.MINIMIZE)

    variables = {"produced": produced, "allocation": alloc}
    return m, variables


def solve(data: dict) -> dict:
    m, variables = build_model(data)
    m.optimize()
    status_map = {GRB.OPTIMAL: "OPTIMAL", GRB.INFEASIBLE: "INFEASIBLE",
                  GRB.UNBOUNDED: "UNBOUNDED", GRB.INF_OR_UNBD: "INF_OR_UNBD",
                  GRB.TIME_LIMIT: "TIME_LIMIT"}
    produced = {str(i): int(round(v.X)) for i, v in variables["produced"].items()}
    allocation = {f"{i},{j}": int(round(var.X)) for (i, j), var in variables["allocation"].items()}
    return {"status": status_map.get(m.Status, str(m.Status)),
            "objective": float(m.ObjVal),
            "solution": {"produced": produced, "allocation": allocation}}
