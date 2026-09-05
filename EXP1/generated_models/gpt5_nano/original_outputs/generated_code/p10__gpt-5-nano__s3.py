import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("GandhiCloth")

    # Decision variables
    shirts = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = model.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=GRB.BINARY, name="y_pants")

    # Extract data
    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]

    unit_contribution = data["unit_contribution"]
    rental_cost = data["rental_cost"]

    # Max possible production per type (Big-M values)
    M_shirts = min(labor_avail / labor_per_unit["shirts"], cloth_avail / cloth_per_unit["shirts"])
    M_shorts = min(labor_avail / labor_per_unit["shorts"], cloth_avail / cloth_per_unit["shorts"])
    M_pants = min(labor_avail / labor_per_unit["pants"], cloth_avail / cloth_per_unit["pants"])

    # Constraints
    model.addConstr(3 * shirts + 2 * shorts + 6 * pants <= labor_avail, name="Labor")
    model.addConstr(4 * shirts + 3 * shorts + 4 * pants <= cloth_avail, name="Cloth")

    model.addConstr(shirts <= M_shirts * y_shirts, name="Link_Shirts")
    model.addConstr(shorts <= M_shorts * y_shorts_m, name="Link_Shorts")
    model.addConstr(pants <= M_pants * y_pants, name="Link_Pants")

    # Objective: maximize contribution minus rental costs
    objective = (unit_contribution["shirts"] * shirts +
                 unit_contribution["shorts"] * shorts +
                 unit_contribution["pants"] * pants -
                 rental_cost["shirts"] * y_shirts -
                 rental_cost["shorts"] * y_shorts_m -
                 rental_cost["pants"] * y_pants)

    model.setObjective(objective, GRB.MAXIMIZE)

    model.update()

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

    # Map status to readable string
    status_num = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_num, str(status_num))

    objective = float(model.ObjVal)

    solution = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }