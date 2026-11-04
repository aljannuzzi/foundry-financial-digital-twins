# Methodology

[Back to the README](../README.md)

## Objective

The laboratory compares treatments over a controlled fictional population. It
is designed to answer:

- which profiles resist each configuration;
- which objections recur;
- which scenario parameters change decisions;
- which hypotheses deserve validation with real customers.

It does not answer how much a product will sell.

## Population generation

The generator is deterministic and does not use a large language model. For
each field:

```text
spec_hash = SHA256(canonical_json(segment_spec))
field_seed = HMAC_SHA256(master_seed,
                         spec_hash || profile_id || field_name)
value = conditional_draw(field_seed, parent_features)
```

Adding a field does not perturb every earlier draw. The manifest records the
seed, specification hash, generator version, profile version, profile digest,
and artifact digest.

### Coverage panel

The 120 profiles form a coverage panel with 15 profiles per behavioral anchor.
It maximizes diversity for proposition testing; it does not represent the
real-world prevalence of each type in the Agro market.

A representative panel would require reliable aggregate statistics or
consented microdata plus independent validation of sampling and weights.

## Synthetic events

Each profile receives 12 months of:

- deposits, expenses, and balances;
- card spending and Agro categories;
- digital sessions and specialist contacts;
- insurance coverage;
- rewards;
- offers shown and accepted;
- overdraft pressure;
- support cases and unresolved items.

Events are coherent with a segregated latent record used only to test the
generator. The profile pipeline recomputes features without access to that
latent record.

## Features and hypotheses

Observable features include:

- cash-flow seasonality;
- balance volatility;
- digital share;
- protection gap;
- rewards redemption;
- offer response;
- relationship intensity;
- overdraft pressure;
- liquidity buffer;
- service friction.

The derived feature is:

- working-capital pressure.

Uncertain hypotheses are:

- liquidity preference;
- price sensitivity;
- digital autonomy;
- protection preference;
- rewards affinity;
- advisor preference;
- novelty openness;
- reversibility preference.

Every hypothesis has status `uncertain`. It is not a psychological diagnosis or
an observed fact.

## Customer Twin protocol

The agent:

1. receives only the allowed profile and scenario;
2. preserves `unknown`;
3. does not infer a protected attribute or vulnerability;
4. returns `accept`, `consider`, `request_change`, or `reject`;
5. uses a scenario `fit_score`, never a purchase probability;
6. cites only evidence IDs supplied in the request;
7. exposes missing information and unsupported inferences;
8. has no write tool or consequential-action capability.

The runtime validates the response schema, twin ID, variant ID, engine
provenance, and cited evidence IDs. An invalid provider response fails the run;
it is not replaced with a deterministic result.

## Paired comparison

All variants receive the same profiles and population manifest. Offer order
should be counterbalanced in agentic experiments. Aggregate changes are
attributable to the treatment only within the simulation; they do not establish
real-world causality or demand.

## MVP gates

These thresholds are engineering gates, not regulatory safe harbors.

| Area | Metric | Gate |
|---|---|---|
| Schema | Pydantic validation | 100% |
| Duplication | Profile hash | 0 duplicates |
| Coverage | Behavioral anchors | 8/8 |
| Provenance | Evidence IDs | 100% valid |
| Layering | Audit/latent values in agent payload | 0 leaks |
| Reproducibility | Digest | Byte-identical |
| Diversity | Trait distance | Mean > 0.15 |
| Hard rules | Impossible combinations | 0 |
| Placebo | Irrelevant ID/name/order changes | Aggregate change ≤ 2 percentage points |
| LLM stability | Repeated choice | Agreement ≥ 85% |
| Sensitivity | Directional tests | ≥ 90% |
| Safety | Personal data or consequential action | 0 |
| Calibration | Real outcome | `not calibrated` |

The local `validate` command implements population, artifact, provenance,
isolation, integrity, reproducibility, coverage, duplicate, bounds, structure,
and diversity checks. Placebo, repeated-LLM, directional-sensitivity, and
agent-safety rows require separate evaluation runs; they are acceptance targets,
not claims about checks performed by the local command.

For later studies:

- at least 10 repetitions per profile;
- hierarchical bootstrap with at least 1,000 resamples;
- Krippendorff's alpha ≥ 0.80;
- aggregate rerun difference ≤ 5 percentage points;
- placebo individual flip rate ≤ 5%.

Intervals measure simulation stability, not uncertainty about real customers.

## Fairness and proxy leakage

The audit sidecar stays outside agent context. It enables:

1. counterfactuals that change only one synthetic protected tag;
2. proxy tests involving geography, language, or production type;
3. comparison of inconsistency, refusal, and error by group;
4. a probe that attempts to predict audit attributes from output.

Proposed gates are:

- matched-pair gap ≤ 3 percentage points;
- flip rate ≤ 5%;
- reportable performance gap ≤ 5 percentage points;
- AUC increase from adding outputs ≤ 0.02.

No single metric proves fairness or legal compliance.

## Future calibration

Converting scenario signals into a predictive model would require:

1. preregistered hypotheses;
2. an untouched holdout;
3. mapped observable outcomes;
4. comparison with a simple baseline;
5. Brier score, expected calibration error, and calibration slope;
6. independent effective challenge;
7. documented approval of the changed intended use.

Until that work is completed, every report remains `not calibrated`.
