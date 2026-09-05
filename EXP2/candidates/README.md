# Candidate models

The controlled set contains 29 certified base models and 82 one-change mutants. The exact Python files are preserved here byte-for-byte from the supplied code artifact. Machine-readable labels and mutation certificates remain in [the source manifests](./manifests/).

- 29 correct bases
- 57 silent mutants: objective value unchanged, formulation requirement violated
- 25 loud mutants: objective value differs from the reference

[View the derived mutation manifest](../benchmark/mutation_manifest.csv).

## P1

- Base: [base_p1.py](./bases/base_p1.py)
- Mutant: [mut_p1_R5_domain.py](./mutants/mut_p1_R5_domain.py) — silent; domain_or_bound_error; R5
- Mutant: [mut_p1_R6_alloc11_lower_bound.py](./mutants/mut_p1_R6_alloc11_lower_bound.py) — silent; domain_or_bound_error; R6
- Mutant: [mut_p1_R7_objective.py](./mutants/mut_p1_R7_objective.py) — loud; objective_accounting_error; R7
## P3

- Base: [base_p3.py](./bases/base_p3.py)
- Mutant: [mut_p3_R7_s2_domain.py](./mutants/mut_p3_R7_s2_domain.py) — silent; domain_or_bound_error; R7
- Mutant: [mut_p3_R2_constraint.py](./mutants/mut_p3_R2_constraint.py) — silent; constraint_misspecification; R2
- Mutant: [mut_p3_R9_s2_objective.py](./mutants/mut_p3_R9_s2_objective.py) — loud; objective_accounting_error; R9
## P5

- Base: [base_p5.py](./bases/base_p5.py)
- Mutant: [mut_p5_R8_sel_calculus_domain.py](./mutants/mut_p5_R8_sel_calculus_domain.py) — silent; domain_or_bound_error; R8
- Mutant: [mut_p5_R3_constraint.py](./mutants/mut_p5_R3_constraint.py) — silent; constraint_misspecification; R3
- Mutant: [mut_p5_R9_sel_calculus_objective.py](./mutants/mut_p5_R9_sel_calculus_objective.py) — loud; objective_accounting_error; R9
## P6

- Base: [base_p6.py](./bases/base_p6.py)
- Mutant: [mut_p6_R_bal_5_constraint.py](./mutants/mut_p6_R_bal_5_constraint.py) — silent; constraint_misspecification; R_bal_5
- Mutant: [mut_p6_R_obj_x_4_1_objective.py](./mutants/mut_p6_R_obj_x_4_1_objective.py) — loud; objective_accounting_error; R_obj
## P8

- Base: [base_p8.py](./bases/base_p8.py)
- Mutant: [mut_p8_R_obj_s1_objective.py](./mutants/mut_p8_R_obj_s1_objective.py) — loud; objective_accounting_error; R_obj
## P9

- Base: [base_p9.py](./bases/base_p9.py)
- Mutant: [mut_p9_R_int_s0_domain.py](./mutants/mut_p9_R_int_s0_domain.py) — silent; domain_or_bound_error; R_int
- Mutant: [mut_p9_R_day1_constraint.py](./mutants/mut_p9_R_day1_constraint.py) — silent; constraint_misspecification; R_day1
- Mutant: [mut_p9_R_obj_s0_objective.py](./mutants/mut_p9_R_obj_s0_objective.py) — loud; objective_accounting_error; R_obj
## P10

- Base: [base_p10.py](./bases/base_p10.py)
- Mutant: [mut_p10_R_cloth_constraint.py](./mutants/mut_p10_R_cloth_constraint.py) — silent; constraint_misspecification; R_cloth
- Mutant: [mut_p10_R_labor_constraint.py](./mutants/mut_p10_R_labor_constraint.py) — silent; constraint_misspecification; R_labor
- Mutant: [mut_p10_R_obj_shirts_objective.py](./mutants/mut_p10_R_obj_shirts_objective.py) — loud; objective_accounting_error; R_obj
## P12

- Base: [base_p12.py](./bases/base_p12.py)
- Mutant: [mut_p12_R_cap_c1_constraint.py](./mutants/mut_p12_R_cap_c1_constraint.py) — silent; constraint_misspecification; R_capacity_open_link
- Mutant: [mut_p12_R_dem_s1_constraint.py](./mutants/mut_p12_R_dem_s1_constraint.py) — silent; constraint_misspecification; R_demand
- Mutant: [mut_p12_R_obj_y_c1_objective.py](./mutants/mut_p12_R_obj_y_c1_objective.py) — loud; objective_accounting_error; R_obj
## P17

- Base: [base_p17.py](./bases/base_p17.py)
- Mutant: [mut_p17_R_open_binary_y_c1_domain.py](./mutants/mut_p17_R_open_binary_y_c1_domain.py) — silent; domain_or_bound_error; R_open_binary
- Mutant: [mut_p17_R_cap_c1_constraint.py](./mutants/mut_p17_R_cap_c1_constraint.py) — silent; constraint_misspecification; R_capacity_open_link
- Mutant: [mut_p17_R_obj_y_c4_objective.py](./mutants/mut_p17_R_obj_y_c4_objective.py) — loud; objective_accounting_error; R_obj
## P22

- Base: [base_p22.py](./bases/base_p22.py)
- Mutant: [mut_p22_R_bottleneck_B_C_constraint.py](./mutants/mut_p22_R_bottleneck_B_C_constraint.py) — silent; constraint_misspecification; R_bottleneck_B_C
- Mutant: [mut_p22_R_bottleneck_C_E_constraint.py](./mutants/mut_p22_R_bottleneck_C_E_constraint.py) — silent; constraint_misspecification; R_bottleneck_C_E
- Mutant: [mut_p22_R_obj_z_objective.py](./mutants/mut_p22_R_obj_z_objective.py) — loud; objective_accounting_error; R_obj
## P23

- Base: [base_p23.py](./bases/base_p23.py)
- Mutant: [mut_p23_R_choose_one_combo_constraint.py](./mutants/mut_p23_R_choose_one_combo_constraint.py) — silent; constraint_misspecification; R_choose_one_combo
- Mutant: [mut_p23_R_weight_constraint.py](./mutants/mut_p23_R_weight_constraint.py) — silent; constraint_misspecification; R_weight
- Mutant: [mut_p23_R_obj_w_0_0_0_objective.py](./mutants/mut_p23_R_obj_w_0_0_0_objective.py) — loud; objective_accounting_error; R_obj
## P27

- Base: [base_p27.py](./bases/base_p27.py)
- Mutant: [mut_p27_R_mtz_2_3_constraint.py](./mutants/mut_p27_R_mtz_2_3_constraint.py) — silent; constraint_misspecification; R_mtz_2_3
- Mutant: [mut_p27_R_mtz_2_4_constraint.py](./mutants/mut_p27_R_mtz_2_4_constraint.py) — silent; constraint_misspecification; R_mtz_2_4
- Mutant: [mut_p27_R_obj_x_1_5_objective.py](./mutants/mut_p27_R_obj_x_1_5_objective.py) — loud; objective_accounting_error; R_obj
## P28

- Base: [base_p28.py](./bases/base_p28.py)
- Mutant: [mut_p28_R_integer_t_t_Verona_Genoa_domain.py](./mutants/mut_p28_R_integer_t_t_Verona_Genoa_domain.py) — silent; domain_or_bound_error; R_integer_t
- Mutant: [mut_p28_R_demand_Ancona_constraint.py](./mutants/mut_p28_R_demand_Ancona_constraint.py) — silent; constraint_misspecification; R_demand_Ancona
- Mutant: [mut_p28_R_obj_t_Verona_Venice_objective.py](./mutants/mut_p28_R_obj_t_Verona_Venice_objective.py) — loud; objective_accounting_error; R_obj
## P29

- Base: [base_p29.py](./bases/base_p29.py)
- Mutant: [mut_p29_R_task_A_constraint.py](./mutants/mut_p29_R_task_A_constraint.py) — silent; constraint_misspecification; R_task_A
- Mutant: [mut_p29_R_task_B_constraint.py](./mutants/mut_p29_R_task_B_constraint.py) — silent; constraint_misspecification; R_task_B
- Mutant: [mut_p29_R_obj_x_I_B_objective.py](./mutants/mut_p29_R_obj_x_I_B_objective.py) — loud; objective_accounting_error; R_obj
## P30

- Base: [base_p30.py](./bases/base_p30.py)
- Mutant: [mut_p30_Ryear2_misspec.py](./mutants/mut_p30_Ryear2_misspec.py) — silent; constraint_misspecification; R_year2_budget
- Mutant: [mut_p30_Rlimit2_misspec.py](./mutants/mut_p30_Rlimit2_misspec.py) — silent; constraint_misspecification; R_limit_project2
- Mutant: [mut_p30_Rfinal_misspec.py](./mutants/mut_p30_Rfinal_misspec.py) — silent; constraint_misspecification; R_final_balance
- Mutant: [mut_p30_Robj_objective.py](./mutants/mut_p30_Robj_objective.py) — loud; objective_accounting_error; R_obj
## P31

- Base: [base_p31.py](./bases/base_p31.py)
- Mutant: [mut_p31_R_demand_Donghai_1_constraint.py](./mutants/mut_p31_R_demand_Donghai_1_constraint.py) — silent; constraint_misspecification; R_demand_Donghai_1
- Mutant: [mut_p31_R_demand_Donghai_2_constraint.py](./mutants/mut_p31_R_demand_Donghai_2_constraint.py) — silent; constraint_misspecification; R_demand_Donghai_2
- Mutant: [mut_p31_R_obj_p3_shortfall_objective.py](./mutants/mut_p31_R_obj_p3_shortfall_objective.py) — loud; objective_accounting_error; R_obj
## P32

- Base: [base_p32.py](./bases/base_p32.py)
- Mutant: [mut_p32_R_route_precedence_pos_1_vat_2_constraint.py](./mutants/mut_p32_R_route_precedence_pos_1_vat_2_constraint.py) — silent; constraint_misspecification; R_route_precedence_pos_1_vat_2
- Mutant: [mut_p32_R_route_precedence_pos_1_vat_3_constraint.py](./mutants/mut_p32_R_route_precedence_pos_1_vat_3_constraint.py) — silent; constraint_misspecification; R_route_precedence_pos_1_vat_3
- Mutant: [mut_p32_R_obj_Cmax_objective.py](./mutants/mut_p32_R_obj_Cmax_objective.py) — loud; objective_accounting_error; R_obj
## P34

- Base: [base_p34.py](./bases/base_p34.py)
- Mutant: [mut_p34_R_integer_trucks_trucks_A_domain.py](./mutants/mut_p34_R_integer_trucks_trucks_A_domain.py) — silent; domain_or_bound_error; R_integer_trucks
- Mutant: [mut_p34_R_raw_A_constraint.py](./mutants/mut_p34_R_raw_A_constraint.py) — silent; constraint_misspecification; R_raw_A
- Mutant: [mut_p34_R_obj_trucks_A_objective.py](./mutants/mut_p34_R_obj_trucks_A_objective.py) — loud; objective_accounting_error; R_obj
## P35

- Base: [base_p35.py](./bases/base_p35.py)
- Mutant: [mut_p35_Rbinary_y_domain.py](./mutants/mut_p35_Rbinary_y_domain.py) — silent; domain_or_bound_error; R_binary_y
- Mutant: [mut_p35_Rcaplink1_linking.py](./mutants/mut_p35_Rcaplink1_linking.py) — silent; linking_or_logic_error; R_capacity_link_station_1
- Mutant: [mut_p35_Rdemand1_misspec.py](./mutants/mut_p35_Rdemand1_misspec.py) — silent; constraint_misspecification; R_demand_1
- Mutant: [mut_p35_Robj_objective.py](./mutants/mut_p35_Robj_objective.py) — loud; objective_accounting_error; R_obj
## P36

- Base: [base_p36.py](./bases/base_p36.py)
- Mutant: [mut_p36_R_binary_y_y_1_domain.py](./mutants/mut_p36_R_binary_y_y_1_domain.py) — silent; domain_or_bound_error; R_binary_y
- Mutant: [mut_p36_R_at_least_two_lengths_constraint.py](./mutants/mut_p36_R_at_least_two_lengths_constraint.py) — silent; constraint_misspecification; R_at_least_two_lengths
- Mutant: [mut_p36_R_obj_x_1_1_objective.py](./mutants/mut_p36_R_obj_x_1_1_objective.py) — loud; objective_accounting_error; R_obj
## P37

- Base: [base_p37.py](./bases/base_p37.py)
- Mutant: [mut_p37_R_capacity_1_constraint.py](./mutants/mut_p37_R_capacity_1_constraint.py) — silent; constraint_misspecification; R_capacity_1
- Mutant: [mut_p37_R_capacity_2_constraint.py](./mutants/mut_p37_R_capacity_2_constraint.py) — silent; constraint_misspecification; R_capacity_2
- Mutant: [mut_p37_R_profit_definition_profit_objective.py](./mutants/mut_p37_R_profit_definition_profit_objective.py) — loud; objective_accounting_error; R_profit_definition
## P38

- Base: [base_p38.py](./bases/base_p38.py)
- Mutant: [mut_p38_R_balance_II_10_constraint.py](./mutants/mut_p38_R_balance_II_10_constraint.py) — silent; constraint_misspecification; R_balance_II_10
- Mutant: [mut_p38_R_balance_II_11_constraint.py](./mutants/mut_p38_R_balance_II_11_constraint.py) — silent; constraint_misspecification; R_balance_II_11
- Mutant: [mut_p38_R_obj_prod_I_7_objective.py](./mutants/mut_p38_R_obj_prod_I_7_objective.py) — loud; objective_accounting_error; R_obj
## P39

- Base: [base_p39.py](./bases/base_p39.py)
- Mutant: [mut_p39_R_cmax_B_constraint.py](./mutants/mut_p39_R_cmax_B_constraint.py) — silent; constraint_misspecification; R_cmax_B
- Mutant: [mut_p39_R_prec_A_D_constraint.py](./mutants/mut_p39_R_prec_A_D_constraint.py) — silent; constraint_misspecification; R_prec_A_D
- Mutant: [mut_p39_R_obj_Cmax_objective.py](./mutants/mut_p39_R_obj_Cmax_objective.py) — loud; objective_accounting_error; R_obj
## P40

- Base: [base_p40.py](./bases/base_p40.py)
- Mutant: [mut_p40_R_max_labor_constraint.py](./mutants/mut_p40_R_max_labor_constraint.py) — silent; constraint_misspecification; R_max_labor
- Mutant: [mut_p40_R_max_skilled_constraint.py](./mutants/mut_p40_R_max_skilled_constraint.py) — silent; constraint_misspecification; R_max_skilled
- Mutant: [mut_p40_R_obj_skilled_t1_A_objective.py](./mutants/mut_p40_R_obj_skilled_t1_A_objective.py) — loud; objective_accounting_error; R_obj
## P41

- Base: [base_p41.py](./bases/base_p41.py)
- Mutant: [mut_p41_R_liquid_balance_constraint.py](./mutants/mut_p41_R_liquid_balance_constraint.py) — silent; constraint_misspecification; R_liquid_balance
- Mutant: [mut_p41_R_machine1_capacity_constraint.py](./mutants/mut_p41_R_machine1_capacity_constraint.py) — silent; constraint_misspecification; R_machine1_capacity
- Mutant: [mut_p41_R_obj_ending_solid_objective.py](./mutants/mut_p41_R_obj_ending_solid_objective.py) — loud; objective_accounting_error; R_obj
## P42

- Base: [base_p42.py](./bases/base_p42.py)
- Mutant: [mut_p42_R_demand_2_capability_constraint.py](./mutants/mut_p42_R_demand_2_capability_constraint.py) — silent; constraint_misspecification; R_demand_2
- Mutant: [mut_p42_R_availability_3_rhs_constraint.py](./mutants/mut_p42_R_availability_3_rhs_constraint.py) — silent; constraint_misspecification; R_availability_3
- Mutant: [mut_p42_R_availability_1_lhs_constraint.py](./mutants/mut_p42_R_availability_1_lhs_constraint.py) — silent; constraint_misspecification; R_availability_1
## P43

- Base: [base_p43.py](./bases/base_p43.py)
- Mutant: [mut_p43_R_integer_domain.py](./mutants/mut_p43_R_integer_domain.py) — silent; domain_or_bound_error; R_integer
## P44

- Base: [base_p44.py](./bases/base_p44.py)
- Mutant: [mut_p44_R_machine2_sequence_2_constraint.py](./mutants/mut_p44_R_machine2_sequence_2_constraint.py) — silent; constraint_misspecification; R_machine2_sequence_2
- Mutant: [mut_p44_R_first_machine_2_constraint.py](./mutants/mut_p44_R_first_machine_2_constraint.py) — silent; constraint_misspecification; R_first_machine_2
- Mutant: [mut_p44_R_machine1_sequence_2_constraint.py](./mutants/mut_p44_R_machine1_sequence_2_constraint.py) — silent; constraint_misspecification; R_machine1_sequence_2
## P45

- Base: [base_p45.py](./bases/base_p45.py)
- Mutant: [mut_p45_R_integer_domain.py](./mutants/mut_p45_R_integer_domain.py) — silent; domain_or_bound_error; R_integer
