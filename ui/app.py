"""
Streamlit UI for LexDraft.
Four tabs: Upload & Process, Generate Draft, Review & Edit, System Status.
"""
import streamlit as st
import httpx
import json
import subprocess
import time
import socket

@st.cache_resource(show_spinner=False)
def start_backend():
    """Start the FastAPI backend as a subprocess if not already running."""
    def is_port_open():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', 8000)) == 0

    if is_port_open():
        return True

    # Port 8000 is not listening, so start the backend
    with open("backend.log", "w") as log_file:
        subprocess.Popen(
            ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
    
    # Wait for the server to be ready (model loading can take 20-30s on cloud)
    for _ in range(45):
        if is_port_open():
            return True
        time.sleep(1)
        
    return False

if 'backend_started' not in st.session_state:
    with st.spinner("Booting up AI models and backend API... (this takes ~20-30s on first load)"):
        start_backend()
    st.session_state.backend_started = True

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(
    page_title="LexDraft", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main App Background (Dark Mode optimization) */
    .stApp {
        background: radial-gradient(circle at 50% -20%, #1e1b4b 0%, #0f172a 100%);
    }

    /* Glassmorphism for metrics */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease, background 0.3s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.3);
        background: rgba(255, 255, 255, 0.06);
    }

    /* Metric Labels & Values */
    [data-testid="stMetricLabel"] p {
        color: #94a3b8 !important;
        font-size: 0.95rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 700;
        font-size: 2.2rem;
    }

    /* Primary buttons with vibrant gradients */
    [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
        letter-spacing: 0.02em;
    }

    [data-testid="baseButton-primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
    }
    
    [data-testid="baseButton-primary"]:active {
        transform: translateY(0px);
    }

    /* File uploader styling */
    [data-testid="stFileUploadDropzone"] {
        background: rgba(255, 255, 255, 0.02);
        border: 2px dashed rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        background: rgba(99, 102, 241, 0.05);
        border-color: rgba(99, 102, 241, 0.8);
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        background-color: transparent;
        padding-bottom: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        background: transparent;
        border: none;
        color: #94a3b8;
        transition: color 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        color: #f8fafc;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #a855f7;
        height: 3px;
        border-radius: 3px 3px 0 0;
    }

    /* Text area and inputs */
    .stTextArea textarea, .stTextInput input, .stSelectbox > div > div {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(0, 0, 0, 0.2);
        color: #f8fafc;
        transition: all 0.2s ease;
    }
    
    .stTextArea textarea:focus, .stTextInput input:focus, .stSelectbox > div > div:focus-within {
        border-color: #a855f7;
        box-shadow: 0 0 0 1px #a855f7;
        background: rgba(0, 0, 0, 0.3);
    }

    /* Success/Info/Warning alerts with glassmorphism */
    [data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(8px);
        color: #f8fafc;
    }

    /* Markdown text */
    .stMarkdown p {
        color: #cbd5e1;
        line-height: 1.6;
    }

    /* Headers */
    h1 {
        background: -webkit-linear-gradient(45deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem !important;
    }
    h2, h3 {
        color: #f8fafc !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }

    /* Hide default streamlit menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

st.title("⚖️ LexDraft")
st.markdown("<h3 style='color: #94a3b8; font-weight: 400; margin-top: -1rem; margin-bottom: 2rem;'>AI-Powered Legal Document Processing & Grounded Drafting</h3>", unsafe_allow_html=True)

# Session state initialisation
if "doc_id" not in st.session_state:
    st.session_state.doc_id = None
if "draft_text" not in st.session_state:
    st.session_state.draft_text = None
if "draft_result" not in st.session_state:
    st.session_state.draft_result = None

tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Upload & Process",
    "✍️ Generate Draft",
    "🔍 Review & Edit",
    "📊 System Status"
])


# ─── Tab 1: Upload & Process ───
with tab1:
    st.header("Upload a Legal Document")

    uploaded_file = st.file_uploader(
        "Drag and drop a file or click to browse",
        type=["pdf", "png", "jpg", "jpeg", "tiff", "txt"],
        help="Supported formats: PDF, PNG, JPG, TIFF, TXT"
    )

    if uploaded_file:
        if st.button("🔄 Process Document", type="primary"):
            with st.spinner("Processing document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    response = httpx.post(f"{API_BASE}/ingest", files=files, timeout=120.0)
                    result = response.json()

                    if response.status_code == 200:
                        st.session_state.doc_id = result["doc_id"]
                        st.success(f"✅ Document processed! Doc ID: `{result['doc_id']}`")

                        col1, col2 = st.columns(2)

                        with col1:
                            st.subheader("📋 Structured Fields")
                            fields = result.get("structured_fields", {})
                            st.write(f"**Document Type:** {fields.get('document_type', 'N/A')}")

                            parties = fields.get("parties", [])
                            if parties:
                                st.write("**Parties:**")
                                for p in parties:
                                    st.write(f"  - {p['name']} ({p['role']})")

                            for key in ["effective_date", "filing_date", "case_number", "governing_law"]:
                                val = fields.get(key)
                                if val:
                                    st.write(f"**{key.replace('_', ' ').title()}:** {val}")

                            obligations = fields.get("key_obligations", [])
                            if obligations:
                                st.write("**Key Obligations:**")
                                for o in obligations:
                                    st.write(f"  - {o}")

                        with col2:
                            st.subheader("📊 Processing Stats")
                            st.metric("Pages", result.get("page_count", 0))
                            st.metric("Words", result.get("word_count", 0))
                            st.metric("Chunks Indexed", result.get("chunks_indexed", 0))
                            st.metric("Processing Time", f"{result.get('processing_time_ms', 0)}ms")

                            avg_conf = result.get("ocr_confidence_avg")
                            if avg_conf is not None:
                                st.metric("OCR Confidence", f"{avg_conf:.1f}%")

                            low_pages = result.get("low_confidence_pages", [])
                            if low_pages:
                                for p in low_pages:
                                    st.warning(f"⚠ Page {p} has low OCR confidence")
                    else:
                        st.error(f"❌ Error: {result.get('detail', {}).get('message', 'Unknown error')}")

                except httpx.ConnectError:
                    st.error("❌ Cannot connect to API server. Run: `uvicorn api.main:app --reload`")
                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ─── Tab 2: Generate Draft ───
with tab2:
    st.header("Generate Case Fact Summary")

    # Fetch document list
    doc_list = []
    try:
        resp = httpx.get(f"{API_BASE}/documents", timeout=10.0)
        if resp.status_code == 200:
            docs = resp.json().get("documents", [])
            doc_list = [f"{d['doc_id']} — {d.get('source_file', 'unknown')}" for d in docs]
    except Exception:
        pass

    if doc_list:
        selected = st.selectbox("Select document", doc_list)
        selected_doc_id = selected.split(" — ")[0] if selected else None

        if st.button("✍️ Generate Draft", type="primary"):
            with st.spinner("Generating draft... (this may take 15-30 seconds)"):
                try:
                    response = httpx.post(
                        f"{API_BASE}/draft",
                        json={"doc_id": selected_doc_id, "draft_type": "case_fact_summary", "top_k": 8},
                        timeout=120.0
                    )
                    result = response.json()

                    if response.status_code == 200:
                        st.session_state.draft_text = result.get("draft_text", "")
                        st.session_state.draft_result = result

                        # Display draft
                        st.markdown(result["draft_text"])

                        # Show applied preferences
                        prefs = result.get("preferences_applied", [])
                        if prefs:
                            st.divider()
                            st.subheader("✓ Applied Preferences")
                            for p in prefs:
                                st.info(f"✓ {p}")

                        # Citations
                        citations = result.get("citations", [])
                        if citations:
                            with st.expander("📎 Evidence Citations", expanded=False):
                                for c in citations:
                                    st.markdown(
                                        f"**{c['label']}** — {c['source_file']}, Page {c['page_number']} "
                                        f"(relevance: {c['relevance_score']:.2f})"
                                    )
                                    st.caption(c['chunk_text'])
                                    st.divider()

                        # Stats
                        st.caption(
                            f"Draft ID: {result.get('draft_id')} | "
                            f"Tokens: {result.get('tokens_used')} | "
                            f"Time: {result.get('generation_time_ms')}ms"
                        )
                    else:
                        st.error(f"❌ Error: {result.get('detail', {}).get('message', 'Unknown error')}")

                except httpx.ConnectError:
                    st.error("❌ Cannot connect to API server.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    else:
        st.info("No documents indexed yet. Upload a document in the first tab.")


# ─── Tab 3: Review & Edit ───
with tab3:
    st.header("Review & Edit Draft")

    if st.session_state.draft_text:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Original Draft")
            st.text_area(
                "Original (read-only)",
                value=st.session_state.draft_text,
                height=500,
                disabled=True,
                key="original_draft_display"
            )

        with col2:
            st.subheader("Your Edited Version")
            edited = st.text_area(
                "Edit the draft below",
                value=st.session_state.draft_text,
                height=500,
                key="edited_draft_input"
            )

        operator_note = st.text_input("Operator note (optional)", key="operator_note_input")

        if st.button("📤 Submit Edit", type="primary"):
            if edited and edited.strip() != st.session_state.draft_text.strip():
                with st.spinner("Analysing edit..."):
                    try:
                        doc_id = st.session_state.draft_result.get("doc_id", "unknown") if st.session_state.draft_result else "unknown"
                        response = httpx.post(
                            f"{API_BASE}/feedback",
                            json={
                                "doc_id": doc_id,
                                "draft_type": "case_fact_summary",
                                "original_draft": st.session_state.draft_text,
                                "edited_draft": edited,
                                "operator_note": operator_note or None
                            },
                            timeout=120.0
                        )
                        result = response.json()

                        if response.status_code == 200:
                            st.success(f"✅ Edit submitted! {result.get('rules_extracted', 0)} rules extracted.")

                            rules = result.get("rules_detail", [])
                            for r in rules:
                                marker = "🆕" if r.get("is_new") else "🔄"
                                st.success(f"{marker} {r['rule']} ({r['category']})")

                            st.metric("Total Active Rules", result.get("total_active_rules", 0))
                        else:
                            st.error(f"❌ Error: {result}")

                    except Exception as e:
                        st.error(f"❌ Error: {e}")
            else:
                st.warning("Please make some edits before submitting.")
    else:
        st.info("Generate a draft first in the 'Generate Draft' tab.")


# ─── Tab 4: System Status ───
with tab4:
    st.header("System Status")

    try:
        # Health check
        health = httpx.get(f"{API_BASE}/health", timeout=5.0)
        if health.status_code == 200:
            st.success("🟢 API Server: Online")
        else:
            st.error("🔴 API Server: Error")
    except Exception:
        st.error("🔴 API Server: Offline")

    # Documents
    try:
        resp = httpx.get(f"{API_BASE}/documents", timeout=10.0)
        if resp.status_code == 200:
            docs = resp.json().get("documents", [])
            st.metric("Documents Indexed", len(docs))
            if docs:
                st.subheader("Indexed Documents")
                for d in docs:
                    st.write(f"- **{d.get('source_file', 'unknown')}** (ID: `{d['doc_id']}`)")
    except Exception:
        st.metric("Documents Indexed", "N/A")

    # Preferences
    try:
        resp = httpx.get(f"{API_BASE}/preferences/case_fact_summary", timeout=10.0)
        if resp.status_code == 200:
            rules = resp.json().get("rules", [])
            st.metric("Learned Rules", len(rules))
            if rules:
                st.subheader("Active Learned Preferences")
                for r in rules:
                    freq_bar = "█" * r["frequency"]
                    st.write(f"- **{r['rule']}** ({r['category']}) — Frequency: {freq_bar} ({r['frequency']})")
    except Exception:
        st.metric("Learned Rules", "N/A")
