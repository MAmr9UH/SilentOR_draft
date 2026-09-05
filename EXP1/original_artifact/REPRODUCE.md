# Reproducing EXP1

The original experiment runner is provided as `experiment/run_exp1.py`. It supports both Ollama and OpenAI providers. Exact model availability and credentials depend on the local environment.

Example interface:

```bash
python experiment/run_exp1.py --help
```

For paper comparisons, use the same 41 problems and 10 samples per problem for each model. The packaged result tables are the completed 410-row final sets used for analysis.
