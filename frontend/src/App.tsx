// Author: Bradley R. Kinnard — the main show
import { useCallback, useState } from 'react'
import { AgentWeights, analyzeCode, getWeights, submitFeedback, Suggestion } from './api/apiClient'
import AgentWeightsBar from './components/AgentWeightsBar'
import CodeEditor from './components/CodeEditor'
import SuggestionsList from './components/SuggestionsList'
import SummaryGenerator from './components/SummaryGenerator'
import WeightHistory from './components/WeightHistory'

type AnalysisState = 'idle' | 'loading' | 'done' | 'error'

export default function App() {
  const [code, setCode] = useState<string>('')
  const [language, setLanguage] = useState<string>('python')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [weights, setWeights] = useState<AgentWeights>({})
  const [analysisId, setAnalysisId] = useState<string>('')
  const [state, setState] = useState<AnalysisState>('idle')
  const [error, setError] = useState<string>('')
  const [fromCache, setFromCache] = useState<boolean>(false)

  const handleAnalyze = useCallback(async () => {
    if (!code.trim()) return

    setState('loading')
    setError('')

    try {
      const result = await analyzeCode(code, language)
      setSuggestions(result.suggestions)
      setWeights(result.agent_weights)
      setAnalysisId(result.analysis_id)
      setFromCache(result.from_cache)
      setState('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
      setState('error')
    }
  }, [code, language])

  const handleFeedback = useCallback(async (
    suggestionId: string,
    agent: string,
    accepted: boolean,
    rating: number
  ) => {
    if (!analysisId) return

    try {
      await submitFeedback(analysisId, suggestionId, agent, accepted, rating)
      // mark suggestion as rated in UI
      setSuggestions(prev => prev.map(s =>
        s.id === suggestionId ? { ...s, rated: true, accepted } : s
      ))
      // refresh weights after a short delay (worker needs time to process)
      setTimeout(async () => {
        try {
          const newWeights = await getWeights()
          setWeights(newWeights)
        } catch (e) {
          console.error('Failed to refresh weights:', e)
        }
      }, 1500)
    } catch (e) {
      console.error('Feedback failed:', e)
    }
  }, [analysisId])

  return (
    <div className="app">
      <header className="header">
        <h1>Code Style Enforcer</h1>
        <p className="tagline">Five AI agents critique your code. Your feedback teaches them.</p>
      </header>

      <main className="main">
        <div className="editor-section">
          <div className="editor-controls">
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              className="language-select"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
            </select>
            <button
              onClick={handleAnalyze}
              disabled={state === 'loading' || !code.trim()}
              className="analyze-btn"
            >
              {state === 'loading' ? 'Analyzing...' : 'Analyze Code'}
            </button>
          </div>

          <CodeEditor
            value={code}
            onChange={setCode}
            language={language}
          />
        </div>

        <div className="results-section">
          <AgentWeightsBar weights={weights} />
          <WeightHistory weights={weights} />

          {state === 'error' && (
            <div className="error-banner">{error}</div>
          )}

          {state === 'done' && (
            <>
              {fromCache && <div className="cache-badge">From cache</div>}
              <SuggestionsList
                suggestions={suggestions}
                onFeedback={handleFeedback}
              />
              <SummaryGenerator
                suggestions={suggestions}
                language={language}
              />
            </>
          )}

          {state === 'idle' && (
            <div className="empty-state">
              Paste some code and click Analyze to get started.
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
