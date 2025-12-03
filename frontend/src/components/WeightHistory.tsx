// Author: Bradley R. Kinnard — proof the RL loop is alive

import { useEffect, useState } from 'react'
import { AgentWeights } from '../api/apiClient'

interface WeightChange {
  agent: string
  oldValue: number
  newValue: number
  direction: 'up' | 'down'
  timestamp: Date
}

interface WeightHistoryProps {
  weights: AgentWeights
}

const AGENT_LABELS: Record<string, string> = {
  style: 'Style',
  naming: 'Naming',
  minimalism: 'Minimalism',
  docstring: 'Docstrings',
  security: 'Security'
}

export default function WeightHistory({ weights }: WeightHistoryProps) {
  const [history, setHistory] = useState<WeightChange[]>([])
  const [prevWeights, setPrevWeights] = useState<AgentWeights>({})

  useEffect(() => {
    // Skip first render (no previous weights to compare)
    if (Object.keys(prevWeights).length === 0) {
      setPrevWeights(weights)
      return
    }

    // Detect changes
    const changes: WeightChange[] = []
    for (const [agent, newValue] of Object.entries(weights)) {
      const oldValue = prevWeights[agent]
      if (oldValue !== undefined && Math.abs(newValue - oldValue) > 0.001) {
        changes.push({
          agent,
          oldValue,
          newValue,
          direction: newValue > oldValue ? 'up' : 'down',
          timestamp: new Date()
        })
      }
    }

    if (changes.length > 0) {
      setHistory(prev => [...changes, ...prev].slice(0, 10)) // keep last 10
    }

    setPrevWeights(weights)
  }, [weights, prevWeights])

  if (history.length === 0) {
    return null
  }

  return (
    <div className="weight-history">
      <div className="history-header">
        <span className="history-title">📊 Learning Activity</span>
        <button
          className="clear-btn"
          onClick={() => setHistory([])}
          title="Clear history"
        >
          Clear
        </button>
      </div>
      <div className="history-list">
        {history.map((change, i) => (
          <div key={i} className={`history-item ${change.direction}`}>
            <span className="change-icon">
              {change.direction === 'up' ? '↑' : '↓'}
            </span>
            <span className="change-text">
              <strong>{AGENT_LABELS[change.agent] || change.agent}</strong>
              {' '}
              {change.direction === 'up'
                ? 'trust increased'
                : 'trust decreased'}
            </span>
            <span className="change-detail">
              {(change.oldValue * 100).toFixed(0)}% → {(change.newValue * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
      <p className="history-explainer">
        When you accept suggestions, that agent gains trust. Reject = loses trust.
      </p>
    </div>
  )
}
