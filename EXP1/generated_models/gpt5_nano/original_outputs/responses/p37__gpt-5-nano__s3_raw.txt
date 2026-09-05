import gurobipy as gp

def build_model(data: dict) -> tuple:
    # Extract data
    months = data.get("months", [1, 2, 3])
    initial_inventory = data["initial_inventory"]
    initial_cash = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]
    purchase_price = data["purchase_price"]
    selling_price = data["selling_price"]
    # same_month_purchases_sellable_next_month flag is acknowledged but not used directly here
    _ = data.get("same_month_purchases_sellable_next_month", True)

    # Create model
    model = gp.Model("grain_trading")

    # Decision variables (flat, per month)
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

    profit = model.addVar(lb=-gp.GRB.INFINITY, name="profit")

    # Convenience constants
    I0 = initial_inventory
    initial_cash_val = initial_cash
    P1 = purchase_price["1"]; P2 = purchase_price["2"]; P3 = purchase_price["3"]
    SP1 = selling_price["1"]; SP2 = selling_price["2"]; SP3 = selling_price["3"]

    # Constraints: inventory flow
    model.addConstr(inventory_1 == I0 + buy_1 - sell_1, name="flow_1")
    model.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="flow_2")
    model.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="flow_3")

    # Capacity constraints
    model.addConstr(inventory_1 <= capacity, name="cap1")
    model.addConstr(inventory_2 <= capacity, name="cap2")
    model.addConstr(inventory_3 <= capacity, name="cap3")

    # Sales cannot exceed available stock in the respective month
    model.addConstr(sell_1 <= I0, name="sell1_limit")
    model.addConstr(sell_2 <= inventory_1, name="sell2_limit")
    model.addConstr(sell_3 <= inventory_2, name="sell3_limit")

    # End-of-quarter inventory target
    model.addConstr(inventory_3 == final_inventory_required, name="final_inventory")

    # Cash flow constraints (payment upon delivery, revenue upon sale)
    model.addConstr(cash_1 == initial_cash_val - P1 * buy_1 + SP1 * sell_1, name="cash1")
    model.addConstr(cash_2 == cash_1 - P2 * buy_2 + SP2 * sell_2, name="cash2")
    model.addConstr(cash_3 == cash_2 - P3 * buy_3 + SP3 * sell_3, name="cash3")

    # Cash non-negativity
    model.addConstr(cash_1 >= 0, name="cash1_min")
    model.addConstr(cash_2 >= 0, name="cash2_min")
    model.addConstr(cash_3 >= 0, name="cash3_min")

    # Profit definition
    model.addConstr(profit == (SP1 * sell_1 - P1 * buy_1) +
                                (SP2 * sell_2 - P2 * buy_2) +
                                (SP3 * sell_3 - P3 * buy_3), name="profit_def")

    # Objective: maximize total profit
    model.setObjective(profit, gp.GRB.MAXIMIZE)

    # Return model and variable mapping
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
    model.optimize()

    # Update to access values
    model.update()
    status_code = model.Status

    # Map status to string
    if status_code == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = model.ObjVal

    # Read solution values
    sol = {
        "buy_1": variables["buy_1"].X,
        "buy_2": variables["buy_2"].X,
        "buy_3": variables["buy_3"].X,
        "sell_1": variables["sell_1"].X,
        "sell_2": variables["sell_2"].X,
        "sell_3": variables["sell_3"].X,
        "inventory_1": variables["inventory_1"].X,
        "inventory_2": variables["inventory_2"].X,
        "inventory_3": variables["inventory_3"].X,
        "cash_1": variables["cash_1"].X,
        "cash_2": variables["cash_2"].X,
        "cash_3": variables["cash_3"].X,
        "profit": variables["profit"].X
    }

    return {
        "status": status,
        "objective": float(objective),
        "solution": sol
    }