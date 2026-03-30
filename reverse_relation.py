from neo4j import GraphDatabase

uri = "bolt://localhost:7687"   # change to Aura later if needed
user = "neo4j"
password = "Sonal@2004"

driver = GraphDatabase.driver(uri, auth=(user, password))


def search_snp_to_diseases(snp_id):
    query = """
    MATCH (d:disease)-[r:ASSOCIATED_WITH]->(s:rsid {id: $id})
    RETURN s, r, d
    """

    with driver.session() as session:
        results = session.run(query, {"id": snp_id})

        found = False

        for record in results:
            s = record["s"]
            d = record["d"]
            r = record["r"]

            if not found:
                if s:
                    print("\n=== SNP Details ===")
                    for key, value in dict(s).items():
                        print(f"{key}: {value}")
                    found = True
                else:
                    print("SNP not found")
                    return

            if d:
                print("\n--- Associated Disease ---")
                for key, value in dict(d).items():
                    print(f"{key}: {value}")

                if r:
                    print("Relationship Attributes:")
                    for key, value in dict(r).items():
                        print(f"{key}: {value}")


def search_plant_to_snps(plant_id):
    query = """
    MATCH (s:rsid)-[r:ASSOCIATED_WITH_PLANT]->(p:plant {id: $id})
    RETURN p, r, s
    """

    with driver.session() as session:
        results = session.run(query, {"id": plant_id})

        found = False

        for record in results:
            p = record["p"]
            s = record["s"]
            r = record["r"]

            if not found:
                if p:
                    print("\n=== Plant Details ===")
                    for key, value in dict(p).items():
                        print(f"{key}: {value}")
                    found = True
                else:
                    print("Plant not found")
                    return

            if s:
                print("\n--- Associated SNP ---")
                for key, value in dict(s).items():
                    print(f"{key}: {value}")

                if r:
                    print("Relationship Attributes:")
                    for key, value in dict(r).items():
                        print(f"{key}: {value}")


def main():
    print("What do you want to search?")
    print("1. SNP → Diseases")
    print("2. Plant → SNPs")

    choice = input("Enter choice (1/2): ").strip()

    if choice == "1":
        snp_id = input("Enter SNP id: ").strip()
        search_snp_to_diseases(snp_id)

    elif choice == "2":
        plant_id = input("Enter Plant id: ").strip()
        search_plant_to_snps(plant_id)

    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
    driver.close()