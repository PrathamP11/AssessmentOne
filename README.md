# AI-First CRM HCP Module

This repository contains **Task 1** for the assignment: an **AI-first CRM HCP Log Interaction Screen** built with:

- **Frontend:** React + Redux Toolkit
- **Backend:** FastAPI
- **AI Agent Framework:** LangGraph
- **LLM Provider:** Groq (`llama-3.3-70b-versatile`)
- **Database:** PostgreSQL by default, SQLAlchemy-compatible with MySQL
- **Font:** Google Inter

The solution follows the video instruction closely:

- The screen is a **split layout**
- The **left panel is an interaction form**
- The **right panel is an AI assistant chat**
- The **form is meant to be controlled by the AI chat**, not manually filled by the user
- The app implements **five LangGraph tools**, including the two mandatory ones:
  - `log_interaction`
  - `edit_interaction`

## Repository Structure

```text
.
├── backend
│   ├── app
│   │   ├── agent.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   ├── state.py
│   │   └── tools.py
│   ├── .env.example
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── features
│   │   │   └── crmSlice.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── store.js
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## LangGraph Agent Design

The LangGraph agent is the orchestration layer between the sales rep's chat request and the CRM form state.

### Agent Responsibilities

1. Accept a natural-language interaction note from the rep.
2. Decide which tool should run.
3. Invoke the correct tool.
4. Update the structured form state.
5. Return a user-friendly assistant response summarizing what changed.

### Graph Flow

1. `route_tools`
   The LLM inspects the latest user message and current form state, then chooses the right tool.
2. `run_tools`
   The selected tool executes and updates the form state.
3. `respond`
   The LLM summarizes the updates and suggests a useful next step.

## Five LangGraph Tools

### 1. `log_interaction`

Mandatory tool.

Purpose:
Capture a new interaction from a free-text note such as:

`Today I met Dr. Smith and discussed Product X efficacy. The sentiment was positive and I shared the brochures.`

What it does:

- Extracts HCP name
- Extracts date and time
- Extracts discussion topics
- Extracts sentiment
- Extracts materials shared
- Populates the form automatically

### 2. `edit_interaction`

Mandatory tool.

Purpose:
Allow the rep to correct only a subset of the existing interaction without re-entering everything.

Example:

`Sorry, the name was actually Dr. John and the sentiment was negative.`

What it does:

- Detects corrected fields
- Updates only those fields
- Preserves untouched information

### 3. `add_materials`

Purpose:
Capture brochure/PDF/leave-behind sharing during the interaction.

Example:

`Also add that I shared the cardiology brochure and dosing guide.`

What it does:

- Appends items to `materials_shared`
- Keeps prior materials intact

### 4. `add_sample`

Purpose:
Track samples distributed to the HCP.

Example:

`I also distributed two starter packs of OncoBoost.`

What it does:

- Extracts product sample name
- Extracts quantity
- Appends structured sample entries

### 5. `suggest_follow_ups`

Purpose:
Generate the next best actions after the interaction.

Example:

`Suggest next steps for this doctor.`

What it does:

- Produces 3 concise follow-up recommendations
- Writes them to the `ai_suggested_follow_ups` section

## Frontend Notes

The React UI is intentionally aligned with the provided screenshot:

- Split page layout
- Left-side interaction form
- Right-side AI assistant
- Light clinical CRM visual style
- Inter font
- AI-controlled form behavior
- Voice-note summarization with consent and transcript fallback

Redux stores:

- current form state
- chat history
- latest tool execution results
- loading and error states
- background save status

## Backend Notes

The FastAPI backend exposes:

- `GET /health`
- `POST /api/agent/message`
- `POST /api/interactions`
- `GET /api/interactions`

The `POST` route accepts:

- the latest user message
- the current form state
- the chat history

It returns:

- updated form state
- assistant reply
- tool events used during that turn

After a successful AI update, the frontend automatically saves the latest interaction state to PostgreSQL using `POST /api/interactions`. There is no visible manual save button because the submitted UI is intended to stay close to the assignment screenshot and remain AI-first.

### Voice Note Flow

The `Summarize from Voice Note (Requires Consent)` button requests user consent before attempting browser speech recognition.

Flow:

1. The user consents to microphone capture.
2. The browser attempts speech-to-text.
3. The transcript is sent to the same LangGraph agent flow.
4. The AI extracts/summarizes details and updates the form.
5. If browser speech recognition fails, the UI provides a transcript fallback prompt.

The fallback still uses the same LangGraph and Groq backend path.

### SQL Persistence

The repository includes SQLAlchemy models in `backend/app/models.py` and real persistence endpoints for interaction records.

Current entities:

- `InteractionRecord`
- `SampleDistribution`

Default database:

- PostgreSQL
- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hcp_crm`

The same SQLAlchemy model layer can be pointed to MySQL by changing `DATABASE_URL` and installing a MySQL driver such as `pymysql`.

## Environment Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Create a PostgreSQL database named `hcp_crm` before starting the backend:

```bash
psql -U postgres
CREATE DATABASE hcp_crm;
\q
```

Set your Groq API key and database URL in `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hcp_crm
```

If the PostgreSQL password contains special characters such as `@`, URL-encode them in `DATABASE_URL`. For example, `@` becomes `%40`.

The assignment mentions `gemma2-9b-it`, but Groq has decommissioned that model. This project uses `llama-3.3-70b-versatile`, which the assignment also mentions as a Groq model to consider.

Run the API:

```bash
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional frontend env:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Demo Prompts for the Video

Use these during the recording to prove all 5 tools:

1. `Today I met Dr. Smith and discussed Product X efficacy. The sentiment was positive and I shared the brochures.`
2. `Sorry, the name was actually Dr. John and the sentiment was negative.`
3. `Also add that I shared the cardiology brochure and the dosage PDF.`
4. `I distributed 2 starter packs of OncoBoost.`
5. `Suggest follow-up actions for this doctor.`

Optional voice-note demo:

1. Click `Summarize from Voice Note (Requires Consent)`.
2. Give consent.
3. Speak or enter the transcript fallback.
4. Confirm the form updates through the same AI flow.

PostgreSQL verification query:

```sql
SELECT id, hcp_name, interaction_type, sentiment, created_at
FROM interaction_records;
```

Reset local demo data before recording:

```sql
TRUNCATE TABLE sample_distributions, interaction_records RESTART IDENTITY CASCADE;
```

## Important Implementation Note

The main path uses **LangGraph + Groq LLM** exactly as requested.

For developer convenience, a **demo fallback mode** is included when `GROQ_API_KEY` is missing, so the UI can still be shown during local build-out. In actual assessment/demo use, configure the Groq key so the real LLM path is active.

The form fields are intentionally read-only. This follows the video instruction that the left form should not be filled manually and should be controlled by the AI assistant.

## Suggested Submission Story

In your final demo/video, explain the app like this:

1. The right-side AI assistant is the only entry point for form updates.
2. LangGraph decides which tool to call from the user's message.
3. Each tool updates the structured CRM state.
4. The updated state is sent back to the React app and reflected in the left panel.
5. This supports a more natural workflow for pharma/medical field representatives.
