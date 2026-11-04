# Responsible AI

[Back to the README](../README.md)

## Intended use

This system is a synthetic laboratory for:

- product and journey ideation;
- controlled counterfactual comparison;
- edge-case discovery;
- formulation of hypotheses for real research.

It is a reference implementation, not a production decision system.

## Prohibited use

Do not use it to:

- make underwriting, credit, limit, eligibility, or individual-pricing
  decisions;
- recommend adverse financial treatment;
- estimate revenue, adoption, or demand without external calibration;
- infer health, vulnerability, religion, ethnicity, or any protected attribute;
- target behavioral manipulation;
- act on behalf of a real customer;
- replace customer research, model risk, compliance, fair-lending review,
  security review, or independent validation.

## Summary impact assessment

| Risk | Mechanism | Mitigation |
|---|---|---|
| Plausibility mistaken for prediction | Convincing model language | Persistent warning and `not calibrated` status |
| Agro-segment stereotyping | Rigid behavioral anchors | Continuous traits, coverage design, and domain-expert review |
| Invented attributes | Unsupported model inference | Schema, evidence IDs, and ungrounded-attribute evaluation |
| Discriminatory proxy | Geography, channel, or production correlations | Segregated audit sidecar, matched pairs, and leakage probe |
| False precision | Numeric score | `fit_score`, never probability |
| Cross-profile memory | Shared sessions | Isolated execution per profile |
| Consequential use | Write/action tools | Read-only agent with no actions |
| Telemetry leakage | Full-content traces | IDs and hashes, redaction, and short retention |

## Lifecycle

The project follows `Identify → Measure → Mitigate → Operate`:

1. identify harms, affected parties, and misuse;
2. measure schema compliance, grounding, stability, fairness signals, and safety;
3. apply isolation, contracts, evaluations, and user-experience controls;
4. operate with inventory, logging, incident response, and revalidation.

## Revalidation

Rerun the complete applicable evaluation set when any of these changes:

- data source or distribution;
- Agro specification;
- generator or profile contract;
- model or deployment;
- prompt or agent definition;
- tools;
- evaluators;
- safety policy;
- intended use.

## Human review

Before any work involving real data, require approval appropriate to the
institution from:

- the accountable product owner;
- model risk management;
- privacy;
- compliance and fair lending;
- security;
- customer research;
- an Agro domain expert.

Foundry evaluators complement but never replace human judgment or independent
effective challenge.

## Banking model-risk caveats

This laboratory has no empirical behavioral calibration, outcome monitoring, or
approval for financial decisioning. Repeated outputs measure only model
stability. Fairness metrics over synthetic audit groups do not prove fairness,
nondiscrimination, or compliance in a real population.

An institution considering any changed use should establish inventory,
accountability, documented assumptions and limitations, validation independent
of development, change control, monitoring, and issue remediation. Referencing
the [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
or [Federal Reserve SR 11-7](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
does not constitute compliance with either.

See the [Simulation Card](simulation-card.md) for the current system record.
