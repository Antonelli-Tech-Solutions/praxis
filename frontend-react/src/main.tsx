import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { configureAmplify, isLocalAuthBypassEnabled } from "./auth/amplifyConfig";
import { OrgGate } from "./auth/OrgGate";
import App from "./App";

configureAmplify();

// The app is normally gated by Cognito (Amplify Authenticator). The Authenticator
// is skipped ONLY for explicit local dev — when no Cognito pool is configured AND
// VITE_PRAXIS_AUTH_DISABLED=1 (paired with a backend started PRAXIS_AUTH_DISABLED=1).
// Any deployed build sets VITE_COGNITO_*, so the bypass never runs in production.
const gated = (
  <OrgGate>
    <App />
  </OrgGate>
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {isLocalAuthBypassEnabled() ? gated : <Authenticator>{gated}</Authenticator>}
  </StrictMode>,
);
