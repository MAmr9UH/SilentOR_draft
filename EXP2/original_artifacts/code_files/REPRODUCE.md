# Static validation and execution

Install the Python dependencies from `requirements.txt`. A working Gurobi installation and
license are needed only when executing the experiment.

Static release validation:

```bash
python -m compileall -q .
python freeze_manifest.py
python -m unittest discover -v
```

These commands do not execute the experiment.

After configuring gemma3:12b, Ollama, and Gurobi, the retained V42 experiment can be launched with:

```bash
python run_exp2.py --config track_b
```

No separate repository initialization command is required. The runner verifies the freeze
manifest and performs the retained V42 Ollama-context and full-prompt budget preflight before
the first evaluated model call.

That experiment command was intentionally not run during cleanup.
