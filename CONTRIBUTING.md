# Contributing

Thank you for improving this non-production reference implementation. By
participating, follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Scope and data safety

- Use synthetic data only. Never contribute customer/personal data,
  credentials, secrets, tenant or subscription details, internal URLs, private
  logs, or confidential business information.
- Preserve the separation among observable, derived, hypothesis, scenario,
  response, and segregated audit layers.
- Do not describe scenario outputs as forecasts, probabilities, financial
  advice, or evidence that a product will succeed.
- Do not add consequential financial actions or production-approval claims.
- Report vulnerabilities through [SECURITY.md](SECURITY.md), not an issue.

## Proposing a change

Use the issue templates for a reproducible defect or bounded feature proposal.
Explain effects on contracts, Responsible AI, model risk, privacy, security,
cost, and intended use. Small, reviewable pull requests are preferred.

## Development

Follow the [Quickstart](README.md#quickstart), then run the checks relevant to
your change:

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m financial_twins validate --count 120

Push-Location ui
pnpm build
pnpm lint
Pop-Location

az bicep build --file infra/main.bicep
az bicep build --file infra/resources.bicep
```

Foundry evaluations incur cost and require an Azure environment. State whether
they were run; do not include environment identifiers or raw service output.

## Pull requests

1. Add or update tests for behavior changes.
2. Update the README, detailed documentation, and
   [Simulation Card](docs/simulation-card.md) when behavior, controls,
   limitations, models, or intended use changes.
3. Keep generated files, caches, local output, and Azure environment values out
   of the commit.
4. Complete the pull-request template with exact validation performed.
5. Address review feedback and keep the branch current before merge.

Submitting a pull request does not guarantee acceptance. Maintainers may decline
changes that expand the project beyond synthetic, non-decisioning research.
