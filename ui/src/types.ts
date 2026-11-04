export type DecisionChoice = 'accept' | 'reject' | 'consider' | 'request_change'

export interface TraitHypothesis {
  id: string
  name: string
  score: number
  confidence: number
  evidence_ids: string[]
}

export interface TwinProfile {
  id: string
  segment: 'Agro'
  behavioral_anchor: string
  profile_version: string
  observables: Array<{ id: string; name: string; value: number | string }>
  derived: Array<{ id: string; name: string; value: number | string }>
  hypotheses: TraitHypothesis[]
  current_products: string[]
  unknowns: string[]
}

export interface ProductVariant {
  id: string
  name: string
  description: string
  monthly_fee_brl: number
  cashback_rate: number
  insurance_bundle: number
  grace_days: number
  digital_service: number
  advisor_access: number
  reversibility: number
}

export interface TwinDecision {
  twin_id: string
  variant_id: string
  engine: 'deterministic' | 'foundry'
  choice: DecisionChoice
  fit_score: number
  confidence: number
  reasons: Array<{
    factor: string
    direction: 'positive' | 'negative' | 'neutral'
    evidence_ids: string[]
    contribution: number
  }>
  requested_changes: string[]
}

export interface VariantSummary {
  variant: ProductVariant
  decision_counts: Record<DecisionChoice, number>
  mean_fit_score: number
  by_anchor: Record<string, Record<DecisionChoice, number>>
}

export interface SimulationResult {
  run_id: string
  engine: 'deterministic' | 'foundry'
  population_digest: string
  variants: ProductVariant[]
  decisions: TwinDecision[]
  summaries: VariantSummary[]
  disclaimer: string
}

export interface DemoPayload {
  manifest: {
    count: number
    seed: string
    profile_digest: string
    anchor_counts: Record<string, number>
  }
  profiles: TwinProfile[]
  simulation: SimulationResult
  evaluation: {
    passed: boolean
    checks: Record<string, boolean>
  }
  foundryConfigured: boolean
  livePopulation: number
  standardPopulation: number
}

export interface SimulationPayload {
  manifest: DemoPayload['manifest']
  profiles: TwinProfile[]
  simulation: SimulationResult
  evaluation: DemoPayload['evaluation']
}
