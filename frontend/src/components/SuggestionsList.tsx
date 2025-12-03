// Author: Bradley R. Kinnard — from junior linter to staff engineer dashboard

import { useState } from 'react'
import { Suggestion } from '../api/apiClient'

interface SuggestionsListProps {
  suggestions: Suggestion[]
  onFeedback: (suggestionId: string, agent: string, accepted: boolean, rating: number) => void
}

// Impact levels sorted by priority (highest first)
const IMPACT_LEVELS = [
  { severity: 5, label: 'CRITICAL', color: '#dc2626', bgColor: '#fef2f2', borderColor: '#fecaca' },
  { severity: 4, label: 'Error', color: '#ef4444', bgColor: '#fef2f2', borderColor: '#fecaca' },
  { severity: 3, label: 'Warning', color: '#f59e0b', bgColor: '#fffbeb', borderColor: '#fde68a' },
  { severity: 2, label: 'Info', color: '#3b82f6', bgColor: '#eff6ff', borderColor: '#bfdbfe' },
  { severity: 1, label: 'Hint', color: '#6b7280', bgColor: '#f9fafb', borderColor: '#e5e7eb' },
] as const

function groupBySeverity(suggestions: Suggestion[]): Map<number, Suggestion[]> {
  const groups = new Map<number, Suggestion[]>()
  for (const level of IMPACT_LEVELS) {
    groups.set(level.severity, [])
  }
  for (const s of suggestions) {
    const sev = Math.min(5, Math.max(1, s.severity || 2))
    groups.get(sev)?.push(s)
  }
  return groups
}

export default function SuggestionsList({ suggestions, onFeedback }: SuggestionsListProps) {
  // CRITICAL starts expanded, everything else collapsed
  const [expanded, setExpanded] = useState<Set<number>>(new Set([5]))

  if (suggestions.length === 0) {
    return (
      <div className="no-suggestions">
        <span className="check-icon">✓</span>
        No suggestions. Your code looks good!
      </div>
    )
  }

  const groups = groupBySeverity(suggestions)

  const toggleGroup = (severity: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(severity)) {
        next.delete(severity)
      } else {
        next.add(severity)
      }
      return next
    })
  }

  return (
    <div className="suggestions-grouped">
      <div className="suggestions-header">
        <h2>Suggestions</h2>
        <span className="total-count">{suggestions.length} issues</span>
      </div>

      {IMPACT_LEVELS.map(level => {
        const items = groups.get(level.severity) || []
        if (items.length === 0) return null

        const isExpanded = expanded.has(level.severity)

        return (
          <ImpactGroup
            key={level.severity}
            level={level}
            items={items}
            isExpanded={isExpanded}
            onToggle={() => toggleGroup(level.severity)}
            onFeedback={onFeedback}
          />
        )
      })}
    </div>
  )
}

interface ImpactGroupProps {
  level: typeof IMPACT_LEVELS[number]
  items: Suggestion[]
  isExpanded: boolean
  onToggle: () => void
  onFeedback: (suggestionId: string, agent: string, accepted: boolean, rating: number) => void
}

function ImpactGroup({ level, items, isExpanded, onToggle, onFeedback }: ImpactGroupProps) {
  return (
    <div
      className="impact-group"
      style={{
        '--group-color': level.color,
        '--group-bg': level.bgColor,
        '--group-border': level.borderColor,
      } as React.CSSProperties}
    >
      <button
        className={`group-header ${isExpanded ? 'expanded' : ''}`}
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <span className="group-label" style={{ color: level.color }}>
          {level.label}
        </span>
        <span className="group-count" style={{ backgroundColor: level.color }}>
          {items.length}
        </span>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </button>

      {isExpanded && (
        <div className="group-content">
          {items.map(s => (
            <SuggestionCard key={s.id} suggestion={s} onFeedback={onFeedback} />
          ))}
        </div>
      )}
    </div>
  )
}

interface SuggestionCardProps {
  suggestion: Suggestion
  onFeedback: (suggestionId: string, agent: string, accepted: boolean, rating: number) => void
}

function SuggestionCard({ suggestion, onFeedback }: SuggestionCardProps) {
  const confidencePercent = Math.round(suggestion.confidence * 100)
  const confidenceClass = confidencePercent === 100 ? 'confidence-full' :
                          confidencePercent >= 90 ? 'confidence-high' :
                          confidencePercent >= 70 ? 'confidence-medium' : 'confidence-low'

  const handleAccept = () => {
    onFeedback(suggestion.id, suggestion.agent, true, 5)
  }

  const handleReject = () => {
    onFeedback(suggestion.id, suggestion.agent, false, 1)
  }

  return (
    <div className={`suggestion-card-v2 ${suggestion.rated ? 'rated' : ''}`}>
      <div className="card-main">
        <span className={`confidence-badge ${confidenceClass}`}>
          {confidencePercent}%
        </span>
        <span className="suggestion-message">{suggestion.message}</span>
      </div>

      <div className="card-meta">
        <span className="agent-tag">{suggestion.agent}</span>
        {suggestion.type && <span className="type-tag">{suggestion.type}</span>}
      </div>

      {!suggestion.rated ? (
        <div className="card-actions">
          <button className="action-btn accept" onClick={handleAccept} title="Accept suggestion">
            ✓ Accept
          </button>
          <button className="action-btn reject" onClick={handleReject} title="Reject suggestion">
            ✗ Reject
          </button>
        </div>
      ) : (
        <div className="card-rated">
          {suggestion.accepted ? '✓ Accepted' : '✗ Rejected'}
        </div>
      )}
    </div>
  )
}
