import { useEffect, useRef, useState } from 'react'
import { BookOpen, BrainCircuit, ChartNoAxesCombined, ChevronRight, CircleHelp, FileText, LibraryBig, LoaderCircle, Plus, RefreshCw, Server, Trash2, Upload } from 'lucide-react'
import { api } from './services/api'
import type { Citation, Explanation, Material, ModelStatus, Quiz, QuizResult, StudentProfile, StudentSummary, Topic } from './types'

type Tab = 'library' | 'study' | 'practice' | 'progress'
const tabs: { id: Tab; label: string; icon: typeof LibraryBig }[] = [
  { id: 'library', label: 'Library', icon: LibraryBig },
  { id: 'study', label: 'Study', icon: BookOpen },
  { id: 'practice', label: 'Practice', icon: BrainCircuit },
  { id: 'progress', label: 'Progress', icon: ChartNoAxesCombined },
]

function HowItWorks({ children }: { children: React.ReactNode }) {
  return <details className="how"><summary><CircleHelp size={16} /> How it works</summary><p>{children}</p></details>
}

function Source({ citation }: { citation: Citation }) {
  return <article className="source">
    <div className="source-head"><strong>{citation.title}</strong><span>{citation.page ? `Page ${citation.page}` : 'Course section'} · {citation.similarity_score.toFixed(2)} similarity</span></div>
    <p>{citation.snippet}</p>
  </article>
}

export default function App() {
  const [tab, setTab] = useState<Tab>('library')
  const [students, setStudents] = useState<StudentSummary[]>([])
  const [studentId, setStudentId] = useState('')
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [topicId, setTopicId] = useState('')
  const [model, setModel] = useState<ModelStatus | null>(null)
  const [explanation, setExplanation] = useState<Explanation | null>(null)
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [result, setResult] = useState<QuizResult | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [newName, setNewName] = useState('')
  const [showNewProfile, setShowNewProfile] = useState(false)
  const activeProfileId = useRef('')
  const requestVersion = useRef(0)

  async function refreshLibrary(id: string) {
    const [nextProfile, nextTopics, nextMaterials] = await Promise.all([api.student(id), api.topics(id), api.materials(id)])
    if (activeProfileId.current !== id) return
    setProfile(nextProfile)
    setTopics(nextTopics)
    setMaterials(nextMaterials)
    setTopicId(current => nextTopics.some(topic => topic.topic_id === current) ? current : (nextTopics[0]?.topic_id || ''))
  }

  function switchProfile(id: string) {
    activeProfileId.current = id
    requestVersion.current++
    setStudentId(id)
    setExplanation(null); setQuiz(null); setResult(null); setBusy(''); setError('')
  }

  useEffect(() => {
    Promise.all([api.students(), api.status()]).then(([list, status]) => {
      setStudents(list); setModel(status); switchProfile(list[0]?.student_id || '')
    }).catch(err => setError(err.message))
  }, [])

  useEffect(() => {
    if (!studentId) return
    refreshLibrary(studentId).catch(err => setError(err.message))
  }, [studentId])

  function selectTopic(id: string) {
    requestVersion.current++
    setTopicId(id); setExplanation(null); setQuiz(null); setResult(null); setAnswers({}); setBusy(''); setError('')
  }

  async function createProfile(event: React.FormEvent) {
    event.preventDefault()
    if (!newName.trim()) return
    setBusy('profile'); setError('')
    try {
      const created = await api.createStudent(newName.trim())
      setStudents(await api.students()); switchProfile(created.student_id)
      setNewName(''); setShowNewProfile(false); setTab('library')
    } catch (err) { setError((err as Error).message) } finally { setBusy('') }
  }

  async function upload(file: File | undefined) {
    if (!file || !studentId) return
    setBusy('upload'); setError('')
    try {
      const item = await api.upload(studentId, file)
      if (activeProfileId.current === studentId) { await refreshLibrary(studentId); selectTopic(item.id) }
    } catch (err) { if (activeProfileId.current === studentId) setError((err as Error).message) } finally { setBusy('') }
  }

  async function remove(item: Material) {
    if (!window.confirm(`Delete “${item.title}” from this profile?`)) return
    setBusy('delete'); setError('')
    try { await api.deleteMaterial(item.id, studentId); if (activeProfileId.current === studentId) { if (topicId === item.id) selectTopic('recursion_call_stack'); await refreshLibrary(studentId) } }
    catch (err) { if (activeProfileId.current === studentId) setError((err as Error).message) } finally { setBusy('') }
  }

  async function generateStudy() {
    setBusy('study'); setError(''); setExplanation(null)
    const version = requestVersion.current
    try { const answer = await api.explain(studentId, topicId); if (requestVersion.current === version) setExplanation(answer) }
    catch (err) { if (requestVersion.current === version) setError((err as Error).message) } finally { if (requestVersion.current === version) setBusy('') }
  }

  async function startQuiz() {
    setBusy('quiz'); setError(''); setQuiz(null); setResult(null); setAnswers({})
    const version = requestVersion.current
    try { const nextQuiz = await api.quiz(studentId, topicId); if (requestVersion.current === version) setQuiz(nextQuiz) }
    catch (err) { if (requestVersion.current === version) setError((err as Error).message) } finally { if (requestVersion.current === version) setBusy('') }
  }

  async function submitQuiz() {
    if (!quiz || quiz.questions.some(question => answers[question.question_id] === undefined)) return
    setBusy('submit'); setError('')
    const version = requestVersion.current
    try { const grade = await api.submit(studentId, quiz, answers); if (requestVersion.current === version) { setResult(grade); const updated = await api.student(studentId); if (requestVersion.current === version) setProfile(updated) } }
    catch (err) { if (requestVersion.current === version) setError((err as Error).message) } finally { if (requestVersion.current === version) setBusy('') }
  }

  const selected = topics.find(topic => topic.topic_id === topicId)
  const topicName = (id: string) => topics.find(topic => topic.topic_id === id)?.title || id.replaceAll('_', ' ')
  const courseTopics = topics.filter(topic => topic.kind === 'built_in')
  const nextTopic = courseTopics.reduce<Topic | undefined>((lowest, topic) =>
    !lowest || (profile?.topic_mastery[topic.topic_id] ?? 0) < (profile?.topic_mastery[lowest.topic_id] ?? 0) ? topic : lowest, undefined)

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark"><BrainCircuit size={21} /></span><div><strong>LearnPulse</strong><small>YOUR STUDY SPACE</small></div></div>
      <div className="header-actions">
        <button className={`model-status ${model?.available ? 'ready' : 'offline'}`} onClick={() => api.status().then(setModel).catch(err => setError(err.message))} title="Refresh local model status"><Server size={15} /><span>{model?.available ? 'MODEL READY' : 'MODEL OFFLINE'}</span><RefreshCw size={13} /></button>
        <label className="profile-select"><span>PROFILE</span><select aria-label="Learner profile" value={studentId} onChange={event => switchProfile(event.target.value)}>{students.map(student => <option key={student.student_id} value={student.student_id}>{student.name}</option>)}</select></label>
        <button className="icon-button" title="Create local profile" aria-label="Create local profile" onClick={() => setShowNewProfile(value => !value)}><Plus size={18} /></button>
      </div>
    </header>
    {showNewProfile && <form className="create-profile" onSubmit={createProfile}><label htmlFor="profile-name">New local profile</label><input id="profile-name" autoFocus maxLength={80} value={newName} onChange={event => setNewName(event.target.value)} placeholder="Your name" /><button className="primary" disabled={busy === 'profile'}>Create profile</button></form>}
    <div className="layout">
      <aside className="sidebar"><div className="side-label">WORKSPACE</div><nav aria-label="Main navigation">{tabs.map(item => <button key={item.id} className={`nav-item ${tab === item.id ? 'active' : ''}`} aria-current={tab === item.id ? 'page' : undefined} onClick={() => { setTab(item.id); setError('') }}><item.icon size={18} /><span>{item.label}</span><ChevronRight size={14} /></button>)}</nav><div className="side-note">All data stays on this computer. Local profiles have no password protection.</div></aside>
      <main className="content">
        {error && <div className="alert" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
        {!model?.available && <div className="notice"><Server size={17} /><span>{model?.message || 'Checking Ollama…'} Study and Practice need the local model.</span><button onClick={() => api.status().then(setModel)}>Retry</button></div>}
        {tab === 'library' && <section>
          <div className="page-head"><div><div className="eyebrow">YOUR WORKSPACE</div><h1>Pick up where you left off.</h1><p>Study the course, or add material you want to understand.</p></div></div>
          {nextTopic && <div className="continue-strip"><div><span className="eyebrow">SUGGESTED NEXT</span><h2>{nextTopic.title}</h2><p>{profile?.topic_mastery[nextTopic.topic_id] === undefined ? 'A good place to begin.' : Math.round(profile.topic_mastery[nextTopic.topic_id]) + '% mastery so far. Keep going.'}</p></div><button className="primary" onClick={() => { selectTopic(nextTopic.topic_id); setTab('study') }}>Study topic <ChevronRight size={17} /></button></div>}
          <div className="library-columns">
            <div className="course-section"><div className="section-heading"><h2>Course topics</h2><span>{courseTopics.length} topics</span></div>
              <div className="topic-list">{courseTopics.map((topic, index) => <button key={topic.topic_id} className="topic-row" onClick={() => { selectTopic(topic.topic_id); setTab('study') }}><span className="topic-number">{String(index + 1).padStart(2, '0')}</span><span className="topic-details"><strong>{topic.title}</strong><small>{profile?.topic_mastery[topic.topic_id] === undefined ? 'Ready to explore' : Math.round(profile.topic_mastery[topic.topic_id]) + '% mastery'}</small></span><ChevronRight size={18} /></button>)}</div>
            </div>
            <div className="material-section"><div className="section-heading"><h2>Your material</h2><span>{materials.length} files</span></div>
              <div className="upload-panel"><div className="upload-symbol"><Upload size={23} /></div><h3>Add study material</h3><p>PDF, TXT, or Markdown, up to 10 MB. Your files stay with this profile.</p><label className={'upload-button ' + (busy === 'upload' ? 'disabled' : '')}>{busy === 'upload' ? 'Indexing?' : 'Choose a file'}<input type="file" accept=".pdf,.txt,.md" disabled={busy === 'upload' || !studentId} onChange={event => { upload(event.target.files?.[0]); event.target.value = '' }} /></label><small>Text-based PDFs only</small></div>
              {materials.length > 0 && <div className="material-list">{materials.map(item => <div className="material-row" key={item.id}><div className="file-icon"><FileText size={18} /></div><div className="material-name"><strong>{item.title}</strong><small>{item.filename} ? {item.pages ? item.pages + ' pages' : 'Text file'} ? {item.chunks} sections</small></div><button className="text-button" onClick={() => { selectTopic(item.id); setTab('study') }}>Study <ChevronRight size={15} /></button><button className="icon-button danger" title={'Delete ' + item.title} aria-label={'Delete ' + item.title} disabled={busy === 'delete'} onClick={() => remove(item)}><Trash2 size={17} /></button></div>)}</div>}
            </div>
          </div>
          <HowItWorks>Built-in topics come from the bundled curriculum. An upload is text-extracted, split into sections, embedded with FastEmbed, and indexed in local Qdrant under this profile. Each document becomes one study topic.</HowItWorks>
        </section>}
        {tab === 'study' && <section>
          <div className="page-head"><div><div className="eyebrow">02 / UNDERSTAND THE MATERIAL</div><h1>Study</h1><p>Build a source-grounded explanation for one topic.</p></div></div>
          <div className="action-bar"><label>TOPIC<select value={topicId} onChange={event => selectTopic(event.target.value)}>{topics.map(topic => <option key={topic.topic_id} value={topic.topic_id}>{topic.title}</option>)}</select></label><button className="primary" disabled={!topicId || !model?.available || busy === 'study'} onClick={generateStudy}>{busy === 'study' ? <LoaderCircle className="spin" size={17} /> : <BrainCircuit size={17} />}{busy === 'study' ? 'Generating…' : 'Generate study guide'}</button></div>
          {explanation ? <div className="study-grid"><article className="panel study-main"><div className="panel-meta">{selected?.title || explanation.topic_name} <span>OLLAMA · {explanation.model_name}</span></div><h2>Core idea</h2><p className="lead">{explanation.summary}</p><h3>Concept breakdown</h3><ol className="breakdown">{explanation.conceptual_breakdown.map((item, index) => <li key={index}>{item}</li>)}</ol>{explanation.code_example && <><h3>Example</h3><pre><code>{explanation.code_example}</code></pre></>}<h3>Watch for</h3><ul>{explanation.common_pitfalls.map((item, index) => <li key={index}>{item}</li>)}</ul><p className="disclaimer">{explanation.disclaimer}</p></article><div className="study-sources"><div className="section-heading"><h2>Sources</h2><span>{explanation.citations.length} excerpts</span></div>{explanation.citations.map(source => <Source key={source.chunk_id} citation={source} />)}</div></div> : <div className="empty tall"><BookOpen size={29} /><strong>{selected ? `Ready to study ${selected.title}` : 'Choose a topic'}</strong><p>Generate a guide to see an explanation alongside the excerpts it used.</p></div>}
          <HowItWorks>The backend searches only the selected topic and profile in Qdrant. It sends the matching excerpts to the installed Ollama model, validates its structured answer, and displays the excerpts for your review.</HowItWorks>
        </section>}
        {tab === 'practice' && <section>
          <div className="page-head"><div><div className="eyebrow">03 / TEST YOUR UNDERSTANDING</div><h1>Practice</h1><p>Answer three adaptive questions grounded in the selected source.</p></div></div>
          <div className="action-bar"><label>TOPIC<select value={topicId} onChange={event => selectTopic(event.target.value)}>{topics.map(topic => <option key={topic.topic_id} value={topic.topic_id}>{topic.title}</option>)}</select></label><button className="primary" disabled={!topicId || !model?.available || !!busy} onClick={startQuiz}>{busy === 'quiz' ? <LoaderCircle className="spin" size={17} /> : <Plus size={17} />}{busy === 'quiz' ? 'Preparing…' : quiz ? 'New quiz' : 'Start quiz'}</button></div>
          {quiz && <div className="quiz-layout"><div className="questions"><div className="quiz-meta">{quiz.difficulty.toUpperCase()} LEVEL <span>{quiz.questions.length} QUESTIONS · {quiz.model_name}</span></div>{quiz.questions.map((question, index) => <fieldset className="panel question" key={question.question_id} disabled={!!result}><legend><span>Q{String(index + 1).padStart(2, '0')}</span> {question.prompt}</legend>{question.options.map((option, optionIndex) => <label className={`option ${answers[question.question_id] === optionIndex ? 'chosen' : ''}`} key={optionIndex}><input type="radio" name={question.question_id} checked={answers[question.question_id] === optionIndex} onChange={() => setAnswers(previous => ({ ...previous, [question.question_id]: optionIndex }))} /><span>{String.fromCharCode(65 + optionIndex)}</span>{option}</label>)}</fieldset>)}{!result && <button className="primary submit" disabled={busy === 'submit' || quiz.questions.some(question => answers[question.question_id] === undefined)} onClick={submitQuiz}>{busy === 'submit' ? 'Grading…' : 'Submit answers'}</button>}</div>{result && <aside className="result-panel"><div className="eyebrow">RESULT</div><strong className="score">{Math.round(result.score_percentage)}%</strong><p>{result.correct_count} of {result.total_questions} correct</p><div className="result-tier">{result.previous_difficulty} <ChevronRight size={15} /> {result.new_difficulty}</div><p>{result.pedagogical_advice}</p><h3>Answer review</h3>{result.feedback.map((feedback, index) => <div className="feedback" key={feedback.question_id}><strong>{feedback.is_correct ? '✓' : '×'} Question {index + 1}</strong><p>{feedback.explanation}</p>{!feedback.is_correct && <p>{feedback.diagnosis}</p>}{feedback.source_chunk_id && <small>Source: {feedback.source_chunk_id}</small>}{quiz.citations.find(source => source.chunk_id === feedback.source_chunk_id) && <Source citation={quiz.citations.find(source => source.chunk_id === feedback.source_chunk_id)!} />}</div>)}</aside>}</div>}
          {!quiz && <div className="empty tall"><BrainCircuit size={29} /><strong>Ready for a quick check?</strong><p>Choose a topic and start a quiz. Your results will appear in Progress.</p></div>}
          <HowItWorks>Ollama generates three questions from retrieved source excerpts. The backend checks the question structure and source IDs, stores the answer key, grades each submission once, then updates mastery and difficulty. Verify AI-generated answers against the cited source.</HowItWorks>
        </section>}
        {tab === 'progress' && <section>
          <div className="page-head"><div><div className="eyebrow">04 / LEARNING RECORD</div><h1>Progress</h1><p>{profile?.student_id.startsWith('STU-') ? 'Sample results and new attempts' : 'Quiz results'} for {profile?.name || 'this profile'}.</p></div></div>
          <div className="stats"><div><small>OVERALL MASTERY</small><strong>{Math.round(profile?.overall_mastery || 0)}%</strong></div><div><small>CURRENT LEVEL</small><strong>{profile?.current_difficulty || 'Easy'}</strong></div><div><small>QUIZZES TAKEN</small><strong>{profile?.quiz_history.length || 0}</strong></div></div>
          <div className="progress-grid">
            <article className="panel"><div className="section-heading"><h2>Topic mastery</h2></div>{profile && Object.keys(profile.topic_mastery).length ? Object.entries(profile.topic_mastery).map(([id, value]) => <div className="mastery-row" key={id}><div><span>{topicName(id)}</span><strong>{Math.round(value)}%</strong></div><div className="track"><span style={{ width: `${value}%` }} /></div></div>) : <p className="muted">Complete a quiz to begin tracking mastery.</p>}</article>
            <article className="panel"><div className="section-heading"><h2>Recent attempts</h2></div>{profile?.quiz_history.length ? [...profile.quiz_history].sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 10).map(entry => <div className="history-row" key={entry.quiz_id}><div><strong>{topicName(entry.topic_id)}</strong><small>{new Date(entry.timestamp).toLocaleString()} · {entry.difficulty}</small></div><span>{Math.round(entry.score)}%</span></div>) : <p className="muted">No attempts yet. Start in Practice.</p>}</article>
          </div>
          <HowItWorks>Each submitted quiz is stored locally for this profile. Topic mastery combines the previous value with the latest score; scores below 60% lower difficulty, scores of 80% or more raise it, and other scores keep the level.</HowItWorks>
        </section>}
      </main>
    </div>
  </div>
}
