import streamlit as st
import time
import plotly.graph_objects as go
from twin.data_loader import get_unit, label_for
from twin.replay import row_to_state
from twin.llm import ask_twin
from twin.model import load_or_train, predict_rul
from twin.contract import validate_row, load_contract
from twin.graph import subsystem_health
from twin.maintenance import evaluate_maintenance

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

@st.cache_resource
def get_model():
    return load_or_train()

model = get_model()

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

maint_threshold = st.sidebar.slider("Maintenance Alert Threshold (RUL)", min_value=1, max_value=50, value=25)

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
current_state = row_to_state(current_row)

# UI Layout
st.title(f"Engine {unit_id} — Cycle {current_cycle} / {len(df)}")

is_valid, errors = validate_row(current_state)
if is_valid:
    st.success("✅ Contract: VALID")
else:
    st.error(f"❌ Contract: INVALID ({', '.join(errors)})")

with st.expander("DTDL Contract Telemetry List"):
    contract_data = load_contract()
    telemetry = [item for item in contract_data.get("contents", []) if item.get("@type") == "Telemetry"]
    st.json(telemetry)

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

predicted_rul = predict_rul(model, current_state)
met1, met2 = st.columns(2)
met1.metric("Actual RUL", current_rul, delta=delta_rul, delta_color="inverse")
met2.metric("Predicted RUL", int(predicted_rul), delta=int(predicted_rul - current_rul), delta_color="off")

def make_sensor_chart(history_df, sensor, current_row):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history_df['cycle'], y=history_df[sensor], mode='lines', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=[current_row['cycle']], y=[current_row[sensor]], mode='markers', marker=dict(color='red', size=10)))
    fig.update_layout(
        title=label_for(sensor), 
        height=200, 
        margin=dict(l=0, r=0, t=30, b=0), 
        showlegend=False,
        xaxis_title="Cycle"
    )
    return fig

# Charts
active_sensor_cols = [c for c in df.columns if c.startswith('sensor_')]

st.sidebar.markdown("---")
selected_sensors = st.sidebar.multiselect(
    "Sensors to display", 
    options=active_sensor_cols, 
    default=active_sensor_cols,
    format_func=label_for
)

history_df = df.iloc[:st.session_state.cursor + 1]

sub_scores = subsystem_health(current_state, history_df)

st.markdown("---")
st.subheader("Subsystem Health Ranking")
st.caption("Higher score = faster degradation over last 20 cycles")
sorted_subs = sorted(sub_scores.items(), key=lambda x: x[1], reverse=True)
for i, (sub, score) in enumerate(sorted_subs):
    if i == 0 and score > 0:
        st.error(f"**{sub}** is degrading fastest (Score: {score:.4f})")
    else:
        st.write(f"- {sub}: {score:.4f}")

maint_decision = evaluate_maintenance(predicted_rul, threshold=maint_threshold)
if maint_decision["schedule"]:
    st.error(f"⚠️ Maintenance scheduled — predicted RUL {int(predicted_rul)} < {maint_threshold} (Urgency: {maint_decision['urgency']})")
    with st.expander("SimPy Maintenance Event Log", expanded=True):
        for log_line in maint_decision["log"]:
            st.code(log_line)

# RUL tracking chart
history_predictions = predict_rul(model, history_df)
fig_rul = go.Figure()
fig_rul.add_trace(go.Scatter(x=history_df['cycle'], y=history_df['RUL'], mode='lines', name='Actual RUL', line=dict(color='green')))
fig_rul.add_trace(go.Scatter(x=history_df['cycle'], y=history_predictions, mode='lines', name='Predicted RUL', line=dict(color='orange')))
fig_rul.update_layout(title="RUL Degradation Curve", height=300, xaxis_title="Cycle", yaxis_title="RUL")
st.plotly_chart(fig_rul, use_container_width=True)

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
display_state = dict(current_state)
display_state["sensors"] = {label_for(k): v for k, v in current_state["sensors"].items()}

with st.expander("Raw State (JSON)"):
    st.json(display_state)

st.markdown("---")
st.subheader("Ask the Twin")
st.caption("Answers reflect the current engine state and history up to the selected cycle.")

if "chat" not in st.session_state:
    st.session_state.chat = []

col1, col2, col3 = st.columns(3)
quick_q = None
if col1.button("Which sensors are trending toward failure?"):
    quick_q = "Which sensors are trending toward failure?"
if col2.button("Estimate remaining useful life and explain why"):
    quick_q = "Estimate remaining useful life and explain why"
if col3.button("What happens if load increases?"):
    quick_q = "What happens if load increases?"

for msg in st.session_state.chat:
    st.chat_message(msg["role"]).write(msg["content"])

user_q = st.chat_input("Ask a question about the engine...")
question_to_ask = quick_q or user_q

if question_to_ask:
    st.chat_message("user").write(question_to_ask)
    st.session_state.chat.append({"role": "user", "content": question_to_ask})
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing engine telemetry..."):
            answer = ask_twin(question_to_ask, current_state, history_df, subsystem_scores=sub_scores)
            st.write(answer)
    
    st.session_state.chat.append({"role": "assistant", "content": answer})

# Auto-play loop logic
if st.session_state.playing:
    if st.session_state.cursor < max_cursor:
        time.sleep(tick_speed)
        st.session_state.cursor += 1
        st.rerun()
    else:
        st.session_state.playing = False
        st.rerun()
