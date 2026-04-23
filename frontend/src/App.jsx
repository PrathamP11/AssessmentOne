import { useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import {
  addUserMessage,
  receiveAgentResult,
  receiveSaveResult,
  setAgentError,
  setAgentPending,
  setSaveError
} from "./features/crmSlice";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const dispatch = useDispatch();
  const { formState, messages, status, toolEvents, error } = useSelector((state) => state.crm);
  const [draft, setDraft] = useState("");
  const [voiceStatus, setVoiceStatus] = useState("idle");
  const recognitionRef = useRef(null);

  const transcriptHistory = messages
    .filter((message) => message.variant !== "hint")
    .map((message) => ({ role: message.role, content: message.content }));

  const saveInteraction = async (updatedFormState) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/interactions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          form_state: updatedFormState
        })
      });

      if (!response.ok) {
        throw new Error("Could not save the interaction.");
      }

      const payload = await response.json();
      dispatch(receiveSaveResult(payload));
    } catch (saveError) {
      dispatch(setSaveError(saveError.message || "Could not save the interaction."));
    }
  };

  const sendAgentMessage = async (rawContent) => {
    const content = rawContent.trim();
    if (!content || status === "loading") {
      return;
    }

    dispatch(addUserMessage(content));
    dispatch(setAgentPending());

    try {
      const response = await fetch(`${API_BASE_URL}/api/agent/message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: content,
          form_state: formState,
          history: transcriptHistory
        })
      });

      if (!response.ok) {
        throw new Error("The agent request failed. Please check the backend server.");
      }

      const payload = await response.json();
      dispatch(receiveAgentResult(payload));
      saveInteraction(payload.form_state);
    } catch (requestError) {
      dispatch(
        setAgentError(
          requestError.message ||
            "The assistant could not process this request. Please verify the backend service."
        )
      );
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const content = draft.trim();
    setDraft("");
    await sendAgentMessage(content);
  };

  const handleVoiceSummary = () => {
    const hasConsent = window.confirm(
      "This will use your browser microphone to capture a voice note and send the transcript to the AI assistant. Do you consent?"
    );

    if (!hasConsent) {
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      const typedNote = window.prompt(
        "Voice capture is not supported in this browser. Paste or type the voice note transcript here:"
      );
      if (typedNote?.trim()) {
        sendAgentMessage(`Summarize this voice note and log the HCP interaction details: ${typedNote}`);
      }
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setVoiceStatus("listening");
    recognition.onerror = (event) => {
      setVoiceStatus("idle");
      const typedNote = window.prompt(
        `Voice note capture failed (${event.error}). Paste or type the voice note transcript here instead:`
      );
      if (typedNote?.trim()) {
        sendAgentMessage(`Summarize this voice note and log the HCP interaction details: ${typedNote}`);
        return;
      }
    };
    recognition.onend = () => setVoiceStatus("idle");
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendAgentMessage(`Summarize this voice note and log the HCP interaction details: ${transcript}`);
    };

    recognition.start();
  };

  return (
    <main className="page-shell">
      <section className="screen-card">
        <header className="screen-header">
          <h1>Log HCP Interaction</h1>
        </header>

        <div className="screen-grid">
          <InteractionPanel
            formState={formState}
            onVoiceSummary={handleVoiceSummary}
            voiceStatus={voiceStatus}
          />
          <ChatPanel
            draft={draft}
            error={error}
            messages={messages}
            onDraftChange={setDraft}
            onSubmit={handleSubmit}
            status={status}
            toolEvents={toolEvents}
          />
        </div>
      </section>
    </main>
  );
}

function InteractionPanel({ formState, onVoiceSummary, voiceStatus }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Interaction Details</h2>
      </div>

      <div className="form-scroll">
        <div className="field-grid">
          <Field label="HCP Name">
            <input value={formState.hcp_name} placeholder="Search or select HCP..." readOnly />
          </Field>
          <Field label="Interaction Type">
            <div className="select-shell">
              <input value={formState.interaction_type} readOnly />
              <span className="select-arrow" aria-hidden="true">
                <svg viewBox="0 0 12 8" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M1.25 1.5L6 6.25L10.75 1.5"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
            </div>
          </Field>
          <Field label="Date">
            <input value={formState.date} placeholder="DD-MM-YYYY" readOnly />
          </Field>
          <Field label="Time">
            <input value={formState.time} placeholder="HH:MM" readOnly />
          </Field>
        </div>

        <Field label="Attendees">
          <input value={formState.attendees.join(", ")} placeholder="Enter names or search..." readOnly />
        </Field>

        <Field label="Topics Discussed">
          <div className="textarea-with-icon">
            <textarea
              value={formState.topics_discussed}
              placeholder="Enter key discussion points..."
              rows="4"
              readOnly
            />
            <span className="textarea-mic-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M8 9.5C9.1 9.5 10 8.6 10 7.5V3.5C10 2.4 9.1 1.5 8 1.5C6.9 1.5 6 2.4 6 3.5V7.5C6 8.6 6.9 9.5 8 9.5Z"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
                <path
                  d="M4.4 7.2C4.4 9.2 6 10.8 8 10.8C10 10.8 11.6 9.2 11.6 7.2M8 10.8V14M6.4 14H9.6"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
              </svg>
            </span>
          </div>
        </Field>

        <button className="secondary-action" type="button" onClick={onVoiceSummary} disabled={voiceStatus === "listening"}>
          ✣ {voiceStatus === "listening" ? "Listening..." : "Summarize from Voice Note (Requires Consent)"}
        </button>

        <section className="sub-card">
          <div className="sub-card-header">
            <div>
              <h3>Materials Shared / Samples Distributed</h3>
            </div>
          </div>

          <div className="material-block">
            <div className="block-header">
              <h4>Materials Shared</h4>
              <button type="button">
                <SearchIcon />
                <span>Search/Add</span>
              </button>
            </div>
            <p>{formState.materials_shared.length ? formState.materials_shared.join(", ") : "No materials added."}</p>
          </div>

          <div className="material-block">
            <div className="block-header">
              <h4>Samples Distributed</h4>
              <button type="button">
                <CubeIcon />
                <span>Add Sample</span>
              </button>
            </div>
            {formState.samples_distributed.length ? (
              <ul className="tag-list">
                {formState.samples_distributed.map((item, index) => (
                  <li key={`${item.name}-${index}`}>
                    {item.name} ({item.quantity})
                  </li>
                ))}
              </ul>
            ) : (
              <p>No samples added.</p>
            )}
          </div>
        </section>

        <Field label="Observed/Inferred HCP Sentiment">
          <div className="sentiment-row">
            <SentimentOption emoji="😊" label="Positive" active={formState.sentiment === "positive"} />
            <SentimentOption emoji="😐" label="Neutral" active={formState.sentiment === "neutral"} />
            <SentimentOption emoji="🙁" label="Negative" active={formState.sentiment === "negative"} />
          </div>
        </Field>

        <Field label="Outcomes">
          <textarea value={formState.outcomes} placeholder="Key outcomes or agreements..." rows="3" readOnly />
        </Field>

        <Field label="Follow-up Actions">
          <textarea
            value={formState.follow_up_actions}
            placeholder="Enter next steps or tasks..."
            rows="3"
            readOnly
          />
        </Field>

        <section className="followup-strip">
          <h3>AI Suggested Follow-ups</h3>
          {formState.ai_suggested_follow_ups.length ? (
            <ul>
              {formState.ai_suggested_follow_ups.map((item) => (
                <li key={item}>+ {item}</li>
              ))}
            </ul>
          ) : (
            <p>No AI suggestions yet.</p>
          )}
        </section>
      </div>
    </section>
  );
}

function ChatPanel({ draft, error, messages, onDraftChange, onSubmit, status, toolEvents }) {
  return (
    <section className="panel chat-panel">
      <div className="panel-heading">
        <h2>🤖 AI Assistant</h2>
        <p>Log interaction via chat</p>
      </div>

      <div className="chat-feed">
        {messages.map((message, index) => (
          <article key={`${message.role}-${index}`} className={`message-bubble ${message.variant}`}>
            {message.content}
          </article>
        ))}

        {status === "loading" && <article className="message-bubble pending">Updating the form through LangGraph...</article>}
      </div>

      <form className="chat-input-row" onSubmit={onSubmit}>
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="Describe interaction..."
          rows="2"
        />
        <button type="submit" disabled={status === "loading"}>
          <span className="button-icon" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M8 0.1L14 12.8H8.15L8 8.2L7.85 12.8H2L8 0.1Z"
                stroke="currentColor"
                strokeWidth="1.35"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span>Log</span>
        </button>
      </form>
    </section>
  );
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function SentimentOption({ active, emoji, label }) {
  return (
    <div className={`sentiment-option ${active ? "active" : ""}`}>
      <span className="dot" />
      <span className="sentiment-emoji" aria-hidden="true">{emoji}</span>
      <span>{label}</span>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg className="inline-icon search-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="7" cy="7" r="4" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10.1 10.1L13.2 13.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function CubeIcon() {
  return (
    <svg className="inline-icon cube-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M9 1.8L15 5.2V12.6L9 16.2L3 12.6V5.2L9 1.8Z" stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" />
      <path d="M3 5.2L9 8.7L15 5.2M9 8.7V16.2" stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" />
    </svg>
  );
}

export default App;
