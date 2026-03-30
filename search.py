from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
user = "neo4j"
password = "Sonal@2004"

driver = GraphDatabase.driver(uri, auth=(user, password))

def search_node(label, node_id):
    query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
    
    with driver.session() as session:
        result = session.run(query, {"id": node_id})
        record = result.single()
        
        if record:
            print(f"Found in {label}:", record["n"])
        else:
            print("Sorry, not present")

def main():
    label_map = {
        "1": "disease",
        "2": "plant",
        "3": "rsid"
    }

    print("Select what you want to search:")
    print("1. Disease")
    print("2. Plant")
    print("3. RSID")

    choice = input("Enter choice (1/2/3): ").strip()

    if choice not in label_map:
        print("Invalid choice")
        return

    label = label_map[choice]
    node_id = input(f"Enter {label} id: ").strip()

    search_node(label, node_id)

if __name__ == "__main__":
    main()
    driver.close()