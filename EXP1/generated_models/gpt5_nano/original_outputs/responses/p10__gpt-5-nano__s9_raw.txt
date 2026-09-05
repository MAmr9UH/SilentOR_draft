import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    # Decision variables
    shirts = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = model.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=GRB.BINARY, name="y_pants")

    model.update()

    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    labor_per = data["labor_per_unit"]
    cloth_per = data["cloth_per_unit"]

    rental = data["rental_cost"]
    unit_contrib = data["unit_contribution"]

    def M_for(key: str) -> int:
        lp = labor_per[key]
        cp = cloth_per[key]
        max_by_labor = int(labor_avail // lp) if lp > 0 else 0
        max_by_cloth = int(cloth_avail // cp) if cp > 0 else 0
        return min(max_by_labor, max_by_cloth)

    M_shirts = M_for("shirts")
    M_shorts = M_for("shorts")
    M_pants = M_for("pants")

    # Linking constraints: production implies renting machinery
    model.addConstr(shirts <= M_shirts * y_shirts)
    model.addConstr(shorts <= M_shorts * y_shorts_m)
    model.addConstr(pants <= M_pants * y_pants)

    # Resource constraints
    model.addConstr(labor_per["shirts"] * shirts +
                    labor_per["shorts"] * shorts +
                    labor_per["pants"] * pants <= labor_avail)

    model.addConstr(cloth_per["shirts"] * shirts +
                    cloth_per["shorts"] * shorts +
                    cloth_per["pants"] * pants <= cloth_avail)

    # Objective: maximize contribution minus rental
    objective = (unit_contrib["shirts"] * shirts +
                 unit_contrib["shorts"] * shorts +
                 unit_contrib["pants"] * pants) - (
        rental["shirts"] * y_shirts +
        rental["shorts"] * y_shorts_m +
        rental["pants"] * y_pants
    )
    model.setObjective(objective, GRB.MAXIMIZE)

    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }

    return model, variables

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
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    obj_val = model.ObjVal

    solution = {
        "shirts": variables["shirts"].X,
        "shorts": variables["shorts"].X,
        "pants": variables["pants"].X,
        "y_shirts": variables["y_shirts"].X,
        "y_shorts_m": variables["y_shorts_m"].X,
        "y_pants": variables["y_pants"].X
    }

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }