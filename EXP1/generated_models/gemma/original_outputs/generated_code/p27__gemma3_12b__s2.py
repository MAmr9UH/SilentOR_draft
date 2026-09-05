import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    nodes = data["nodes"]
    start_node = data["start_node"]
    distance = data["distance"]
    mtz_big_m = data["mtz_big_m"]

    # Decision variables
    x = {}
    for i in nodes:
        for j in nodes:
            if i != j:
                x[f"{i},{j}"] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    u = {}
    for node in nodes[1:]:  # Exclude start node from MTZ variables
        u[node] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"u_{node}")

    # Objective function
    model.setObjective(
        gp.quicksum(distance[f"{i},{j}"] * x[f"{i},{j}"] for i in nodes for j in nodes if i != j),
        GRB.MINIMIZE
    )

    # Constraints
    # 1. Each node must have exactly one incoming and one outgoing arc (except start node)
    for node in nodes[1:]:
        model.addConstr(
            gp.quicksum(x[f"{i},{node}"] for i in nodes if i != node) == 1,
            name=f"in_out_{node}"
        )

    # 2. Start node must have one outgoing arc and no incoming arcs
    model.addConstr(
        gp.quicksum(x[f"{start_node},{j}"] for j in nodes if j != start_node) == 1,
        name="start_out"
    )

    # 3. End node must have one incoming arc and no outgoing arcs
    model.addConstr(
        gp.quicksum(x[f"{i},{start_node}"] for i in nodes if i != start_node) == 0,
        name="end_in"
    )

    # 4. Subtour elimination constraints (MTZ)
    for r in range(2, len(nodes)):  # Consider subtours of length 2 or more
        for subset in combinations(nodes[1:], r):
            model.addConstr(
                gp.quicksum(u[i] for i in subset) <= mtz_big_m * (len(subset) - 1),
                name=f"subtour_{subset}"
            )
            model.addConstr(
                gp.quicksum(x[f"{i},{j}"] for i in subset for j in subset if i != j) <= \
                len(subset) - 1,
                name=f"subtour_arcs_{subset}"
            )

    # 5. MTZ linking constraints
    for node1 in nodes[1:]:
        for node2 in nodes[1:]:
            if node1 != node2 and node2 not in get_predecessors(node1, x):
                model.addConstr(u[node1] >= u[node2] + 1, name=f"mtz_{node1}_{node2}")

    variables = {
        "x_1_2": x["1,2"],
        "x_1_3": x["1,3"],
        "x_1_4": x["1,4"],
        "x_1_5": x["1,5"],
        "x_1_6": x["1,6"],
        "x_1_7": x["1,7"],
        "x_2_1": x["2,1"],
        "x_2_3": x["2,3"],
        "x_2_4": x["2,4"],
        "x_2_5": x["2,5"],
        "x_2_6": x["2,6"],
        "x_2_7": x["2,7"],
        "x_3_1": x["3,1"],
        "x_3_2": x["3,2"],
        "x_3_4": x["3,4"],
        "x_3_5": x["3,5"],
        "x_3_6": x["3,6"],
        "x_3_7": x["3,7"],
        "x_4_1": x["4,1"],
        "x_4_2": x["4,2"],
        "x_4_3": x["4,3"],
        "x_4_5": x["4,5"],
        "x_4_6": x["4,6"],
        "x_4_7": x["4,7"],
        "x_5_1": x["5,1"],
        "x_5_2": x["5,2"],
        "x_5_3": x["5,3"],
        "x_5_4": x["5,4"],
        "x_5_6": x["5,6"],
        "x_5_7": x["5,7"],
        "x_6_1": x["6,1"],
        "x_6_2": x["6,2"],
        "x_6_3": x["6,3"],
        "x_6_4": x["6,4"],
        "x_6_5": x["6,5"],
        "x_6_7": x["6,7"],
        "x_7_1": x["7,1"],
        "x_7_2": x["7,2"],
        "x_7_3": x["7,3"],
        "x_7_4": x["7,4"],
        "x_7_5": x["7,5"],
        "x_7_6": x["7,6"],
        "u_2": u[2],
        "u_3": u[3],
        "u_4": u[4],
        "u_5": u[5],
        "u_6": u[6],
        "u_7": u[7]
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "x_1_2": float(variables["x_1_2"].X),
        "x_1_3": float(variables["x_1_3"].X),
        "x_1_4": float(variables["x_1_4"].X),
        "x_1_5": float(variables["x_1_5"].X),
        "x_1_6": float(variables["x_1_6"].X),
        "x_1_7": float(variables["x_1_7"].X),
        "x_2_1": float(variables["x_2_1"].X),
        "x_2_3": float(variables["x_2_3"].X),
        "x_2_4": float(variables["x_2_4"].X),
        "x_2_5": float(variables["x_2_5"].X),
        "x_2_6": float(variables["x_2_6"].X),
        "x_2_7": float(variables["x_2_7"].X),
        "x_3_1": float(variables["x_3_1"].X),
        "x_3_2": float(variables["x_3_2"].X),
        "x_3_4": float(variables["x_3_4"].X),
        "x_3_5": float(variables["x_3_5"].X),
        "x_3_6": float(variables["x_3_6"].X),
        "x_3_7": float(variables["x_3_7"].X),
        "x_4_1": float(variables["x_4_1"].X),
        "x_4_2": float(variables["x_4_2"].X),
        "x_4_3": float(variables["x_4_3"].X),
        "x_4_5": float(variables["x_4_5"].X),
        "x_4_6": float(variables["x_4_6"].X),
        "x_4_7": float(variables["x_4_7"].X),
        "x_5_1": float(variables["x_5_1"].X),
        "x_5_2": float(variables["x_5_2"].X),
        "x_5_3": float(variables["x_5_3"].X),
        "x_5_4": float(variables["x_5_4"].X),
        "x_5_6": float(variables["x_5_6"].X),
        "x_5_7": float(variables["x_5_7"].X),
        "x_6_1": float(variables["x_6_1"].X),
        "x_6_2": float(variables["x_6_2"].X),
        "x_6_3": float(variables["x_6_3"].X),
        "x_6_4": float(variables["x_6_4"].X),
        "x_6_5": float(variables["x_6_5"].X),
        "x_6_7": float(variables["x_6_7"].X),
        "x_7_1": float(variables["x_7_1"].X),
        "x_7_2": float(variables["x_7_2"].X),
        "x_7_3": float(variables["x_7_3"].X),
        "x_7_4": float(variables["x_7_4"].X),
        "x_7_5": float(variables["x_7_5"].X),
        "x_7_6": float(variables["x_7_6"].X),
        "u_2": float(variables["u_2"].X),
        "u_3": float(variables["u_3"].X),
        "u_4": float(variables["u_4"].X),
        "u_5": float(variables["u_5"].X),
        "u_6": float(variables["u_6"].X),
        "u_7": float(variables["u_7"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }


from itertools import combinations

def get_predecessors(node, x):
  predecessors = []
  for i in range(1, 8):
    if i != node:
      key = f"{i},{node}"
      if key in x and x[key].X == 1:
        predecessors.append(i)
  return predecessors