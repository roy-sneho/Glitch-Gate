"""Streamlit front end for Glitch Gate v0.2.

Run: streamlit run app.py
This app performs no physical injection and makes no ChipWhisperer API calls.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from search_map import observed_grid, focused_range

from model import (
    EDGE_GUARD_NS, FLAG_UPDATE_PATH_NS, MIN_PULSE_WIDTH_NS,
    MAX_CYCLE_SHIFT, MAX_EXT_OFFSET, PERIOD_NS, SETUP_NS, WRONG_PASSWORDS,
    GlitchSettings, AttemptResult, failure_flag_cycle, inject,
    operation_at, program_trace, run_baseline,
)

st.set_page_config(page_title="Glitch Gate | ECE 576", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 1.5rem;}
h1, h2, h3 {letter-spacing: -0.015em;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
.hero-note {font-size: 0.98rem; opacity:.82; margin-top:-.5rem;}
</style>
""", unsafe_allow_html=True)



# Four questions; answer choices are randomized once per challenge.
MCQ_BANK = (
    (
        "Which statement best explains why some settings are NORMAL?",
        (
            "The target automatically knows the attacker is present.",
            "The pulse is not effective or the selected operation still meets its timing requirement.",
            "Every clock glitch changes the correct password.",
        ),
        "The pulse is not effective or the selected operation still meets its timing requirement.",
    ),
    (
        "Why can increasing width lead to RESET rather than SUCCESS?",
        (
            "A wider pulse always produces a cleaner instruction skip.",
            "A wide pulse may overlap a normal edge and disrupt execution.",
            "The target password changes length.",
        ),
        "A wide pulse may overlap a normal edge and disrupt execution.",
    ),
    (
        "What does a negative timing margin indicate in this model?",
        (
            "The inserted pulse is always too short to be registered.",
            "The available sampling interval is shorter than path delay plus setup time.",
            "A real processor has definitely skipped an instruction.",
        ),
        "The available sampling interval is shorter than path delay plus setup time.",
    ),
    (
        "What does changing ext_offset do?",
        (
            "It changes the expected password.",
            "It changes the high duration of the injected pulse.",
            "It moves the glitch to a different virtual clock cycle.",
        ),
        "It moves the glitch to a different virtual clock cycle.",
    ),
)


def randomized_mcq_options() -> list[list[str]]:
    rng = secrets.SystemRandom()
    # All three answer positions are represented, so the right choice
    # is not always the second option.
    positions = [0, 1, 2, rng.randrange(3)]
    rng.shuffle(positions)
    randomized = []
    for (_, options, answer), position in zip(MCQ_BANK, positions):
        alternatives = [option for option in options if option != answer]
        rng.shuffle(alternatives)
        alternatives.insert(position, answer)
        randomized.append(alternatives)
    return randomized


# Ten stored prediction scenarios. Only one is chosen per challenge.
# The three success-case offsets are derived from the selected password's
# illustrative path delay, keeping them consistent with the fault model.
# (label, operation, pulse width, offset or violation amount, expected status)
PREDICTION_BANK = (
    ("Short pulse at failure write", "flag", 0.40, -1.8, "NORMAL"),
    ("Short pulse at comparison", "compare", 0.35, -2.5, "NORMAL"),
    ("Adequate timing at comparison", "compare", 0.80, -1.5, "NORMAL"),
    ("Adequate timing at return", "return", 0.80, -1.2, "NORMAL"),
    ("Overlapping pulse at failure write", "flag", 1.50, -1.0, "RESET"),
    ("Overlapping pulse at comparison", "compare", 1.25, -0.8, "RESET"),
    ("Severe violation at failure write", "flag", 0.80, -3.0, "RESET"),
    ("Moderate violation at failure write A", "flag", 0.75, 0.35, "SUCCESS"),
    ("Moderate violation at failure write B", "flag", 0.80, 0.50, "SUCCESS"),
    ("Moderate violation at failure write C", "flag", 0.80, 0.60, "SUCCESS"),
)


def choose_prediction_case(password: str, shift: int) -> tuple[GlitchSettings, str]:
    """Select one of ten scenarios and evaluate it for the current target."""
    ops = program_trace(password, shift)
    flag_op = next(op for op in ops if op.security_sensitive)
    compare_op = next(op for op in ops if op.name.startswith("COMPARE"))
    return_op = next(op for op in ops if op.name == "RETURN")
    targets = {"flag": flag_op, "compare": compare_op, "return": return_op}

    choices = []
    for _label, target, width, value, expected in PREDICTION_BANK:
        op = targets[target]
        # SUCCESS scenarios prescribe a moderate model-timing violation.
        offset = (round(op.path_delay_ns + SETUP_NS - PERIOD_NS - value, 1)
                  if expected == "SUCCESS" else value)
        probe = GlitchSettings(width_ns=width, offset_ns=offset, ext_offset=op.cycle)
        observed = inject(probe, password, shift)
        if observed.status != expected:
            raise RuntimeError(f"Prediction bank case does not match model: {_label}")
        choices.append((probe, op.name))

    return secrets.choice(choices)


def init_session() -> None:
    if "password_choice" not in st.session_state:
        st.session_state.password_choice = WRONG_PASSWORDS[0]
    if "chosen_password" not in st.session_state:
        st.session_state.chosen_password = st.session_state.password_choice
    if "cycle_shift" not in st.session_state:
        st.session_state.cycle_shift = secrets.randbelow(MAX_CYCLE_SHIFT + 1)
    if "attempts" not in st.session_state:
        st.session_state.attempts = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "baseline_seen" not in st.session_state:
        st.session_state.baseline_seen = False
    if "learning_feedback" not in st.session_state:
        st.session_state.learning_feedback = None
    if "mcq_options" not in st.session_state:
        st.session_state.mcq_options = randomized_mcq_options()
    if "quiz_prediction" not in st.session_state:
        st.session_state.quiz_prediction = choose_prediction_case(
            st.session_state.chosen_password, st.session_state.cycle_shift
        )
    for key, default in (
        ("glitch_width", 0.0),
        ("glitch_offset", 0.0),
        ("glitch_cycle", 0),
    ):
        if key not in st.session_state:
            st.session_state[key] = default


def clear_run(new_shift: bool = False) -> None:
    if new_shift:
        st.session_state.cycle_shift = (st.session_state.cycle_shift + 1 + secrets.randbelow(MAX_CYCLE_SHIFT)) % (MAX_CYCLE_SHIFT + 1)
    st.session_state.attempts = []
    st.session_state.last_result = None
    st.session_state.baseline_seen = False
    st.session_state.learning_feedback = None
    st.session_state.glitch_width = 0.0
    st.session_state.glitch_offset = 0.0
    st.session_state.glitch_cycle = 0
    st.session_state.mcq_options = randomized_mcq_options()
    st.session_state.quiz_prediction = choose_prediction_case(
        st.session_state.chosen_password, st.session_state.cycle_shift
    )
    for key in ("why_region", "prediction", *(f"conceptual_q{i}" for i in range(1, 5)),
                *(f"prediction_{i}" for i in range(1, 11))):
        st.session_state.pop(key, None)


def plot_clock(result: AttemptResult) -> go.Figure:
    """Draw illustrative nominal and extra early pulses in one virtual cycle."""
    t = [i * 0.025 for i in range(641)]  # 0 to 16 model ns
    # Clock starts low and rises at the next nominal edge, T=10 model ns.
    normal = [int(PERIOD_NS <= x < PERIOD_NS + 4.0) for x in t]
    if result.settings is not None:
        early = PERIOD_NS + result.settings.offset_ns
        end = early + result.settings.width_ns
        # An electrical pulse is drawn even if the modeled logic ignores it.
        injected = [int((PERIOD_NS <= x < PERIOD_NS + 4.0) or
                        (early <= x < end)) for x in t]
    else:
        early = None
        injected = normal
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=[1.5 + v for v in normal], mode="lines",
                             line=dict(width=2.4, color="#2563EB", shape="hv"),
                             name="Normal clock"))
    fig.add_trace(go.Scatter(x=t, y=[v for v in injected], mode="lines",
                             line=dict(width=2.4, color="#D97706", shape="hv"),
                             name="Glitched clock"))
    fig.add_vline(x=PERIOD_NS, line_dash="dot", line_color="#64748B",
                  annotation_text="Nominal edge", annotation_position="top right")
    if early is not None:
        fig.add_vline(x=early, line_dash="dash", line_color="#DC2626",
                      annotation_text="Early edge", annotation_position="bottom left")
    fig.update_layout(height=245, margin=dict(l=10, r=10, t=35, b=25),
                      yaxis=dict(tickmode="array", tickvals=[.5, 2.0],
                                 ticktext=["Injected", "Normal"], range=[-.25, 3.1],
                                 showgrid=False, zeroline=False),
                      xaxis=dict(title="Model time (ns)", range=[0, 16], dtick=2),
                      legend=dict(orientation="h", yanchor="bottom", y=1.15, x=0))
    return fig


def status_callout(r: AttemptResult) -> None:
    if r.status == "SUCCESS":
        st.success("SUCCESS — the incorrect password was accepted in the fault model.", icon="✅")
    elif r.status == "RESET":
        st.error("RESET — the modeled clock disturbance interrupted the target.", icon="🔴")
    else:
        st.info("NORMAL — the incorrect password was rejected.", icon="🔵")
    st.write(r.explanation)


def recorded_row(r: AttemptResult) -> dict:
    assert r.settings is not None
    return {
        "attempt": len(st.session_state.attempts) + 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "password_used": st.session_state.chosen_password,
        "width_ns": r.settings.width_ns,
        "offset_ns": r.settings.offset_ns,
        "ext_offset": r.settings.ext_offset,
        "operation": r.operation.name,
        "effective_interval_ns": round(r.effective_interval_ns, 3),
        "required_interval_ns": round(r.required_interval_ns, 3),
        "slack_ns": round(r.slack_ns, 3),
        "status": r.status,
        "modeled_effect": r.fault_effect,
    }


def draw_attempt_heatmap(attempts: list[dict], x_field: str, y_field: str,
                         x_values: list, y_values: list, filters: dict,
                         x_title: str, y_title: str, chart_height: int = 380) -> None:
    """Draw only observed outcomes; gray cells are genuinely untested."""
    z, hover = observed_grid(attempts, x_field, y_field, x_values, y_values, filters)
    # Discrete color bands: UNTESTED / NORMAL / RESET / SUCCESS.
    discrete = [
        [0.0, "#E5E7EB"], [0.2499, "#E5E7EB"],
        [0.25, "#2563EB"], [0.4999, "#2563EB"],
        [0.50, "#DC2626"], [0.7499, "#DC2626"],
        [0.75, "#00C853"], [1.0, "#00C853"],
    ]
    fig = go.Figure(go.Heatmap(
        x=x_values, y=y_values, z=z, text=hover,
        hovertemplate="%{text}<extra></extra>",
        zmin=-0.5, zmax=3.5, colorscale=discrete, zsmooth=False,
        colorbar=dict(title="Observed", tickvals=[0, 1, 2, 3],
                      ticktext=["Not tested", "NORMAL", "RESET", "SUCCESS"],
                      thickness=14, len=0.92),
        xgap=1, ygap=1,
    ))
    fig.update_layout(height=chart_height, margin=dict(l=5, r=5, t=15, b=5),
                      xaxis=dict(title=x_title, type="linear"),
                      yaxis=dict(title=y_title, type="linear"))
    st.plotly_chart(fig, use_container_width=True)


init_session()

st.title("⚡ Glitch Gate")
st.markdown('<p class="hero-note">ECE 576: A software-only, timing-based learning game inspired by the ChipWhisperer password-bypass lab</p>', unsafe_allow_html=True)
st.warning("**Model boundary:** This is a teaching simulation, not a ChipWhisperer emulator or real hardware data. "
           "The timing values and the mapping from a violation to an instruction effect are stated assumptions.", icon="🧪")

with st.sidebar:
    st.header("Challenge setup")
    st.selectbox("Intentionally wrong password", WRONG_PASSWORDS, key="password_choice",
                 help="The toy target always receives a password with exactly one wrong character. "
                      "You cannot bypass by submitting the correct password.")
    if st.session_state.password_choice != st.session_state.chosen_password:
        st.session_state.chosen_password = st.session_state.password_choice
        clear_run()
    st.caption("The lesson is about a timing fault, not guessing the password. Glitch attempts are unlimited.")
    if st.button("🔄 New challenge / new trigger alignment", use_container_width=True):
        clear_run(new_shift=True)
        st.rerun()
    st.divider()
    st.subheader("Model assumptions")
    st.write(f"Normal clock period: **{PERIOD_NS:g} model ns**")
    st.write(f"Minimum registered pulse: **{MIN_PULSE_WIDTH_NS:g} model ns**")
    st.write(
        "Failure-flag timing depends on the selected wrong-character position."
    )
   
    st.caption("These are illustrative values; they are **not measured ChipWhisperer settings**. "
               "The early edge is at T + offset; width is its high duration.")

pwd = st.session_state.chosen_password
shift = st.session_state.cycle_shift

st.markdown("**Your task:** Make the simulated target accept the incorrect password. "
            "Test settings, read the clock/timing evidence, then explain what caused each result.")

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Glitch attempts", len(st.session_state.attempts))
metric_b.metric("Successful attempts", sum(r["status"] == "SUCCESS" for r in st.session_state.attempts))
metric_c.metric("Current target response", st.session_state.last_result.status if st.session_state.last_result else "Not tested")

left, right = st.columns([0.87, 1.13], gap="large")
with left:
    st.subheader("1. Inject a clock glitch")
    if st.button("Run baseline (no glitch)", use_container_width=True):
        st.session_state.last_result = run_baseline(pwd, shift)
        st.session_state.baseline_seen = True
    with st.form("inject_form"):
        width = st.slider("width — inserted pulse high time (model ns)",
                          min_value=0.0, max_value=4.0, step=0.05, key="glitch_width")
        offset = st.slider("offset — early edge relative to normal edge (model ns)",
                           min_value=-4.0, max_value=0.0, step=0.1, key="glitch_offset")
        ext = st.slider("ext_offset — targeted virtual clock cycle",
                        min_value=0, max_value=MAX_EXT_OFFSET, step=1, key="glitch_cycle")
        submitted = st.form_submit_button("⚡ Inject Glitch", use_container_width=True, type="primary")
    if submitted:
        if width == 0.0 or offset == 0.0:
            st.session_state.last_result = run_baseline(pwd, shift)
            st.session_state.baseline_seen = True
            st.info("Set width above 0 and offset below 0 to inject a glitch.")
        else:
            if not st.session_state.baseline_seen:
                st.session_state.last_result = run_baseline(pwd, shift)
                st.session_state.baseline_seen = True
            r = inject(GlitchSettings(width, round(offset, 3), ext), pwd, shift)
            st.session_state.attempts.append(recorded_row(r))
            st.session_state.last_result = r
    st.caption("`ext_offset` chooses a cycle; `offset` advances one edge; `width` sets the added pulse duration. "
               "The simulator checks pulse shape and the selected operation's timing margin.")

with right:
    st.subheader("2. Observe the response")
    r = st.session_state.last_result
    if r is None:
        st.info("Click **Run baseline** to confirm that a wrong password is denied, then try an injection.")
        r_plot = run_baseline(pwd, shift)
    else:
        status_callout(r)
        st.caption(f"Targeted virtual operation: **{r.operation.name}** — {r.operation.detail}")
        a, b, c = st.columns(3)
        a.metric("Sampling interval", f"{r.effective_interval_ns:.2f} ns")
        b.metric("Delay + setup", f"{r.required_interval_ns:.2f} ns")
        c.metric("Timing margin", f"{r.slack_ns:+.2f} ns")
        st.caption(f"Assumed modeled effect: {r.fault_effect}")
        r_plot = r
    st.plotly_chart(plot_clock(r_plot), use_container_width=True)
    st.caption("Waveforms are illustrative. A negative timing margin means an assumed setup-time violation; "
               "it does **not** by itself establish what a real CPU instruction does.")

st.divider()
map_tab, trace_tab, model_tab = st.tabs(["3. Parameter search map", "Target execution timeline", "Why these rules?"])
with map_tab:
    if st.session_state.attempts:
        rows = st.session_state.attempts
        
        full_cycles = list(range(MAX_EXT_OFFSET + 1))
        full_offsets = [round(-4.0 + i * 0.1, 1) for i in range(39)]
        full_widths = [round(0.10 + i * 0.05, 2) for i in range(79)]
        focus = st.checkbox("Focus heatmaps on explored / observed SUCCESS region", value=True)

        st.markdown("**A. Search the virtual clock cycles**")
        choices = sorted(set(r["width_ns"] for r in rows))
        success_rows = [r for r in rows if r["status"] == "SUCCESS"]
        default_width = success_rows[-1]["width_ns"] if success_rows else rows[-1]["width_ns"]
        chosen_width = st.selectbox("Show attempts with this width (model ns)", choices,
                                    index=choices.index(default_width),
                                    help="Hold width fixed to compare tested cycles and offsets accurately.")
        filtered = [r for r in rows if r["width_ns"] == chosen_width]
        successful = [r for r in filtered if r["status"] == "SUCCESS"]
        center = successful or filtered
        cycles = focused_range(full_cycles, [r["ext_offset"] for r in center], 2, focus)
        offsets = focused_range(full_offsets, [r["offset_ns"] for r in center], 0.4, focus)
        draw_attempt_heatmap(rows, "ext_offset", "offset_ns", cycles, offsets,
                             {"width_ns": chosen_width}, "ext_offset: virtual cycle to test",
                             "offset (model ns)")
        st.caption("Choose a different observed width above or turn off focus to see the entire 0–20 cycle range. "
                   "Only attempts at the selected width are colored.")

        st.markdown("**B. Fine-tune around a cycle you have tested**")
        tested_cycles = sorted(set(r["ext_offset"] for r in rows))
        default_cycle = success_rows[-1]["ext_offset"] if success_rows else rows[-1]["ext_offset"]
        cycle_choice = st.selectbox("Inspect one tested ext_offset", tested_cycles,
                                    index=tested_cycles.index(default_cycle))
        at_cycle = [r for r in rows if r["ext_offset"] == cycle_choice]
        successful_at_cycle = [r for r in at_cycle if r["status"] == "SUCCESS"]
        center = successful_at_cycle or at_cycle
        offsets2 = focused_range(full_offsets, [r["offset_ns"] for r in center], 0.4, focus)
        widths2 = focused_range(full_widths, [r["width_ns"] for r in center], 0.45, focus)
        draw_attempt_heatmap(rows, "offset_ns", "width_ns", offsets2, widths2,
                             {"ext_offset": cycle_choice}, "offset (model ns)",
                             "width (model ns)")
        st.caption("This view keeps ext_offset fixed, so you can search the narrower "
                   "width/offset region without mixing results from different cycles.")

        with st.expander("Attempt history and CSV export"):
            frame = pd.DataFrame(rows)
            st.dataframe(frame, use_container_width=True, hide_index=True)
            st.download_button("Download results (CSV)", data=frame.to_csv(index=False),
                               mime="text/csv", file_name="glitch_gate_attempts.csv")
    else:
        st.info("No injected attempts yet. Heatmaps will show only your tested settings, "
                "with all other cells marked untested.")
with trace_tab:
    st.write("This is the virtual program used for the experiment, not a real CPU instruction trace. "
             "The expected password is `touch`; the selected input differs in **one** character. "
             "The **cycle numbers are hidden**: use `ext_offset` and the response feedback to discover "
             "which cycles execute which operations.")
    operations = program_trace(pwd, shift)
    st.dataframe(pd.DataFrame([{"virtual operation": op.name,
                                "description": op.detail,
                                "assumed path delay (ns)": op.path_delay_ns}
                               for op in operations]), use_container_width=True, hide_index=True)
    st.caption("Only a missed write of `passok = 0` can produce a bypass in this version. "
               "A clock violation is mapped to that missed update only as an explicit educational assumption.")
with model_tab:
    st.markdown(f"""
    The model inserts a **premature rising edge** within a virtual clock cycle.
    The input `offset` is negative, so the available sampling interval is
    **T + offset**, where **T = {PERIOD_NS:g} model ns**. The added pulse stays high for `width` model ns.

    - **No effective pulse:** width below {MIN_PULSE_WIDTH_NS:g} ns is ignored in this toy model.
    - **Normal:** the chosen operation still meets `path delay + setup`.
    - **Success:** a **moderate** setup-time violation on the one failure-flag write is *modeled* as a missed write.
    - **Reset:** a pulse overlapping the normal edge (guard {EDGE_GUARD_NS:g} ns), or a severe timing violation, is *modeled* as a reset.

    These assumptions produce different outcome regions by calculation. They are **not**
    experimental probability curves, transistor simulations, or a guaranteed map of physical behavior.
    """)

st.divider()
st.subheader("4. Explain what happened")
st.write("Finding SUCCESS is only part of the task. First interpret the timing behavior, "
         "then predict one untested setting.")

with st.form("learning_check"):
    mcq_answers = []
    for i, (question, _, _) in enumerate(MCQ_BANK, start=1):
        mcq_answers.append(st.radio(
            question, st.session_state.mcq_options[i - 1],
            index=None, key=f"conceptual_q{i}"
        ))

    # One prediction per challenge, chosen from ten cases in PREDICTION_BANK.
    probe, target_name = st.session_state.quiz_prediction
    st.write(f"**Prediction:** Suppose the injected pulse has width **{probe.width_ns:.2f}**, "
             f"offset **{probe.offset_ns:.1f}**, and targets the **{target_name}** operation. "
             "What will the model report?")
    prediction = st.radio(
        "Predicted outcome", ["NORMAL", "RESET", "SUCCESS"],
        index=None, horizontal=True, key="prediction"
    )

    explanation = st.text_area("Explain your prediction using the waveform and timing rules",
                               placeholder="Explain your prediction and the relevant timing behavior...",
                               height=105, key="why_region")
    check = st.form_submit_button("Check learning answers", type="primary")

if check:
    if any(answer is None for answer in mcq_answers) or prediction is None or not explanation.strip():
        st.warning("Answer all four concept questions, make one prediction, and write a brief explanation.")
    else:
        mcq_results = [
            (selected, correct_answer)
            for selected, (_, _, correct_answer) in zip(mcq_answers, MCQ_BANK)
        ]
        actual = inject(probe, pwd, shift)
        correct = sum(selected == answer for selected, answer in mcq_results)
        correct += int(prediction == actual.status)
        st.session_state.learning_feedback = {
            "score": correct,
            "mcqs": mcq_results,
            "prediction": (prediction, actual, probe, target_name),
            "explanation": explanation,
        }

if st.session_state.learning_feedback is not None:
    feedback = st.session_state.learning_feedback
    score = feedback["score"]
    st.info(f"Concept and prediction score: **{score}/5**. "
            "Your written explanation needs instructor/peer review; it is not automatically graded.")

    for i, (selected, answer) in enumerate(feedback["mcqs"], start=1):
        result_text = "Correct" if selected == answer else "Incorrect"
        st.write(f"**Question {i}: {result_text}.** Correct answer: {answer}")

    selected, actual, probe, target_name = feedback["prediction"]
    result_text = "Correct" if selected == actual.status else "Incorrect"
    st.write(f"**Prediction: {result_text}.** Your answer: {selected}. "
             f"**Result: {actual.status}.** {actual.explanation}")

    with st.container(border=True):
        st.markdown("**Example written answer — shown after submission**")
        st.write(f"With width **{probe.width_ns:.2f} model ns** and offset "
                 f"**{probe.offset_ns:.1f} model ns** targeting **{target_name}**, "
                 f"the model reports **{actual.status}**. "
                 f"{actual.explanation}")

    if any(row["status"] == "SUCCESS" for row in st.session_state.attempts) and score == 5:
        st.success("Challenge cleared: you found a useful glitch and correctly interpreted the model.")
    else:
        st.caption("To finish the challenge, also find a SUCCESS outcome and answer all five checks correctly.")

st.divider()
st.caption("**Technical source:** ChipWhisperer Fault 1.2 'Clock Glitching to Bypass Password' ")
           
        
