import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime
import re

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
    page_title="Knowledge Graph Search System",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .search-container {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.1);
        margin: 1rem 0;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    .result-card {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(252, 182, 159, 0.2);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        border: 1px solid rgba(252, 182, 159, 0.3);
    }
    .success-message {
        background: linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%);
        color: #0d5d0d;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(150, 230, 161, 0.5);
        box-shadow: 0 2px 10px rgba(150, 230, 161, 0.2);
    }
    .error-message {
        background: linear-gradient(135deg, #feb692 0%, #ea5455 100%);
        color: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(234, 84, 85, 0.5);
        box-shadow: 0 2px 10px rgba(234, 84, 85, 0.2);
    }
    .warning-message {
        background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
        color: #2d3436;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(253, 203, 110, 0.5);
        box-shadow: 0 2px 10px rgba(253, 203, 110, 0.2);
    }
    .info-message {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        color: #2d3436;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(254, 214, 227, 0.5);
        box-shadow: 0 2px 10px rgba(168, 237, 234, 0.2);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        border: 1px solid rgba(118, 75, 162, 0.3);
    }
    .sidebar-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #667eea;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .search-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .search-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    /* Remove default Streamlit white background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    /* Style dataframes to blend with theme */
    .dataframe {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header" style="font-size: 3rem; font-weight: 800; text-shadow: 3px 3px 6px rgba(0,0,0,0.2); margin-bottom: 1rem;">🧬 Knowledge Graph Search System</h1>', unsafe_allow_html=True)

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
        st.metric("Total Searches", f"{_total_attempts:,}", help="Total searches performed")
    with col2:
        st.metric("Success Rate", f"{_success_rate:.1f}%", help="Search success rate")
    
    st.markdown("---")
    
    menu = st.selectbox(
        "Select Search Type",
        ["🔍 Single Node Search", "🔗 Relationship Search", "📈 Analytics Dashboard"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 🛠️ Help & Info")
    
    with st.expander("📖 How to Use"):
        st.markdown("""
        **Single Node Search:**
        - Select node type (Disease, Plant, SNP)
        - Enter the ID (e.g., MESH:D012871)
        - Click Search to view details
        
        **Relationship Search:**
        - Choose relationship type (forward or reverse)
        - Enter the source ID
        - View connected nodes
        
        **Analytics Dashboard:**
        - View search statistics
        - Explore data insights
        """)
    
    with st.expander("💡 Tips"):
        st.markdown("""
        - Use exact IDs for better results
        - Check the format before searching
        - Relationship searches show connections
        - Use the analytics dashboard for insights
        """)
    
    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

# ---------- SINGLE SEARCH ----------
if menu == "🔍 Single Node Search":
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    # Add welcome text inside the container
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #667eea; margin-bottom: 0.5rem;">🔍 Explore Individual Nodes</h2>
        <p style="color: #555; font-size: 1.1rem; margin: 0;">
            Search for specific diseases, plants, or genetic variants (SNPs) in our knowledge graph.
            Enter a valid ID to retrieve detailed information about the node.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        option = st.selectbox(
            "Select Node Type",
            ["🏥 Disease", "🌿 Plant", "🧬 SNP"],
            help="Choose the type of node you want to search for"
        )
        
        # Add input validation and examples
        example_ids = {
            "🏥 Disease": "MESH:D012871",
            "🌿 Plant": "PLANT:001",
            "🧬 SNP": "RS:123456"
        }
        
        st.markdown(f"**Example ID:** `{example_ids[option]}`")
        
        node_id = st.text_input(
            "Enter ID",
            placeholder=f"e.g., {example_ids[option]}",
            help="Enter the exact ID of the node you want to search"
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
                    st.markdown('<div class="success-message">✅ Node Found Successfully!</div>', unsafe_allow_html=True)
                    
                    # Display results in a better format
                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.subheader(f"📋 {option.split(' ')[1]} Details")
                    
                    # Create a dataframe for better display
                    df = pd.DataFrame(list(result.items()), columns=["Property", "Value"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Add export functionality
                    if st.button("📥 Export Results", use_container_width=True):
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"{option.replace(' ', '_').lower()}_{node_id}.csv",
                            mime="text/csv"
                        )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="error-message">❌ Node not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                    
                    # Show suggestions
                    st.markdown("### 💡 Suggestions")
                    st.markdown(f"- Try using the example ID: `{example_ids[option]}`")
                    st.markdown("- Check if the ID format is correct")
                    st.markdown("- Verify the node exists in the database")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ---------- RELATION SEARCH ----------
elif menu == "🔗 Relationship Search":
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    # Add welcome text inside the container
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #667eea; margin-bottom: 0.5rem; font-size: 2.2rem; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.1); background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            🔗 Discover Relationships
        </h2>
        <p style="color: #555; font-size: 1.1rem; margin: 0; font-weight: 300; line-height: 1.6;">
            Explore connections between diseases, SNPs, and plants. 
            Find genetic associations and therapeutic relationships in the knowledge graph.
        </p>
        <div style="margin-top: 1rem;">
            <span style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.9rem; font-weight: 500;">
                🧬 Genetic Insights
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        option = st.selectbox(
            "Select Query Type",
            [
                "🏥 Disease → SNP",
                "🧬 SNP → Plant",
                "🧬 SNP → Disease",
                "🌿 Plant → SNP",
            ],
            help="Choose the relationship direction you want to explore (including reverse lookups)",
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
                        st.markdown('<div class="success-message">✅ Disease and relationships found!</div>', unsafe_allow_html=True)
                        
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

                            st.markdown("Showing a summary table. Full properties are shown for a small sample below.")
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
                        
                        # Export functionality
                        if st.button("📥 Export Results (first 200)", use_container_width=True):
                            # Create combined data for export
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
                                    label="Download CSV",
                                    data=csv,
                                    file_name=f"disease_snp_relationships_{input_id}.csv",
                                    mime="text/csv"
                                )
                    else:
                        st.markdown('<div class="error-message">❌ Disease not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                
                elif option == "🧬 SNP → Plant":
                    data = search_snp_with_plants(input_id.strip(), limit=max_results)
                    log_search("relationship_snp_to_plant", bool(data["snp"]))
                    
                    if data["snp"]:
                        st.markdown('<div class="success-message">✅ SNP and relationships found!</div>', unsafe_allow_html=True)
                        
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

                            st.markdown("Showing a summary table. Full properties are shown for a small sample below.")
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
                        
                        # Export functionality
                        if st.button("📥 Export Results (first 200)", use_container_width=True):
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
                                    label="Download CSV",
                                    data=csv,
                                    file_name=f"snp_plant_relationships_{input_id}.csv",
                                    mime="text/csv"
                                )
                    else:
                        st.markdown('<div class="error-message">❌ SNP not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                
                elif option == "🧬 SNP → Disease":
                    data = search_snp_to_diseases(
                        input_id.strip(), limit=max_results, neo4j_driver=driver
                    )
                    log_search("relationship_snp_to_disease", bool(data["snp"]))
                    
                    if data["snp"]:
                        st.markdown('<div class="success-message">✅ SNP and relationships found!</div>', unsafe_allow_html=True)
                        
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
                            st.markdown("Showing a summary table. Full properties are shown for a small sample below.")
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
                        
                        if st.button("📥 Export Results (first 200)", use_container_width=True, key="export_snp_disease"):
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
                                    label="Download CSV",
                                    data=csv,
                                    file_name=f"snp_disease_relationships_{input_id}.csv",
                                    mime="text/csv",
                                    key="dl_snp_disease",
                                )
                    else:
                        st.markdown('<div class="error-message">❌ SNP not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
                
                elif option == "🌿 Plant → SNP":
                    data = search_plant_to_snps(
                        input_id.strip(), limit=max_results, neo4j_driver=driver
                    )
                    log_search("relationship_plant_to_snp", bool(data["plant"]))
                    
                    if data["plant"]:
                        st.markdown('<div class="success-message">✅ Plant and relationships found!</div>', unsafe_allow_html=True)
                        
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
                            st.markdown("Showing a summary table. Full properties are shown for a small sample below.")
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
                        
                        if st.button("📥 Export Results (first 200)", use_container_width=True, key="export_plant_snp"):
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
                                    label="Download CSV",
                                    data=csv,
                                    file_name=f"plant_snp_relationships_{input_id}.csv",
                                    mime="text/csv",
                                    key="dl_plant_snp",
                                )
                    else:
                        st.markdown('<div class="error-message">❌ Plant not found. Please check the ID and try again.</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


# ---------- ANALYTICS DASHBOARD ----------
elif menu == "📈 Analytics Dashboard":
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    # Add welcome text inside the container
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #667eea; margin-bottom: 0.5rem; font-size: 2.2rem; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.1); background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            📈 Analytics Dashboard
        </h2>
        <p style="color: #555; font-size: 1.1rem; margin: 0; font-weight: 300; line-height: 1.6;">
            View comprehensive statistics and insights about the knowledge graph data. 
            Explore node distributions, relationship patterns, and search analytics.
        </p>
        <div style="margin-top: 1rem;">
            <span style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.9rem; font-weight: 500;">
                📊 Data Intelligence
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="info-message">📊 Analytics and insights coming soon! This dashboard will show search statistics, data distributions, and relationship patterns.</div>', unsafe_allow_html=True)
    
    # Session-based search analytics (tracked via st.session_state)
    init_search_stats()
    _stats = st.session_state.search_stats
    _total_attempts = _stats.get("total_attempts", 0)
    _total_success = _stats.get("total_success", 0)
    _success_rate = (float(_total_success) / _total_attempts * 100.0) if _total_attempts else 0.0
    
    st.markdown("### 🔍 Search Usage (This Session)")
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
    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🧬 Knowledge Graph powered by Neo4j 🚀")
with col2:
    st.caption(f"⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col3:
    st.caption("📧 Support: prateek23391@iiitd.ac.in, nitesh23356@iiitd.ac.in")
