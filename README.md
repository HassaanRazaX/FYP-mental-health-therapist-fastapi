# Deterministic Mental-Health Screening Platform (V6)

This is a **backend-only** FastAPI project for an educational mental-health **support + screening** app designed for a Flutter frontend.

## Safety & Non‑Negotiables (enforced by architecture)
- **No diagnosis** (educational screening only)
- **DSM-style logic is deterministic**
- **LLM never decides**: outcome, confidence, exclusions, progression, or disorder selection
- LLM is allowed only for:
  - **natural-language slot extraction**
  - **empathetic wording / paraphrasing**
- Stateless REST APIs, JWT-based auth, mobile friendly.

---

## What V6 changes (fixes the failures you observed)

### 1) Control inversion (critical)
**Rubrics do not ask questions.**  
Rubrics are **silent evaluators** that compute:
- what evidence exists
- what evidence is missing
- whether exclusions apply
- whether minimum evidence thresholds are met

A separate **Conversation Planner** decides what to ask next.

### 2) Conversation Readiness Layer (prevents “age too early” and other leaks)
The system tracks readiness: `UNREADY | WARMING | READY`.

When readiness is not `READY`, the system:
- **does not ask age**
- **does not ask DSM checklists**
- stays in **RELATIONAL** track (empathy + one gentle question)

### 3) Dual-track system
Each turn selects exactly one track:
- **RELATIONAL**: empathy/reflection/one gentle question
- **CLINICAL**: ask one focused question to resolve **one** missing slot

### 4) Report Readiness Gate (prevents early wrap-up)
Report is only offered if:
- rubric outcome is at least `POSSIBLE_MATCH`
- disorder YAML `interaction_requirements` are met (min turns, progress summary, closure ack)
- the user has received a progress summary and responded with an acknowledgment

### 5) Strict age gating (YAML hard rule)
If age is outside a disorder’s gating range:
- the disorder’s score is forced to **0**
- it cannot be selected as the top hypothesis

### 6) Debuggable response envelope for Flutter development
Each assistant response (in dev mode) includes a `meta` object:
- phase, readiness, track
- active hypotheses probabilities
- active disorder id (best hypothesis)
- missing slots
- rubric outcome + confidence
- next intent

Flutter can hide `meta` in production UI; it’s there for QA.

---

## Where the LLM is used (and what it is NOT allowed to do)

### Used in exactly 2 places
1) `app/llm/extractor.py`
- reads the user message
- extracts slot-like facts into JSON
- **does not** score, select disorder, set outcome, or set confidence

2) `app/llm/composer.py`
- writes a calm empathetic reply
- uses planner intent + optional question text
- ensures only one question max
- **does not** change state or decide what to ask next

### Not used for any deterministic logic
- disorder gating
- hypothesis scoring rules
- rubric evaluation
- report readiness
- slot state transitions

Those are deterministic Python modules.

---

## Project structure

```
app/
  api/
    routes/
      auth.py          # signup/login/refresh/logout
      users.py         # profile endpoints
      chat.py          # session chat + report
      feedback.py
      misc.py          # health/version/config
    schemas.py
    deps.py
  conversation/
    acts.py            # deterministic act router (rules)
    readiness.py       # readiness gate
    planner.py         # decides intent + track (does NOT know DSM)
    hypotheses.py      # EMA + gating + pick_top
    orchestrator.py    # glue (planner + extractor + rubric engine)
  rubric/
    loader.py          # loads YAML disorders
    eval.py            # safe deterministic expression evaluator
    engine.py          # rubric evaluator + missing slots
  disorders/           # YAML rubrics (no hardcoded disorder logic)
    *.yaml
  core/
    config.py
    db.py
    security.py
  services/
    image_uploads.py   # Cloudinary uploads for avatars
    oauth.py           # verify Google/Firebase identity tokens
  models.py
  main.py
docs/
  dsm_extracted_excerpt.txt  # excerpt text from the provided DSM PDF for traceability
tests/
  test_regressions.py
Dockerfile
requirements.txt
```

---

## API summary (Flutter contract)

### Auth
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/oauth/google` (Google ID token -> our JWT)
- `POST /auth/oauth/firebase` (Firebase ID token -> our JWT, recommended)
- `POST /auth/refresh`
- `POST /auth/logout` (idempotent)

### User profile
- `GET /users/me`
- `PATCH /users/me`
- `POST /users/me/avatar` (multipart)

### Chat
- `POST /chat/message` (creates session if `sessionId` is null)
- `GET /chat/sessions?page=1&limit=20`
- `GET /chat/sessions/{id}`
- `DELETE /chat/sessions/{id}`
- `DELETE /chat/sessions`
- `GET /chat/sessions/{id}/report`

### Other
- `GET /health`
- `GET /version`
- `GET /config/app`
- `POST /feedback`

---

## Running locally

### 1) Configure env
Copy:
```
cp .env.example .env
```
Set:
- `OPENAI_API_KEY`
- `JWT_SECRET`

For Cloudinary avatar uploads, set:
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- (optional) `CLOUDINARY_FOLDER`

For Google / Firebase login, set:
- `GOOGLE_CLIENT_ID` (required to verify Google ID tokens)
- `FIREBASE_PROJECT_ID` and `FIREBASE_SERVICE_ACCOUNT_JSON` (required to verify Firebase ID tokens)

If you want avatar uploads, set Cloudinary env vars:
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `CLOUDINARY_FOLDER` (optional)

If you want Google sign-in:
- `GOOGLE_CLIENT_ID` (required for /auth/oauth/google)

If you want Firebase token verification (recommended):
- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON` (service account JSON contents)

### 2) Run
```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3) Docker
```
docker build -t mh-v6 .
docker run -p 8000:8000 --env-file .env mh-v6
```

---

## Example use cases (maps to V6 requirements)

### Use case 1: Greeting should not trigger age
1. Send:
`POST /chat/message` with `"message": "hi"`
2. Response should:
- be warm
- ask what brings them in
- meta: `track=RELATIONAL`, `readiness != READY`

### Use case 2: Symptom disclosure -> empathy first, then gentle narrowing
1. `"message": "I feel very low lately"`
2. Response should:
- acknowledge
- ask one gentle question (not age)
- only after readiness reaches READY + presenting concern captured:
  - ask age softly (`ask_age_soft`)

### Use case 3: Adult cannot activate DMDD
Provide age 22; DMDD YAML has age_max=18.
Meta must show `dmdd` score = 0.

### Use case 4: No PROBABLE_MATCH from one symptom
Even if `depressed_mood=true`, without enough core criteria met + coverage:
- rubric outcome stays `INSUFFICIENT` or `POSSIBLE_MATCH`
- report gate remains closed

### Use case 5: FAQ interruption then resume
User asks: `"what is bipolar?"`
- system answers briefly
- then next turn continues with the planned intent (no duplicate question)

### Use case 6: Google sign-in -> issue JWT
Client obtains a Google **ID token** (via Flutter `google_sign_in`) and sends it to the backend:

```bash
curl -X POST http://127.0.0.1:8000/auth/oauth/google \
  -H 'Content-Type: application/json' \
  -d '{"idToken":"<GOOGLE_ID_TOKEN>"}'
```

Backend response is the same shape as /auth/login:
- `accessToken` + `refreshToken`
- `user` object

### Use case 7: Firebase sign-in (recommended) -> issue JWT
If you use Firebase Auth in Flutter (Google sign-in, Apple, etc.) you will get a **Firebase ID token**.
Send it to:

```bash
curl -X POST http://127.0.0.1:8000/auth/oauth/firebase \
  -H 'Content-Type: application/json' \
  -d '{"idToken":"<FIREBASE_ID_TOKEN>"}'
```

This keeps the backend stateless while letting Flutter use Firebase-provided providers.

---

## Updating DSM disorder YAMLs from the provided PDF
This repo includes `docs/dsm_extracted_excerpt.txt` as an extraction excerpt for traceability.

The YAMLs are structured to be extended:
- `slots`: types + signal phrases (no fixed question strings)
- `criteria`: deterministic rules using `count_true([...])` and comparisons
- `thresholds`: minimum evidence for PROBABLE
- `interaction_requirements`: min turns + closure gating

If you want a full, exact DSM transcription into YAML, add more pages to `docs/` extraction and update the YAML criteria/rules accordingly.

---

## Testing
Run:
```
pytest -q
```

The regression tests cover:
- greeting does not trigger age
- confusion forces relational track
- adult age gates out DMDD
- no probable match with insufficient evidence

---

## Notes for deployment
- SQLite for dev; set `DATABASE_URL` to Postgres in production.
- `/media/*` is local file serving for dev only; use object storage in production.
