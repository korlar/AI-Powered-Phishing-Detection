import html
import os
import re
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Configuration ---
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Phishing Detector",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded",
)


# --- Robust API Session Setup ---
def get_api_session():
    """Creates a requests session that automatically retries on transient failures."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


api_session = get_api_session()

# --- State Management ---
if "access_token" not in st.session_state:
    st.session_state.access_token = None


def login(username, password):
    try:
        response = api_session.post(
            f"{BACKEND_URL}/token", data={"username": username, "password": password}
        )
        if response.status_code == 200:
            st.session_state.access_token = response.json().get("access_token")
            st.toast("Logged in successfully!", icon="✅")
        else:
            st.error("Invalid credentials.")
    except requests.exceptions.RequestException as e:
        st.error(f"Backend connection failed: {e}")


def logout():
    """Clears the session token to log the user out."""
    st.session_state.access_token = None
    st.toast("Logged out securely.", icon="🔒")


def parse_uploaded_file(uploaded_file, key_suffix: str) -> list[str] | None:
    """Parses uploaded files of type CSV, TXT, or DOCX and returns a list of strings."""
    # Enforce 20MB file size limit (20 * 1024 * 1024 bytes)
    if uploaded_file.size > 20 * 1024 * 1024:
        st.error("Uploaded file size exceeds the 20MB limit.")
        return None

    filename = uploaded_file.name.lower()
    if filename.endswith(".csv"):
        try:
            df = pd.read_csv(uploaded_file)
            cols = list(df.columns)
            selected_col = st.selectbox(
                "Select column to analyze:", cols, key=f"csv_col_{key_suffix}"
            )
            return [str(x) for x in df[selected_col].dropna().tolist()]
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            return None
    elif filename.endswith(".txt"):
        try:
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            return [line.strip() for line in content.split("\n") if line.strip()]
        except Exception as e:
            st.error(f"Failed to read TXT: {e}")
            return None
    elif filename.endswith(".docx"):
        try:
            from io import BytesIO

            import docx

            doc = docx.Document(BytesIO(uploaded_file.read()))
            return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        except Exception as e:
            st.error(f"Failed to read Word document: {e}")
            return None
    return None


def run_batch_inference(items: list[str], input_type: str, headers: dict) -> list[dict] | None:
    """Processes batch inference in chunks of 32 to respect API limit."""
    chunk_size = 32
    all_results = []
    progress_bar = st.progress(0.0)

    for i in range(0, len(items), chunk_size):
        chunk = items[i : i + chunk_size]
        try:
            resp = api_session.post(
                f"{BACKEND_URL}/api/v1/predict/batch",
                json={"texts": chunk, "input_type": input_type},
                headers=headers,
            )
            if resp.status_code == 200:
                all_results.extend(resp.json().get("results", []))
            elif resp.status_code == 401:
                st.error("Session expired. Please log in again.")
                return None
            else:
                st.error(f"Batch API error (status {resp.status_code}): {resp.text}")
                return None
        except Exception as e:
            st.error(f"Inference request failed: {e}")
            return None
        progress_bar.progress(min((i + chunk_size) / len(items), 1.0))

    progress_bar.empty()
    return all_results


# --- Sidebar: Authentication ---
with st.sidebar:
    st.title("🔐 Access Control")
    if not st.session_state.access_token:
        # st.info("Please log in to use the engine.\n\n**Demo Credentials:**\n`admin` / your DEMO_PASSWORD")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            if submit:
                login(username, password)
    else:
        st.success("✅ Securely Authenticated")
        st.button("Logout", on_click=logout, use_container_width=True)

# --- Main UI ---
st.title("🛡️ AI-Powered Phishing Detection")
st.markdown("##### *Enterprise-grade machine learning for analyzing malicious URLs and emails.*")
st.divider()

if not st.session_state.access_token:
    st.warning("Please log in using the sidebar on the left to access the prediction engine.")
    st.stop()

tab_email, tab_url, tab_history = st.tabs(
    ["📧 Email Prediction", "🔗 URL Prediction", "📜 Prediction History"]
)
headers = {"Authorization": f"Bearer {st.session_state.access_token}"}


# Regex that matches http(s):// and www. URLs inside text
_URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+",
    re.IGNORECASE,
)


def extract_urls(text: str) -> list[str]:
    """Returns all URLs found in an email body string."""
    return _URL_RE.findall(text)


def render_explanation(importances, is_phishing, email_text: str = ""):
    """Renders the word importances as plain text.

    - Top-N highest-importance words → bold colored text.
    - Tokens that are part of a URL → bold colored text (always, URL is a strong signal).
    - Color scheme: red (#dc2626) for phishing, green (#16a34a) for legitimate/spam.
    - All other words → completely unstyled plain text.
    """
    if not importances:
        return

    # Choose highlight color based on classification verdict
    if is_phishing:
        highlight_color = "#dc2626"  # red — danger signal
        color_label = "red"
        verdict_emoji = "🚨"
    else:
        highlight_color = "#16a34a"  # green — safe/benign signal
        color_label = "green"
        verdict_emoji = "✅"

    st.markdown("### 🔍 Model Explainability (Saliency)")
    st.caption(
        f"Words in **{color_label}** are the key terms and URLs the model used to reach its "
        f"{verdict_emoji} decision. All other words appear as normal plain text."
    )

    # --- Top-N saliency words ---
    top_n_words = 7
    sorted_scores = sorted(importances, key=lambda x: abs(x["importance"]), reverse=True)
    flag_ids = {id(item) for item in sorted_scores[:top_n_words]}

    # --- URL token detection ---
    # Reconstruct the full token string to find URL character spans
    full_text = "".join(item["word"] for item in importances)
    url_spans = [(m.start(), m.end()) for m in _URL_RE.finditer(full_text)]

    def _in_url_span(char_offset: int, word_len: int) -> bool:
        """Returns True if the token at char_offset overlaps any detected URL span."""
        for start, end in url_spans:
            if char_offset < end and (char_offset + word_len) > start:
                return True
        return False

    html_parts = []
    char_pos = 0
    for item in importances:
        raw_word = item["word"]
        word = html.escape(raw_word)
        score = item["importance"]
        wlen = len(raw_word)
        is_url_token = _in_url_span(char_pos, wlen)
        char_pos += wlen

        if word == " ":
            word = "&nbsp;"
        elif word.startswith(" "):
            word = "&nbsp;" + word[1:]

        if id(item) in flag_ids or is_url_token:
            # Flag word or URL token → bold colored text matching verdict
            html_parts.append(
                f"<span style='color: {highlight_color}; font-weight: bold;' title='Score: {score:.3f}'>{word}</span>"
            )
        else:
            # Everything else → plain unstyled text
            html_parts.append(f"<span title='Score: {score:.3f}'>{word}</span>")

    html_content = "".join(html_parts)
    st.markdown(
        f"<div style='line-height: 1.9; font-size: 1.05em; padding: 14px 18px; "
        f"border-left: 3px solid {highlight_color}; border-radius: 4px;'>{html_content}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# TAB 1: EMAIL PREDICTION
# ============================================================
with tab_email:
    st.markdown("### 📧 Email Content Analysis")

    email_sub_tab1, email_sub_tab2 = st.tabs(["🔍 Single Prediction", "📂 Batch Prediction"])

    # --- Email: Single Prediction ---
    with email_sub_tab1:
        email_input = st.text_area(
            "Paste the email body below:",
            height=150,
            placeholder="e.g., URGENT: Your account has been compromised. Click here to verify your identity immediately...",
            key="email_single_input",
        )
        enable_explain = st.checkbox(
            "Enable Explainability [Highlight Words]", value=True, key="email_explain"
        )

        if st.button("Analyze Email", key="email_single_btn", type="primary"):
            if not email_input.strip():
                st.warning("Please enter some email text.")
            else:
                with st.spinner("Analyzing email content..."):
                    try:
                        resp = api_session.post(
                            f"{BACKEND_URL}/api/v1/predict",
                            json={
                                "text": email_input,
                                "input_type": "email",
                                "explain": enable_explain,
                            },
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                            if result["is_phishing"]:
                                st.error(
                                    f"🚨 **PHISHING DETECTED** (Confidence: {result['confidence']:.2%})\n\n**Reason:** {result.get('message', 'N/A')}"
                                )
                            else:
                                st.success(
                                    f"✅ **SAFE** (Confidence: {result['confidence']:.2%})\n\n**Reason:** {result.get('message', 'N/A')}"
                                )

                            if result.get("word_importances"):
                                render_explanation(
                                    result["word_importances"],
                                    result["is_phishing"],
                                    email_text=email_input,
                                )

                            # --- URL-in-Email Analysis ---
                            found_urls = extract_urls(email_input)
                            if found_urls:
                                st.markdown("### 🔗 URLs Detected in Email")
                                st.caption(
                                    f"Found **{len(found_urls)}** URL(s) in the email body. "
                                    "Each is scanned independently by the URL model."
                                )
                                for url in found_urls:
                                    try:
                                        url_resp = api_session.post(
                                            f"{BACKEND_URL}/api/v1/predict",
                                            json={
                                                "text": url,
                                                "input_type": "url",
                                                "explain": False,
                                            },
                                            headers=headers,
                                        )
                                        if url_resp.status_code == 200:
                                            url_result = url_resp.json()
                                            label = (
                                                "🚨 PHISHING"
                                                if url_result["is_phishing"]
                                                else "✅ SAFE"
                                            )
                                            conf = url_result["confidence"]
                                            with st.expander(
                                                f"{label}  —  `{url[:80]}`  ({conf:.2%})"
                                            ):
                                                if url_result["is_phishing"]:
                                                    st.error(
                                                        f"This URL was classified as **phishing** "
                                                        f"(confidence: {conf:.2%})"
                                                    )
                                                else:
                                                    st.success(
                                                        f"This URL appears **safe** "
                                                        f"(confidence: {conf:.2%})"
                                                    )
                                                st.code(url, language="text")
                                        else:
                                            st.warning(f"Could not scan URL: {url[:60]}")
                                    except Exception:
                                        st.warning(f"URL scan failed: {url[:60]}")

                        elif resp.status_code == 401:
                            st.error("Session expired. Please log in again.")
                            logout()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Request failed: {e}")

    # --- Email: Batch Prediction ---
    with email_sub_tab2:
        batch_source = st.radio(
            "Choose input method:", ["Paste Text", "Upload File"], key="email_batch_source"
        )
        lines = []

        if batch_source == "Paste Text":
            email_batch_input = st.text_area(
                "Paste multiple email texts (one per line):",
                height=200,
                placeholder="Dear customer, your account has been locked...\nCongratulations! You've won a prize...",
                key="email_batch_input",
            )
            if st.button("Analyze Email Batch", key="email_batch_btn", type="primary"):
                lines = [line.strip() for line in email_batch_input.split("\n") if line.strip()]
        else:
            uploaded_file = st.file_uploader(
                "Upload CSV, TXT, or DOCX file:",
                type=["csv", "txt", "docx"],
                key="email_file_uploader",
            )
            if uploaded_file:
                parsed_lines = parse_uploaded_file(uploaded_file, "email")
                if parsed_lines:
                    lines = parsed_lines
                    st.success(f"Successfully loaded {len(lines)} items from {uploaded_file.name}.")
                    analyze_file = st.button(
                        "Analyze Uploaded File", key="email_file_btn", type="primary"
                    )
                    if not analyze_file:
                        lines = []

        if lines:
            with st.spinner(f"Analyzing {len(lines)} emails..."):
                results = run_batch_inference(lines, "email", headers)
                if results:
                    st.subheader("📊 Batch Statistics")
                    df = pd.DataFrame(results)
                    df.insert(0, "Input Text", lines)
                    # Use the authoritative `label` field from the API response directly.
                    # Normalise "Legitimate" → "Safe" for display consistency.
                    df["Label"] = df["label"].map(
                        lambda lbl: "Safe" if lbl == "Legitimate" else lbl
                    )

                    total = len(df)
                    phishing_count = int((df["Label"] == "Phishing").sum())
                    spam_count = int((df["Label"] == "Spam").sum())
                    safe_count = int((df["Label"] == "Safe").sum())

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Analyzed", total)
                    c2.metric("🚨 Phishing", phishing_count)
                    c3.metric("⚠️ Spam", spam_count)
                    c4.metric("✅ Safe", safe_count)

                    st.bar_chart(df["Label"].value_counts())

                    # Download button
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv_data,
                        file_name="email_phishing_results.csv",
                        mime="text/csv",
                        key="email_download_btn",
                    )

                    st.divider()
                    st.subheader("📋 Detailed Results")
                    for i, res in enumerate(results):
                        lbl = df.at[i, "Label"]
                        prefix = (
                            "🚨 PHISHING"
                            if lbl == "Phishing"
                            else ("⚠️ SPAM" if lbl == "Spam" else "✅ SAFE")
                        )
                        reason = res.get("message", "N/A")
                        with st.expander(f"Email {i + 1}: {prefix} — {res['confidence']:.2%}"):
                            st.markdown(f"**Reason:** {reason}")
                            st.code(lines[i], language="text")


# ============================================================
# TAB 2: URL PREDICTION
# ============================================================
with tab_url:
    st.markdown("### 🔗 URL Analysis")

    url_sub_tab1, url_sub_tab2 = st.tabs(["🔍 Single Prediction", "📂 Batch Prediction"])

    # --- URL: Single Prediction ---
    with url_sub_tab1:
        url_input = st.text_input(
            "Enter a URL to analyze:",
            placeholder="e.g., http://suspicious-bank-login.com/verify",
            key="url_single_input",
        )

        if st.button("Analyze URL", key="url_single_btn", type="primary"):
            if not url_input.strip():
                st.warning("Please enter a URL.")
            else:
                with st.spinner("Analyzing URL..."):
                    try:
                        resp = api_session.post(
                            f"{BACKEND_URL}/api/v1/predict",
                            json={"text": url_input, "input_type": "url", "explain": False},
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                            if result["is_phishing"]:
                                st.error(
                                    f"🚨 **PHISHING DETECTED** (Confidence: {result['confidence']:.2%})\n\n**Reason:** {result.get('message', 'N/A')}"
                                )
                            else:
                                st.success(
                                    f"✅ **SAFE** (Confidence: {result['confidence']:.2%})\n\n**Reason:** {result.get('message', 'N/A')}"
                                )
                        elif resp.status_code == 401:
                            st.error("Session expired. Please log in again.")
                            logout()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Request failed: {e}")

    # --- URL: Batch Prediction ---
    with url_sub_tab2:
        batch_source_url = st.radio(
            "Choose input method:", ["Paste Text", "Upload File"], key="url_batch_source"
        )
        lines = []

        if batch_source_url == "Paste Text":
            url_batch_input = st.text_area(
                "Paste multiple URLs (one per line):",
                height=200,
                placeholder="http://google.com\nhttp://suspicious-link.net\nhttps://phishing-site.xyz/login",
                key="url_batch_input",
            )
            if st.button("Analyze URL Batch", key="url_batch_btn", type="primary"):
                lines = [line.strip() for line in url_batch_input.split("\n") if line.strip()]
        else:
            uploaded_file = st.file_uploader(
                "Upload CSV, TXT, or DOCX file:",
                type=["csv", "txt", "docx"],
                key="url_file_uploader",
            )
            if uploaded_file:
                parsed_lines = parse_uploaded_file(uploaded_file, "url")
                if parsed_lines:
                    lines = parsed_lines
                    st.success(f"Successfully loaded {len(lines)} items from {uploaded_file.name}.")
                    analyze_file = st.button(
                        "Analyze Uploaded File", key="url_file_btn", type="primary"
                    )
                    if not analyze_file:
                        lines = []

        if lines:
            with st.spinner(f"Analyzing {len(lines)} URLs..."):
                results = run_batch_inference(lines, "url", headers)
                if results:
                    st.subheader("📊 Batch Statistics")
                    df = pd.DataFrame(results)
                    df.insert(0, "Input Text", lines)
                    df["Label"] = df["is_phishing"].map({True: "Phishing", False: "Safe"})

                    total = len(df)
                    phishing_count = int(df["is_phishing"].sum())
                    safe_count = total - phishing_count

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Analyzed", total)
                    c2.metric("🚨 Phishing", phishing_count)
                    c3.metric("✅ Safe", safe_count)

                    st.bar_chart(df["Label"].value_counts())

                    # Download button
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv_data,
                        file_name="url_phishing_results.csv",
                        mime="text/csv",
                        key="url_download_btn",
                    )

                    st.divider()
                    st.subheader("📋 Detailed Results")
                    for i, res in enumerate(results):
                        prefix = "🚨 PHISHING" if res["is_phishing"] else "✅ SAFE"
                        reason = res.get("message", "N/A")
                        with st.expander(f"URL {i + 1}: {prefix} — {res['confidence']:.2%}"):
                            st.markdown(f"**Reason:** {reason}")
                            st.code(lines[i], language="text")

# ============================================================
# TAB 3: PREDICTION HISTORY
# ============================================================
with tab_history:
    st.markdown("### 📜 Prediction History Logs")
    st.caption("View and analyze historical scanning logs saved by the classification engine.")

    # Reload button
    if st.button("🔄 Refresh Log History", key="refresh_history_btn"):
        st.rerun()

    try:
        resp = api_session.get(f"{BACKEND_URL}/api/v1/history", headers=headers)
        if resp.status_code == 200:
            history_data = resp.json().get("history", [])
            if history_data:
                df_history = pd.DataFrame(history_data)

                # Metrics cards
                total_runs = len(df_history)
                phish_count = df_history[df_history["prediction_label"] == "Phishing"].shape[0]
                spam_count = df_history[df_history["prediction_label"] == "Spam"].shape[0]
                safe_count = df_history[df_history["prediction_label"] == "Legitimate"].shape[0]

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Checks", total_runs)
                c2.metric("🚨 Phishing Hits", phish_count)
                c3.metric("⚠️ Spam Hits", spam_count)
                c4.metric("✅ Safe Logs", safe_count)

                st.divider()

                # Interactive clear button
                if st.button("🗑️ Clear Log History", key="clear_history_btn", type="secondary"):
                    clear_resp = api_session.delete(
                        f"{BACKEND_URL}/api/v1/history", headers=headers
                    )
                    if clear_resp.status_code == 200:
                        st.toast("Logs successfully cleared!", icon="🗑️")
                        st.rerun()
                    else:
                        st.error("Failed to clear log history.")

                # Format dataframe for display
                df_disp = df_history[
                    [
                        "timestamp",
                        "input_type",
                        "input_text",
                        "prediction_label",
                        "confidence",
                        "reason",
                    ]
                ].copy()
                df_disp.rename(
                    columns={
                        "timestamp": "Timestamp",
                        "input_type": "Input Type",
                        "input_text": "Input Content",
                        "prediction_label": "Verdict Label",
                        "confidence": "Confidence Score",
                        "reason": "Reason Details",
                    },
                    inplace=True,
                )

                st.dataframe(df_disp, use_container_width=True)

                # Export history as CSV
                export_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M")
                csv_export = df_disp.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download History as CSV",
                    data=csv_export,
                    file_name=f"{export_ts}_prediction_history.csv",
                    mime="text/csv",
                    key="history_download_btn",
                )
            else:
                st.info("No scanning history found. Run some tests first!")
        elif resp.status_code == 401:
            st.error("Session expired. Please log in again.")
            logout()
        else:
            st.error("Failed to load prediction history from API.")
    except Exception as e:
        st.error(f"Error loading logs: {e}")


st.markdown("---")
st.caption(
    "🛡️ **Disclaimer:** This AI-powered phishing detector can occasionally make mistakes. "
    "Please double-check critical security classifications and never click on suspicious links, "
    "even if they are flagged as safe."
)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>Powered by Hugging Face RoBERTa & FastAPI <br> © Phishing Detection Research • Built and Developed by <b>[Kolade_Giwa]</b></div>",
    unsafe_allow_html=True,
)
