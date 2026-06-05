import streamlit as st
import time
import plotly.graph_objects as go
from twin.data_loader import get_unit
from twin.replay import row_to_state

st.set_page_config(page_title="C-MAPSS Digital Twin", layout="wide")

@st.cache_data
def load_unit_data(unit_id):
    return get_unit(unit_id)

st.sidebar.title("Controls")

# Select Unit
unit_id = st.sidebar.number_input("Unit ID (1-100)", min_value=1, max_value=100, value=1, step=1)

# Check if unit changed to reset state
if "current_unit" not in st.session_state:
    st.session_state.current_unit = unit_id

if st.session_state.current_unit != unit_id:
    st.session_state.current_unit = unit_id
    st.session_state.cursor = 0
    st.session_state.playing = False

# Load Data
df = load_unit_data(unit_id)
max_cursor = len(df) - 1

# Initialize state variables
if "cursor" not in st.session_state:
    st.session_state.cursor = 0
if "playing" not in st.session_state:
    st.session_state.playing = False

# Playback speed
tick_speed = st.sidebar.slider("Tick Speed (seconds)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)

# Playback controls
col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ Play"):
    if st.session_state.cursor >= max_cursor:
        st.session_state.cursor = 0
    st.session_state.playing = True
    st.rerun()

if col2.button("⏸️ Pause"):
    st.session_state.playing = False
    st.rerun()

# Scrub slider
cursor = st.sidebar.slider("Scrub Cycle", min_value=0, max_value=max_cursor, value=st.session_state.cursor)
if cursor != st.session_state.cursor:
    st.session_state.cursor = cursor
    # User is scrubbing, pause autoplay
    st.session_state.playing = False

current_row = df.iloc[st.session_state.cursor]
current_cycle = int(current_row['cycle'])
current_rul = int(current_row['RUL'])

# UI Layout
st.title(f"Engine {unit_id} — Cycle {current_cycle} / {len(df)}")

if current_rul == 0:
    st.error("🚨 Engine failed / end of trajectory")
elif current_rul < 30:
    st.warning("⚠️ Warning: RUL is critically low!")

# Metric
prev_rul = None
if st.session_state.cursor > 0:
    prev_rul = int(df.iloc[st.session_state.cursor - 1]['RUL'])
    delta_rul = current_rul - prev_rul
else:
    delta_rul = None

st.metric("Remaining Useful Life (RUL)", current_rul, delta=delta_rul, delta_color="inverse")

def make_sensor_chart(history_df, sensor, current_row):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history_df['cycle'], y=history_df[sensor], mode='lines', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=[current_row['cycle']], y=[current_row[sensor]], mode='markers', marker=dict(color='red', size=10)))
    fig.update_layout(
        title=sensor, 
        height=200, 
        margin=dict(l=0, r=0, t=30, b=0), 
        showlegend=False,
        xaxis_title="Cycle"
    )
    return fig

# Charts
active_sensor_cols = [c for c in df.columns if c.startswith('sensor_')]

st.sidebar.markdown("---")
selected_sensors = st.sidebar.multiselect("Sensors to display", options=active_sensor_cols, default=active_sensor_cols)

history_df = df.iloc[:st.session_state.cursor + 1]

if selected_sensors:
    N = 3
    for i in range(0, len(selected_sensors), N):
        cols = st.columns(N)
        for j in range(N):
            if i + j < len(selected_sensors):
                sensor = selected_sensors[i + j]
                fig = make_sensor_chart(history_df, sensor, current_row)
                cols[j].plotly_chart(fig, use_container_width=True)

# Raw State
with st.expander("Raw State (JSON)"):
    st.json(row_to_state(current_row))

# Auto-play loop logic
if st.session_state.playing:
    if st.session_state.cursor < max_cursor:
        time.sleep(tick_speed)
        st.session_state.cursor += 1
        st.rerun()
    else:
        st.session_state.playing = False
        st.rerun()
