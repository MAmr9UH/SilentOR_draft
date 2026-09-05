# EXP1 documentation validation

This release was checked against the preserved EXP1 reviewer files and the supplied `runs.zip` outputs.

## Checks completed

- 41 unique problem IDs are present.
- Four source result tables contain 410 rows each, for 1,640 evaluation records.
- **1,580 generated Python models** and **1,580 raw responses** are linked to their exact run IDs.
- Every copied generated Python file and raw response matches its source SHA-256 hash.
- `ORIGINAL_OUTPUT_MANIFEST.csv` contains one row for every evaluation record and records the output paths and hashes.
- All 60 records without supplied outputs have final verdict `code_failure`; none are marked unknown or unevaluated, and no absent model was reconstructed.
- All generated-model and checker pages begin with the full corresponding problem description.

## Source-output coverage

| Model | Python models | Raw responses | Code-failure runs without outputs |
|---|---:|---:|---:|
| Gemma 3 12B | 400 | 400 | 10 |
| Llama 3.3 70B | 410 | 410 | 0 |
| GPT-5 Nano | 410 | 410 | 0 |
| SIRL-Gurobi | 360 | 360 | 50 |

[EXP1 home](README.md)
