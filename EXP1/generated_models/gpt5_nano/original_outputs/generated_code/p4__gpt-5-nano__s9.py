import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    foods = data["foods"]
    min_vals = data["min"]
    prot = data["protein"]
    carb = data["carb"]
    cal = data["calories"]
    cost = data["cost"]

    model = gp.Model()

    vars = {}
    for f in foods:
        vars[f] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"{f}")

    model.update()

    model.setObjective(gp.quicksum(cost[f] * vars[f] for f in foods), GRB.MINIMIZE)

    model.addConstr(gp.quicksum(prot[f] * vars[f] for f in foods) >= min_vals["protein"], name="protein_min")
    model.addConstr(gp.quicksum(carb[f] * vars[f] for f in foods) >= min_vals["carb"], name="carb_min")
    model.addConstr(gp.quicksum(cal[f] * vars[f] for f in foods) >= min_vals["calories"], name="cal_min")

    model.update()
    return model, vars

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = "UNKNOWN"

    obj = float(model.ObjVal) if model.ObjVal is not None else 0.0

    def safeX(v):
        try:
            val = v.X
            return float(val)
        except Exception:
            return 0.0

    solution = {
        "chicken": safeX(variables["chicken"]) if "chicken" in variables else 0.0,
        "rice": safeX(variables["rice"]) if "rice" in variables else 0.0,
        "broccoli": safeX(variables["broccoli"]) if "broccoli" in variables else 0.0,
        "tofu": safeX(variables["tofu"]) if "tofu" in variables else 0.0,
        "beans": safeX(variables["beans"]) if "beans" in variables else 0.0,
    }

    return {
        "status": status_str,
        "objective": obj,
        "solution": solution
    }