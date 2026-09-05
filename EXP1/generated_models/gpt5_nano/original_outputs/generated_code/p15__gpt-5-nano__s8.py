import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.Params.OutputFlag = 0

    centers = data.get("centers", [])
    stores = data.get("stores", [])
    fixed_opening_cost = data.get("fixed_opening_cost", {})
    transport_cost = data.get("transport_cost", {})
    demand = data.get("demand", {})
    capacity = data.get("capacity", {})

    # Decision variables
    # Binary opening variables y_c1 ... y_c5
    variables = {}

    for i in range(1, 6):
        key = f"y_c{i}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Continuous shipment variables f_c{i}_s{j}
    for i in range(1, 6):
        for j in range(1, 8):
            key = f"f_c{i}_s{j}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Demand constraints: sum over centers of shipments to store j equals its demand
    store_keys = ["s1","s2","s3","s4","s5","s6","s7"]
    demands = [demand[k] for k in store_keys]
    for j_idx, s_key in enumerate(store_keys, start=1):
        expr = gp.quicksum(variables[f"f_c{i}_s{j_idx}"] for i in range(1, 6))
        model.addConstr(expr == demands[j_idx-1], name=f"demand_{s_key}")

    # Capacity constraints: sum over stores of shipments from center i <= capacity_i * y_c{i}
    for i in range(1, 6):
        cap = capacity.get(f"c{i}", 0)
        expr = gp.quicksum(variables[f"f_c{i}_s{j}"] for j in range(1, 8))
        model.addConstr(expr <= cap * variables[f"y_c{i}"], name=f"cap_c{i}")

    # Objective: minimize total opening costs plus transportation costs
    obj = gp.quicksum(fixed_opening_cost[f"c{i}"] * variables[f"y_c{i}"] for i in range(1, 6))
    for i in range(1, 6):
        center_key = f"c{i}"
        for j in range(1, 8):
            store_key = f"s{j}"
            c = transport_cost[center_key][store_key]
            obj += c * variables[f"f_c{i}_s{j}"]

    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.DELAYED: "DELAYED"
    }
    status_str = status_map.get(status_int, str(status_int))
    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }