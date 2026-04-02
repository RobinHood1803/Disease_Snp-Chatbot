import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime
import re

# ---------- Neo4j Connection ----------
uri = "bolt://localhost:7687"
user = "neo4j"
password = "Sonal@2004"

driver = GraphDatabase.driver(uri, auth=(user, password))


# ---------- Functions ----------

def search_node(label, node_id):
    query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
    
    with driver.session() as session:
        result = session.run(query, {"id": node_id})
        record = result.single()
        
        if record:
            return dict(record["n"])
        else:
            return None


def search_disease_with_snps(disease_id):
    query = """
    MATCH (d:disease {id: $id})
    OPTIONAL MATCH (d)-[r:ASSOCIATED_WITH]->(s:rsid)
    RETURN d, r, s
    """

    data = {"disease": None, "snps": []}

    with driver.session() as session:
        results = session.run(query, {"id": disease_id})

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

    return data


def search_snp_with_plants(snp_id):
    query = """
    MATCH (s:rsid {id: $id})
    OPTIONAL MATCH (s)-[r:ASSOCIATED_WITH_PLANT]->(p:plant)
    RETURN s, r, p
    """

    data = {"snp": None, "plants": []}

    with driver.session() as session:
        results = session.run(query, {"id": snp_id})

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
    st.markdown("### 📊 Quick Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Searches", "0", help="Total searches performed")
    with col2:
        st.metric("Success Rate", "0%", help="Search success rate")
    
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
        - Choose relationship type
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
                
                result = search_node(label_map[option], node_id.strip())
                
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
            ["🏥 Disease → SNP", "🧬 SNP → Plant"],
            help="Choose the relationship direction you want to explore"
        )
        
        # Add context-specific examples
        if option == "🏥 Disease → SNP":
            example_id = "MESH:D012871"
            input_label = "Enter Disease ID"
            help_text = "Enter the disease ID to find associated SNPs"
        else:
            example_id = "RS:123456"
            input_label = "Enter SNP ID"
            help_text = "Enter the SNP ID to find associated plants"
        
        st.markdown(f"**Example ID:** `{example_id}`")
        
        input_id = st.text_input(
            input_label,
            placeholder=f"e.g., {example_id}",
            help=help_text
        )
    
    with col2:
        st.markdown("### 🎯 Quick Actions")
        if st.button("🔎 Search Relationships", type="primary", use_container_width=True):
            if not input_id.strip():
                st.error("⚠️ Please enter an ID")
                st.stop()
            
            with st.spinner("🔍 Searching relationships..."):
                if option == "🏥 Disease → SNP":
                    data = search_disease_with_snps(input_id.strip())
                    
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
                        st.subheader(f"🧬 Associated SNPs ({len(data['snps'])} found)")
                        
                        if data["snps"]:
                            for i, item in enumerate(data["snps"], 1):
                                st.markdown(f"**SNP {i}:**")
                                
                                # SNP details
                                snp_df = pd.DataFrame(list(item["snp"].items()), columns=["Property", "Value"])
                                st.dataframe(snp_df, use_container_width=True, hide_index=True)
                                
                                # Relationship attributes
                                if item["relation"]:
                                    st.markdown("**🔗 Relationship Attributes:**")
                                    rel_df = pd.DataFrame(list(item["relation"].items()), columns=["Property", "Value"])
                                    st.dataframe(rel_df, use_container_width=True, hide_index=True)
                                
                                if i < len(data["snps"]):
                                    st.markdown("---")
                        else:
                            st.markdown('<div class="warning-message">⚠️ No associated SNPs found for this disease.</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Export functionality
                        if st.button("📥 Export All Results", use_container_width=True):
                            # Create combined data for export
                            export_data = []
                            for item in data["snps"]:
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
                    data = search_snp_with_plants(input_id.strip())
                    
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
                        st.subheader(f"🌿 Associated Plants ({len(data['plants'])} found)")
                        
                        if data["plants"]:
                            for i, item in enumerate(data["plants"], 1):
                                st.markdown(f"**Plant {i}:**")
                                
                                # Plant details
                                plant_df = pd.DataFrame(list(item["plant"].items()), columns=["Property", "Value"])
                                st.dataframe(plant_df, use_container_width=True, hide_index=True)
                                
                                # Relationship attributes
                                if item["relation"]:
                                    st.markdown("**🔗 Relationship Attributes:**")
                                    rel_df = pd.DataFrame(list(item["relation"].items()), columns=["Property", "Value"])
                                    st.dataframe(rel_df, use_container_width=True, hide_index=True)
                                
                                if i < len(data["plants"]):
                                    st.markdown("---")
                        else:
                            st.markdown('<div class="warning-message">⚠️ No associated plants found for this SNP.</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Export functionality
                        if st.button("📥 Export All Results", use_container_width=True):
                            export_data = []
                            for item in data["plants"]:
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
    
    # Placeholder for future analytics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Nodes", "0", "📈")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Relationships", "0", "🔗")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Data Categories", "3", "📂")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🧬 Knowledge Graph powered by Neo4j 🚀")
with col2:
    st.caption(f"⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col3:
    st.caption("📧 Support: admin@example.com")