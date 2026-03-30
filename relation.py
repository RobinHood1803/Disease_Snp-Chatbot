from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
user = "neo4j"
password = "Sonal@2004"

driver = GraphDatabase.driver(uri, auth=(user, password))


def search_disease_with_snps(disease_id):
    query = """
    MATCH (d:disease {id: $id})
    OPTIONAL MATCH (d)-[r:ASSOCIATED_WITH]->(s:rsid)
    RETURN d, r, s
    """

    with driver.session() as session:
        results = session.run(query, {"id": disease_id})

        found = False

        for record in results:
            d = record["d"]
            r = record["r"]
            s = record["s"]

            if not found:
                if d:
                    print("\n=== Disease Details ===")
                    for key, value in dict(d).items():
                        print(f"{key}: {value}")
                    found = True
                else:
                    print("Disease not found")
                    return

            if s:
                print("\n--- Associated SNP ---")

                print("SNP Attributes:")
                for key, value in dict(s).items():
                    print(f"{key}: {value}")

                if r:
                    print("Relationship Attributes (ASSOCIATED_WITH):")
                    for key, value in dict(r).items():
                        print(f"{key}: {value}")


def search_snp_with_plants(snp_id):
    query = """
    MATCH (s:rsid {id: $id})
    OPTIONAL MATCH (s)-[r:ASSOCIATED_WITH_PLANT]->(p:plant)
    RETURN s, r, p
    """

    with driver.session() as session:
        results = session.run(query, {"id": snp_id})

        found = False

        for record in results:
            s = record["s"]
            r = record["r"]
            p = record["p"]

            if not found:
                if s:
                    print("\n=== SNP Details ===")
                    for key, value in dict(s).items():
                        print(f"{key}: {value}")
                    found = True
                else:
                    print("SNP not found")
                    return

            if p:
                print("\n--- Associated Plant ---")

                print("Plant Attributes:")
                for key, value in dict(p).items():
                    print(f"{key}: {value}")

                if r:
                    print("Relationship Attributes (ASSOCIATED_WITH_PLANT):")
                    for key, value in dict(r).items():
                        print(f"{key}: {value}")


def main():
    print("What do you want to search?")
    print("1. Disease")
    print("2. SNP")

    choice = input("Enter choice (1/2): ").strip()

    if choice == "1":
        disease_id = input("Enter disease id: ").strip()
        search_disease_with_snps(disease_id)

    elif choice == "2":
        snp_id = input("Enter SNP id: ").strip()
        search_snp_with_plants(snp_id)

    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
    driver.close()