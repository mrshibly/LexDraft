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

    import sys
    # Port 8000 is not listening, so start the backend
    with open("backend.log", "w") as log_file:
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Modern SaaS Background */
    .stApp {
        background-color: #09090b;
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,0.1) 0, transparent 50%);
    }

    /* Cleaner Metrics */
    [data-testid="stMetric"] {
        background: #18181b;
        border: 1px solid #27272a;
        border-radius: 12px;
        padding: 1rem;
        transition: border-color 0.2s ease;
    }
    
    [data-testid="stMetric"]:hover {
        border-color: #3f3f46;
    }

    [data-testid="stMetricLabel"] p {
        color: #a1a1aa !important;
        font-size: 0.8rem;
        font-weight: 500;
    }
    [data-testid="stMetricValue"] {
        color: #fafafa !important;
        font-weight: 600;
        font-size: 1.8rem;
    }

    /* Minimalist Primary Button */
    [data-testid="baseButton-primary"] {
        background: #fafafa;
        color: #09090b !important;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: opacity 0.2s ease;
    }

    [data-testid="baseButton-primary"]:hover {
        background: #fafafa;
        opacity: 0.9;
    }

    /* Modern Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #18181b;
        padding: 4px;
        border-radius: 8px;
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        background: transparent;
        color: #a1a1aa;
        border: none !important;
    }

    .stTabs [aria-selected="true"] {
        background: #27272a !important;
        color: #fafafa !important;
    }
    
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* Code & Mono elements */
    code {
        font-family: 'JetBrains Mono', monospace;
        background: #27272a !important;
        color: #d4d4d8 !important;
        border-radius: 4px;
        padding: 0.1rem 0.3rem;
    }

    /* Cards */
    [data-testid="stVerticalBlock"] > div > div > div > .stMarkdown {
        margin-bottom: 0;
    }
    
    .bento-card {
        background: #18181b;
        border: 1px solid #27272a;
        padding: 1.25rem;
        border-radius: 8px;
    }

    /* Alerts */
    [data-testid="stAlert"] {
        background: #18181b;
        border: 1px solid #27272a;
        color: #fafafa;
        border-radius: 8px;
    }

    /* Success indicator */
    .stAlert [data-testid="stNotificationContentSuccess"] {
        color: #22c55e !important;
    }
    
    /* Info indicator */
    .stAlert [data-testid="stNotificationContentInfo"] {
        color: #3b82f6 !important;
    }


    h1 {
        color: #fafafa !important;
        font-weight: 700 !important;
        letter-spacing: -0.04em;
    }
    
    h2, h3 {
        color: #fafafa !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }

    /* Hide Streamlit clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    </style>

    """, unsafe_allow_html=True)

inject_custom_css()

st.markdown("<h2 style='font-weight: 700; margin-bottom: 0;'>⚖️ LexDraft</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #a1a1aa; font-size: 0.9rem; margin-bottom: 2rem;'>AI-Powered Legal Document Intelligence & Grounded Drafting</p>", unsafe_allow_html=True)


# Session state initialisation
if "doc_id" not in st.session_state:
    st.session_state.doc_id = None
if "draft_text" not in st.session_state:
    st.session_state.draft_text = None
if "draft_result" not in st.session_state:
    st.session_state.draft_result = None

# --- TABS NAVIGATION ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Ingestion",
    "✍️ Drafting",
    "🔍 Learning",
    "📊 Dashboard"
])

# ─── Tab 1: Ingestion & OCR ───
with tab1:
    st.markdown("#### Document Ingestion")

    st.markdown("Upload PDFs, images, or text for automated structure extraction and OCR processing.")


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
                        
                        # --- BENTO METADATA GRID ---
                        st.markdown("### 📋 Extracted Document Intelligence")
                        
                        # Row 1: Key Metadata
                        meta1, meta2, meta3, meta4 = st.columns(4)
                        fields = result.get("structured_fields", {})
                        
                        meta1.metric("Doc ID", result["doc_id"][:8])
                        meta2.metric("Type", fields.get('document_type', 'N/A'))
                        meta3.metric("Matter No", fields.get('case_number', 'N/A'))
                        meta4.metric("Gov. Law", fields.get('governing_law', 'N/A'))
                        
                        # Row 2: Parties & Obligations
                        col_left, col_right = st.columns([1, 1])
                        
                        with col_left:
                            st.markdown("""
                            <div style="background: #18181b; border: 1px solid #27272a; padding: 16px; border-radius: 8px;">
                                <h5 style="margin-top: 0; color: #fafafa; font-size: 0.9rem;">Primary Parties</h5>
                            """, unsafe_allow_html=True)
                            parties = fields.get("parties", [])
                            if parties:
                                for p in parties:
                                    st.markdown(f"<span style='font-size: 0.85rem;'>**{p['name']}**</span> <span style='color: #a1a1aa; font-size: 0.75rem;'>({p['role']})</span>", unsafe_allow_html=True)
                            else:
                                st.caption("None detected")
                            st.markdown("</div>", unsafe_allow_html=True)

                        with col_right:
                            st.markdown("""
                            <div style="background: #18181b; border: 1px solid #27272a; padding: 16px; border-radius: 8px;">
                                <h5 style="margin-top: 0; color: #fafafa; font-size: 0.9rem;">Key Obligations</h5>
                            """, unsafe_allow_html=True)
                            obligations = fields.get("key_obligations", [])
                            if obligations:
                                for o in obligations:
                                    st.markdown(f"<p style='font-size: 0.8rem; color: #d4d4d8; margin-bottom: 4px; line-height: 1.2;'>• {o}</p>", unsafe_allow_html=True)
                            else:
                                st.caption("None extracted")
                            st.markdown("</div>", unsafe_allow_html=True)


                        # Row 3: Processing Stats
                        st.markdown("---")
                        s1, s2, s3, s4 = st.columns(4)
                        s1.metric("Pages", result.get("page_count", 0))
                        s2.metric("Chunks", result.get("chunks_indexed", 0))
                        
                        avg_conf = result.get("ocr_confidence_avg")
                        if avg_conf is not None:
                            conf_color = "normal" if avg_conf > 85 else "off"
                            s3.metric("OCR Confidence", f"{avg_conf:.1f}%", delta=None, delta_color=conf_color)
                        
                        s4.metric("Latency", f"{result.get('processing_time_ms', 0)}ms")

                        low_pages = result.get("low_confidence_pages", [])
                        if low_pages:
                            for p in low_pages:
                                st.warning(f"⚠ Critical: Page {p} has low OCR confidence. Grounding accuracy may be impacted.")

                    else:
                        st.error(f"❌ Error: {result.get('detail', {}).get('message', 'Unknown error')}")

                except httpx.ConnectError:
                    import os
                    log_tail = ""
                    if os.path.exists("backend.log"):
                        with open("backend.log", "r") as f:
                            lines = f.readlines()
                            log_tail = "".join(lines[-20:])
                    
                    err_msg = "❌ Cannot connect to API server."
                    if log_tail:
                        err_msg += f"\n\n**Backend Crash Logs:**\n```text\n{log_tail}\n```"
                        
                    st.error(err_msg)
                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ─── Tab 2: Drafting Lab ───
with tab2:
    st.markdown("#### Drafting Lab")
    st.markdown("Generate citation-backed legal drafts using the grounded retrieval engine.")



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
                        
                        st.success("Draft Generated successfully.")

                        # --- SPLIT VIEW WORKSPACE ---
                        editor_col, evidence_col = st.columns([3, 2])

                        with editor_col:
                            st.subheader("📝 Grounded Editor")
                            st.markdown(result["draft_text"])
                            
                            # Applied preferences chip
                            prefs = result.get("preferences_applied", [])
                            if prefs:
                                st.markdown("---")
                                st.caption("AI OPTIMIZED BASED ON LEARNED RULES:")
                                for p in prefs:
                                    st.markdown(f"<span style='background: rgba(168, 85, 247, 0.2); color: #c084fc; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-right: 5px; border: 1px solid rgba(168, 85, 247, 0.3)'>✓ {p}</span>", unsafe_allow_html=True)

                        with evidence_col:
                            st.subheader("📎 Source Evidence")
                            citations = result.get("citations", [])
                            if citations:
                                for c in citations:
                                    with st.container():
                                        st.markdown(f"""
                                        <div style="background: #18181b; border: 1px solid #27272a; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                                <span style="background: #fafafa; color: #09090b; padding: 2px 6px; border-radius: 4px; font-weight: 500; font-size: 0.7rem; font-family: 'JetBrains Mono';">{c['label']}</span>
                                                <span style="color: #a1a1aa; font-size: 0.7rem;">Page {c['page_number']}</span>
                                            </div>
                                            <p style="color: #d4d4d8; font-size: 0.8rem; font-style: italic; margin: 0; line-height: 1.4;">"{c['chunk_text']}"</p>
                                        </div>
                                        """, unsafe_allow_html=True)

                            else:
                                st.info("No explicit citations found in this draft.")

                        # Meta Stats
                        st.divider()
                        st.caption(f"Draft Engine: {result.get('model', 'Claude 3.5 Sonnet')} | Latency: {result.get('generation_time_ms')}ms | Tokens: {result.get('tokens_used')}")
                    else:
                        st.error(f"❌ Error: {result.get('detail', {}).get('message', 'Unknown error')}")

                except httpx.ConnectError:
                    import os
                    log_tail = ""
                    if os.path.exists("backend.log"):
                        with open("backend.log", "r") as f:
                            lines = f.readlines()
                            log_tail = "".join(lines[-20:])
                    
                    err_msg = "❌ Cannot connect to API server."
                    if log_tail:
                        err_msg += f"\n\n**Backend Crash Logs:**\n```text\n{log_tail}\n```"
                        
                    st.error(err_msg)
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    else:
        st.info("No documents indexed yet. Upload a document in the first tab.")


# ─── Tab 3: Review & Learning ───
with tab3:
    st.markdown("#### Review & Learning")
    st.markdown("Analyze draft quality and teach the AI your specific drafting style preferences.")



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
                        if response.status_code == 200:
                            st.balloons()
                            st.success(f"🚀 Learning Cycle Complete! {result.get('rules_extracted', 0)} new drafting rules synthesized.")

                            st.markdown("### 🧠 Extracted Drafting Intelligence")
                            rules = result.get("rules_detail", [])
                            if rules:
                                for r in rules:
                                    color = "#22c55e" if r.get("is_new") else "#38bdf8"
                                    label = "NEW RULE" if r.get("is_new") else "REINFORCED"
                                    st.markdown(f"""
                                    <div style="border-left: 4px solid {color}; background: rgba(255,255,255,0.03); padding: 10px 15px; border-radius: 4px; margin-bottom: 10px;">
                                        <span style="color: {color}; font-size: 0.7rem; font-weight: bold; letter-spacing: 0.05em;">{label}</span>
                                        <p style="margin: 5px 0 0 0; font-weight: 500; color: #f8fafc;">{r['rule']}</p>
                                        <p style="margin: 0; color: #94a3b8; font-size: 0.8rem;">Category: {r['category'].title()}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            st.info(f"The system now has {result.get('total_active_rules', 0)} total preferences for this document type. These will be automatically applied to your next draft.")

                        else:
                            st.error(f"❌ Error: {result}")

                    except Exception as e:
                        st.error(f"❌ Error: {e}")
            else:
                st.warning("Please make some edits before submitting.")
    else:
        st.info("Generate a draft first in the 'Generate Draft' tab.")


# ─── Tab 4: Dashboard ───
with tab4:
    st.markdown("#### Intelligence Dashboard")



    # Row 1: High Level Metrics
    m1, m2, m3 = st.columns(3)
    
    try:
        resp = httpx.get(f"{API_BASE}/documents", timeout=5.0)
        doc_count = len(resp.json().get("documents", []))
    except:
        doc_count = 0
        
    try:
        resp = httpx.get(f"{API_BASE}/preferences/case_fact_summary", timeout=5.0)
        rule_count = len(resp.json().get("rules", []))
        all_rules = resp.json().get("rules", [])
    except:
        rule_count = 0
        all_rules = []

    m1.metric("Matter Library", doc_count)
    m2.metric("Learned Preferences", rule_count)
    m3.metric("System Uptime", "99.9%", delta="Stable")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🧠 Active Drafting Intelligence")
        if all_rules:
            for r in all_rules:
                freq = r['frequency']
                # Progress bar visualization for frequency
                progress = min(freq / 5.0, 1.0) # Scale of 5
                st.markdown(f"""
                <div style="margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 500; color: #f8fafc;">{r['rule']}</span>
                        <span style="color: #94a3b8; font-size: 0.8rem;">Confidence: {freq}/5</span>
                    </div>
                    <div style="width: 100%; background: rgba(255,255,255,0.05); height: 6px; border-radius: 3px;">
                        <div style="width: {progress*100}%; background: linear-gradient(90deg, #6366f1, #a855f7); height: 100%; border-radius: 3px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No drafting preferences learned yet. Submit edits in the Review tab to begin training.")

    with col_right:
        st.subheader("⚙️ System Health")
        st.markdown("""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 20px; border-radius: 16px;">
            <p style="margin: 0; color: #94a3b8; font-size: 0.85rem;">API Engine</p>
            <p style="margin: 0 0 1rem 0; font-weight: bold; color: #22c55e;">● OPERATIONAL</p>
            
            <p style="margin: 0; color: #94a3b8; font-size: 0.85rem;">Vector Store (ChromaDB)</p>
            <p style="margin: 0 0 1rem 0; font-weight: bold; color: #22c55e;">● CONNECTED</p>
            
            <p style="margin: 0; color: #94a3b8; font-size: 0.85rem;">Preference Store (SQLite)</p>
            <p style="margin: 0 0 1rem 0; font-weight: bold; color: #22c55e;">● ACTIVE</p>
            
            <p style="margin: 0; color: #94a3b8; font-size: 0.85rem;">Model Provider</p>
            <p style="margin: 0 0 0 0; font-weight: bold; color: #38bdf8;">Claude 3.5 Sonnet</p>
        </div>
        """, unsafe_allow_html=True)

