# LearnPulse interface design

## Screen contract

Audience: learners using a trusted local computer. The primary job is to choose a source, understand it, test recall, and see progress. Navigation has four persistent entries: Library, Study, Practice, Progress. The selected profile and real Ollama status remain visible in the header. Each screen includes a short technical "How it works" disclosure.

| Screen | Primary action | Required states |
| --- | --- | --- |
| Library | Upload or choose topic | Built-in topics, empty uploads, indexing, invalid file, delete confirmation |
| Study | Generate study guide | Ready, generating, error/retry, answer and source excerpts |
| Practice | Start quiz, answer, submit | Ready, generating, unanswered, submitting, graded review |
| Progress | Review performance | Empty history, mastery bars, recent attempts |

## Visual rules

- A dark green navigation rail frames a warm, light reading surface. Green marks actions and progress; amber marks model issues, and coral marks errors.
- System sans carries headings and reading text. Monospace is reserved for small technical metadata. Body text remains readable at 320 px.
- The Library leads with the lowest-mastery course topic, then shows a compact course list beside the upload area. Uploaded files appear directly below that area.
- One sidebar on desktop becomes horizontal navigation on narrow screens. Library, study, and quiz columns stack on smaller viewports.
- Borders and spacing create hierarchy; no simulated activity, oversized card grid, heavy motion, or marketing hero. Respect reduced-motion preference.
- Keyboard-operable controls, visible focus, semantic headings, labeled inputs, radio groups, and status errors with `role="alert"`.

The console style is for visual clarity; labels use learner language. Source similarity is a retrieval score, not a correctness guarantee.

## Reference decisions

- Readwise Reader's library workflow informed the separation between available course material and personal files.
- Linear's dense detail views informed compact rows, restrained borders, and persistent navigation.
- The app's own source and quiz flows determine content and actions; no reference branding or layout is copied.
