import { useEffect, useMemo, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  Database,
  FlaskConical,
  Info,
  Play,
  RefreshCcw,
  ShieldCheck,
  SlidersHorizontal,
  Sprout,
} from 'lucide-react'
import { PopulationMap } from './components/PopulationMap'
import type {
  DemoPayload,
  ProductVariant,
  SimulationPayload,
  TwinDecision,
  TwinProfile,
} from './types'
import './App.css'

const API = {
  async demo(): Promise<DemoPayload> {
    const response = await fetch('/api/demo')
    if (!response.ok) {
      throw new Error(`Falha ao carregar a população (${response.status})`)
    }
    return response.json()
  },
  async simulate(
    engine: 'deterministic' | 'foundry',
    populationSize: number,
    seed: string,
    variants: ProductVariant[],
  ): Promise<SimulationPayload> {
    const response = await fetch('/api/simulations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        engine,
        population_size: populationSize,
        seed,
        variants,
      }),
    })
    if (!response.ok) {
      const body = await response.text()
      throw new Error(`Falha na simulação (${response.status}): ${body}`)
    }
    return response.json()
  },
}

const decisionLabels: Record<TwinDecision['choice'], string> = {
  accept: 'Aceita',
  consider: 'Considera',
  request_change: 'Pede ajuste',
  reject: 'Rejeita',
}

function trait(profile: TwinProfile, name: string): number {
  return profile.hypotheses.find((item) => item.name === name)?.score ?? 0
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

interface SliderProps {
  label: string
  value: number
  min: number
  max: number
  step: number
  format: (value: number) => string
  onChange: (value: number) => void
  disabled?: boolean
}

function ProductSlider({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
  disabled = false,
}: SliderProps) {
  return (
    <label className="slider-field">
      <span>
        {label}
        <strong>{format(value)}</strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function App() {
  const [data, setData] = useState<DemoPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [selectedVariantId, setSelectedVariantId] = useState('')
  const [selectedTwinId, setSelectedTwinId] = useState('')
  const [editedVariant, setEditedVariant] = useState<ProductVariant | null>(null)
  const [engine, setEngine] = useState<'deterministic' | 'foundry'>('deterministic')

  useEffect(() => {
    API.demo()
      .then((payload) => {
        setData(payload)
        const firstVariant = payload.simulation.variants[0]
        setSelectedVariantId(firstVariant.id)
        setEditedVariant(firstVariant)
        setSelectedTwinId(payload.profiles[0].id)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  const decisions = useMemo(
    () =>
      data?.simulation.decisions.filter(
        (decision) => decision.variant_id === selectedVariantId,
      ) ?? [],
    [data, selectedVariantId],
  )
  const decisionByTwin = useMemo(
    () => new Map(decisions.map((decision) => [decision.twin_id, decision])),
    [decisions],
  )
  const selectedProfile = data?.profiles.find((item) => item.id === selectedTwinId)
  const selectedDecision = decisionByTwin.get(selectedTwinId)
  const summary = data?.simulation.summaries.find(
    (item) => item.variant.id === selectedVariantId,
  )
  const accepted = summary?.decision_counts.accept ?? 0
  const considered = summary?.decision_counts.consider ?? 0
  const populationCount = data?.profiles.length ?? 0

  function chooseVariant(variant: ProductVariant) {
    if (running) return
    setSelectedVariantId(variant.id)
    setEditedVariant(variant)
  }

  function updateVariant(field: keyof ProductVariant, value: number) {
    if (running) return
    setEditedVariant((current) => (current ? { ...current, [field]: value } : current))
  }

  async function runCounterfactual() {
    if (!data || !editedVariant) return
    setRunning(true)
    setError(null)
    const requestEngine = engine
    const requestVariantId = editedVariant.id
    const requestedVariants = data.simulation.variants.map((variant) =>
      variant.id === editedVariant.id ? editedVariant : variant,
    )
    try {
      const response = await API.simulate(
        requestEngine,
        requestEngine === 'foundry' ? data.livePopulation : data.standardPopulation,
        data.manifest.seed,
        requestedVariants,
      )
      setData((current) =>
        current
          ? {
              ...current,
              manifest: response.manifest,
              profiles: response.profiles,
              simulation: response.simulation,
              evaluation: response.evaluation,
            }
          : current,
      )
      const returnedVariant =
        response.simulation.variants.find(
          (variant) => variant.id === requestVariantId,
        ) ?? response.simulation.variants[0]
      setSelectedVariantId(returnedVariant.id)
      setEditedVariant(returnedVariant)
      setSelectedTwinId(response.profiles[0]?.id ?? '')
      setEngine(requestEngine)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setRunning(false)
    }
  }

  if (loading) {
    return (
      <main className="status-page">
        <RefreshCcw className="spin" aria-hidden="true" />
        <h1>Preparando o mercado sintético Agro</h1>
        <p>Gerando eventos, features, hipóteses e decisões pareadas.</p>
      </main>
    )
  }

  if (!data || !editedVariant) {
    return (
      <main className="status-page error-state">
        <Info aria-hidden="true" />
        <h1>A experiência não pôde ser carregada</h1>
        <p>{error ?? 'A API não retornou o contrato esperado.'}</p>
      </main>
    )
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><Sprout aria-hidden="true" /></span>
          <div>
            <p>Microsoft Foundry · laboratório sintético</p>
            <h1>Agro Twin Lab</h1>
          </div>
        </div>
        <div className="disclaimer">
          <ShieldCheck aria-hidden="true" />
          <span><strong>Não é previsão.</strong> Cenários com clientes fictícios.</span>
        </div>
      </header>

      {error && <div className="error-banner" role="alert">{error}</div>}

      <section className="hero-panel">
        <div>
          <span className="eyebrow">Pergunte ao mercado digital antes do piloto real</span>
          <h2>Um segmento. 120 histórias. Decisões diferentes.</h2>
          <p>
            A mesma população Agro é reaplicada a cada configuração. Clique em um
            gêmeo para rastrear uso, hipótese comportamental e reação ao produto.
          </p>
        </div>
        <div className="flow" aria-label="Fluxo de hiperpersonalização">
          <span><Database /> Uso sintético</span>
          <i>→</i>
          <span><SlidersHorizontal /> Features</span>
          <i>→</i>
          <span><Bot /> Customer Twin</span>
          <i>→</i>
          <span><FlaskConical /> Cenário</span>
        </div>
      </section>

      <section className="metric-grid" aria-label="Resumo da simulação">
        <article className="metric-card">
          <Bot aria-hidden="true" />
          <div><strong>{populationCount}</strong><span>agentes Agro</span></div>
        </article>
        <article className="metric-card">
          <CheckCircle2 aria-hidden="true" />
          <div><strong>{populationCount ? Math.round((accepted / populationCount) * 100) : 0}%</strong><span>aceitam esta configuração</span></div>
        </article>
        <article className="metric-card">
          <SlidersHorizontal aria-hidden="true" />
          <div><strong>{populationCount ? Math.round(((accepted + considered) / populationCount) * 100) : 0}%</strong><span>aceitam ou consideram</span></div>
        </article>
        <article className="metric-card">
          <ShieldCheck aria-hidden="true" />
          <div><strong>{data.evaluation.passed ? `${Object.keys(data.evaluation.checks).length}/${Object.keys(data.evaluation.checks).length}` : 'Revisar'}</strong><span>gates de população</span></div>
        </article>
      </section>

      <section className="variant-tabs" aria-label="Variantes do produto">
        {data.simulation.variants.map((variant) => (
          <button
            type="button"
            key={variant.id}
            className={variant.id === selectedVariantId ? 'active' : ''}
            disabled={running}
            onClick={() => chooseVariant(variant)}
          >
            <span>{variant.name}</span>
            <small>{variant.description}</small>
          </button>
        ))}
      </section>

      <section className="workspace-grid">
        <aside className="control-panel card">
          <div className="section-title">
            <SlidersHorizontal aria-hidden="true" />
            <div><h3>Reconfigurar oferta</h3><p>Replay com a mesma população e seed.</p></div>
          </div>
          <div className="engine-toggle" aria-label="Motor da simulação">
            <button
              type="button"
              className={engine === 'deterministic' ? 'active' : ''}
              disabled={running}
              onClick={() => setEngine('deterministic')}
            >
              Baseline
            </button>
            <button
              type="button"
              className={engine === 'foundry' ? 'active' : ''}
              disabled={running || !data.foundryConfigured}
              onClick={() => setEngine('foundry')}
              title={
                data.foundryConfigured
                  ? 'Executar 24 Customer Twins no Foundry'
                  : 'Foundry não configurado neste ambiente'
              }
            >
              Foundry · 24
            </button>
          </div>
          <ProductSlider disabled={running} label="Tarifa mensal" value={editedVariant.monthly_fee_brl} min={0} max={120} step={1} format={(value) => `R$ ${value}`} onChange={(value) => updateVariant('monthly_fee_brl', value)} />
          <ProductSlider disabled={running} label="Cashback" value={editedVariant.cashback_rate} min={0} max={0.04} step={0.002} format={percent} onChange={(value) => updateVariant('cashback_rate', value)} />
          <ProductSlider disabled={running} label="Proteção" value={editedVariant.insurance_bundle} min={0} max={1} step={0.05} format={percent} onChange={(value) => updateVariant('insurance_bundle', value)} />
          <ProductSlider disabled={running} label="Carência" value={editedVariant.grace_days} min={0} max={180} step={15} format={(value) => `${value} dias`} onChange={(value) => updateVariant('grace_days', value)} />
          <ProductSlider disabled={running} label="Experiência digital" value={editedVariant.digital_service} min={0} max={1} step={0.05} format={percent} onChange={(value) => updateVariant('digital_service', value)} />
          <ProductSlider disabled={running} label="Acesso a especialista" value={editedVariant.advisor_access} min={0} max={1} step={0.05} format={percent} onChange={(value) => updateVariant('advisor_access', value)} />
          <button className="primary-button" type="button" disabled={running} onClick={runCounterfactual}>
            {running ? <RefreshCcw className="spin" /> : <Play />}
            {running
              ? 'Executando replay...'
              : `Executar contrafactual · ${engine === 'foundry' ? 'Foundry' : 'baseline'}`}
          </button>
          <p className="control-note"><Info /> O score é afinidade de cenário, não probabilidade de compra.</p>
        </aside>

        <section className="map-panel card">
          <div className="section-title split">
            <div>
              <h3>Mapa da população</h3>
              <p>Eixo X: autonomia digital · Eixo Y: preferência por liquidez</p>
            </div>
            <div className="legend">
              <span className="accept">Aceita</span>
              <span className="consider">Considera</span>
              <span className="change">Pede ajuste</span>
              <span className="reject">Rejeita</span>
            </div>
          </div>
          <PopulationMap
            profiles={data.profiles}
            decisions={decisionByTwin}
            selectedTwinId={selectedTwinId}
            onSelect={setSelectedTwinId}
          />
        </section>

        <aside className="detail-panel card">
          {selectedProfile && selectedDecision ? (
            <>
              <div className="twin-heading">
                <span className={`decision-badge ${selectedDecision.choice}`}>
                  {decisionLabels[selectedDecision.choice]}
                </span>
                <small>{selectedProfile.id}</small>
                <h3>{selectedProfile.behavioral_anchor}</h3>
                <p>Fit de cenário <strong>{Math.round(selectedDecision.fit_score)}/100</strong></p>
              </div>
              <div className="trait-list">
                {[
                  ['Liquidez', 'liquidity_preference'],
                  ['Preço', 'price_sensitivity'],
                  ['Digital', 'digital_autonomy'],
                  ['Proteção', 'risk_protection_preference'],
                  ['Recompensas', 'reward_affinity'],
                  ['Relacionamento', 'advisor_preference'],
                ].map(([label, key]) => (
                  <div className="trait-row" key={key}>
                    <span>{label}</span>
                    <div><i style={{ width: `${trait(selectedProfile, key) * 100}%` }} /></div>
                    <strong>{percent(trait(selectedProfile, key))}</strong>
                  </div>
                ))}
              </div>
              <div className="reason-list">
                <h4>Fatores da decisão</h4>
                {selectedDecision.reasons.map((reason) => (
                  <article key={`${reason.factor}-${reason.direction}`}>
                    <span className={reason.direction}>{reason.direction === 'positive' ? '+' : '−'}</span>
                    <div>
                      <strong>{reason.factor.replaceAll('_', ' ')}</strong>
                      <small>Evidências {reason.evidence_ids.join(', ')}</small>
                    </div>
                  </article>
                ))}
              </div>
              {selectedDecision.requested_changes.length > 0 && (
                <div className="requested-change">
                  <h4>O que faria este agente reconsiderar</h4>
                  <p>{selectedDecision.requested_changes[0]}</p>
                </div>
              )}
            </>
          ) : <p>Selecione um agente no mapa.</p>}
        </aside>
      </section>

      <section className="anchor-section card">
        <div className="section-title">
          <Sprout aria-hidden="true" />
          <div><h3>Mesmo segmento, respostas heterogêneas</h3><p>Distribuição por âncora comportamental exploratória.</p></div>
        </div>
        <div className="anchor-grid">
          {summary && Object.entries(summary.by_anchor).map(([anchor, counts]) => (
            <article key={anchor}>
              <h4>{anchor}</h4>
              <div className="stacked-bar" aria-label={`Decisões para ${anchor}`}>
                <i className="accept" style={{ flex: counts.accept }} />
                <i className="consider" style={{ flex: counts.consider }} />
                <i className="change" style={{ flex: counts.request_change }} />
                <i className="reject" style={{ flex: counts.reject }} />
              </div>
              <p>{counts.accept} aceitam · {counts.consider} consideram · {counts.request_change + counts.reject} resistem</p>
            </article>
          ))}
        </div>
      </section>

      <footer>
        <p>{data.simulation.disclaimer}</p>
        <span>Population digest {data.manifest.profile_digest.slice(0, 12)} · Seed {data.manifest.seed}</span>
      </footer>
    </main>
  )
}

export default App
