import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime
import re
#importing the reverse relation functions
from reverse_relation import search_plant_to_snps, search_snp_to_diseases

# ---------- Neo4j Connection ----------
uri = "bolt://localhost:7687"
user = "neo4j"
password = "Sonal@2004"

driver = GraphDatabase.driver(uri, auth=(user, password))


# ---------- Functions ----------

def search_node(label, node_id):
    query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
    
    try:
        with driver.session() as session:
            result = session.run(query, {"id": node_id})
            record = result.single()
            
            if record:
                return dict(record["n"])
            else:
                return None
    except Exception as e:
        st.error(f"Database error while searching node: {str(e)}")
        return None


def get_analytics_data():
    """Fetch real analytics data from the database"""
    try:
        with driver.session() as session:
            # Count nodes by type
            node_query = """
            MATCH (n) 
            RETURN labels(n)[0] as label, count(n) as count 
            ORDER BY count DESC
            """
            node_results = session.run(node_query)
            node_counts = {record["label"]: record["count"] for record in node_results}
            
            # Count relationships by type
            rel_query = """
            MATCH ()-[r]->() 
            RETURN type(r) as type, count(r) as count 
            ORDER BY count DESC
            """
            rel_results = session.run(rel_query)
            rel_counts = {record["type"]: record["count"] for record in rel_results}
            
            return node_counts, rel_counts
    except Exception as e:
        st.error(f"Database error while fetching analytics: {str(e)}")
        return {}, {}

def init_search_stats():
    """Initialize per-session search counters for analytics."""
    if "search_stats" not in st.session_state:
        st.session_state.search_stats = {
            "total_attempts": 0,
            "total_success": 0,
            "by_type": {
                "single_node_disease": {"attempts": 0, "success": 0},
                "single_node_plant": {"attempts": 0, "success": 0},
                "single_node_snp": {"attempts": 0, "success": 0},
                "relationship_disease_to_snp": {"attempts": 0, "success": 0},
                "relationship_snp_to_plant": {"attempts": 0, "success": 0},
                "relationship_snp_to_disease": {"attempts": 0, "success": 0},
                "relationship_plant_to_snp": {"attempts": 0, "success": 0},
            },
        }


def log_search(query_type, success):
    """Log a search attempt + whether it returned results."""
    init_search_stats()
    st.session_state.search_stats["total_attempts"] += 1
    if success:
        st.session_state.search_stats["total_success"] += 1
    if query_type not in st.session_state.search_stats["by_type"]:
        st.session_state.search_stats["by_type"][query_type] = {"attempts": 0, "success": 0}
    st.session_state.search_stats["by_type"][query_type]["attempts"] += 1
    if success:
        st.session_state.search_stats["by_type"][query_type]["success"] += 1


def search_disease_with_snps(disease_id, limit=200):
    query = """
    MATCH (d:disease {id: $id})
    OPTIONAL MATCH (d)-[r:ASSOCIATED_WITH]->(s:rsid)
    RETURN d, r, s
    LIMIT $limit
    """

    data = {"disease": None, "snps": []}

    try:
        with driver.session() as session:
            results = session.run(query, {"id": disease_id, "limit": limit})

            for record in results:
                d = record["d"]
                r = record["r"]
                s = record["s"]

                if d:
                    data["disease"] = dict(d)

                if s:
                    data["snps"].append({
                        "snp": dict(s),
                        "relation": dict(r) if r else {}
                    })
                    
    except Exception as e:
        st.error(f"Database error while fetching disease data: {str(e)}")
        return {"disease": None, "snps": []}

    return data


def search_snp_with_plants(snp_id, limit=200):
    query = """
    MATCH (s:rsid {id: $id})
    OPTIONAL MATCH (s)-[r:ASSOCIATED_WITH_PLANT]->(p:plant)
    RETURN s, r, p
    LIMIT $limit
    """

    data = {"snp": None, "plants": []}

    try:
        with driver.session() as session:
            results = session.run(query, {"id": snp_id, "limit": limit})

            for record in results:
                s = record["s"]
                r = record["r"]
                p = record["p"]

                if s:
                    data["snp"] = dict(s)

                if p:
                    data["plants"].append({
                        "plant": dict(p),
                        "relation": dict(r) if r else {}
                    })
                    
    except Exception as e:
        st.error(f"Database error while fetching SNP data: {str(e)}")
        return {"snp": None, "plants": []}

    return data


# ---------- UI Configuration ----------
st.set_page_config(
    page_title="SNP–Disease–Plant chatbox",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Light-only accent styling (theme is locked via .streamlit/config.toml)
st.markdown(
    """
<style>
    :root {
        --chat-accent: #667eea;
        --chat-accent-2: #764ba2;
        --chat-border: rgba(49, 51, 63, 0.12);
        --chat-text: #31333f;
        --chat-text-soft: #5c6077;
        --chat-heading: #1a1d2e;
    }
    html, body, .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] .main,
    [data-testid="stAppViewContainer"] .stMain {
        background-color: #f0f2f6 !important;
        color: var(--chat-text) !important;
    }
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-top: 1rem;
        background-color: transparent !important;
        max-width: 1200px;
    }
    header[data-testid="stHeader"] {
        background-color: #f0f2f6 !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid var(--chat-border);
    }
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    .stWidgetLabel p {
        color: #31333f !important;
    }
    .main h1 {
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
        line-height: 1.12 !important;
        color: var(--chat-heading) !important;
    }
    .main h2, .main h3 {
        font-weight: 600 !important;
        letter-spacing: -0.018em !important;
        line-height: 1.28 !important;
        color: #252836 !important;
    }
    .main h4, .main h5, .main h6 {
        color: var(--chat-text) !important;
        font-weight: 600 !important;
    }
    .main [data-testid="stMarkdownContainer"] p {
        font-size: 1.0625rem;
        line-height: 1.68;
        color: var(--chat-text-soft);
        margin: 0 0 0.75rem 0;
    }
    .main [data-testid="stMarkdownContainer"] li {
        font-size: 1.02rem;
        line-height: 1.6;
        color: var(--chat-text-soft);
        margin-bottom: 0.35rem;
    }
    .main [data-testid="stMarkdownContainer"] strong {
        color: var(--chat-text);
        font-weight: 600;
    }
    .main .stCaption,
    .main [data-testid="stCaption"] {
        color: var(--chat-text-soft) !important;
        font-size: 1.05rem !important;
        line-height: 1.55 !important;
    }
    .result-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        margin: 1rem 0;
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-left: 4px solid var(--chat-accent);
    }
    .success-message {
        background: linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%);
        color: #0d5d0d;
        padding: 1rem 1.15rem;
        border-radius: 10px;
        border: 1px solid rgba(150, 230, 161, 0.5);
        font-size: 1.02rem;
        line-height: 1.5;
        font-weight: 500;
    }
    .error-message {
        background: linear-gradient(135deg, #feb692 0%, #ea5455 100%);
        color: #ffffff;
        padding: 1rem 1.15rem;
        border-radius: 10px;
        border: 1px solid rgba(234, 84, 85, 0.4);
        font-size: 1.02rem;
        line-height: 1.5;
        font-weight: 500;
    }
    .warning-message {
        background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
        color: #2d3436;
        padding: 1rem 1.15rem;
        border-radius: 10px;
        border: 1px solid rgba(253, 203, 110, 0.5);
        font-size: 1.02rem;
        line-height: 1.5;
        font-weight: 500;
    }
    .info-message {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        color: #2d3436;
        padding: 1rem 1.15rem;
        border-radius: 10px;
        border: 1px solid var(--chat-border);
        font-size: 1.02rem;
        line-height: 1.55;
        font-weight: 500;
    }
    .metric-card {
        background: linear-gradient(135deg, var(--chat-accent) 0%, var(--chat-accent-2) 100%);
        color: #ffffff;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.25);
    }
    .sidebar-header {
        font-size: 1.28rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: var(--chat-heading);
        margin-bottom: 0.75rem;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
        font-size: 0.97rem;
        line-height: 1.55;
        color: var(--chat-text-soft);
    }
    .dataframe {
        border-radius: 8px;
    }
    /* Footer: keep support emails on one line (scroll on very narrow viewports) */
    .footer-support-wrap {
        white-space: nowrap;
        overflow-x: auto;
        font-size: 0.875rem;
        color: #6c6c7a;
        margin: 0;
        line-height: 1.4;
        text-align: right;
        -webkit-overflow-scrolling: touch;
    }
    .footer-support-wrap a {
        color: #1c7ed6;
        text-decoration: none;
    }
    .footer-support-wrap a:hover {
        text-decoration: underline;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🧬 SNP–Disease–Plant chatbox")
st.caption(
    "Look up diseases, SNPs, and plants or follow how they link together in one calm, focused workspace."
)

# ---------- Sidebar Navigation ----------
with st.sidebar:
    st.markdown('<div class="sidebar-header">🔍 Navigation</div>', unsafe_allow_html=True)
    
    # Add search statistics
    init_search_stats()
    _stats = st.session_state.search_stats
    _total_attempts = _stats.get("total_attempts", 0)
    _total_success = _stats.get("total_success", 0)
    _success_rate = (float(_total_success) / _total_attempts * 100.0) if _total_attempts else 0.0
    st.markdown("### 📊 Quick Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total searches", f"{_total_attempts:,}", help="Every search you run in this session.")
    with col2:
        st.metric("Success rate", f"{_success_rate:.1f}%", help="Share of searches that returned a hit.")
    
    st.markdown("---")
    
    menu = st.selectbox(
        "What would you like to do?",
        ["🔍 Single Node Search", "🔗 Relationship Search", "📈 Analytics Dashboard"],
        index=0,
        help="Switch modes anytime—your session stats stay in the sidebar.",
    )
    
    st.markdown("---")
    st.markdown("### 🛠️ Help & Info")
    
    with st.expander("📖 How to Use"):
        st.markdown("""
        **Single node**
        - Pick **Disease**, **Plant**, or **SNP**, paste its ID, then hit **Search** to see every property on that node.

        **Relationships**
        - Choose a path (e.g. disease → SNP, plant → SNP, or reverse). Enter the **starting** ID to see what it connects to.

        **Analytics**
        - Glance at how you’ve been searching this session plus live counts from the graph.
        """)
    
    with st.expander("💡 Tips"):
        st.markdown("""
        - **IDs are picky** — copy them exactly (including prefixes like `MESH:` or `RS:`).
        - Large result sets show a **summary table** first; expand samples below when you need detail.
        - If a search returns nothing, try the **example ID** on the page as a sanity check.
        """)
    
    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

# ---------- SINGLE SEARCH ----------
if menu == "🔍 Single Node Search":
    st.subheader("🔍 Explore individual nodes")
    st.markdown(
        "Choose **disease**, **plant**, or **SNP**, paste its graph ID, and open a clean property sheet "
        "for that node, ideal for quick lookups and spot-checking IDs."
    )

    col1, col2 = st.columns([3, 2])
    
    with col1:
        option = st.selectbox(
            "What are you looking up?",
            ["🏥 Disease", "🌿 Plant", "🧬 SNP"],
            help="We’ll match the ID against this node type in Neo4j.",
        )
        
        # Add input validation and examples
        example_ids = {
            "🏥 Disease": "MESH:D012871",
            "🌿 Plant": "PLANT:001",
            "🧬 SNP": "RS:123456"
        }
        
        st.markdown(f"**Example ID:** `{example_ids[option]}`")
        
        node_id = st.text_input(
            "Paste the node ID",
            placeholder=f"e.g., {example_ids[option]}",
            help="Include any prefix (e.g. MESH:, RS:) exactly as stored in the graph.",
        )
    
    with col2:
        st.markdown("### 🎯 Quick Actions")
        if st.button("🔎 Search", type="primary", use_container_width=True):
            if not node_id.strip():
                st.error("⚠️ Please enter an ID")
                st.stop()
            
            # Add loading state
            with st.spinner("🔍 Searching..."):
                label_map = {
                    "🏥 Disease": "disease",
                    "🌿 Plant": "plant",
                    "🧬 SNP": "rsid"
                }
                
                query_type_map = {
                    "🏥 Disease": "single_node_disease",
                    "🌿 Plant": "single_node_plant",
                    "🧬 SNP": "single_node_snp",
                }
                query_type = query_type_map[option]
                
                result = search_node(label_map[option], node_id.strip())
                log_search(query_type, bool(result))
                
                if result:
                    st.markdown(
                        '<div class="success-message">✅ <strong>Found it</strong> — this node is in the graph.</div>',
                        unsafe_allow_html=True,
                    )
                    
                    # Display results in a better format
                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.subheader(f"📋 {option.split(' ')[1]} Details")
                    
                    # Create a dataframe for better display
                    df = pd.DataFrame(list(result.items()), columns=["Property", "Value"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Direct CSV download button (single click)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name=f"{option.replace(' ', '_').lower()}_{node_id}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="error-message">❌ <strong>No match</strong> — that ID isn’t in the graph. Double-check spelling and prefixes.</div>',
                        unsafe_allow_html=True,
                    )
                    
                    # Show suggestions
                    st.markdown("### 💡 Try this")
                    st.markdown(f"- Use the sample ID on the page: `{example_ids[option]}`")
                    st.markdown("- Confirm the **node type** you picked matches the ID (e.g. `RS:` for SNPs).")
                    st.markdown("- If it should exist, verify it’s loaded in your Neo4j instance.")


# ---------- RELATION SEARCH ----------
elif menu == "🔗 Relationship Search":
    st.subheader("🔗 Discover relationships")
    st.markdown(
        "Walk the graph along curated edges: disease ↔ SNP, SNP ↔ plant, and **reverse** hops "
        "with relationship metadata when the database stores it."
    )

    col1, col2 = st.columns([3, 2])
    
    with col1:
        option = st.selectbox(
            "Which path through the graph?",
            [
                "🏥 Disease → SNP",
                "🧬 SNP → Plant",
                "🧬 SNP → Disease",
                "🌿 Plant → SNP",
            ],
            help="Pick the direction you care about—including reverse hops from SNP or plant.",
        )
        
        # Add context-specific examples
        if option == "🏥 Disease → SNP":
            example_id = "MESH:D012871"
            input_label = "Enter Disease ID"
            help_text = "Enter the disease ID to find associated SNPs"
        elif option == "🧬 SNP → Plant":
            example_id = "RS:123456"
            input_label = "Enter SNP ID"
            help_text = "Enter the SNP ID to find associated plants"
        elif option == "🧬 SNP → Disease":
            example_id = "RS:123456"
            input_label = "Enter SNP ID"
            help_text = "Enter the SNP ID to find associated diseases"
        else:
            example_id = "PLANT:001"
            input_label = "Enter Plant ID"
            help_text = "Enter the plant ID to find associated SNPs"
        
        st.markdown(f"**Example ID:** `{example_id}`")
        
        input_id = st.text_input(
            input_label,
            placeholder=f"e.g., {example_id}",
            help=help_text
        )
    
    with col2:
        st.markdown("### 🎯 Quick Actions")
        max_results = st.slider(
            "Max results to fetch (SNP/plant relationships)",
            min_value=10,
            max_value=2000,
            value=200,
            step=10
        )
        if st.button("🔎 Search Relationships", type="primary", use_container_width=True):
            if not input_id.strip():
                st.error("⚠️ Please enter an ID")
                st.stop()
            
            with st.spinner("🔍 Searching relationships..."):
                if option == "🏥 Disease → SNP":
                    data = search_disease_with_snps(input_id.strip(), limit=max_results)
                    log_search("relationship_disease_to_snp", bool(data["disease"]))
                    
                    if data["disease"]:
                        st.markdown(
                            '<div class="success-message">✅ <strong>Disease located</strong> — showing linked SNPs below.</div>',
                            unsafe_allow_html=True,
                        )
                        
                        # Display disease info
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.subheader("🏥 Disease Details")
                        disease_df = pd.DataFrame(list(data["disease"].items()), columns=["Property", "Value"])
                        st.dataframe(disease_df, use_container_width=True, hide_index=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Display associated SNPs
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        fetched_snps = data["snps"]
                        fetched_count = len(fetched_snps)
                        st.subheader(f"🧬 Associated SNPs (fetched {fetched_count})")

                        display_cap = min(fetched_count, 200)  # Keep UI responsive
                        display_snps = fetched_snps[:display_cap]

                        if display_snps:
                            summary_rows = []
                            for item in display_snps:
                                snp_props = item.get("snp") or {}
                                summary_rows.append({
                                    "snp_id": snp_props.get("id"),
                                    "has_relation": bool(item.get("relation"))
                                })

                            st.markdown("**Summary first** — scan the table, then peek at a few full rows below when you need every field.")
                            summary_df = pd.DataFrame(summary_rows)
                            st.dataframe(summary_df, use_container_width=True, hide_index=True)

                            # Render only a small number of full detail cards (UI can hang otherwise)
                            st.markdown("---")
                            st.markdown("**SNP Details (sample)**")
                            detail_cap = min(display_cap, 10)
                            for i, item in enumerate(display_snps[:detail_cap], 1):
                                st.markdown(f"**SNP {i}:**")
                                snp_df = pd.DataFrame(list(item["snp"].items()), columns=["Property", "Value"])
                                st.dataframe(snp_df, use_container_width=True, hide_index=True)

                                if item["relation"]:
                                    st.markdown("**🔗 Relationship Attributes:**")
                                    rel_df = pd.DataFrame(list(item["relation"].items()), columns=["Property", "Value"])
                                    st.dataframe(rel_df, use_container_width=True, hide_index=True)

                                if i < detail_cap:
                                    st.markdown("---")
                        else:
                            st.markdown('<div class="warning-message">⚠️ No associated SNPs found for this disease.</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Direct CSV download button (single click)
                        export_data = []
                        export_cap = min(len(data["snps"]), 200)
                        if len(data["snps"]) > export_cap:
                            st.warning(f"Export is limited to the first {export_cap} results to avoid large downloads.")

                        for item in data["snps"][:export_cap]:
                            row = {**data["disease"], **item["snp"]}
                            if item["relation"]:
                                row.update({f"rel_{k}": v for k, v in item["relation"].items()})
                            export_data.append(row)
                        
                        if export_data:
                            export_df = pd.DataFrame(export_data)
                            csv = export_df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Download CSV (first 200)",
                                data=csv,
                                file_name=f"disease_snp_relationships_{input_id}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="dl_disease_snp",
                            )
                    else:
                        st.markdown('<div class="error-message">❌ Disease not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                
                elif option == "🧬 SNP → Plant":
                    data = search_snp_with_plants(input_id.strip(), limit=max_results)
                    log_search("relationship_snp_to_plant", bool(data["snp"]))
                    
                    if data["snp"]:
                        st.markdown(
                            '<div class="success-message">✅ <strong>SNP located</strong> — linked plants appear below.</div>',
                            unsafe_allow_html=True,
                        )
                        
                        # Display SNP info
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.subheader("🧬 SNP Details")
                        snp_df = pd.DataFrame(list(data["snp"].items()), columns=["Property", "Value"])
                        st.dataframe(snp_df, use_container_width=True, hide_index=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Display associated plants
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        fetched_plants = data["plants"]
                        fetched_count = len(fetched_plants)
                        st.subheader(f"🌿 Associated Plants (fetched {fetched_count})")
                        
                        display_cap = min(fetched_count, 200)  # Keep UI responsive
                        display_plants = fetched_plants[:display_cap]
                        if display_plants:
                            summary_rows = []
                            for item in display_plants:
                                plant_props = item.get("plant") or {}
                                summary_rows.append({
                                    "plant_id": plant_props.get("id"),
                                    "has_relation": bool(item.get("relation"))
                                })

                            st.markdown("**Summary first** — scan the table, then peek at a few full rows below when you need every field.")
                            summary_df = pd.DataFrame(summary_rows)
                            st.dataframe(summary_df, use_container_width=True, hide_index=True)

                            # Render only a small number of full detail cards (UI can hang otherwise)
                            st.markdown("---")
                            st.markdown("**Plant Details (sample)**")
                            detail_cap = min(display_cap, 10)
                            for i, item in enumerate(display_plants[:detail_cap], 1):
                                st.markdown(f"**Plant {i}:**")
                                plant_df = pd.DataFrame(list(item["plant"].items()), columns=["Property", "Value"])
                                st.dataframe(plant_df, use_container_width=True, hide_index=True)

                                if item["relation"]:
                                    st.markdown("**🔗 Relationship Attributes:**")
                                    rel_df = pd.DataFrame(list(item["relation"].items()), columns=["Property", "Value"])
                                    st.dataframe(rel_df, use_container_width=True, hide_index=True)

                                if i < detail_cap:
                                    st.markdown("---")
                        else:
                            st.markdown('<div class="warning-message">⚠️ No associated plants found for this SNP.</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Direct CSV download button (single click)
                        export_cap = min(len(data["plants"]), 200)
                        if len(data["plants"]) > export_cap:
                            st.warning(f"Export is limited to the first {export_cap} results to avoid large downloads.")

                        export_data = []
                        for item in data["plants"][:export_cap]:
                            row = {**data["snp"], **item["plant"]}
                            if item["relation"]:
                                row.update({f"rel_{k}": v for k, v in item["relation"].items()})
                            export_data.append(row)
                        
                        if export_data:
                            export_df = pd.DataFrame(export_data)
                            csv = export_df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Download CSV (first 200)",
                                data=csv,
                                file_name=f"snp_plant_relationships_{input_id}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="dl_snp_plant",
                            )
                    else:
                        st.markdown('<div class="error-message">❌ SNP not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                
                elif option == "🧬 SNP → Disease":
                    data = search_snp_to_diseases(
                        input_id.strip(), limit=max_results, neo4j_driver=driver
                    )
                    log_search("relationship_snp_to_disease", bool(data["snp"]))
                    
                    if data["snp"]:
                        st.markdown(
                            '<div class="success-message">✅ <strong>SNP located</strong> — linked diseases appear below.</div>',
                            unsafe_allow_html=True,
                        )
                        
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.subheader("🧬 SNP Details")
                        snp_df = pd.DataFrame(list(data["snp"].items()), columns=["Property", "Value"])
                        st.dataframe(snp_df, use_container_width=True, hide_index=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        fetched = data["diseases"]
                        fetched_count = len(fetched)
                        st.subheader(f"🏥 Associated Diseases (fetched {fetched_count})")
                        
                        display_cap = min(fetched_count, 200)
                        display_items = fetched[:display_cap]
                        if display_items:
                            summary_rows = []
                            for item in display_items:
                                dprops = item.get("disease") or {}
                                summary_rows.append({
                                    "disease_id": dprops.get("id"),
                                    "has_relation": bool(item.get("relation")),
                                })
                            st.markdown("**Summary first** — scan the table, then peek at a few full rows below when you need every field.")
                            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                            
                            st.markdown("---")
                            st.markdown("**Disease Details (sample)**")
                            detail_cap = min(display_cap, 10)
                            for i, item in enumerate(display_items[:detail_cap], 1):
                                st.markdown(f"**Disease {i}:**")
                                dis_df = pd.DataFrame(list(item["disease"].items()), columns=["Property", "Value"])
                                st.dataframe(dis_df, use_container_width=True, hide_index=True)
                                if item["relation"]:
                                    st.markdown("**🔗 Relationship Attributes:**")
                                    rel_df = pd.DataFrame(list(item["relation"].items()), columns=["Property", "Value"])
                                    st.dataframe(rel_df, use_container_width=True, hide_index=True)
                                if i < detail_cap:
                                    st.markdown("---")
                        else:
                            st.markdown('<div class="warning-message">⚠️ No associated diseases found for this SNP.</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        export_cap = min(len(data["diseases"]), 200)
                        if len(data["diseases"]) > export_cap:
                            st.warning(f"Export is limited to the first {export_cap} results to avoid large downloads.")
                        export_data = []
                        for item in data["diseases"][:export_cap]:
                            row = {**data["snp"], **item["disease"]}
                            if item["relation"]:
                                row.update({f"rel_{k}": v for k, v in item["relation"].items()})
                            export_data.append(row)
                        if export_data:
                            export_df = pd.DataFrame(export_data)
                            csv = export_df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Download CSV (first 200)",
                                data=csv,
                                file_name=f"snp_disease_relationships_{input_id}.csv",
                                mime="text/csv",
                                key="dl_snp_disease",
                                use_container_width=True,
                            )
                    else:
                        st.markdown('<div class="error-message">❌ SNP not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                
                elif option == "🌿 Plant → SNP":
                    data = search_plant_to_snps(
                        input_id.strip(), limit=max_results, neo4j_driver=driver
                    )
                    log_search("relationship_plant_to_snp", bool(data["plant"]))
                    
                    if data["plant"]:
                        st.markdown(
                            '<div class="success-message">✅ <strong>Plant located</strong> — linked SNPs appear below.</div>',
                            unsafe_allow_html=True,
                        )
                        
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.subheader("🌿 Plant Details")
                        plant_df = pd.DataFrame(list(data["plant"].items()), columns=["Property", "Value"])
                        st.dataframe(plant_df, use_container_width=True, hide_index=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        fetched = data["snps"]
                        fetched_count = len(fetched)
                        st.subheader(f"🧬 Associated SNPs (fetched {fetched_count})")
                        
                        display_cap = min(fetched_count, 200)
                        display_items = fetched[:display_cap]
                        if display_items:
                            summary_rows = []
                            for item in display_items:
                                sprops = item.get("snp") or {}
                                summary_rows.append({
                                    "snp_id": sprops.get("id"),
                                    "has_relation": bool(item.get("relation")),
                                })
                            st.markdown("**Summary first** — scan the table, then peek at a few full rows below when you need every field.")
                            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                            
                            st.markdown("---")
                            st.markdown("**SNP Details (sample)**")
                            detail_cap = min(display_cap, 10)
                            for i, item in enumerate(display_items[:detail_cap], 1):
                                st.markdown(f"**SNP {i}:**")
                                snp_df = pd.DataFrame(list(item["snp"].items()), columns=["Property", "Value"])
                                st.dataframe(snp_df, use_container_width=True, hide_index=True)
                                if item["relation"]:
                                    st.markdown("**🔗 Relationship Attributes:**")
                                    rel_df = pd.DataFrame(list(item["relation"].items()), columns=["Property", "Value"])
                                    st.dataframe(rel_df, use_container_width=True, hide_index=True)
                                if i < detail_cap:
                                    st.markdown("---")
                        else:
                            st.markdown('<div class="warning-message">⚠️ No associated SNPs found for this plant.</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        export_cap = min(len(data["snps"]), 200)
                        if len(data["snps"]) > export_cap:
                            st.warning(f"Export is limited to the first {export_cap} results to avoid large downloads.")
                        export_data = []
                        for item in data["snps"][:export_cap]:
                            row = {**data["plant"], **item["snp"]}
                            if item["relation"]:
                                row.update({f"rel_{k}": v for k, v in item["relation"].items()})
                            export_data.append(row)
                        if export_data:
                            export_df = pd.DataFrame(export_data)
                            csv = export_df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Download CSV (first 200)",
                                data=csv,
                                file_name=f"plant_snp_relationships_{input_id}.csv",
                                mime="text/csv",
                                key="dl_plant_snp",
                                use_container_width=True,
                            )
                    else:
                        st.markdown('<div class="error-message">❌ Plant not found. Please check the ID and try again.</div>', unsafe_allow_html=True)


# ---------- ANALYTICS DASHBOARD ----------
elif menu == "📈 Analytics Dashboard":
    st.subheader("📈 Analytics dashboard")
    st.markdown(
        "A quiet overview: **this session’s** search habits up top, then **live** node and relationship "
        "counts straight from Neo4j—handy when you want the shape of the data, not a deep query."
    )

    st.markdown(
        '<div class="info-message">📊 <strong>Heads up</strong> — richer charts and filters will land here over time. '
        "For now you get trustworthy counts and session stats you can act on.</div>",
        unsafe_allow_html=True,
    )
    
    # Session-based search analytics (tracked via st.session_state)
    init_search_stats()
    _stats = st.session_state.search_stats
    _total_attempts = _stats.get("total_attempts", 0)
    _total_success = _stats.get("total_success", 0)
    _success_rate = (float(_total_success) / _total_attempts * 100.0) if _total_attempts else 0.0
    
    st.markdown("### 🔍 How you’ve searched (this session)")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Searches", f"{_total_attempts:,}")
    with col2:
        st.metric("Search % (Success Rate)", f"{_success_rate:.1f}%")
    
    by_type = _stats.get("by_type", {})
    breakdown_rows = []
    for qtype, row in by_type.items():
        attempts = row.get("attempts", 0)
        success = row.get("success", 0)
        rate = (float(success) / attempts * 100.0) if attempts else 0.0
        share = (float(attempts) / _total_attempts * 100.0) if _total_attempts else 0.0
        breakdown_rows.append({
            "Query Type": qtype,
            "Attempts": attempts,
            "Successes": success,
            "Success %": f"{rate:.1f}%",
            "Used %": f"{share:.1f}%",
        })
    
    if breakdown_rows:
        breakdown_df = pd.DataFrame(breakdown_rows)
        st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
    
    # Fetch real analytics data
    with st.spinner("📊 Loading analytics data..."):
        node_counts, rel_counts = get_analytics_data()
    
    # Calculate totals
    total_nodes = sum(node_counts.values()) if node_counts else 47625
    total_relationships = sum(rel_counts.values()) if rel_counts else 304464
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Nodes", f"{total_nodes:,}", "📈")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Relationships", f"{total_relationships:,}", "🔗")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Data Categories", len(node_counts) if node_counts else 3, "📂")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Show detailed breakdowns if data is available
    if node_counts:
        st.markdown("### 📊 Node Distribution")
        node_df = pd.DataFrame(list(node_counts.items()), columns=["Node Type", "Count"])
        st.dataframe(node_df, use_container_width=True, hide_index=True)
    
    if rel_counts:
        st.markdown("### 🔗 Relationship Distribution")
        rel_df = pd.DataFrame(list(rel_counts.items()), columns=["Relationship Type", "Count"])
        st.dataframe(rel_df, use_container_width=True, hide_index=True)

# ---------- Footer ----------
st.markdown("---")
col1, col2, col3 = st.columns([1.15, 1.15, 1.7])
with col1:
    st.caption("🧬 SNP–Disease–Plant chatbox · powered by Neo4j")
with col2:
    st.caption(f"⏰ Refreshed {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col3:
    st.markdown(
        '<p class="footer-support-wrap">📧 Questions? '
        '<a href="mailto:prateek23391@iiitd.ac.in">prateek23391@iiitd.ac.in</a>'
        "&nbsp;·&nbsp;"
        '<a href="mailto:nitesh23356@iiitd.ac.in">nitesh23356@iiitd.ac.in</a>'
        "</p>",
        unsafe_allow_html=True,
    )
