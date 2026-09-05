import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    m = gp.Model()

    # Extract data
    products = data["products"]
    rental_cost = data["rental_cost"]
    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]
    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]
    unit_contrib = data["unit_contribution"]

    # Upper bounds for production (based on resource limits)
    M_shirts = min(int(labor_avail / labor_per_unit["shirts"]), int(cloth_avail / cloth_per_unit["shirts"]))
    M_shorts = min(int(labor_avail / labor_per_unit["shorts"]), int(cloth_avail / cloth_per_unit["shorts"]))
    M_pants = min(int(labor_avail / labor_per_unit["pants"]), int(cloth_avail / cloth_per_unit["pants"]))

    # Decision variables
    shirts = m.addVar(lb=0.0, ub=M_shirts, vtype=GRB.CONTINUOUS, name="shirts")
    shorts = m.addVar(lb=0.0, ub=M_shorts, vtype=GRB.CONTINUOUS, name="shorts")
    pants = m.addVar(lb=0.0, ub=M_pants, vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = m.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = m.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = m.addVar(vtype=GRB.BINARY, name="y_pants")

    # Objective: max contribution minus rental costs
    objective = (unit_contrib["shirts"] * shirts +
                 unit_contrib["shorts"] * shorts +
                 unit_contrib["pants"] * pants -
                 rental_cost["shirts"] * y_shirts -
                 rental_cost["shorts"] * y_shorts_m -
                 rental_cost["pants"] * y_pants)

    m.setObjective(objective, GRB.MAXIMIZE)

    # Constraints
    # Labor
    m.addConstr(labor_per_unit["shirts"] * shirts +
                labor_per_unit["shorts"] * shorts +
                labor_per_unit["pants"] * pants <= labor_avail,
                name="labor")

    # Cloth
    m.addConstr(cloth_per_unit["shirts"] * shirts +
                cloth_per_unit["shorts"] * shorts +
                cloth_per_unit["pants"] * pants <= cloth_avail,
                name="cloth")

    # Big-M linking constraints to enforce rental when production > 0
    m.addConstr(shirts <= M_shirts * y_shirts, name="link_shirts")
    m.addConstr(shorts <= M_shorts * y_shorts_m, name="link_shorts")
    m.addConstr(pants <= M_pants * y_pants, name="link_pants")

    # Prepare variables dict to return
    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Update to ensure values are ready to read
    model.update()

    status_int = model.Status
    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.UNKNOWN: "UNKNOWN"
    }
    status_str = status_map.get(status_int, str(status_int))

    objective_value = model.ObjVal if model.ObjVal is not None else None

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
        "objective": float(objective_value) if objective_value is not None else None,
        "solution": solution
    }