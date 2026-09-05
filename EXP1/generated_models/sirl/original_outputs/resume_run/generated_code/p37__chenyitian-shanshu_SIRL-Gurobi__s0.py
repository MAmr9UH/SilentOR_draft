import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("grain_trading_model")
    
    # Define decision variables
    buy = {
        1: model.addVar(name="buy_1", vtype=GRB.CONTINUOUS, lb=0),
        2: model.addVar(name="buy_2", vtype=GRB.CONTINUOUS, lb=0),
        3: model.addVar(name="buy_3", vtype=GRB.CONTINUOUS, lb=0)
    }
    
    sell = {
        1: model.addVar(name="sell_1", vtype=GRB.CONTINUOUS, lb=0),
        2: model.addVar(name="sell_2", vtype=GRB.CONTINUOUS, lb=0),
        3: model.addVar(name="sell_3", vtype=GRB.CONTINUOUS, lb=0)
    }
    
    inventory = {
        1: model.addVar(name="inventory_1", vtype=GRB.CONTINUOUS, lb=0),
        2: model.addVar(name="inventory_2", vtype=GRB.CONTINUOUS, lb=0),
        3: model.addVar(name="inventory_3", vtype=GRB.CONTINUOUS, lb=0)
    }
    
    cash = {
        1: model.addVar(name="cash_1", vtype=GRB.CONTINUOUS, lb=0),
        2: model.addVar(name="cash_2", vtype=GRB.CONTINUOUS, lb=0),
        3: model.addVar(name="cash_3", vtype=GRB.CONTINUOUS, lb=0)
    }
    
    profit = model.addVar(name="profit", vtype=GRB.CONTINUOUS, lb=0)
    
    variables = {
        "buy_1": buy[1],
        "buy_2": buy[2],
        "buy_3": buy[3],
        "sell_1": sell[1],
        "sell_2": sell[2],
        "sell_3": sell[3],
        "inventory_1": inventory[1],
        "inventory_2": inventory[2],
        "inventory_3": inventory[3],
        "cash_1": cash[1],
        "cash_2": cash[2],
        "cash_3": cash[3],
        "profit": profit
    }
    
    # Initial inventory and cash
    model.addConstr(inventory[1] == data["initial_inventory"])
    model.addConstr(cash[1] == data["initial_cash"])
    
    # Capacity constraint
    model.addConstr(inventory[1] + buy[1] <= data["capacity"])
    
    # Purchase and selling prices
    purchase_prices = {
        1: data["purchase_price"]["1"],
        2: data["purchase_price"]["2"],
        3: data["purchase_price"]["3"]
    }
    
    selling_prices = {
        1: data["selling_price"]["1"],
        2: data["selling_price"]["2"],
        3: data["selling_price"]["3"]
    }
    
    # Inventory and cash flow for each month
    model.addConstr(inventory[1] - buy[1] + sell[1] == inventory[2])
    model.addConstr(cash[1] - purchase_prices[1] * buy[1] == cash[2])
    model.addConstr(inventory[2] - buy[2] + sell[2] == inventory[3])
    model.addConstr(cash[2] - purchase_prices[2] * buy[2] == cash[3])
    model.addConstr(inventory[3] - buy[3] + sell[3] == data["final_inventory_required"])
    model.addConstr(cash[3] - purchase_prices[3] * buy[3] == cash[3])
    
    # Selling in the next month
    model.addConstr(sell[1] <= inventory[2])
    model.addConstr(sell[2] <= inventory[3])
    
    # Profit calculation
    model.addConstr(profit == 
                    (selling_prices[1] * sell[1] - purchase_prices[1] * buy[1] + 
                     selling_prices[2] * sell[2] - purchase_prices[2] * buy[2] + 
                     selling_prices[3] * sell[3] - purchase_prices[3] * buy[3]))
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "buy_1": variables["buy_1"].x,
            "buy_2": variables["buy_2"].x,
            "buy_3": variables["buy_3"].x,
            "sell_1": variables["sell_1"].x,
            "sell_2": variables["sell_2"].x,
            "sell_3": variables["sell_3"].x,
            "inventory_1": variables["inventory_1"].x,
            "inventory_2": variables["inventory_2"].x,
            "inventory_3": variables["inventory_3"].x,
            "cash_1": variables["cash_1"].x,
            "cash_2": variables["cash_2"].x,
            "cash_3": variables["cash_3"].x,
            "profit": variables["profit"].x
        }
        return {
            "status": "OPTIMAL",
            "objective": solution["profit"],
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }