import type { TwinDecision, TwinProfile } from '../types'

interface Props {
  profiles: TwinProfile[]
  decisions: Map<string, TwinDecision>
  selectedTwinId: string
  onSelect: (twinId: string) => void
}

function trait(profile: TwinProfile, name: string): number {
  return profile.hypotheses.find((item) => item.name === name)?.score ?? 0
}

export function PopulationMap({
  profiles,
  decisions,
  selectedTwinId,
  onSelect,
}: Props) {
  const width = 720
  const height = 380
  const margin = 34

  return (
    <svg
      className="population-map"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Mapa de agentes Agro por autonomia digital e preferência por liquidez"
    >
      <line className="axis" x1={margin} y1={height - margin} x2={width - margin} y2={height - margin} />
      <line className="axis" x1={margin} y1={margin} x2={margin} y2={height - margin} />
      {[0.25, 0.5, 0.75].map((point) => (
        <g key={point}>
          <line className="gridline" x1={margin + point * (width - 2 * margin)} y1={margin} x2={margin + point * (width - 2 * margin)} y2={height - margin} />
          <line className="gridline" x1={margin} y1={margin + point * (height - 2 * margin)} x2={width - margin} y2={margin + point * (height - 2 * margin)} />
        </g>
      ))}
      <text className="axis-label" x={width / 2} y={height - 6}>Autonomia digital →</text>
      <text className="axis-label vertical" transform={`translate(12 ${height / 2}) rotate(-90)`}>Preferência por liquidez →</text>
      {profiles.map((profile) => {
        const x = margin + trait(profile, 'digital_autonomy') * (width - 2 * margin)
        const y = height - margin - trait(profile, 'liquidity_preference') * (height - 2 * margin)
        const decision = decisions.get(profile.id)
        const selected = profile.id === selectedTwinId
        return (
          <circle
            key={profile.id}
            cx={x}
            cy={y}
            r={selected ? 8 : 5}
            className={`agent-dot ${decision?.choice ?? 'consider'} ${selected ? 'selected' : ''}`}
            onClick={() => onSelect(profile.id)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') onSelect(profile.id)
            }}
            tabIndex={0}
            aria-label={`${profile.id}, ${profile.behavioral_anchor}, ${decision?.choice ?? 'sem decisão'}`}
          />
        )
      })}
    </svg>
  )
}
