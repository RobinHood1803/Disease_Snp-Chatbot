from neo4j import GraphDatabase

uri = "bolt://localhost:7687"   # change to Aura later if needed
user = "neo4j"
password = "Sonal@2004"

_driver = None


def _default_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def search_snp_to_diseases(snp_id, limit=200, neo4j_driver=None):
    """
    Reverse of Disease → SNP: find diseases linked to a given SNP (rsid).
    Returns { "snp": dict|None, "diseases": [ { "disease": dict, "relation": dict }, ... ] }
    """
    drv = neo4j_driver or _default_driver()
    query = """
    MATCH (s:rsid {id: $id})
    OPTIONAL MATCH (d:disease)-[r:ASSOCIATED_WITH]->(s)
    RETURN s, r, d
    LIMIT $limit
    """

    data = {"snp": None, "diseases": []}

    with drv.session() as session:
        results = session.run(query, {"id": snp_id, "limit": limit})

        for record in results:
            s = record["s"]
            d = record["d"]
            r = record["r"]

            if s and data["snp"] is None:
                data["snp"] = dict(s)

            if d:
                data["diseases"].append({
                    "disease": dict(d),
                    "relation": dict(r) if r else {},
                })

    return data


def search_plant_to_snps(plant_id, limit=200, neo4j_driver=None):
    """
    Reverse of SNP → Plant: find SNPs linked to a given plant.
    Returns { "plant": dict|None, "snps": [ { "snp": dict, "relation": dict }, ... ] }
    """
    drv = neo4j_driver or _default_driver()
    query = """
    MATCH (p:plant {id: $id})
    OPTIONAL MATCH (s:rsid)-[r:ASSOCIATED_WITH_PLANT]->(p)
    RETURN p, r, s
    LIMIT $limit
    """

    data = {"plant": None, "snps": []}

    with drv.session() as session:
        results = session.run(query, {"id": plant_id, "limit": limit})

        for record in results:
            p = record["p"]
            s = record["s"]
            r = record["r"]

            if p and data["plant"] is None:
                data["plant"] = dict(p)

            if s:
                data["snps"].append({
                    "snp": dict(s),
                    "relation": dict(r) if r else {},
                })

    return data


def _print_snp_to_diseases(snp_id, limit=200):
    data = search_snp_to_diseases(snp_id, limit=limit)
    if not data["snp"]:
        print("SNP not found")
        return
    print("\n=== SNP Details ===")
    for key, value in data["snp"].items():
        print(f"{key}: {value}")
    for item in data["diseases"]:
        print("\n--- Associated Disease ---")
        for key, value in item["disease"].items():
            print(f"{key}: {value}")
        if item["relation"]:
            print("Relationship Attributes:")
            for key, value in item["relation"].items():
                print(f"{key}: {value}")


def _print_plant_to_snps(plant_id, limit=200):
    data = search_plant_to_snps(plant_id, limit=limit)
    if not data["plant"]:
        print("Plant not found")
        return
    print("\n=== Plant Details ===")
    for key, value in data["plant"].items():
        print(f"{key}: {value}")
    for item in data["snps"]:
        print("\n--- Associated SNP ---")
        for key, value in item["snp"].items():
            print(f"{key}: {value}")
        if item["relation"]:
            print("Relationship Attributes:")
            for key, value in item["relation"].items():
                print(f"{key}: {value}")


def main():
    print("What do you want to search?")
    print("1. SNP → Diseases")
    print("2. Plant → SNPs")

    choice = input("Enter choice (1/2): ").strip()

    if choice == "1":
        snp_id = input("Enter SNP id: ").strip()
        _print_snp_to_diseases(snp_id)

    elif choice == "2":
        plant_id = input("Enter Plant id: ").strip()
        _print_plant_to_snps(plant_id)

    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    finally:
        if _driver is not None:
            _driver.close()
