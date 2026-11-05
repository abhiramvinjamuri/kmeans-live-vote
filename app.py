"""Human vs K-Means: a classroom voting demo. Python 3.10+."""
import os
import hmac
import csv
import io
from urllib.parse import urlsplit, urlunsplit

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Human vs K-Means", page_icon="🔵", layout="wide")

from model import POINTS, INITIAL, STAGES
from storage import setting, change_setting, votes, vote_once, new_round

BLUE, ORANGE, NEUTRAL = "#2878C7", "#ED8D3D", "#9CA3AF"


def chart(labels=None, centroids=INITIAL, human=None):
    fig = go.Figure()
    for name, x in POINTS.items():
        if human is not None:
            color = [BLUE, ORANGE, NEUTRAL][human.get(name, 2)]
        elif labels is not None:
            color = BLUE if labels[name] == 0 else ORANGE
        else:
            color = NEUTRAL
        fig.add_trace(go.Scatter(
            x=[x], y=[0], mode="markers+text", text=[name],
            textposition="top center", textfont=dict(size=16),
            marker=dict(size=18, color=color, line=dict(width=1, color="white")),
            name=f"{name} = {POINTS[name]:.1f}", hovertemplate=f"{name} = {x:.1f}<extra></extra>", showlegend=False,
        ))
    if human is None:
        for k, x in enumerate(centroids):
            fig.add_trace(go.Scatter(
                x=[x], y=[-0.12], mode="markers+text", text=[f"C{k+1}"],
                textposition="bottom center", textfont=dict(size=15),
                marker=dict(size=26, symbol="star", color=BLUE if k == 0 else ORANGE,
                            line=dict(width=1, color="black")),
                hovertemplate=f"Centroid {k+1} = {x:.3f}<extra></extra>", showlegend=False,
            ))
    fig.update_layout(
        height=280, margin=dict(l=12, r=12, t=30, b=10),
        xaxis=dict(title="Value (one numerical feature)", range=[9.7, 13.3], dtick=0.5, showgrid=True),
        yaxis=dict(visible=False, range=[-0.45, 0.35], fixedrange=True),
        plot_bgcolor="rgba(128,128,128,0.045)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
    )
    return fig


def majority(counts):
    out = {}
    for name, (blue, orange) in counts.items():
        out[name] = 0 if blue > orange else 1 if orange > blue else 2
    return out


def secret_password():
    password = os.getenv("ADMIN_PASSWORD", "")
    if password:
        return password
    try:
        return st.secrets.get("ADMIN_PASSWORD", "")
    except (FileNotFoundError, KeyError):
        return ""


role = st.query_params.get("role", "vote")
if role != "presenter":
    st.title("Human vs K-Means")
    st.caption("Audience activity · 9 close values · 2 clusters")
    if setting("voting", "open") != "open":
        st.info("Voting is closed. Please look at the projected screen for the reveal.")
        st.stop()
    st.write("**Your challenge:** For each letter, select the centroid it appears closest to. "
             "The stars are the initial centroids. Blue = C1, Orange = C2.")
    st.plotly_chart(chart(), width="stretch", config={"displayModeBar": False})
    st.write(" · ".join(f"**{n}** = {v:.1f}" for n, v in POINTS.items()))
    st.caption("The letters identify values; there is no second feature. Stars are offset vertically for readability.")
    if "ballot_round" not in st.session_state:
        st.session_state.ballot_round = int(setting("round", "1"))
    with st.form("ballot", clear_on_submit=False):
        seat_text = st.text_input("Your assigned seat number (1–60)", placeholder="e.g., 17")
        st.caption("Each seat can submit only once. No name or email is collected.")
        choices = {}
        left, right = st.columns(2)
        for i, name in enumerate(POINTS):
            with (left if i < 5 else right):
                choices[name] = st.radio(f"{name} = {POINTS[name]:.1f}", ["Blue", "Orange"],
                                         index=None, horizontal=True, key=f"vote_{name}")
        submitted = st.form_submit_button("Submit my 9 choices", type="primary", width="stretch")
    if submitted:
        if not seat_text.isdigit() or not 1 <= int(seat_text) <= 60:
            st.error("Enter a seat number between 1 and 60.")
        elif any(value is None for value in choices.values()):
            st.error("Choose Blue or Orange for all nine points.")
        else:
            result = vote_once(int(seat_text), choices, st.session_state.ballot_round)
            if result == "recorded":
                st.success("Vote recorded. Watch the projector for the class results and K-Means reveal!")
            elif result == "closed":
                st.warning("Voting has closed. Your vote was not recorded.")
            elif result == "stale":
                st.session_state.ballot_round = int(setting("round", "1"))
                st.warning("The presenter started a new round. Review your choices and submit again.")
            elif result == "duplicate":
                st.warning("That seat has already voted in this round. Check your assigned seat number.")
            else:
                st.error("Check your seat number and choose a group for every value.")
    st.caption("This is a teaching activity. Cluster names are arbitrary; the centroids determine their meaning here.")
    st.stop()

# Presenter-only page. Change ADMIN_PASSWORD before deployment.
st.title("Presenter Dashboard · Human vs K-Means")
password = secret_password()
if not password:
    st.error("Set ADMIN_PASSWORD in your environment or in Streamlit Cloud Secrets to enable presenter mode.")
    st.stop()
if not st.session_state.get("presenter_ok", False):
    guess = st.text_input("Presenter password", type="password")
    if st.button("Unlock dashboard"):
        if hmac.compare_digest(guess.encode(), password.encode()):
            st.session_state.presenter_ok = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

if st.button("Lock dashboard"):
    st.session_state.presenter_ok = False
    st.rerun()

with st.expander("Audience link and QR code", expanded=True):
    default_url = os.getenv("PUBLIC_APP_URL", "")
    public_url = st.text_input("Paste your deployed app URL here", value=default_url,
                               placeholder="https://your-app.streamlit.app/")
    parsed = urlsplit(public_url)
    if parsed.scheme in ("http", "https") and parsed.netloc and not parsed.username:
        audience_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        st.link_button("Open audience voting", audience_url)
        st.code(audience_url, language=None)
        st.caption("Share the audience URL only. Your presenter address is:")
        st.code(audience_url + "?role=presenter", language=None)
        try:
            import qrcode
            qr = qrcode.make(audience_url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")
            st.image(buffer.getvalue(), width=220)
            st.download_button("Download audience QR", buffer.getvalue(), "audience-qr.png", "image/png")
        except ImportError:
            st.info("Install requirements.txt to enable the QR code.")
    elif public_url:
        st.warning("Enter a full http:// or https:// app address.")
    st.caption("Keep your presenter password private. Assign unique seat numbers 1–60.")

st.markdown("**Presenter flow:** open voting → close voting → reveal audience votes → show K-Means iterations.")
ctrl1, ctrl2, ctrl3 = st.columns(3)
with ctrl1:
    if st.button("Open voting", width="stretch"):
        change_setting("voting", "open")
        st.rerun()
with ctrl2:
    if st.button("Close voting", width="stretch"):
        change_setting("voting", "closed")
        st.rerun()
with ctrl3:
    if st.button("Start a new round", width="stretch", type="secondary"):
        st.session_state.confirm_reset = True
if st.session_state.get("confirm_reset", False):
    st.warning("Start a fresh round? Current votes are retained in the local database. Voting will be closed until you open it.")
    if st.button("Yes, start a new round"):
        new_round()
        st.session_state.confirm_reset = False
        st.rerun()

st.write("**Voting status:** " + ("OPEN" if setting("voting", "open") == "open" else "CLOSED"))

@st.fragment(run_every="3s")
def live_vote_panel():
    counts, total = votes()
    st.metric("Votes received", f"{total} / 60")
    rows = io.StringIO()
    writer = csv.writer(rows)
    writer.writerow(["Point", "Value", "Blue votes", "Orange votes"])
    for name, value in POINTS.items():
        writer.writerow([name, value, *counts[name]])
    st.download_button("Download vote totals (CSV)", rows.getvalue(), "class-vote-totals.csv", "text/csv")
    if total == 0:
        st.info("No votes yet. Participants join using the audience link/QR code.")
        return
    if setting("audience_reveal", "no") == "yes":
        st.subheader("The class's votes")
        # Keep charts simple: one grouped bar chart for all nine points.
        fig = go.Figure()
        fig.add_bar(name="Blue", x=list(POINTS), y=[counts[n][0] for n in POINTS], marker_color=BLUE)
        fig.add_bar(name="Orange", x=list(POINTS), y=[counts[n][1] for n in POINTS], marker_color=ORANGE)
        fig.update_layout(barmode="group", height=300, margin=dict(l=10, r=10, t=10, b=5),
                          xaxis_title="Data points", yaxis_title="Audience votes")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("Class majority per point; a tie is shown in grey.")
        st.plotly_chart(chart(human=majority(counts)), width="stretch",
                        config={"displayModeBar": False})

live_vote_panel()
reveal = setting("audience_reveal", "no") == "yes"
if st.button("Hide class results" if reveal else "Reveal class results", width="stretch"):
    change_setting("audience_reveal", "no" if reveal else "yes")
    st.rerun()

st.divider()
st.subheader("K-Means algorithm reveal")
st.caption("No calculations need to be presented. Explain the movement and reassignment verbally.")
current = int(setting("stage", "0"))
current = max(0, min(current, len(STAGES) - 1))
stepname, labels, centroids, explanation = STAGES[current]
left, middle, right = st.columns([1, 2, 1])
with left:
    if st.button("◀ Previous", disabled=current == 0, width="stretch"):
        change_setting("stage", current - 1)
        st.rerun()
with middle:
    st.markdown(f"<h3 style='text-align:center;margin:0'>Step {current+1}/{len(STAGES)} · {stepname}</h3>", unsafe_allow_html=True)
with right:
    if st.button("Next ▶", disabled=current == len(STAGES) - 1, width="stretch"):
        change_setting("stage", current + 1)
        st.rerun()
st.plotly_chart(chart(labels, centroids), width="stretch", config={"displayModeBar": False})
st.info(explanation)
st.caption(f"Blue centroid: {centroids[0]:.3f} · Orange centroid: {centroids[1]:.3f}")
with st.expander("Values and distances at this step"):
    st.dataframe([{"Point": n, "Value": v, "Distance to Blue": round(abs(v-centroids[0]), 3),
                   "Distance to Orange": round(abs(v-centroids[1]), 3)} for n,v in POINTS.items()],
                 hide_index=True, width="stretch")
if current == len(STAGES) - 1:
    counts, total = votes()
    if total:
        correct = sum(counts[n][labels[n]] for n in POINTS)
        st.write(f"**Audience agreement with final K-Means assignments:** "
                 f"{correct} of {total * len(POINTS)} individual point choices "
                 f"({correct / (total * len(POINTS)):.0%}).")
        st.caption("Agreement is not a measure of objective truth. K-Means is one clustering method, not an answer key.")

st.caption("Tip: for the classroom, hide Streamlit's sidebar/menu and use browser full-screen mode (F11).")
