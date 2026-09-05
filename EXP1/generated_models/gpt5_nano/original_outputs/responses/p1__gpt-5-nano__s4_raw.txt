import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]
    n = len(cap)
    M = sum(dem)

    model = gp.Model()

    # Produced variables: units produced of each type
    produced = {}
    for i in range(n):
        produced[str(i+1)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i+1}")

    # Allocation variables: amount of type i used to satisfy demand j
    allocation = {}
    for i in range(n):
        for j in range(n):
            if cap[i] >= cap[j]:
                allocation[f"{i+1},{j+1}"] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"alloc_{i+1}_{j+1}")

    # Binary indicators for fixed costs (not exposed in output per spec)
    y = {}
    for i in range(n):
        y[i] = model.addVar(vtype=GRB.BINARY, name=f"produce_on_{i+1}")

    model.update()

    # 1) produced_i equals sum_j allocation_{i,j} (only for valid (i,j) pairs)
    for i in range(n):
        terms = []
        for j in range(n):
            if cap[i] >= cap[j]:
                key = f"{i+1},{j+1}"
                if key in allocation:
                    terms.append(allocation[key])
        if terms:
            model.addConstr(produced[str(i+1)] == gp.quicksum(terms), name=f"prodEqAlloc_{i+1}")
        else:
            model.addConstr(produced[str(i+1)] == 0, name=f"prodEqAlloc_{i+1}")

    # 2) Demand constraints: sum_i allocation_{i,j} == dem_j
    for j in range(n):
        terms = []
        for i in range(n):
            if cap[i] >= cap[j]:
                key = f"{i+1},{j+1}"
                if key in allocation:
                    terms.append(allocation[key])
        model.addConstr(gp.quicksum(terms) == dem[j], name=f"demand_{j+1}")

    # 3) Link produced to fixed-cost indicator: produced_i <= M * y_i
    for i in range(n):
        model.addConstr(produced[str(i+1)] <= M * y[i], name=f"prod_link_{i+1}")

    # 4) Objective: minimize production costs + fixed costs
    objective = gp.quicksum(vcost[i] * produced[str(i+1)] for i in range(n)) + fixed * gp.quicksum(y[i] for i in range(n))
    model.setObjective(objective, GRB.MINIMIZE)

    model.update()

    variables = {
        "produced": {str(i+1): produced[str(i+1)] for i in range(n)},
        "allocation": allocation
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status, str(status))

    objective = float(model.ObjVal)

    produced_vals = {}
    for k, var in variables["produced"].items():
        produced_vals[k] = int(var.X)

    allocation_vals = {}
    for k, var in variables["allocation"].items():
        allocation_vals[k] = int(var.X)

    produced_out = {str(i+1): produced_vals[str(i+1)] for i in range(len(data["cap"]))}
    allocation_out = {k: allocation_vals[k] for k in sorted(allocation_vals.keys(), key=lambda s: (int(s.split(',')[0]), int(s.split(',')[1])))}

    solution = {
        "produced": produced_out,
        "allocation": allocation_out
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }