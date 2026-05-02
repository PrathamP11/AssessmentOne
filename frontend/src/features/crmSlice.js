import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  formState: {
    hcp_name: "",
    interaction_type: "Meeting",
    date: "",
    time: "",
    attendees: [],
    topics_discussed: "",
    materials_shared: [],
    samples_distributed: [],
    sentiment: "",
    outcomes: "",
    follow_up_actions: "",
    ai_suggested_follow_ups: [
      "Schedule follow-up meeting in 2 weeks",
      "Send OncoBoost Phase III PDF",
      "Add Dr. Sharma to advisory board invite list"
    ],
    compliance_notes: []
  },
  messages: [
    {
      role: "assistant",
      variant: "hint",
      content:
        'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.'
    }
  ],
  toolEvents: [],
  status: "idle",
  saveStatus: "idle",
  saveMessage: "",
  error: ""
};

const crmSlice = createSlice({
  name: "crm",
  initialState,
  reducers: {
    addUserMessage(state, action) {
      state.messages.push({
        role: "user",
        variant: "user",
        content: action.payload
      });
    },
    setAgentPending(state) {
      state.status = "loading";
      state.error = "";
    },
    receiveAgentResult(state, action) {
      state.status = "idle";
      state.formState = action.payload.form_state;
      state.toolEvents = action.payload.tool_events;
      state.messages.push({
        role: "assistant",
        variant: "success",
        content: action.payload.assistant_message
      });
    },
    setAgentError(state, action) {
      state.status = "failed";
      state.error = action.payload;
      state.messages.push({
        role: "assistant",
        variant: "error",
        content: action.payload
      });
    },
    setSavePending(state) {
      state.saveStatus = "loading";
      state.saveMessage = "";
    },
    receiveSaveResult(state, action) {
      state.saveStatus = "idle";
      state.saveMessage = `Saved interaction #${action.payload.id}`;
    },
    setSaveError(state, action) {
      state.saveStatus = "failed";
      state.saveMessage = action.payload;
    }
  }
});

export const {
  addUserMessage,
  setAgentPending,
  receiveAgentResult,
  setAgentError,
  setSavePending,
  receiveSaveResult,
  setSaveError
} = crmSlice.actions;
export default crmSlice.reducer;
