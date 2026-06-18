import streamlit as st
import pandas as pd
from mock_data import get_mock_candidates

st.set_page_config(
    page_title="PRAXIS Candidate Review Gate",
    page_icon="🧠",
    layout="wide"
)

# --- State Management ---
if "candidates_df" not in st.session_state:
    st.session_state.candidates_df = get_mock_candidates()

def promote_candidate(cand_id):
    idx = st.session_state.candidates_df.index[st.session_state.candidates_df['id'] == cand_id].tolist()[0]
    current_state = st.session_state.candidates_df.at[idx, 'state']
    
    if current_state == 'proposed':
        st.session_state.candidates_df.at[idx, 'state'] = 'suggested'
        st.toast(f"Promoted candidate to Suggested")
    elif current_state == 'suggested':
        st.session_state.candidates_df.at[idx, 'state'] = 'active'
        st.toast(f"Promoted candidate to Active")
    else:
        st.toast(f"Candidate is already Active", icon="⚠️")

def reject_candidate(cand_id):
    # In a real app, this might delete it or mark it as rejected.
    # Here we'll just drop it from the dataframe for demonstration.
    st.session_state.candidates_df = st.session_state.candidates_df[st.session_state.candidates_df['id'] != cand_id]
    st.toast(f"Rejected candidate")

# --- UI Header ---
st.title("Candidate Review Gate")
st.markdown("Review and promote AI-learned knowledge candidates from agent sessions.")

# --- Filters & Search ---
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search", placeholder="Search by title or content...")
    with col2:
        state_filter = st.selectbox("Filter by State", ["All", "proposed", "suggested", "active"])

# Apply filters
filtered_df = st.session_state.candidates_df.copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df["title"].str.contains(search_query, case=False, na=False) |
        filtered_df["content"].str.contains(search_query, case=False, na=False)
    ]

if state_filter != "All":
    filtered_df = filtered_df[filtered_df["state"] == state_filter]


# --- Main Content Area ---
tab1, tab2 = st.tabs(["Table View", "Card View"])

with tab1:
    st.markdown(f"**{len(filtered_df)} candidates**")
    
    if len(filtered_df) == 0:
        st.info("No candidates match the current filter.")
    else:
        # We create a display dataframe that formats things nicely
        display_df = filtered_df[['title', 'state', 'confidence', 'provenance', 'createdAt']].copy()
        
        # Streamlit's dataframe handles column resizing, sorting, and formatting automatically
        st.dataframe(
            display_df,
            column_config={
                "title": st.column_config.TextColumn("Title", width="large"),
                "state": st.column_config.TextColumn("State", width="medium"),
                "confidence": st.column_config.ProgressColumn(
                    "Confidence",
                    help="AI Confidence Score",
                    min_value=0,
                    max_value=1,
                    format="%.2f",
                    width="medium"
                ),
                "provenance": st.column_config.TextColumn("Provenance", width="large"),
                "createdAt": st.column_config.DatetimeColumn("Created At", format="MMM DD, YYYY", width="medium"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Because st.dataframe doesn't currently support arbitrary button clicks per row easily,
        # a common pattern is to show the table, and have an action section below it.
        st.markdown("### Actions")
        action_col1, action_col2 = st.columns([3, 1])
        with action_col1:
            selected_id = st.selectbox("Select a candidate to action:", filtered_df['id'].tolist(), format_func=lambda x: filtered_df[filtered_df['id'] == x]['title'].values[0])
        with action_col2:
            st.write("") # Spacing
            st.write("")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Promote", type="primary", use_container_width=True):
                    promote_candidate(selected_id)
                    st.rerun()
            with b2:
                if st.button("Reject", use_container_width=True):
                    reject_candidate(selected_id)
                    st.rerun()

with tab2:
    st.markdown(f"**{len(filtered_df)} candidates**")
    
    if len(filtered_df) == 0:
        st.info("No candidates match the current filter.")
    else:
        # Create a grid layout for cards
        cols = st.columns(3)
        for idx, row in filtered_df.iterrows():
            col = cols[idx % 3]
            with col:
                with st.container(border=True):
                    st.subheader(row['title'])
                    
                    # State badge equivalent
                    color = "orange" if row['state'] == 'proposed' else "blue" if row['state'] == 'suggested' else "green"
                    st.markdown(f":{color}[**{row['state'].upper()}**]")
                    
                    st.progress(row['confidence'], text=f"Confidence: {row['confidence']:.2f}")
                    
                    st.caption(f"**Source:** `{row['provenance']}`")
                    st.write(row['content'])
                    
                    st.caption(f"Created: {pd.to_datetime(row['createdAt']).strftime('%b %d, %Y')}")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("Promote", key=f"promo_{row['id']}", type="primary", use_container_width=True):
                            promote_candidate(row['id'])
                            st.rerun()
                    with b2:
                        if st.button("Reject", key=f"rej_{row['id']}", use_container_width=True):
                            reject_candidate(row['id'])
                            st.rerun()
