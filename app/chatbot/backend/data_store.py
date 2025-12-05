import csv
import os
from datetime import datetime

# Global list to hold all people (patient + family)
people = []

# Global unique ID counter for each person added
person_id_counter = 1

# Maps disease labels to their MONDO codes
disease_columns = {}
# Maps disease labels to formatted column names
disease_column_names = {}

# 📏 Save all people to CSV (overwrite)
def save_all_to_csv():
    # Ensure results directory exists
    os.makedirs("../results", exist_ok=True)
    
    base_columns = ["id", "relation", "first_name", "last_name", "birthday", "sex", "is_dead", "dad_id", "mom_id", "partner_id"]
    disease_cols = [disease_column_names[disease] for disease in disease_columns.keys()]
    all_columns = base_columns + disease_cols

    with open("../results/patients.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        
        for person in people:
            row = {col: person.get(col, 0) for col in base_columns}
            person_conditions = person.get("conditions", {})
            for disease_label in disease_columns.keys():
                col_name = disease_column_names[disease_label]
                if isinstance(person_conditions, dict):
                    row[col_name] = 1 if person_conditions.get(disease_label, False) else 0
                else:
                    row[col_name] = "NA"
            writer.writerow(row)

def seed_memory_from_csv():
    try:
        with open("../results/patients.csv", "r") as f:
            reader = csv.DictReader(f)
            facts = []
            base_columns = ["id", "relation", "first_name", "last_name", "birthday", "sex", "is_dead", "dad_id", "mom_id", "partner_id"]

            for row in reader:
                if not row.get("relation") or not row.get("first_name"):
                    continue
                name = f"{row['first_name']} {row['last_name']}"
                relation = row["relation"]
                facts.append(f"The patient's {relation} is named {name}.")
                
                # Format birthday to dd/mm/yyyy for readability
                try:
                    bday = datetime.strptime(row["birthday"], "%Y%m%d").strftime("%d/%m/%Y")
                except:
                    bday = row["birthday"]

                sex = "male" if row["sex"] == "1" else "female"
                status = "deceased" if row["is_dead"] == "1" else "alive"
                # ✅ Now we define `line` first before adding disease history
                line = f"{name} was born on {bday}, is {sex}, and is currently {status}."

                # Add any diseases marked as present
                for key, val in row.items():
                    if val == "1" and key not in base_columns:
                        label_clean = key.split(" (MONDO")[0]  # removes MONDO code from display
                        line += f" They have a history of {label_clean}."
                facts.append(line)
            return "\n".join(facts)
    except FileNotFoundError:
        return ""
