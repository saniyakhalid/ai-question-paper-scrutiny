# Architecture, Validation, and Acceptance Notes

## Runtime components

- `frontend/`: Vite + React client; `/api` is proxied to FastAPI in development.
- `backend/app/api/`: authentication, subjects/curriculum, uploads, reports, history, dashboard, and moderator workflows.
- `backend/app/services/`: document extraction, question parsing, subject validation, optional Gemini analysis, similarity, scoring, audit, and PDF export.
- `backend/app/rules/rule_engine.py`: deterministic checks.
- `backend/app/db/mongo.py`: PyMongo connection, collection indexes, IDs, and serialization.
- MongoDB is the running API's source of truth. There are legacy SQLAlchemy definitions under `backend/app/models/` and SQLite helpers under `backend/app/db/`; the FastAPI routes do not use them for live persistence. No SQL migrations are run by the current app.

## Upload and validation lifecycle

1. The authenticated upload endpoint looks up the selected subject by database ID.
2. It validates the extension, streams the file through the configured size limit, extracts text, and parses question structure.
3. Subject validation compares the selected subject's stored code/name/curriculum with extracted header and question evidence. Filenames are advisory only.
4. The paper receives `validation_status=VALID_MATCH`, `SUBJECT_MISMATCH`, `VALIDATION_INCONCLUSIVE`, or `DOCUMENT_PROCESSING_FAILED`. `validation_details` holds the outcome and reasons separately from `overall_score`.
5. Failed validation is retained as a paper/audit event and receives no report or score. An analysis request requires `VALID_MATCH` at both the API and pipeline layers. Moderator decisions are blocked until validation passes.
6. A preflight call to `/api/papers/validate-subject` does not retain the uploaded file; failed preflight evidence is written to an audit event. The final upload endpoint repeats validation and persists the paper outcome.

Validation details and the original upload are visible only through normal paper access checks. Faculty can access their own records; moderators/admins have broader review access.

### Validation statuses

| Status | Meaning | Scoring |
|---|---|---|
| `VALID_MATCH` | Evidence is sufficient to proceed with the selected subject | Allowed |
| `SUBJECT_MISMATCH` | Evidence supports another subject | Blocked |
| `VALIDATION_INCONCLUSIVE` | Evidence is insufficient to confirm a match | Blocked |
| `DOCUMENT_PROCESSING_FAILED` | Extraction or parsing failed | Blocked |
| `NOT_VALIDATED` | Legacy or manually created record has no passing validation result | Blocked |

## Reports and score interpretation

`ScrutinyReport` stores its upload ID/version, validation-independent analysis metadata, nullable overall score, score breakdown, evidence coverage, analysis mode/notice, and solving-time estimate. Rule results use `PASS`, `WARNING`, `FAIL`, or `NOT_EVALUATED`. Findings store a nullable confidence value; offline heuristics do not get an invented confidence percentage.

Category weights sum to 100: marks 15, numbering 5, Bloom 15, CO 15, units 20, grammar/quality 10, previous-paper similarity 10, time 5, and choice pattern 5. A passing check receives its full category weight, a warning half, and a failing check zero. Unavailable checks have a null score and do not increase evidence coverage. The report score is normalized over the evaluated weight and is withheld unless all four core checks (marks, numbering, CO, and unit coverage) are evaluable. The report always exposes evaluated weight as a percentage of the 100-point rubric.

Core and optional check availability:

- Marks needs a declared or configured total and identifiable question marks.
- Numbering uses parsed question identifiers.
- CO/unit compliance needs configured COs/units and configured thresholds; no CO/unit configuration does not become a 100% pass.
- Bloom compliance needs classified questions and an institution-configured Bloom target. Otherwise, classification is informational and compliance is `NOT_EVALUATED`.
- Time comparison needs a configured exam duration plus marks and a Bloom level for every analyzed question. The estimate uses the existing marks/Bloom heuristic and is not an observed duration.
- Choice compliance needs an explicit internal-choice requirement.
- Historical similarity runs only against previous questions belonging to the selected subject. TF-IDF matches are review flags and do not establish plagiarism.
- Offline grammar/quality is unavailable. Gemini results are only used when the configured provider returns a valid response.

## Security and data safety boundaries

- JWT keys have no committed fallback. Local default uses an ephemeral process key; configure a persistent `JWT_SECRET` for deployments.
- Public self-registration is faculty-only. Moderator/admin roles are not accepted from a public registration payload.
- API bearer tokens are accepted only in the Authorization header, not query strings.
- CORS origins are configured explicitly. Mongo connection strings are not logged.
- Tests force local MongoDB and a unique randomized test database/upload folder; only that generated database is dropped at the end of the test session.
- The root `.gitignore` excludes environment files, local upload contents, SQLite files, caches, and build output without deleting any of them.

## Current limitations

- In-paper duplicate detection is not implemented.
- There is no separately curated question-bank collection/comparison workflow.
- Similarity is TF-IDF/cosine text matching, not sentence embeddings or vector retrieval.
- OCR for scanned documents depends on local Tesseract support; unreadable files remain unscored.
- Gemini configuration is external. With no key/provider, the application reports offline heuristic mode rather than claiming an LLM analysis.
- Legacy records without a `VALID_MATCH` outcome cannot be reanalyzed through the current scoring endpoint; upload them again through the validated workflow if a new report is needed.
