import pandas as pd

def get_mock_candidates():
    return pd.DataFrame([
        {
            "id": "cand_1",
            "title": "TypeScript Exhaustive Switch Pattern",
            "content": "When using a switch statement on a discriminated union or enum, include a default case that assigns the value to a variable of type `never`. This ensures the compiler will throw an error if a new variant is added to the union but not handled in the switch.",
            "state": "proposed",
            "confidence": 0.85,
            "provenance": "logs/session_20260615.jsonl",
            "createdAt": "2026-06-15T14:30:00Z"
        },
        {
            "id": "cand_2",
            "title": "React useEffect Cleanup",
            "content": "Always return a cleanup function from useEffect when subscribing to external events or setting up intervals. This prevents memory leaks and unexpected behavior when components unmount.",
            "state": "suggested",
            "confidence": 0.92,
            "provenance": "logs/session_20260614.jsonl",
            "createdAt": "2026-06-14T09:15:00Z"
        },
        {
            "id": "cand_3",
            "title": "GitLab CI Artifact Expiration",
            "content": "Set an explicit `expire_in` value for all GitLab CI artifacts to prevent storage bloat. A good default is '1 week' for temporary build artifacts.",
            "state": "active",
            "confidence": 0.98,
            "provenance": "logs/session_20260610.jsonl",
            "createdAt": "2026-06-10T11:45:00Z"
        },
        {
            "id": "cand_4",
            "title": "Python Type Hinting for Dicts",
            "content": "Use `Dict[str, Any]` instead of `dict` when typing dictionaries with string keys and mixed value types to provide better IDE support and static analysis.",
            "state": "proposed",
            "confidence": 0.75,
            "provenance": "logs/session_20260616.jsonl",
            "createdAt": "2026-06-16T16:20:00Z"
        },
        {
            "id": "cand_5",
            "title": "Streamlit Session State",
            "content": "Use `st.session_state` to persist variables across Streamlit app reruns. This is essential for maintaining user input or application state between interactions.",
            "state": "suggested",
            "confidence": 0.88,
            "provenance": "logs/session_20260617.jsonl",
            "createdAt": "2026-06-17T10:05:00Z"
        }
    ])