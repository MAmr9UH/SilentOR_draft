import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    # Parameters from data
    initial_inventory = float(data.get("initial_inventory", 0))
    initial_cash = float(data.get("initial_cash", 0))
    capacity = float(data.get("capacity", 0))
    final_inventory_required = float(data.get("final_inventory_required", 0))

    purchase_price = data.get("purchase_price", {})
    selling_price = data.get("selling_price", {})

    p = {
        1: float(purchase_price[str(1)]),
        2: float(purchase_price[str(2)]),
        3: float(purchase_price[str(3)])
    }
    s = {
        1: float(selling_price[str(1)]),
        2: float(selling_price[str(2)]),
        3: float(selling_price[str(3)])
    }

    # Decision variables
    buy_1 = model.addVar(lb=0.0, name="buy_1")
    buy_2 = model.addVar(lb=0.0, name="buy_2")
    buy_3 = model.addVar(lb=0.0, name="buy_3")

    sell_1 = model.addVar(lb=0.0, name="sell_1")
    sell_2 = model.addVar(lb=0.0, name="sell_2")
    sell_3 = model.addVar(lb=0.0, name="sell_3")

    inventory_1 = model.addVar(lb=0.0, name="inventory_1")
    inventory_2 = model.addVar(lb=0.0, name="inventory_2")
    inventory_3 = model.addVar(lb=0.0, name="inventory_3")

    cash_1 = model.addVar(lb=0.0, name="cash_1")
    cash_2 = model.addVar(lb=0.0, name="cash_2")
    cash_3 = model.addVar(lb=0.0, name="cash_3")

    # Profit variable (can be negative)
    profit = model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name="profit")

    # Balance equations
    model.addConstr(inventory_1 == initial_inventory - sell_1 + buy_1)
    model.addConstr(inventory_2 == inventory_1 - sell_2 + buy_2)
    model.addConstr(inventory_3 == inventory_2 - sell_3 + buy_3)

    # Final inventory requirement
    model.addConstr(inventory_3 == final_inventory_required)

    # Capacity constraints
    model.addConstr(inventory_1 <= capacity)
    model.addConstr(inventory_2 <= capacity)
    model.addConstr(inventory_3 <= capacity)

    # Sales cannot exceed available inventory (same-month purchases cannot be used)
    model.addConstr(sell_1 <= initial_inventory)
    model.addConstr(sell_2 <= inventory_1)
    model.addConstr(sell_3 <= inventory_2)

    # Cash flow constraints
    model.addConstr(cash_1 == initial_cash - p[1] * buy_1 + s[1] * sell_1)
    model.addConstr(cash_2 == cash_1 - p[2] * buy_2 + s[2] * sell_2)
    model.addConstr(cash_3 == cash_2 - p[3] * buy_3 + s[3] * sell_3)

    # Profit definition
    model.addConstr(profit == s[1] * sell_1 - p[1] * buy_1
                             + s[2] * sell_2 - p[2] * buy_2
                             + s[3] * sell_3 - p[3] * buy_3)

    # Objective: maximize profit
    model.setObjective(profit, GRB.MAXIMIZE)

    # Return model and a dictionary of variables
    variables = {
        "buy_1": buy_1,
        "buy_2": buy_2,
        "buy_3": buy_3,
        "sell_1": sell_1,
        "sell_2": sell_2,
        "sell_3": sell_3,
        "inventory_1": inventory_1,
        "inventory_2": inventory_2,
        "inventory_3": inventory_3,
        "cash_1": cash_1,
        "cash_2": cash_2,
        "cash_3": cash_3,
        "profit": profit
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.update()
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    model.update()
    solution = {
        "buy_1": float(variables["buy_1"].X),
        "buy_2": float(variables["buy_2"].X),
        "buy_3": float(variables["buy_3"].X),
        "sell_1": float(variables["sell_1"].X),
        "sell_2": float(variables["sell_2"].X),
        "sell_3": float(variables["sell_3"].X),
        "inventory_1": float(variables["inventory_1"].X),
        "inventory_2": float(variables["inventory_2"].X),
        "inventory_3": float(variables["inventory_3"].X),
        "cash_1": float(variables["cash_1"].X),
        "cash_2": float(variables["cash_2"].X),
        "cash_3": float(variables["cash_3"].X),
        "profit": float(variables["profit"].X)
    }

    objective_value = float(model.ObjVal)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }