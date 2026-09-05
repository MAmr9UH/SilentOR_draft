# EXP1 final verdicts

For the GitHub presentation, every one of the 1,640 runs is assigned one of four final verdicts:

- **correct** - the generated formulation passed the EXP1 evaluation.
- **loud** - the objective value did not match the benchmark reference.
- **silent** - the objective matched, but the formulation failed one or more mathematical checks.
- **code_failure** - every other outcome, including execution, contract, schema, or provider failure.

The original labels are preserved byte-for-byte in `original_artifact/results/`. The CSVs in this folder are derived presentation views and retain the source label in `source_final_label` for auditing.

## Summary by model

| Model | Correct | Loud | Silent | Code failure | Total | Derived CSV |
|---|---:|---:|---:|---:|---:|---|
| Gemma 3 12B | 9 | 71 | 5 | 325 | 410 | [`gemma3_12b_final_verdicts.csv`](gemma3_12b_final_verdicts.csv) |
| Llama 3.3 70B | 145 | 60 | 24 | 181 | 410 | [`llama3_3_70b_final_verdicts.csv`](llama3_3_70b_final_verdicts.csv) |
| GPT-5 Nano | 258 | 37 | 40 | 75 | 410 | [`gpt5_nano_final_verdicts.csv`](gpt5_nano_final_verdicts.csv) |
| SIRL-Gurobi | 34 | 196 | 18 | 162 | 410 | [`sirl_gurobi_final_verdicts.csv`](sirl_gurobi_final_verdicts.csv) |
| **All systems** | **446** | **364** | **87** | **743** | **1640** | [`all_final_verdicts.csv`](all_final_verdicts.csv) |

## Browse by problem

| Problem | Scenario | Verdict summary |
|---|---|---|
| P01 | `red_star_plastic` | [Open](P01.md) |
| P02 | `or_course_selection` | [Open](P02.md) |
| P03 | `convenience_store_staffing` | [Open](P03.md) |
| P04 | `diet_min_cost` | [Open](P04.md) |
| P05 | `basketweavers_course_selection` | [Open](P05.md) |
| P06 | `china_railroad_car_relocation` | [Open](P06.md) |
| P07 | `multiproduct_production_inventory` | [Open](P07.md) |
| P08 | `fastfood_shift_scheduling` | [Open](P08.md) |
| P09 | `post_office_scheduling` | [Open](P09.md) |
| P10 | `gandhi_cloth_fixed_charge` | [Open](P10.md) |
| P11 | `food_manufacture_blending` | [Open](P11.md) |
| P12 | `supplylink_facility_location_5x5` | [Open](P12.md) |
| P13 | `marketflow_facility_location_4x6` | [Open](P13.md) |
| P14 | `logichain_facility_location_4x8` | [Open](P14.md) |
| P15 | `distribution_dynamics_facility_location_5x7` | [Open](P15.md) |
| P16 | `supplytek_facility_location_7x4` | [Open](P16.md) |
| P17 | `logisticorp_facility_location_7x9` | [Open](P17.md) |
| P18 | `supplychain_solutions_facility_location_6x7` | [Open](P18.md) |
| P19 | `logisphere_facility_location_5x9` | [Open](P19.md) |
| P20 | `supplychain_innovations_facility_location_7x5` | [Open](P20.md) |
| P21 | `post_office_5on2off_staffing` | [Open](P21.md) |
| P22 | `network_bandwidth_maximin_path_via_C` | [Open](P22.md) |
| P23 | `spare_component_reliability_budget_weight` | [Open](P23.md) |
| P24 | `container_packing_minimum_count_with_requirements` | [Open](P24.md) |
| P25 | `vrphtw_20_customer_euclidean_distance` | [Open](P25.md) |
| P26 | `university_computer_lab_weekly_staff_scheduling` | [Open](P26.md) |
| P27 | `seven_customer_symmetric_tsp_mtz` | [Open](P27.md) |
| P28 | `italian_empty_container_truck_transportation_mip` | [Open](P28.md) |
| P29 | `five_worker_four_task_assignment_min_hours` | [Open](P29.md) |
| P30 | `three_year_investment_cash_flow_lp` | [Open](P30.md) |
| P31 | `jieli_branch_professional_goal_planning_preference_city` | [Open](P31.md) |
| P32 | `fabric_dyeing_three_vat_flowshop_makespan` | [Open](P32.md) |
| P33 | `three_year_investment_cash_flow_lp_variant_500k` | [Open](P33.md) |
| P34 | `raw_material_two_warehouse_truck_dispatch_mip` | [Open](P34.md) |
| P35 | `fixed_charge_two_station_transshipment_mip` | [Open](P35.md) |
| P36 | `warehouse_contract_covering_binary_logic_mip` | [Open](P36.md) |
| P37 | `grain_trading_three_month_inventory_cash_flow_lp` | [Open](P37.md) |
| P38 | `two_product_july_december_inventory_production_storage_lp` | [Open](P38.md) |
| P39 | `project_scheduling_precedence_machine_rental_lp` | [Open](P39.md) |
| P40 | `three_task_method_selection_worker_mix_fixed_setup_mip` | [Open](P40.md) |
| P41 | `two_fertilizer_machine_inventory_max_ending_lp` | [Open](P41.md) |

[EXP1 home](../README.md)
