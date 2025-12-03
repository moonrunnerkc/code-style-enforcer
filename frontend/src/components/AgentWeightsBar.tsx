// Author: Bradley R. Kinnard — trust scores, not robot numbers
import { AgentWeights } from '../api/apiClient'

interface AgentWeightsBarProps {
  weights: AgentWeights
}

const AGENT_CONFIG: Record<string, { color: string; label: string; description: string }> = {
  style: {
    color: '#3b82f6',
    label: 'Style',
    description: 'Formatting, consistency'
  },
  naming: {
    color: '#10b981',
    label: 'Naming',
    description: 'Variable & function names'
  },
  minimalism: {
    color: '#8b5cf6',
    label: 'Minimalism',
    description: 'Dead code, redundancy'
  },
  docstring: {
    color: '#f59e0b',
    label: 'Docstrings',
    description: 'Documentation coverage'
  },
  security: {
    color: '#ef4444',
    label: 'Security',
    description: 'Vulnerabilities, risks'
  }
}

function weightToTrust(weight: number): { label: string; emoji: string } {
  // 0.1 = min (very low trust), 1.0 = neutral, 2.0 = max (high trust)
  if (weight >= 1.5) return { label: 'High Trust', emoji: '🟢' }
  if (weight >= 1.1) return { label: 'Good', emoji: '🟢' }
  if (weight >= 0.9) return { label: 'Neutral', emoji: '⚪' }
  if (weight >= 0.5) return { label: 'Low', emoji: '🟡' }
  return { label: 'Very Low', emoji: '🔴' }
}

export default function AgentWeightsBar({ weights }: AgentWeightsBarProps) {
  const agents = Object.keys(weights)

  if (agents.length === 0) {
    return (
      <div className="agent-weights-bar empty">
        <h3>Agent Trust</h3>
        <p className="muted">Run an analysis to see trust levels</p>
      </div>
    )
  }

  return (
    <div className="agent-weights-bar">
      <div className="weights-header">
        <h3>Agent Trust</h3>
        <span className="weights-hint">Based on your feedback</span>
      </div>
      <div className="weights-grid">
        {agents.map(agent => {
          const config = AGENT_CONFIG[agent] || { color: '#6b7280', label: agent, description: '' }
          const trust = weightToTrust(weights[agent])
          const percentage = Math.round(((weights[agent] - 0.1) / 1.9) * 100) // 0.1-2.0 → 0-100%

          return (
            <div key={agent} className="weight-item" title={config.description}>
              <div className="weight-label">
                <span
                  className="agent-dot"
                  style={{ backgroundColor: config.color }}
                />
                {config.label}
              </div>
              <div className="weight-bar-container">
                <div
                  className="weight-bar"
                  style={{
                    width: `${percentage}%`,
                    backgroundColor: config.color
                  }}
                />
              </div>
              <span className="weight-value" title={`Raw: ${weights[agent].toFixed(2)}`}>
                {trust.emoji}
              </span>
            </div>
          )
        })}
      </div>
      <p className="weights-explainer">
        Accept suggestions → agent trust rises. Reject → trust falls.
      </p>
    </div>
  )
}
