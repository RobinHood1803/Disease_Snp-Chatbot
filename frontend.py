import streamlit as st
from neo4j import GraphDatabase

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


# ---------- UI ----------

st.set_page_config(page_title="KG Chatbot", layout="wide")

st.title("🧬 Knowledge Graph Search System")

menu = st.sidebar.selectbox(
    "Select Search Type",
    ["Single Node Search", "Relationship Search"]
)

# ---------- SINGLE SEARCH ----------
if menu == "Single Node Search":
    st.header("🔍 Single Node Search")

    option = st.selectbox("Select Node Type", ["Disease", "Plant", "SNP"])

    node_id = st.text_input("Enter ID")

    if st.button("Search"):
        label_map = {
            "Disease": "disease",
            "Plant": "plant",
            "SNP": "rsid"
        }

        result = search_node(label_map[option], node_id)

        if result:
            st.success(f"{option} Found ✅")
            for key, value in result.items():
                st.write(f"**{key}**: {value}")
        else:
            st.error("Not found ❌")


# ---------- RELATION SEARCH ----------
elif menu == "Relationship Search":
    st.header("🔗 Relationship Search")

    option = st.selectbox(
        "Select Query",
        ["Disease → SNP", "SNP → Plant"]
    )

    if option == "Disease → SNP":
        disease_id = st.text_input("Enter Disease ID")

        if st.button("Search"):
            data = search_disease_with_snps(disease_id)

            if data["disease"]:
                st.success("Disease Found ✅")

                st.subheader("Disease Details")
                for k, v in data["disease"].items():
                    st.write(f"**{k}**: {v}")

                st.subheader("Associated SNPs")

                if data["snps"]:
                    for item in data["snps"]:
                        st.write("---")
                        for k, v in item["snp"].items():
                            st.write(f"**{k}**: {v}")

                        if item["relation"]:
                            st.caption("Relationship Attributes")
                            for k, v in item["relation"].items():
                                st.write(f"{k}: {v}")
                else:
                    st.warning("No SNPs found")

            else:
                st.error("Disease not found ❌")


    elif option == "SNP → Plant":
        snp_id = st.text_input("Enter SNP ID")

        if st.button("Search"):
            data = search_snp_with_plants(snp_id)

            if data["snp"]:
                st.success("SNP Found ✅")

                st.subheader("SNP Details")
                for k, v in data["snp"].items():
                    st.write(f"**{k}**: {v}")

                st.subheader("Associated Plants")

                if data["plants"]:
                    for item in data["plants"]:
                        st.write("---")
                        for k, v in item["plant"].items():
                            st.write(f"**{k}**: {v}")

                        if item["relation"]:
                            st.caption("Relationship Attributes")
                            for k, v in item["relation"].items():
                                st.write(f"{k}: {v}")
                else:
                    st.warning("No Plants found")

            else:
                st.error("SNP not found ❌")


# ---------- Footer ----------
st.markdown("---")
st.caption("Knowledge Graph powered by Neo4j 🚀")