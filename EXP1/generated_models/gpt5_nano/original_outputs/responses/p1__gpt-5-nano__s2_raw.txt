import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data.get("fixed", 0)

    n = len(cap)
    m = gp.Model()

    # Decision variables
    produced = {}
    for i in range(1, n + 1):
        produced[str(i)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"produced_{i}")

    y = {}
    for i in range(1, n + 1):
        y[i] = m.addVar(vtype=GRB.BINARY, name=f"use_{i}")

    allocation = {}
    feasible_pairs = []
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                key = f"{i},{j}"
                allocation[key] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"a_{i}_{j}")
                feasible_pairs.append((i, j))

    m.update()

    total_demand = sum(dem)

    # Constraint: produced equals sum of allocations for each i
    for i in range(1, n + 1):
        m.addConstr(produced[str(i)] == gp.quicksum(allocation[f"{i},{j}"] for j in range(1, n + 1) if cap[i - 1] >= cap[j - 1]),
                    name=f"prod_eq_alloc_{i}")

    # Constraint: meet each demand exactly
    for j in range(1, n + 1):
        m.addConstr(gp.quicksum(allocation[f"{i},{j}"] for i in range(1, n + 1) if cap[i - 1] >= cap[j - 1]) == dem[j - 1],
                    name=f"meet_dem_{j}")

    # Fixed cost linking: produced <= total_demand * y_i
    for i in range(1, n + 1):
        m.addConstr(produced[str(i)] <= total_demand * y[i], name=f"prod_y_link_{i}")

    # Objective: minimize variable costs plus fixed costs
    m.setObjective(
        gp.quicksum(vcost[i - 1] * produced[str(i)] for i in range(1, n + 1)) +
        fixed * gp.quicksum(y[i] for i in range(1, n + 1)),
        GRB.MINIMIZE
    )

    m.update()

    variables = {
        "produced": {str(i): produced[str(i)] for i in range(1, n + 1)},
        "allocation": allocation  # keys are "i,j" strings
    }
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_num = model.Status
    status_str = status_map.get(status_num, str(status_num))

    model.update()

    objective = float(model.ObjVal)

    produced_sol = {k: float(v.X) for k, v in sorted(variables["produced"].items(), key=lambda item: int(item[0]))}
    allocation_sol = {k: float(v.X) for k, v in sorted(variables["allocation"].items(), key=lambda item: tuple(int(x) for x in item[0].split(',')))}

    solution = {
        "produced": produced_sol,
        "allocation": allocation_sol
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }