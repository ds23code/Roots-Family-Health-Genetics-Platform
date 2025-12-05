import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from datetime import datetime
from backend import data_store
from backend.mondo_integration import process_medical_conditions

# Convert phrases to boolean (e.g. "he died" → False)
def normalize_is_dead(tool_args):
    if isinstance(tool_args["is_dead"], str):
        txt = tool_args["is_dead"].strip().lower()
        if any(x in txt for x in ["no", "not", "dead", "deceased", "not alive", "passed away", "died", "he died", "she died"]):
            tool_args["is_dead"] = 1
        elif any(x in txt for x in ["yes", "alive", "ofc", "living", "still", "she is", "he is", "of course", "obviously", "yep", "yeah"]):
            tool_args["is_dead"] = 0

def get_current_datetime():
    """Return the current date and time as a datetime object"""
    return datetime.today()
    
def compute_age_from_yyyymmdd(birthday_int):
    """Convert YYYYMMDD integer to age in years."""
    try:
        birth_date = datetime.strptime(str(birthday_int), "%Y%m%d")
    except (ValueError, TypeError):
        return None

    today = datetime.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

# 🔍 Check for biological age consistency
def validate_relative_age(tool_args):
    relation = tool_args["relation"]
    new_birthday = tool_args["birthday"]
    new_age = compute_age_from_yyyymmdd(new_birthday)

    if new_age is None:
        return  # skip if invalid

    # Find the patient (self)
    self_person = next((p for p in data_store.people if p["relation"] == "self"), None)
    if not self_person:
        return  # no patient yet

    self_age = compute_age_from_yyyymmdd(self_person["birthday"])
    if self_age is None:
        return

    # Parents should be at least 10 years older than patient
    if relation in ["father", "mother"] and new_age <= self_age + 10:
        print(f"\n⚠️ Warning: {relation.title()}'s age ({new_age}) is too close to patient's age ({self_age}).")
        confirm = input("   Type 'yes' to accept or provide corrected birthday (in dd/mm/yyyy): ").strip().lower()
        if confirm != "yes":
            try:
                corrected_date = datetime.strptime(confirm, "%d/%m/%Y")
                tool_args["birthday"] = int(corrected_date.strftime("%Y%m%d"))
            except:
                print("   ❌ Invalid correction. Keeping original value.")

    # Children should be at least 10 years younger than patient
    if relation.startswith("child") and new_age >= self_age - 10:
        print(f"\n⚠️ Warning: Child's age ({new_age}) is too close to or greater than patient's age ({self_age}).")
        confirm = input("   Type 'yes' to accept or provide corrected birthday (in dd/mm/yyyy): ").strip().lower()
        if confirm != "yes":
            try:
                corrected_date = datetime.strptime(confirm, "%d/%m/%Y")
                tool_args["birthday"] = int(corrected_date.strftime("%Y%m%d"))
            except:
                print("   ❌ Invalid correction. Keeping original value.")
                
# Fix short or non-alphabetical names
def validate_names(tool_args):
    for field in ["first_name", "last_name"]:
        name = tool_args[field]
        if len(name) < 2 or not name.isalpha():
            print(f"⚠️ {field.replace('_', ' ').title()} '{name}' seems unusual.")
            confirm = input(f"   Type 'yes' to accept or enter a corrected name: ").strip()
            if confirm.lower() != "yes" and confirm.isalpha():
                tool_args[field] = confirm
        tool_args[field] = tool_args[field].capitalize()

# Convert ["none", "no"] to empty list
def normalize_conditions(tool_args):
    conditions = tool_args.get("conditions", [])
    if any(isinstance(c, str) and c.lower() in ["no", "none", "n"] for c in conditions):
        tool_args["conditions"] = {}

def finalize_person(tool_args, relation_label):
    # Normalize relation_label to always use underscores
    relation_label = relation_label.replace(' ', '_')
    tool_args["relation"] = relation_label

    # 🧹 Step 1: Clean and normalize data
    # validate_height_weight(tool_args)
    validate_names(tool_args)
    normalize_conditions(tool_args)

    # 🧠 MONDO: Convert each condition to (label + MONDO code) structure
    if tool_args.get("conditions"):
        joined = ", ".join(tool_args["conditions"])
        tool_args["conditions"] = process_medical_conditions(joined, tool_args["relation"])


    normalize_is_dead(tool_args)

    # 👶 Step 2: Check for biologically plausible age vs. patient
    validate_relative_age(tool_args)

    # 🚫 Step 3: Prevent duplicates
    if any(p["relation"] == relation_label for p in data_store.people):
        print(f"⚠️ Entry for {relation_label} already exists. Skipping duplicate.")
        return

    # 🆔 Step 4: Assign unique ID and default relationship fields
    # tool_args["relation"] = relation_label
    tool_args["id"] = data_store.person_id_counter
    tool_args["dad_id"] = 0
    tool_args["mom_id"] = 0
    tool_args["partner_id"] = 0
    data_store.person_id_counter += 1

    # 👨‍👩‍👧 Step 5: Assign parents to sibling (inherit from patient)
    if relation_label.startswith("sibling"):
        for p in data_store.people:
            if p["relation"] == "self":
                tool_args["dad_id"] = p.get("dad_id")
                tool_args["mom_id"] = p.get("mom_id")

    # 👶 Step 6: Assign parents to child (patient + partner)
    if relation_label.startswith("child"):
        self_person = next((p for p in data_store.people if p["relation"] == "self"), None)
        partner_person = next((p for p in data_store.people if p["relation"] == "partner"), None)
        if self_person:
            if self_person["sex"] == '1':
                tool_args["dad_id"] = self_person["id"]
            elif self_person["sex"] == '2':
                tool_args["mom_id"] = self_person["id"]
    
        if partner_person:
            if partner_person["sex"] == '1':
                tool_args["dad_id"] = partner_person["id"]
            elif partner_person["sex"] == '2':
                tool_args["mom_id"] = partner_person["id"]
    
        # 🔥 Do NOT assign partner_id — children don't have one
        tool_args["partner_id"] = 0

    # 🧾 Step 7: Add to the global list
    data_store.people.append(tool_args)

    # 👴 Step 8: If father/mother is added, assign their ID to patient's dad_id/mom_id
    if relation_label == "father":
        for p in data_store.people:
            if p["relation"] == "self":
                p["dad_id"] = tool_args["id"]
    elif relation_label == "mother":
        for p in data_store.people:
            if p["relation"] == "self":
                p["mom_id"] = tool_args["id"]

    # 👵 Step 8.1: Link grandparents to father/mother
    if relation_label.startswith("paternal_grandfather"):
        father = next((p for p in data_store.people if p["relation"] == "father"), None)
        if father:
            father["dad_id"] = tool_args["id"]
    elif relation_label.startswith("paternal_grandmother"):
        father = next((p for p in data_store.people if p["relation"] == "father"), None)
        if father:
            father["mom_id"] = tool_args["id"]
    elif relation_label.startswith("maternal_grandfather"):
        mother = next((p for p in data_store.people if p["relation"] == "mother"), None)
        if mother:
            mother["dad_id"] = tool_args["id"]
    elif relation_label.startswith("maternal_grandmother"):
        mother = next((p for p in data_store.people if p["relation"] == "mother"), None)
        if mother:
            mother["mom_id"] = tool_args["id"]


    # 💞 Step 9: Set partner_id between father and mother
    if relation_label in ["father", "mother"]:
        other = "mother" if relation_label == "father" else "father"
        current_id = tool_args["id"]
        for p in data_store.people:
            if p["relation"] == other:
                p["partner_id"] = current_id
                tool_args["partner_id"] = p["id"]

    print(f"DEBUG: finalize_person called with relation_label = '{relation_label}'")
    # 💞 Step 9.1: Set partner_id between paternal grandparents
    if relation_label in ["paternal_grandfather", "paternal_grandmother"]:
        other = "paternal_grandmother" if relation_label == "paternal_grandfather" else "paternal_grandfather"
        current_id = tool_args["id"]
        print(f"DEBUG: finalize_person called with current_id = '{current_id}'")
        for p in data_store.people:
            if p["relation"] == other:
                p["partner_id"] = current_id
                tool_args["partner_id"] = p["id"]

    # 💞 Step 9.2: Set partner_id between maternal grandparents
    if relation_label in ["maternal_grandfather", "maternal_grandmother"]:
        other = "maternal_grandmother" if relation_label == "maternal_grandfather" else "maternal_grandfather"
        current_id = tool_args["id"]
        for p in data_store.people:
            if p["relation"] == other:
                p["partner_id"] = current_id
                tool_args["partner_id"] = p["id"]

    
    # 💑 Step 10: Link partner to self and vice versa
    if relation_label == "partner":
        for p in data_store.people:
            if p["relation"] == "self":
                # set each other's partner_id
                p["partner_id"] = tool_args["id"]
                tool_args["partner_id"] = p["id"]
    elif relation_label == "self":
        for p in data_store.people:
            if p["relation"] == "partner":
                # set each other's partner_id
                p["partner_id"] = tool_args["id"]
                tool_args["partner_id"] = p["id"]

    # ✅ Step 11: Show extracted info and save to CSV
    print("\n✅ Extracted info:")
    for key, value in tool_args.items():
        print(f"  {key}: {value}")
    data_store.save_all_to_csv()
    print("📌 Data saved.")



