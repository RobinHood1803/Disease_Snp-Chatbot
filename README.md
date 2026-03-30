# Disease_Snp-Chatbot

## Overview

## Requirements

Make sure the following are installed:

* Python 3.8 or above
* Neo4j Database (Desktop or Aura)
* pip (Python package manager)

---

## Setup Instructions

### 1. Create Virtual Environment

**Mac/Linux:**

```bash
python3 -m venv neo4j_env
source neo4j_env/bin/activate
```

---

### 2. Install Dependencies

```bash
pip install neo4j streamlit
```

---

## Configuration

Update the following values in your Python file:

```python
uri = "bolt://localhost:7687"   # For local Neo4j
# OR
uri = "neo4j+s://<your-aura-endpoint>"  # For Neo4j Aura

user = "neo4j"
password = "your_password"
```

---

## Example Query

This query checks whether a disease node with a specific ID exists:

```cypher
MATCH (d:disease {id: "MESH:D012871"})
RETURN d.disease_title, d.disease_category, d.efo_id
```

---

## Running the Backend Script

```bash
python search.py
```

---

## Running Streamlit Frontend (Optional)

Create a file `app.py` and run:

```bash
streamlit run app.py
```

---

## Expected Output

```json
{
  "title": "Skin Diseases",
  "category": "Skin and Connective Tissue Diseases",
  "efo_id": "EFO:0000701"
}
```

If the node does not exist:

```
Not found
```

---

## Common Issues

### 1. Connection Error

* Check if Neo4j is running
* Verify URI (bolt vs neo4j+s)

### 2. Authentication Failed

* Ensure username/password are correct

### 3. No Data Found

* Verify label (`disease`) and property (`id`) match your database

### 4. Streamlit Not Found

* Make sure environment is activated
* Re-run: `pip install streamlit`

---

## Notes

* Always test queries in Neo4j Browser before using them in Python
* Avoid returning full nodes (`RETURN d`) unless necessary
* Use specific properties for better performance
* Streamlit is optional but useful for quick UI testing

---
