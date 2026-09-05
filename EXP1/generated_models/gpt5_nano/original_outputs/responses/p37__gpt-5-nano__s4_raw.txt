import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Parameters from data
    initial_inventory = data["initial_inventory"]
    initial_cash = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]

    purchase_price = data["purchase_price"]  # dict with keys "1","2","3"
    selling_price = data["selling_price"]    # dict with keys "1","2","3"

    # Decision variables (flat continuous)
    buy_1 = model.addVar(lb=0, name="buy_1", vtype=GRB.CONTINUOUS)
    buy_2 = model.addVar(lb=0, name="buy_2", vtype=GRB.CONTINUOUS)
    buy_3 = model.addVar(lb=0, name="buy_3", vtype=GRB.CONTINUOUS)

    sell_1 = model.addVar(lb=0, name="sell_1", vtype=GRB.CONTINUOUS)
    sell_2 = model.addVar(lb=0, name="sell_2", vtype=GRB.CONTINUOUS)
    sell_3 = model.addVar(lb=0, name="sell_3", vtype=GRB.CONTINUOUS)

    inventory_1 = model.addVar(lb=0, ub=capacity, name="inventory_1", vtype=GRB.CONTINUOUS)
    inventory_2 = model.addVar(lb=0, ub=capacity, name="inventory_2", vtype=GRB.CONTINUOUS)
    inventory_3 = model.addVar(lb=0, ub=capacity, name="inventory_3", vtype=GRB.CONTINUOUS)

    cash_1 = model.addVar(lb=0, name="cash_1", vtype=GRB.CONTINUOUS)
    cash_2 = model.addVar(lb=0, name="cash_2", vtype=GRB.CONTINUOUS)
    cash_3 = model.addVar(lb=0, name="cash_3", vtype=GRB.CONTINUOUS)

    profit = model.addVar(lb=-GRB.INFINITY, name="profit", vtype=GRB.CONTINUOUS)

    model.update()

    # Constraints
    # Inventory balance
    model.addConstr(inventory_1 == initial_inventory + buy_1 - sell_1, name="inv_bal_1")
    model.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="inv_bal_2")
    model.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="inv_bal_3")

    # Sales limits (cannot sell more than stock at sale time)
    model.addConstr(sell_1 <= initial_inventory, name="sell_lim_1")
    model.addConstr(sell_2 <= inventory_1, name="sell_lim_2")
    model.addConstr(sell_3 <= inventory_2, name="sell_lim_3")

    # Cash flow (payment upon delivery; revenue on sale)
    model.addConstr(cash_1 == initial_cash - buy_1 * purchase_price["1"] + sell_1 * selling_price["1"], name="cash_flow_1")
    model.addConstr(cash_2 == cash_1 - buy_2 * purchase_price["2"] + sell_2 * selling_price["2"], name="cash_flow_2")
    model.addConstr(cash_3 == cash_2 - buy_3 * purchase_price["3"] + sell_3 * selling_price["3"], name="cash_flow_3")

    # Final inventory requirement
    model.addConstr(inventory_3 == final_inventory_required, name="final_inv")

    # Profit definition
    model.addConstr(profit == (
        sell_1 * selling_price["1"] + sell_2 * selling_price["2"] + sell_3 * selling_price["3"]
    ) - (
        buy_1 * purchase_price["1"] + buy_2 * purchase_price["2"] + buy_3 * purchase_price["3"]
    ), name="profit_def")

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

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status_str = status_map.get(status_code, str(status_code))

    objective = model.ObjVal if model.Status == GRB.OPTIMAL else None

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "maximum total profit over the three months"},
            "solution": {
                "type": "object",
                "required": [
                    "buy_1","buy_2","buy_3",
                    "sell_1","sell_2","sell_3",
                    "inventory_1","inventory_2","inventory_3",
                    "cash_1","cash_2","cash_3",
                    "profit"
                ],
                "properties": {
                    "buy_1": {"type": "number"},
                    "buy_2": {"type": "number"},
                    "buy_3": {"type": "number"},
                    "sell_1": {"type": "number"},
                    "sell_2": {"type": "number"},
                    "sell_3": {"type": "number"},
                    "inventory_1": {"type": "number"},
                    "inventory_2": {"type": "number"},
                    "inventory_3": {"type": "number"},
                    "cash_1": {"type": "number"},
                    "cash_2": {"type": "number"},
                    "cash_3": {"type": "number"},
                    "profit": {"type": "number"}
                }
            }
        }
    }

    return {
        "status": status_str,
        "objective": float(objective) if objective is not None else None,
        "solution": solution
    }