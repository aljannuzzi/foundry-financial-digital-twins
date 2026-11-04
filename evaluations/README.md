# Evaluations

The local gate is executable without Azure:

```powershell
python -m financial_twins validate --count 120
```

It verifies:

- schema and bounds;
- evidence provenance;
- audit-sidecar isolation;
- exact reproducibility;
- anchor coverage;
- duplicate detection;
- trait-space diversity.

Foundry smoke evaluation is intentionally separate because it incurs model
usage. It should run on the 24-profile live panel before a demonstration and on
the 120-profile panel before a release.

The first cloud gates are:

- valid structured output;
- preserved twin and variant identifiers;
- 100% evidence-reference validity;
- zero unsupported sensitive-attribute inference;
- zero prohibited actions;
- repeated-choice agreement and aggregate variance report.

LLM-judge scores never replace deterministic contract checks or human review.

