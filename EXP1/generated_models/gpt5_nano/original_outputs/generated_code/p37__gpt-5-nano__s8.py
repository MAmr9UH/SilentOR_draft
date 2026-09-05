import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    months = data.get("months", [1, 2, 3])
    n = len(months)

    initial_inventory = data["initial_inventory"]
    initial_cash = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]

    purchase_price = data["purchase_price"]  # dict with keys "1","2","3"
    selling_price = data["selling_price"]    # dict with keys "1","2","3"

    # Variables (flat, as required)
    buy_1 = model.addVar(lb=0, name="buy_1")
    buy_2 = model.addVar(lb=0, name="buy_2")
    buy_3 = model.addVar(lb=0, name="buy_3")

    sell_1 = model.addVar(lb=0, name="sell_1")
    sell_2 = model.addVar(lb=0, name="sell_2")
    sell_3 = model.addVar(lb=0, name="sell_3")

    inventory_1 = model.addVar(lb=0, name="inventory_1")
    inventory_2 = model.addVar(lb=0, name="inventory_2")
    inventory_3 = model.addVar(lb=0, name="inventory_3")

    cash_1 = model.addVar(lb=0, name="cash_1")
    cash_2 = model.addVar(lb=0, name="cash_2")
    cash_3 = model.addVar(lb=0, name="cash_3")

    profit = model.addVar(lb=-GRB.INFINITY, name="profit")

    # Convenience numbers
    p1 = float(purchase_price["1"])
    p2 = float(purchase_price["2"])
    p3 = float(purchase_price["3"])

    s1 = float(selling_price["1"])
    s2 = float(selling_price["2"])
    s3 = float(selling_price["3"])

    # Inventory balances
    model.addConstr(inventory_1 == initial_inventory + buy_1 - sell_1)
    model.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2)
    model.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3)

    # Capacity constraints
    model.addConstr(inventory_1 <= capacity)
    model.addConstr(inventory_2 <= capacity)
    model.addConstr(inventory_3 <= capacity)

    # Non-negativity for inventories already ensured by lb=0

    # Sale constraints: can't sell more than what is available before that month
    model.addConstr(sell_1 <= initial_inventory)
    model.addConstr(sell_2 <= inventory_1)
    model.addConstr(sell_3 <= inventory_2)

    # End inventory requirement
    model.addConstr(inventory_3 == final_inventory_required)

    # Cash balance constraints
    model.addConstr(cash_1 == initial_cash - buy_1 * p1 + sell_1 * s1)
    model.addConstr(cash_2 == cash_1 - buy_2 * p2 + sell_2 * s2)
    model.addConstr(cash_3 == cash_2 - buy_3 * p3 + sell_3 * s3)

    # Payment feasibility each month
    model.addConstr(initial_cash - buy_1 * p1 >= 0)
    model.addConstr(cash_1 >= buy_2 * p2)
    model.addConstr(cash_2 >= buy_3 * p3)

    # Non-negativity on cash
    model.addConstr(cash_1 >= 0)
    model.addConstr(cash_2 >= 0)
    model.addConstr(cash_3 >= 0)

    # Profit relation
    model.addConstr(profit == cash_3 - initial_cash)

    # Objective: maximize profit
    model.setObjective(profit, GRB.MAXIMIZE)

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

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_value = model.Status
    if status_value == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_value == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_value == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_value == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_value == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_value)

    # Read objective
    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Ensure values are up-to-date
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

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }