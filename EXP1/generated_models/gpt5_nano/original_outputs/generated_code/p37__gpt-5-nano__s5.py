import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    initial_inventory = data["initial_inventory"]
    initial_cash = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]

    purchase_price = data["purchase_price"]
    selling_price = data["selling_price"]

    m = gp.Model()

    # Decision variables
    buy_1 = m.addVar(lb=0, name="buy_1", vtype=GRB.CONTINUOUS)
    buy_2 = m.addVar(lb=0, name="buy_2", vtype=GRB.CONTINUOUS)
    buy_3 = m.addVar(lb=0, name="buy_3", vtype=GRB.CONTINUOUS)

    sell_1 = m.addVar(lb=0, name="sell_1", vtype=GRB.CONTINUOUS)
    sell_2 = m.addVar(lb=0, name="sell_2", vtype=GRB.CONTINUOUS)
    sell_3 = m.addVar(lb=0, name="sell_3", vtype=GRB.CONTINUOUS)

    inventory_1 = m.addVar(lb=0, name="inventory_1", vtype=GRB.CONTINUOUS)
    inventory_2 = m.addVar(lb=0, name="inventory_2", vtype=GRB.CONTINUOUS)
    inventory_3 = m.addVar(lb=0, name="inventory_3", vtype=GRB.CONTINUOUS)

    cash_1 = m.addVar(lb=0, name="cash_1", vtype=GRB.CONTINUOUS)
    cash_2 = m.addVar(lb=0, name="cash_2", vtype=GRB.CONTINUOUS)
    cash_3 = m.addVar(lb=0, name="cash_3", vtype=GRB.CONTINUOUS)

    profit = m.addVar(lb=-GRB.INFINITY, name="profit", vtype=GRB.CONTINUOUS)

    # Constraints

    # Inventory balance
    m.addConstr(inventory_1 == initial_inventory + buy_1 - sell_1, name="inv1")
    m.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="inv2")
    m.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="inv3")

    # Capacity
    m.addConstr(inventory_1 <= capacity, name="cap1")
    m.addConstr(inventory_2 <= capacity, name="cap2")
    m.addConstr(inventory_3 <= capacity, name="cap3")

    # Sell limits (can't sell same-month purchases)
    m.addConstr(sell_1 <= initial_inventory, name="sell1_cap")
    m.addConstr(sell_2 <= inventory_1, name="sell2_cap")
    m.addConstr(sell_3 <= inventory_2, name="sell3_cap")

    # Cash flow with immediate payment on purchase and revenue on sale
    m.addConstr(cash_1 == initial_cash - purchase_price["1"] * buy_1 + selling_price["1"] * sell_1, name="cash1")
    m.addConstr(cash_2 == cash_1 - purchase_price["2"] * buy_2 + selling_price["2"] * sell_2, name="cash2")
    m.addConstr(cash_3 == cash_2 - purchase_price["3"] * buy_3 + selling_price["3"] * sell_3, name="cash3")

    # Non-negativity of cash (practical constraint)
    m.addConstr(cash_1 >= 0, name="cash1_nonneg")
    m.addConstr(cash_2 >= 0, name="cash2_nonneg")
    m.addConstr(cash_3 >= 0, name="cash3_nonneg")

    # Final inventory requirement
    m.addConstr(inventory_3 == final_inventory_required, name="final_inventory")

    # Profit linkage
    profit_expr = (
        selling_price["1"] * sell_1 +
        selling_price["2"] * sell_2 +
        selling_price["3"] * sell_3 -
        purchase_price["1"] * buy_1 -
        purchase_price["2"] * buy_2 -
        purchase_price["3"] * buy_3
    )
    m.addConstr(profit == profit_expr, name="profit_link")

    # Objective
    m.setObjective(profit, GRB.MAXIMIZE)

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

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    # Read status and objective
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    model.update()
    objective = float(model.ObjVal) if model.ObjVal is not None else None

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
        "status": status,
        "objective": objective,
        "solution": solution
    }