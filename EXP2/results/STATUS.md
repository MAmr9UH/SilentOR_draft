# Result completeness

- Gemma Direct Detector: 111/111 rows; complete.
- Gemma Detector + Requirement List: 111/111 rows; complete.
- Gemma SilentOR: **95/111 rows recorded; incomplete**. Its reported policy score uses 90 valid rows after five recorded rows were excluded. [The 16 absent candidates are listed here](./gemma/silentor/missing_candidates.csv).

No missing or invalid candidate is silently counted as a successful evaluation.
