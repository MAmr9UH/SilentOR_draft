import sys

def build_model(data: dict) -> tuple:
    from gurobipy import Model, GRB, quicksum

    nodes = data.get("nodes", [])
    bandwidth = data.get("bandwidth", {})
    big_m = data.get("big_m", 100)

    # Determine maximum possible bandwidth to set z upper bound
    max_w = 0
    for u in nodes:
        row = bandwidth.get(u, {})
        for v in nodes:
            w = row.get(v, 0)
            if w > max_w:
                max_w = w
    z_ub = max_w if max_w > 0 else big_m

    m = Model()
    m.setAttr("ModelName", "A_E_via_C_bottleneck_path")

    # Decision variables for positive-bandwidth arcs
    x = {}
    for u in nodes:
        for v in nodes:
            w = bandwidth.get(u, {}).get(v, 0)
            if w > 0:
                key = f"x_{u}_{v}"
                x[key] = m.addVar(vtype=GRB.BINARY, name=key)

    # Bottleneck variable
    z = m.addVar(lb=0.0, ub=z_ub, vtype=GRB.CONTINUOUS, name="z")

    m.update()

    # Helper sums for constraints
    def sum_out(v: str):
        terms = []
        row = bandwidth.get(v, {})
        for to in nodes:
            w = row.get(to, 0)
            if w > 0:
                key = f"x_{v}_{to}"
                if key in x:
                    terms.append(x[key])
        return quicksum(terms)

    def sum_in(v: str):
        terms = []
        for frm in nodes:
            w = bandwidth.get(frm, {}).get(v, 0)
            if w > 0:
                key = f"x_{frm}_{v}"
                if key in x:
                    terms.append(x[key])
        return quicksum(terms)

    # Flow constraints to ensure a single A->E path
    m.addConstr(sum_out("A") - sum_in("A") == 1)
    m.addConstr(sum_out("E") - sum_in("E") == -1)
    for n in nodes:
        if n not in ("A", "E"):
            m.addConstr(sum_out(n) - sum_in(n) == 0)

    # Degree limits to avoid loops / branching
    for n in nodes:
        m.addConstr(sum_out(n) <= 1)
        m.addConstr(sum_in(n) <= 1)

    # Enforce that the path passes through C
    m.addConstr(sum_in("C") == 1)
    m.addConstr(sum_out("C") == 1)

    # Link z with arc bottlenecks (big-M formulation)
    for u in nodes:
        for v in nodes:
            w = bandwidth.get(u, {}).get(v, 0)
            if w > 0:
                m.addConstr(z <= w + big_m * (1 - x[f"x_{u}_{v}"]))

    m.setObjective(z, GRB.MAXIMIZE)

    # Collect variables to return
    variables = {"z": z}
    for key, var in x.items():
        variables[key] = var

    return m, variables


def solve(data: dict) -> dict:
    # Build model
    model, variables = build_model(data)

    # Optimize
    model.optimize()
    model.update()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    # Build solution dict
    solution = {}
    solution["z"] = float(variables["z"].X)
    for key in [
        "x_A_B",
        "x_A_C",
        "x_A_E",
        "x_B_A",
        "x_B_C",
        "x_B_D",
        "x_B_E",
        "x_C_A",
        "x_C_D",
        "x_C_E",
        "x_D_A",
        "x_D_B",
        "x_D_C",
        "x_D_E",
        "x_E_B",
        "x_E_D",
    ]:
        solution[key] = float(variables[key].X)

    result = {
        "status": status_str,
        "objective": float(model.ObjVal) if model.ObjVal is not None else None,
        "solution": solution
    }

    return result


if __name__ == "__main__":
    # This module is intended to be imported, not run directly.
    # If needed for quick local tests, you can uncomment the following lines.
    # data = {
    #     "nodes": ["A","B","C","D","E"],
    #     "source": "A",
    #     "sink": "E",
    #     "required_service_node": "C",
    #     "bandwidth": {
    #         "A": {"A": 0, "B": 90, "C": 85, "D": 0, "E": 65},
    #         "B": {"A": 95, "B": 0, "C": 70, "D": 65, "E": 34},
    #         "C": {"A": 60, "B": 0, "C": 0, "D": 88, "E": 80},
    #         "D": {"A": 67, "B": 30, "C": 25, "D": 0, "E": 84},
    #         "E": {"A": 0, "B": 51, "C": 0, "D": 56, "E": 0}
    #     },
    #     "big_m": 100
    # }
    # print(solve(data))
    pass