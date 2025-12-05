import streamlit as st
from openai import OpenAI
from datetime import datetime
import os
import csv
import json
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import re

#  --- App Configuration & Title ---
st.set_page_config(
    page_title="ROOTS - Genetic Counseling Assistant",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling - IMPROVED VERSION
st.markdown("""
<style>
:root {
    --primary: #59A52C;
    --secondary: #6fca3a;
    --dark: #111111;
    --accent: #437d21;
    --background: #f7fbfc;
    --white: #fff;
    --gray: #2a2a2a;
}

.main-header {
    text-align: center;
    padding: 1.8rem 0;
    background: linear-gradient(
        90deg,
        rgba(89, 165, 44, 0.9) 0%,
        rgba(67, 125, 33, 0.9) 100%
    );
    color: var(--white);
    border-radius: 14px;
    margin-bottom: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    box-shadow: 0 4px 20px rgba(17, 17, 17, 0.08); 
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.2rem;
    position: relative;
}

.chat-container {
    background-color: #f9f9f9;
    border-radius: 10px;
    padding: 1rem;
    max-height: 500px;
    overflow-y: auto;
    margin-bottom: 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.user-message {
    background: linear-gradient(135deg, #e3f2fd, #bbdefb);
    border-radius: 18px 18px 0 18px;
    padding: 14px 18px;
    margin: 12px 0;
    max-width: 80%;
    float: right;
    clear: both;
    border: 1px solid #90caf9;
    color: #1565c0;
    font-weight: 500;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.assistant-message {
    background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
    border-radius: 18px 18px 18px 0;
    padding: 14px 18px;
    margin: 12px 0;
    max-width: 80%;
    float: left;
    clear: both;
    border: 1px solid #a5d6a7;
    color: var(--dark);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.genetic-insight {
    background-color: #fffbe6;
    border: 1px solid #ece7d3;
    border-radius: 10px;
    padding: 1.05rem;
    margin: 1.2rem 0;
    color: var(--gray);
    font-weight: 500;
}

.progress-container {
    height: 8px;
    background-color: #e3ebde;
    border-radius: 4px;
    margin: 1.2rem 0;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--primary), var(--secondary));
    border-radius: 4px;
    transition: width 0.3s;
}

.sidebar-section {
    padding: 1.2rem;
    background-color: var(--white);
    border-radius: 12px;
    margin-bottom: 1.2rem;
    box-shadow: 0 2px 6px rgba(67, 125, 33, 0.06);
}

.empty-state {
    text-align: center;
    padding: 2.2rem;
    background-color: var(--background);
    border: 2px dashed #e3ebde;
    border-radius: 12px;
    color: var(--gray);
}

.status-indicator {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 9px;
}

.status-active {
    background-color: var(--primary);
}

.status-inactive {
    background-color: #d9534f;
}

.highlight-box {
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: var(--white);
    padding: 1rem;
    border-radius: 12px;
    margin: 1.2rem 0;
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(89,165,44,0.08);
}

.pedigree-container {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-top: 1rem;
    text-align: center;
}

/* NEW: Fix for pedigree plot display */
.pedigree-plot {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
}

/* NEW: Styling for chat input */
.chat-input-container {
    position: sticky;
    bottom: 0;
    background: white;
    padding: 1rem 0;
    z-index: 100;
}

/* NEW: Styling for action buttons */
.action-button {
    margin-top: 0.5rem !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# --- Initialization & State Management ---

api_key = st.secrets.get("API_KEY")  # pulls directly from .streamlit/secrets.toml

if not api_key or api_key.strip() == "" or api_key == "your-openai-api-key-here":
    st.error("OpenAI API key is missing or invalid. Please set it in .streamlit/secrets.toml.", icon="🚨")
    st.stop()

client = OpenAI(api_key=api_key)

def initialize_session_state():
    required_keys = [
        "people", "person_id_counter", "disease_columns", "disease_column_names",
        "focal_disease", "current_relation", "messages", "chat_input_key",
        "action_required", "action_context", "chat_history", "interview_started",
        "backend_state", "mondo_code", "interview_stage", "interview_index",
        "awaiting_confirmation", "confirmation_type", "patient_name"
    ]
    
    defaults = {
        "people": [],
        "person_id_counter": 1,
        "disease_columns": {},
        "disease_column_names": {},
        "focal_disease": None,
        "mondo_code": None,
        "current_relation": None,
        "messages": [],
        "chat_input_key": 0,
        "action_required": None,
        "action_context": {},
        "chat_history": [],
        "interview_started": False,
        "interview_stage": "focal_disease",
        "interview_index": 0,
        "awaiting_confirmation": False,
        "confirmation_type": None,
        "patient_name": None,
        "backend_state": {
            "people": [],
            "conversation_stage": "welcome",
            "focal_disease": None,
            "mondo_code": None
        }
    }
    
    for key in required_keys:
        if key not in st.session_state:
            st.session_state[key] = defaults.get(key, None)

    if 'editing_person_id' not in st.session_state:
        st.session_state.editing_person_id = None
    
    # Initialize backend_state with default values
    if "backend_state" not in st.session_state:
        st.session_state.backend_state = defaults["backend_state"]
    else:
        # Ensure all necessary keys exist in backend_state
        for k in ["people", "conversation_stage", "focal_disease", "mondo_code"]:
            if k not in st.session_state.backend_state:
                st.session_state.backend_state[k] = defaults["backend_state"][k]

def edit_person_form(person):
    with st.form(key=f"edit_form_{person['id']}"):
        st.subheader(f"Edit {person.get('relation', '').replace('_', ' ').title()}")
        
        # Text inputs for names
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name", value=person.get('first_name', ''))
        with col2:
            last_name = st.text_input("Last Name", value=person.get('last_name', ''))
        
        # Date input for birthday
        bday_int = person.get('birthday', 0)
        bday_date = None
        if bday_int and bday_int != 0:
            try:
                bday_str = str(bday_int)
                year = int(bday_str[:4])
                month = int(bday_str[4:6])
                day = int(bday_str[6:8])
                bday_date = datetime(year, month, day)
            except:
                pass
        birthday = st.date_input("Birthday", value=bday_date or datetime(1980, 1, 1))
        
        # Radio buttons for sex and status
        sex = st.radio("Sex", options=["Male", "Female"], 
                      index=0 if person.get('sex') == '1' else 1)
        status = st.radio("Status", options=["Alive", "Deceased"], 
                         index=0 if person.get('is_dead') == 0 else 1)
        
        # Condition checkboxes
        st.write("**Medical Conditions:**")
        conditions = {}
        for disease in st.session_state.disease_columns:
            display_name = st.session_state.disease_column_names.get(disease, disease)
            has_condition = person.get('conditions', {}).get(disease, False)
            conditions[disease] = st.checkbox(display_name, value=has_condition)
        
        # Form buttons
        col1, col2 = st.columns(2)
        with col1:
            save_btn = st.form_submit_button("💾 Save Changes")
        with col2:
            cancel_btn = st.form_submit_button("❌ Cancel")
        
        if save_btn:
            # Update person data
            person['first_name'] = first_name
            person['last_name'] = last_name
            person['birthday'] = int(birthday.strftime("%Y%m%d"))
            person['sex'] = '1' if sex == "Male" else '2'
            person['is_dead'] = 1 if status == "Deceased" else 0
            person['conditions'] = conditions
            
            # Update in session state
            for i, p in enumerate(st.session_state.people):
                if p['id'] == person['id']:
                    st.session_state.people[i] = person
            
            # Update backend state
            for i, p in enumerate(st.session_state.backend_state['people']):
                if p['id'] == person['id']:
                    st.session_state.backend_state['people'][i] = person
            
            st.session_state.editing_person_id = None
            save_all_to_csv()
            st.rerun()
        
        if cancel_btn:
            st.session_state.editing_person_id = None
            st.rerun()

# --- Core Functions (Identical to original functionality) ---
def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "store_patient_info",
                "description": "Extract structured patient or family member data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relation": {"type": "string"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "birthday": {"type": "integer", "description": "Patient's birthday in YYYYMMDD format."},
                        "sex": {"type": "string", "enum": ["1", "2"], "description": "1 for male, 2 for female."},
                        "conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Medical conditions or known diagnoses."
                        },
                        "is_dead": {
                            "type": "integer", "description": "Whether the person has died. 0 for alive, 1 for dead."
                        }
                    },
                    "required": ["relation", "first_name", "last_name", "birthday", "sex", "is_dead"]
                }
            }
        }
    ]

def extract_mondo_code(iri):
    if iri and "MONDO_" in iri:
        return iri.split("/")[-1]
    return "N/A"

def is_likely_human_disease(label):
    return "," not in label

def get_mondo_matches(disease_name, max_results=3):
    url = "https://www.ebi.ac.uk/ols4/api/search"
    params = {
        "q": disease_name,
        "ontology": "mondo"
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.warning(f"[MONDO API ERROR] Status code: {response.status_code}")
        return []
    
    data = response.json()
    results = data.get('response', {}).get('docs', [])
    filtered_results = [res for res in results if is_likely_human_disease(res.get('label', ''))]
    
    top_matches = []
    for res in filtered_results[:max_results]:
        label = res.get("label", "N/A")
        iri = res.get("iri", "")
        mondo_code = extract_mondo_code(iri)
        top_matches.append({
            "label": label,
            "mondo_code": mondo_code
        })
    
    return top_matches

# Define results directory and CSV path once
CURRENT_DIR = os.path.dirname(__file__)                  # app/chatbot/frontend
RESULTS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "results"))  # app/chatbot/results
CSV_PATH = os.path.join(RESULTS_DIR, "patients.csv")

# Make sure results folder exists
os.makedirs(RESULTS_DIR, exist_ok=True)

def seed_memory_from_csv():
    try:
        if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0:
            return ""
        
        with open(CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            facts = []
            base_columns = ["id", "relation", "first_name", "last_name", "birthday", "sex", "is_dead", "dad_id", "mom_id", "partner_id"]
            
            for row in reader:
                if not row.get("relation") or not row.get("first_name"):
                    continue
                name = f"{row['first_name']} {row['last_name']}"
                relation = row["relation"]
                facts.append(f"The patient's {relation} is named {name}.")
                try:
                    bday = datetime.strptime(row["birthday"], "%Y%m%d").strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    bday = "unknown"
                
                sex = "male" if row.get("sex") == "1" else "female"
                status = "deceased" if row.get("is_dead") == "1" else "alive"
                line = f"{name} was born on {bday}, is {sex}, and is currently {status}."
                
                for key, val in row.items():
                    if val == "1" and key not in base_columns:
                        label_clean = key.split(" (MONDO")[0]
                        line += f" They have a history of {label_clean}."
                facts.append(line)
            return "\n".join(facts)
    except FileNotFoundError:
        return ""
    except Exception as e:
        st.warning(f"Could not read `patients.csv`: {e}")
        return ""

def process_medical_conditions(input_text, person_relation=""):
    # If already a processed dict, return as-is
    if isinstance(input_text, dict):
        return input_text

    # Convert array to comma-separated string if needed
    if isinstance(input_text, list):
        input_text = ", ".join(input_text)
    
    # Now input_text is a string (assumed)    
    conditions = [c.strip() for c in input_text.split(',') if c.strip()]
    person_diseases = {}
    
    for condition in conditions[:4]:
        existing_match = None
        for existing_disease in st.session_state.disease_columns.keys():
            if condition.lower() in existing_disease.lower() or existing_disease.lower() in condition.lower():
                st.session_state.action_required = 'confirm_condition'
                st.session_state.action_context = {
                    "condition": condition,
                    "existing_disease": existing_disease,
                    "person_relation": person_relation
                }
                return None
        
        st.info(f"🔍 Searching MONDO for: **{condition}**")
        matches = get_mondo_matches(condition, max_results=10)
        
        if not matches:
            st.warning(f"⚠️ No MONDO matches found for '{condition}'. Recording as free text.")
            disease_label = condition
            mondo_code = "N/A"
            if disease_label not in st.session_state.disease_columns:
                st.session_state.disease_columns[disease_label] = mondo_code
                st.session_state.disease_column_names[disease_label] = f"{disease_label} ({mondo_code})"
            person_diseases[disease_label] = True
        else:
            st.session_state.action_required = 'select_mondo'
            st.session_state.action_context = {
                "condition": condition,
                "matches": matches,
                "person_relation": person_relation
            }
            return None
    
    return person_diseases

def save_all_to_csv():
    if not st.session_state.people:
        return
    
    base_columns = ["id", "relation", "first_name", "last_name", "birthday", "sex", "is_dead", 
                    "dad_id", "mom_id", "partner_id"]
    disease_cols = sorted([st.session_state.disease_column_names[disease] for disease in st.session_state.disease_columns.keys()])
    all_columns = base_columns + disease_cols + ["interview_stage", "interview_index", "focal_disease", "mondo_code"]
    
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        
        for person in st.session_state.people:
            row = {col: person.get(col, 0) for col in base_columns}
            
            person_conditions = person.get("conditions", {})
            for disease_label in st.session_state.disease_columns.keys():
                col_name = st.session_state.disease_column_names[disease_label]
                if isinstance(person_conditions, dict):
                    row[col_name] = 1 if person_conditions.get(disease_label, False) else 0
                else:
                    row[col_name] = "NA"
            
            # Add session state information
            row["interview_stage"] = st.session_state.interview_stage
            row["interview_index"] = st.session_state.interview_index
            row["focal_disease"] = st.session_state.focal_disease
            row["mondo_code"] = st.session_state.mondo_code
            
            writer.writerow(row)
    st.sidebar.success("✅ Data saved to patients.csv!")

def validate_names(tool_args):
    for field in ["first_name", "last_name"]:
        name = tool_args[field]
        if len(name) < 2 or not name.isalpha():
            st.warning(f"⚠️ {field.replace('_', ' ').title()} '{name}' seems unusual.")
            confirm = st.text_input(f"Type 'yes' to accept or enter a corrected name:", key=f"validate_name_{field}")
            if confirm and confirm.lower() != "yes" and confirm.isalpha():
                tool_args[field] = confirm
        tool_args[field] = tool_args[field].capitalize()

def normalize_conditions(tool_args):
    conditions = tool_args.get("conditions", [])
    if any(isinstance(c, str) and c.lower() in ["no", "none", "n"] for c in conditions):
        tool_args["conditions"] = {}

def normalize_is_dead(tool_args):
    if isinstance(tool_args["is_dead"], str):
        txt = tool_args["is_dead"].strip().lower()
        if any(x in txt for x in ["no", "not", "dead", "deceased", "not alive", "passed away", "died", "he died", "she died"]):
            tool_args["is_dead"] = 1
        elif any(x in txt for x in ["yes", "alive", "ofc", "living", "still", "she is", "he is", "of course", "obviously", "yep", "yeah"]):
            tool_args["is_dead"] = 0

def compute_age_from_yyyymmdd(birthday_int):
    try:
        birth_date = datetime.strptime(str(birthday_int), "%Y%m%d")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except (ValueError, TypeError):
        return None

def validate_relative_age(tool_args):
    relation = tool_args.get("relation")
    new_birthday = tool_args.get("birthday")
    
    if not all([relation, new_birthday]):
        return True
    
    new_age = compute_age_from_yyyymmdd(new_birthday)
    if new_age is None:
        return True
    
    self_person = next((p for p in st.session_state.get("people", []) if p.get("relation") == "self"), None)
    if not self_person or "birthday" not in self_person:
        return True
    
    self_age = compute_age_from_yyyymmdd(self_person["birthday"])
    if self_age is None:
        return True
    
    warning_message = None
    
    if relation in ["father", "mother"] and new_age is not None and new_age <= self_age + 10:
        warning_message = (
            f"The {relation.title()}'s age ({new_age}) seems too close to the patient's age ({self_age}). "
            "Are you sure this is correct?"
        )
    
    if relation.startswith("child") and new_age is not None and new_age >= self_age - 10:
        warning_message = (
            f"The Child's age ({new_age}) seems too close to or older than the patient's age ({self_age}). "
            "Are you sure this is correct?"
        )
    
    if warning_message:
        st.session_state.action_required = 'validate_age'
        st.session_state.action_context = {
            "tool_args": tool_args,
            "warning_message": warning_message
        }
        return False
    
    return True

def finalize_person(tool_args):
    relation_label = tool_args.get("relation", "").replace(' ', '_')
    tool_args["relation"] = relation_label
    
    if any(p["relation"] == relation_label for p in st.session_state.people):
        st.warning(f"⚠️ An entry for **{relation_label}** already exists. Skipping duplicate.")
        return
    
    validate_names(tool_args)
    normalize_conditions(tool_args)
    
    if tool_args.get("conditions"):
        processed_conditions = process_medical_conditions(tool_args["conditions"], relation_label)
        if processed_conditions is None:
            st.session_state.action_context["tool_args"] = tool_args
            return
        tool_args["conditions"] = processed_conditions
    
    normalize_is_dead(tool_args)
    
    if not validate_relative_age(tool_args):
        return
    
    tool_args["id"] = st.session_state.person_id_counter
    tool_args["dad_id"] = 0
    tool_args["mom_id"] = 0
    tool_args["partner_id"] = 0
    st.session_state.person_id_counter += 1
    
    if relation_label.startswith("sibling"):
        for p in st.session_state.people:
            if p["relation"] == "self":
                tool_args["dad_id"] = p.get("dad_id")
                tool_args["mom_id"] = p.get("mom_id")
    
    if relation_label.startswith("child"):
        self_person = next((p for p in st.session_state.people if p["relation"] == "self"), None)
        partner_person = next((p for p in st.session_state.people if p["relation"] == "partner"), None)
        
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
        
        tool_args["partner_id"] = 0
    
    st.session_state.people.append(tool_args)
    
    if relation_label == "father":
        for p in st.session_state.people:
            if p["relation"] == "self":
                p["dad_id"] = tool_args["id"]
    elif relation_label == "mother":
        for p in st.session_state.people:
            if p["relation"] == "self":
                p["mom_id"] = tool_args["id"]
    
    if relation_label.startswith("paternal_grandfather"):
        father = next((p for p in st.session_state.people if p["relation"] == "father"), None)
        if father:
            father["dad_id"] = tool_args["id"]
    elif relation_label.startswith("paternal_grandmother"):
        father = next((p for p in st.session_state.people if p["relation"] == "father"), None)
        if father:
            father["mom_id"] = tool_args["id"]
    elif relation_label.startswith("maternal_grandfather"):
        mother = next((p for p in st.session_state.people if p["relation"] == "mother"), None)
        if mother:
            mother["dad_id"] = tool_args["id"]
    elif relation_label.startswith("maternal_grandmother"):
        mother = next((p for p in st.session_state.people if p["relation"] == "mother"), None)
        if mother:
            mother["mom_id"] = tool_args["id"]
    
    if relation_label in ["father", "mother"]:
        other = "mother" if relation_label == "father" else "father"
        current_id = tool_args["id"]
        for p in st.session_state.people:
            if p["relation"] == other:
                p["partner_id"] = current_id
                tool_args["partner_id"] = p["id"]
    
    if relation_label in ["paternal_grandfather", "paternal_grandmother"]:
        other = "paternal_grandmother" if relation_label == "paternal_grandfather" else "paternal_grandfather"
        current_id = tool_args["id"]
        for p in st.session_state.people:
            if p["relation"] == other:
                p["partner_id"] = current_id
                tool_args["partner_id"] = p["id"]
    
    if relation_label in ["maternal_grandfather", "maternal_grandmother"]:
        other = "maternal_grandmother" if relation_label == "maternal_grandfather" else "maternal_grandfather"
        current_id = tool_args["id"]
        for p in st.session_state.people:
            if p["relation"] == other:
                p["partner_id"] = current_id
                tool_args["partner_id"] = p["id"]
    
    if relation_label == "partner":
        for p in st.session_state.people:
            if p["relation"] == "self":
                p["partner_id"] = tool_args["id"]
                tool_args["partner_id"] = p["id"]
    elif relation_label == "self":
        for p in st.session_state.people:
            if p["relation"] == "partner":
                p["partner_id"] = tool_args["id"]
                tool_args["partner_id"] = p["id"]
    
    st.success(f"✅ Extracted info for {tool_args['first_name']} {tool_args['last_name']} ({relation_label})")
    save_all_to_csv()
    
    # Update backend state
    st.session_state.backend_state['people'] = st.session_state.people

def start_interview(relation_label, patient_name=None):
    relation_label = relation_label.replace(' ', '_')
    st.session_state.current_relation = relation_label
    st.session_state.messages = []
    
    self_data = next((p for p in st.session_state.people if p["relation"] == "self"), None)
    patient_age = compute_age_from_yyyymmdd(self_data["birthday"]) if self_data else None
    
    base_system_prompt_template = """
    You are a friendly, empathetic medical assistant chatbot conducting a patient intake interview for family health history.

    Your goal is to collect complete and accurate structured data using the `store_patient_info` tool.

    The intro message before AI is called introduces the bot and states that we collect names, birth dates, sexes, living status (NA for self), and medical conditions - use the understanding of the user having that intro to naturally ask what the user can tell you about themselves (dont use that exact wording)

    If the user doesnt answer all things then prompt for the rest of the information.

    Information collected:
    - Name - if they dont provide a first and last name prompt for the last name. give a confirmation of their name e.g. (NOT THE SAME WORDING EVERY TIME) Thank you, I've saved your full name as Kellie Lai. Don't say your first name is Kellie, and your last name is Lai.
    - Birth dates - get their full date of birth but dont give an example of input. Store birthday in the following format: yyyymmdd
    - Sexes - record 1 for male and 2 for female but dont give an example input
    - Living status - skip for user, record 0 for alive and 1 for dead
    - Medical conditions - If a condition looks misspelt ask the user if its right. If confirmed to be misspelled by the user (e.g., user says "cold", you suggest "could", user confirms "cold"), save the corrected spelling as the condition to be searched on mondo.

    **Crucial Context: The current date for this entire interview is August 4th, 2025. All your calculations, age references, and mentions of 'today' or 'now' MUST be based on this date.**
    
    **Rule of Addressing: You are speaking to the patient, {patient_name}. Always address them by this name or as 'you'. When asking about a family member (the 'subject'), 
    refer to them by their name (e.g., 'Dan') or their pronoun ('his'/'her'). NEVER address the patient using the subject's name.**

    **Remember information already provided in the conversation history and leverage it.**

    **IMPORTANT: Relation Labeling Rule** — If you are collecting information about one of multiple relatives of the same type (e.g., siblings, children, paternal siblings, maternal siblings), you MUST use the full label with a numeric suffix in the `relation` field of the tool call, such as `'sibling_1'`, `'child_2'`, `'paternal_sibling_1'`, etc. Do NOT use just `'sibling'` or `'child'` unless explicitly instructed.
    
    **Avoid excessive confirmation for obvious facts (e.g., if a person states their sex, do not ask them to confirm their sex).**
    Handle "I don't know" or missing information gracefully (e.g., "Okay, we'll leave that as unknown for now").
    
    **If a user provides just a single name, assume it is their first name, and ask for their last name. If they provide two or more names separated by whitespace, 
    acknowledge that they have provided their full name, and get first and last name from that.**
    
    **Infer Sex from Role:** If the person's role clearly implies their sex (e.g., 'biological mother', 'father'), do NOT explicitly ask for their sex. Assume it and pass it to the tool. Only ask for sex if the role is ambiguous (e.g., 'sibling', 'partner', 'child') or the user explicitly states a different sex.
    
    **Remember Quantities:** If the user states a specific number for siblings or children (e.g., "I have 3 sisters"), remember this and ask for each one sequentially until that number is reached, without asking redundant "Do you have any other X?" questions.
    
    **Redirecting:** If the user veers off-topic, politely but firmly steer the conversation back to collecting the required family history information. For example, "That's interesting, but could we get back to collecting your family's health history?"
    
    **Tool Calling Rule: You MUST call the `store_patient_info` tool only when you have successfully collected ALL of the following fields for the current person AND the person has confirmed
    that the following information is all correct: 
    first name, last name, birthday, sex, and living status (`is_dead`).

    ** Do not move on to the next family member until the tool has been called for the current one. If you are 
    missing a field, you MUST ask for it. 

    Your current focus is on the {relation_label_clean}.

    **Summary box:** Please add a little summary box on the information extracted from the chat and ask the user if everything's is correct.

    **The main reason for this visit, or the focal disease being investigated, is: '{focal_disease}'.**
    When asking about medical conditions for family members, keep this focal disease in mind. 
    If a patient describes a condition known to be associated with the focal disease, you MUST acknowledge this connection directly. 
    Your goal is to inform the user naturally, without sounding repetitive.
    
    **Vary your phrasing and tone based on the context. Here are some principles and examples:**
    *   **For less severe or common conditions (like nearsightedness):** Be informative and conversational.
        *   *Example 1:* "Thanks for mentioning that. I'm noting it down, as nearsightedness can sometimes be linked to {focal_disease}."
        *   *Example 2:* "Interesting that you mention that. It's helpful to know, since [the mentioned condition] is one of the things we look for with {focal_disease}."

    *   **For more significant conditions (like an aortic aneurysm):** Be more direct and empathetic.
        *   *Example 1:* "Thank you, that's a very important piece of information. As you may know, [the mentioned condition] is a primary concern we monitor with {focal_disease}."
        *   *Example 2:* "I appreciate you sharing that. We'll pay close attention to that, as there's a strong connection between [the mentioned condition] and {focal_disease}."

    **Crucial Rule: You MUST NOT use the exact same phrasing for this acknowledgement multiple times in the interview.** After acknowledging the connection, continue the interview by asking for any other conditions or moving to the next required question."
    """

    relation_label_clean = relation_label.replace('_', ' ')
    if relation_label == "self":
        role_specific_prompt  = (
            "You're a friendly medical interviewer chatbot named ROOTS. Your job is to guide a person through an informal conversation to collect important health and family background information."
            "You are interviewing the patient (self)."
            "Start the conversation in a warm, relaxed, and open-ended way. Instead of asking directly for things like name or birth date, ask general questions like: - 'What can you tell me about yourself to get started?'"
            "Your goal is to make it feel like a natural conversation, not a questionnaire. Use emojis and encouragement. Let the user speak freely first — then ask clarifying questions to collect details like full name, date of birth, sex, and health conditions only if the user doesn't provide them up front."
            "NEVER start by asking directly for information. Let the user share what feels natural first."
            "While asking for medical conditions, if patient says that they have a condition, always ask if the patient has any other conditions. If patient implies that they do not have a condition, proceed to the next required question. Prompt for more conditions even after the patient made a mistake and just corrected it"
            "Patient is always alive (`is_dead` is `0`). Do NOT ask them to confirm this."
            "Do not ask for height or weight. "
            "Once all fields are collected and confirmed, use the `store_patient_info` tool."
            "Summary box: Please add a little summary box on the information extracted from the chat and ask the user if everything's is correct."
        )
    else:
        role_specific_prompt = (
            f"You are interviewing the patient's {relation_label_clean}."
            f"naturally ask what the user can tell you about {relation_label_clean} (dont use that exact wording but keep it open ended rather thank asking for specific details)"
            "Try to ask questions open-endedly with multiple possible fields answered in one question rather than in a rigid q&a structure but if they dont answer everything ask for the following conversationally; full name (first and last), birth date, sex (record 1 if they  say male, or 2 if they say female (dont accept other), living status (record 1 for dead and 0 for alive) and medical conditions."
            "**Infer Sex from Role**: If the person's role clearly implies their sex (e.g., 'biological mother', 'father'), do NOT explicitly ask for their sex. Assume it and pass it to the tool. **Always** ask for sex if the role is ambiguous (e.g., 'sibling', 'partner', 'child')"
            f"While asking for medical conditions, if patient implies that their {relation_label_clean} has at least a condition, always ask if the patient's {relation_label_clean} has any other conditions. If patient implies that their {relation_label_clean} do not have a condition, proceed to the next required question. Prompt for more conditions even after the patient made a mistake and just corrected it"
            f" The patient is {patient_age} years old. Use this to assess if the patient's {relation_label_clean} age is biologically plausible. "
            "If an age seems implausible (parents too young to have kids of certain age), gently ask for confirmation or correction, otherwise continue with the next question without mentioning it"
            "Then ask if they are alive"
            "Do not ask for height or weight. "
            f"Once all fields specific to the the patient's {relation_label_clean} are collected and confirmed, use the `store_patient_info` tool."
            "IMPORTANT: if the individuals condition is already in the CSV, ask whether it is the same condition rather than calling the mondo search again"
            "Summary box: Please add a little summary box on the information extracted from the chat and ask the user if everything's is correct."
        )
    
    memory = seed_memory_from_csv()
    combined_prompt = (
        memory + "\n\n" +
        base_system_prompt_template.format(
            relation_label_clean=relation_label_clean,
            focal_disease=st.session_state.focal_disease,
            patient_name=patient_name if patient_name else "the patient"
        ) +
        role_specific_prompt
    )
    
    st.session_state.messages.append({
        "role": "system",
        "content": combined_prompt
    })
    
    # Get the first assistant message
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=st.session_state.messages,
        tools=get_tools(),
        tool_choice="auto"
    )
    reply = response.choices[0].message
    
    if reply.tool_calls:
        for tool_call in reply.tool_calls:
            tool_args = json.loads(tool_call.function.arguments)
            tool_relation = tool_args.get("relation", "").replace(' ', '_')
            if tool_relation != relation_label:
                continue
            finalize_person(tool_args)
            st.session_state.current_relation = None
            return
    else:
        assistant_message = reply.content.strip()
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        # FIXED: Only add to chat_history once here
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': assistant_message
        })

def interview_multiple(relation_base, patient_name=None):
    st.session_state.awaiting_confirmation = True
    st.session_state.confirmation_type = relation_base
    st.session_state.multiple_relation_index = 1

def process_user_message(user_input):
    # Handle confirmation for multiple relations
    if st.session_state.awaiting_confirmation:
        st.session_state.awaiting_confirmation = False
        if user_input.lower() in ("yes", "y", "yeah", "i do"):
            relation_label = f"{st.session_state.confirmation_type}_{st.session_state.multiple_relation_index}"
            st.session_state.multiple_relation_index += 1
            start_interview(relation_label, st.session_state.patient_name)
            return "Starting interview for new family member..."
        else:
            # Move to next stage
            st.session_state.interview_index += 1
            return "Moving to next family member..."
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    # FIXED: Add user message to chat_history here
    st.session_state.chat_history.append({
        'role': 'user',
        'content': user_input
    })
    
    # Get assistant response
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=st.session_state.messages,
        tools=get_tools(),
        tool_choice="auto"
    )
    reply = response.choices[0].message
    
    # Check for tool calls
    if reply.tool_calls:
        for tool_call in reply.tool_calls:
            tool_args = json.loads(tool_call.function.arguments)
            tool_relation = tool_args.get("relation", "").replace(' ', '_')
            if tool_relation != st.session_state.current_relation:
                continue
            finalize_person(tool_args)
            st.session_state.current_relation = None
            
            # Handle multiple relations after storing
            if tool_relation.startswith("sibling") or tool_relation.startswith("child"):
                st.session_state.awaiting_confirmation = True
                st.session_state.confirmation_type = tool_relation.split('_')[0]
                return "Family member stored. Do you have another one to add? (yes/no)"
            
            # Move to next interview stage
            st.session_state.interview_index += 1
            return "Family member stored. Moving to next family member..."
    else:
        assistant_message = reply.content.strip()
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        # FIXED: Only add to chat_history once here, removed duplicate
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': assistant_message
        })
        return assistant_message

def store_family_member_data(person_data):
    # This function would store the person data in the backend state
    st.session_state.backend_state['people'].append(person_data)
    # Update other state variables as needed
    st.session_state.backend_state['conversation_stage'] = 'collecting'

# ================ PEDIGREE FUNCTIONS ================
def draw_pedigree(people_data, focal_disease=None):
    """Draw family pedigree chart"""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_aspect('equal')
    ax.axis('off')
    
    if not people_data:
        ax.text(0.5, 0.5, 'No family data to display', 
                transform=ax.transAxes, ha='center', va='center', fontsize=16)
        return fig
    
    # Create positions for family members
    positions = {}
    generation_y = {0: 3, 1: 2, 2: 1, 3: 0}  # Y positions by generation
    
    # Assign positions based on relation
    relation_positions = {
        'paternal_grandfather': (0, 3),
        'paternal_grandmother': (1, 3),
        'maternal_grandfather': (3, 3),
        'maternal_grandmother': (4, 3),
        'father': (0.5, 2),
        'mother': (3.5, 2),
        'self': (2, 1),
        'sibling_1': (1, 1),
        'sibling_2': (3, 1),
        'child_1': (1.5, 0),
        'child_2': (2.5, 0)
    }
    
    # Plot family members
    for person in people_data:
        relation = person.get('relation', '')
        pos = relation_positions.get(relation, (len(positions), 1))
        positions[person['id']] = pos
        
        x, y = pos
        
        # Determine if person has focal disease
        has_focal_disease = False
        conditions = person.get('conditions', {})
        if focal_disease and isinstance(conditions, dict):
            for condition in conditions:
                if focal_disease.lower() in condition.lower():
                    has_focal_disease = True
                    break
        
        # Draw shape based on sex
        if person.get('sex') == '1':  # Male - square
            color = 'red' if has_focal_disease else 'lightblue'
            rect = patches.Rectangle((x-0.2, y-0.2), 0.4, 0.4, 
                                   facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(rect)
        else:  # Female - circle
            color = 'red' if has_focal_disease else 'pink'
            circle = patches.Circle((x, y), 0.2, facecolor=color, 
                                  edgecolor='black', linewidth=2)
            ax.add_patch(circle)
        
        # Add deceased marking
        if person.get('is_dead'):
            ax.plot([x-0.2, x+0.2], [y-0.2, y+0.2], 'k-', lw=3)
        
        # Add name
        name = person.get('name', '').split()[0] if person.get('name') else relation
        ax.text(x, y-0.4, name, ha='center', va='top', fontsize=8, weight='bold')
    
    # Draw family connections
    # Parent-child lines
    for person in people_data:
        x, y = positions.get(person['id'], (0, 0))
        
        # Connect to parents
        dad_id = person.get('dad_id')
        mom_id = person.get('mom_id')
        
        if dad_id and dad_id in [p['id'] for p in people_data]:
            dad_pos = positions.get(dad_id)
            if dad_pos:
                ax.plot([x, dad_pos[0]], [y+0.2, dad_pos[1]-0.2], 'k-', alpha=0.6)
        
        if mom_id and mom_id in [p['id'] for p in people_data]:  
            mom_pos = positions.get(mom_id)
            if mom_pos:
                ax.plot([x, mom_pos[0]], [y+0.2, mom_pos[1]-0.2], 'k-', alpha=0.6)
    
    # Set plot limits
    if positions:
        x_coords = [pos[0] for pos in positions.values()]
        y_coords = [pos[1] for pos in positions.values()]
        ax.set_xlim(min(x_coords) - 0.5, max(x_coords) + 0.5)
        ax.set_ylim(min(y_coords) - 0.5, max(y_coords) + 0.5)
    
    # Add title and legend
    title = f'Family Pedigree'
    if focal_disease:
        title += f' - {focal_disease}'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Legend
    legend_elements = [
        patches.Rectangle((0, 0), 1, 1, facecolor='lightblue', edgecolor='black', label='Male'),
        patches.Circle((0, 0), 0.5, facecolor='pink', edgecolor='black', label='Female'),
        patches.Rectangle((0, 0), 1, 1, facecolor='red', edgecolor='black', label='Affected')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    return fig

def standardize_focal_disease(raw_input):
    """Standardize the focal disease input using GPT"""
    standardization_messages = [
        {"role": "system", "content": (
            "You are a text standardization and summarization assistant. "
            "Your task is to take a user's input describing a medical concern or reason for a visit "
            "and output a concise, clear, and standardized medical phrase (2-5 words). "
            "If the input is vague or describes symptoms, try to infer the most likely general condition. "
            "Examples:\n"
            "Input: 'my doctor said something about cancer like my mom had'\nOutput: 'Family history of cancer'\n"
            "Input: 'I feel tired all the time and gained weight'\nOutput: 'Fatigue and weight gain'\n"
            "Input: 'heart problems'\nOutput: 'Heart disease concerns'\n"
            "Input: 'feeling sick'\nOutput: 'General illness'\n"
            "Output only the standardized phrase, no other text or punctuation."
        )},
        {"role": "user", "content": raw_input}
    ]
    
    try:
        standardization_response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=standardization_messages,
            max_tokens=30,
            temperature=0.2
        )
        return standardization_response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error during focal disease standardization: {str(e)}")
        return raw_input

# ================ STREAMLIT FRONTEND ================
def main():
    initialize_session_state()
    
    # Header - FIXED: Use styled header instead of image
    st.markdown("""
    <div class="main-header">
        <h1>🧬 ROOTS - Genetic Counseling Assistant</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat history - FIXED: Ensure proper initialization
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'interview_started' not in st.session_state:
        st.session_state.interview_started = False

    # Sidebar with current information
    with st.sidebar:
        st.header("📋 Session Overview")
        
        # FIXED: Use proper backend state reference
        state = st.session_state.backend_state
        
        # Status indicator
        status = "Active" if state.get('conversation_stage') != 'complete' else "Completed"
        status_color = "status-active" if status == "Active" else "status-inactive"
        st.markdown(f"<div><span class='status-indicator {status_color}'></span> <b>Status:</b> {status}</div>", 
                    unsafe_allow_html=True)
        
        # Progress bar - FIXED: Handle division by zero
        family_count = len(state.get('people', []))
        progress = min(family_count / max(10, 1), 1.0)  # Avoid division by zero
        st.markdown(f"<div class='progress-container'><div class='progress-bar' style='width:{progress*100}%'></div></div>", 
                    unsafe_allow_html=True)
        st.caption(f"{family_count} family members collected")
        
        # Display focal disease - FIXED: Handle missing state
        if state.get('focal_disease'):
            disease_info = state['focal_disease']
            mondo_code = state.get('mondo_code', 'N/A')
            if mondo_code and mondo_code != 'N/A':
                disease_info += f" (MONDO:{mondo_code})"
            
            st.markdown(f"""
            <div class="sidebar-section">
                <h4>Primary Concern</h4>
                <div class="highlight-box">
                    {disease_info}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No primary health concern set yet")
            
        # Display current stage - FIXED: Handle missing state
        stage_map = {
            'welcome': "Introduction",
            'concern': "Establishing primary concern",
            'collecting': "Collecting family history",
            'analysis': "Genetic analysis",
            'complete': "Session complete"
        }
        current_stage = stage_map.get(state.get('conversation_stage', 'welcome'), "Introduction")
        st.markdown(f"""
        <div class="sidebar-section">
            <h4>Current Stage</h4>
            <b>{current_stage}</b>
        </div>
        """, unsafe_allow_html=True)
        
        # Display collected family members - FIXED: Handle missing people
        people = state.get('people', [])
        if people:
            st.markdown("""
            <div class="sidebar-section">
                <h4>Family Members Collected</h4>
            """, unsafe_allow_html=True)
            
            for person in people:
                relation = person.get('relation', '').replace('_', ' ').title()
                first_name = person.get('first_name', '')
                last_name = person.get('last_name', '')
                name = f"{first_name} {last_name}" if first_name or last_name else relation
                
                if st.session_state.editing_person_id == person['id']:
                    edit_person_form(person)
                else:
                    with st.expander(f"{relation}: {name}"):
                        # FIXED: Compute age safely
                        birthday = person.get('birthday')
                        age = None
                        if birthday:
                            try:
                                birth_year = int(str(birthday)[:4])
                                current_year = datetime.now().year
                                age = current_year - birth_year
                            except:
                                pass
                        
                        st.write(f"**Sex:** {'Male' if person.get('sex') == '1' else 'Female'}")
                        st.write(f"**Age:** {age if age else 'Unknown'}")
                        
                        conditions = person.get('conditions', {})
                        if st.button("✏️ Edit", key=f"edit_{person['id']}", 
                                use_container_width=True):
                            st.session_state.editing_person_id = person['id']
                            st.rerun()
                        if conditions and isinstance(conditions, dict):
                            st.write("**Medical Conditions:**")
                            for condition in conditions:
                                if conditions.get(condition):
                                    st.write(f"• {condition}")
                        else:
                            st.write("**Medical Conditions:** None reported")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No family members collected yet")
        
        # Quick upload option - FIXED: Improve UX
        st.subheader("⚡ Quick Upload")
        with st.expander("Upload CSV"):
            uploaded_file = st.file_uploader("Upload existing family history CSV", type=['csv'], label_visibility="collapsed")
            
            # In the sidebar upload section:
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    
                    # Process uploaded data
                    state = st.session_state.backend_state
                    state['people'] = []
                    
                    # Reset ID counter
                    max_id = 0
                    
                    # Extract session state from first row
                    first_row = df.iloc[0]
                    interview_stage = first_row.get("interview_stage", "focal_disease")
                    interview_index = first_row.get("interview_index", 0)
                    focal_disease = first_row.get("focal_disease", None)
                    mondo_code = first_row.get("mondo_code", None)
                    
                    for idx, row in df.iterrows():
                        # Create person data from CSV row
                        person_data = {
                            'id': int(row.get('id', idx + 1)),
                            'relation': str(row.get('relation', '')).lower(),
                            'first_name': str(row.get('first_name', '')),
                            'last_name': str(row.get('last_name', '')),
                            'birthday': int(row.get('birthday', 0)),
                            'sex': str(row.get('sex', '')),
                            'is_dead': int(row.get('is_dead', 0)),
                            'dad_id': int(row.get('dad_id', 0)),
                            'mom_id': int(row.get('mom_id', 0)),
                            'partner_id': int(row.get('partner_id', 0)),
                        }
                        
                        # Track max ID
                        if person_data['id'] > max_id:
                            max_id = person_data['id']
                        
                        # Collect conditions
                        conditions = {}
                        for col in df.columns:
                            if col not in ['id', 'relation', 'first_name', 'last_name', 
                                        'birthday', 'sex', 'is_dead', 'dad_id', 'mom_id', 'partner_id',
                                        'interview_stage', 'interview_index', 'focal_disease', 'mondo_code']:
                                # Check if the value indicates the condition is present
                                if row[col] in [1, "1", "True", True]:
                                    conditions[col] = True
                                else:
                                    conditions[col] = False
                        
                        person_data['conditions'] = conditions
                        
                        # Add to state
                        state['people'].append(person_data)
                    
                    # Update ID counter
                    st.session_state.person_id_counter = max_id + 1
                    
                    # Set focal disease if available
                    if focal_disease and not pd.isna(focal_disease):
                        state['focal_disease'] = focal_disease
                        st.session_state.focal_disease = focal_disease
                    
                    # Set MONDO code if available
                    if mondo_code and not pd.isna(mondo_code):
                        state['mondo_code'] = mondo_code
                        st.session_state.mondo_code = mondo_code
                    
                    # Set interview stage
                    if interview_stage and not pd.isna(interview_stage):
                        state['conversation_stage'] = 'collecting'
                        st.session_state.interview_stage = interview_stage
                        st.session_state.interview_index = int(interview_index)
                    
                    # Set backend people
                    st.session_state.people = state['people']
                    
                    # Set patient name from self record
                    self_person = next((p for p in state['people'] if p['relation'] == 'self'), None)
                    if self_person:
                        st.session_state.patient_name = f"{self_person['first_name']} {self_person['last_name']}"
                    
                    # Update disease columns
                    for col in df.columns:
                        if col not in base_columns + ['interview_stage', 'interview_index', 'focal_disease', 'mondo_code']:
                            # Extract disease name and MONDO code from column name
                            match = re.match(r"(.*?)\s*\((MONDO:\w+)\)", col)
                            if match:
                                disease_name = match.group(1)
                                mondo = match.group(2)
                                st.session_state.disease_columns[disease_name] = mondo
                                st.session_state.disease_column_names[disease_name] = col
                            else:
                                st.session_state.disease_columns[col] = "N/A"
                                st.session_state.disease_column_names[col] = col
                    
                    st.success(f"✅ Loaded {len(state['people'])} family members from CSV")
                    st.success(f"↩️ Resuming interview at: {interview_stage.replace('_', ' ').title()} stage")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error processing uploaded file: {str(e)}")
                    
        # Reset button - FIXED: Improve button styling
        if st.button("🔄 Start New Session", use_container_width=True, key="reset_session", 
                    help="Clear all current session data and start fresh"):
            # Reset all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="main-header">
            <h4 style="margin:0;">💬 Genetic Counseling Chat</h4>
        </div>
        """, unsafe_allow_html=True)

        # Focal disease collection - FIXED: Add clearer instructions
        if st.session_state.interview_stage == "focal_disease":
            st.markdown("""
            <div class="empty-state">
                <h3>Welcome to Your Genetic Counseling Session</h3>
                <p>To begin, please tell us:</p>
                <p><strong>What brings you to genetic counseling today?</strong></p>
                <p>Is there a specific health condition you're concerned about?</p>
            </div>
            """, unsafe_allow_html=True)
            
            focal_input = st.text_input(
                "e.g., 'concern about breast cancer', 'family history of heart disease'", 
                key="focal_input",
                placeholder="Enter your primary health concern here..."
            )
            
            if st.button("Submit Reason", key="submit_reason", use_container_width=True):
                if focal_input:
                    standardized = standardize_focal_disease(focal_input)
                    st.session_state.focal_disease = standardized
                    st.session_state.mondo_code = "N/A"
                    st.session_state.backend_state['focal_disease'] = standardized
                    st.session_state.interview_stage = "self"
                    st.session_state.chat_history.append({
                        'role': 'user',
                        'content': focal_input
                    })
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': f"Thank you. We'll focus our discussion on: **{standardized}**."
                    })
                    st.rerun()
                else:
                    st.warning("Please provide a reason for the visit to continue.")
        
        # Interview stages
        interview_stages = [
            "self", "father", "mother", "siblings", 
            "partner", "children", "paternal_grandfather", 
            "paternal_grandmother", "maternal_grandfather", 
            "maternal_grandmother"
        ]
        
        # Start interview for current stage
        if st.session_state.interview_stage in interview_stages:
            if st.session_state.interview_stage == "siblings":
                if not st.session_state.awaiting_confirmation:
                    interview_multiple("sibling", st.session_state.patient_name)
                    st.rerun()
            elif st.session_state.interview_stage == "children":
                if not st.session_state.awaiting_confirmation:
                    interview_multiple("child", st.session_state.patient_name)
                    st.rerun()
            else:
                if st.session_state.current_relation is None:
                    start_interview(st.session_state.interview_stage, st.session_state.patient_name)
                    st.rerun()
        
        # Chat container - FIXED: Improve chat display
        st.markdown("### Conversation")
        chat_container = st.container()
        with chat_container:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            # Display chat history
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You:</strong> {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                elif message['role'] == 'assistant':
                    # Check for genetic reasoning in message
                    content = message['content']
                    if "🧬" in content or "genetic" in content.lower():
                        st.markdown(f"""
                        <div class="genetic-insight">
                            <strong>ROOTS:</strong> {content}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="assistant-message">
                            <strong>ROOTS:</strong> {content}
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Chat input - FIXED: Position at bottom
        if st.session_state.interview_stage != "focal_disease" and st.session_state.interview_stage != "complete":
            st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
            user_input = st.chat_input("Type your message here...", key="chat_input")
            st.markdown('</div>', unsafe_allow_html=True)

            if user_input:
                # Process message and get response
                with st.spinner("🤔 Analyzing and responding..."):
                    try:
                        response = process_user_message(user_input)
                        
                        # Update patient name if self interview is complete
                        if st.session_state.interview_stage == "self" and st.session_state.current_relation is None:
                            self_person = next((p for p in st.session_state.people if p["relation"] == "self"), None)
                            if self_person:
                                st.session_state.patient_name = f"{self_person['first_name']} {self_person['last_name']}"
                        
                        # Move to next stage if appropriate
                        if response and "Moving to next family member" in response:
                            if st.session_state.interview_index < len(interview_stages):
                                st.session_state.interview_stage = interview_stages[st.session_state.interview_index]
                            else:
                                st.session_state.interview_stage = "complete"
                                st.session_state.backend_state['conversation_stage'] = 'complete'
                        
                    except Exception as e:
                        st.error(f"Error processing message: {str(e)}")

                st.rerun()
        elif st.session_state.interview_stage == "complete":
            st.info("✅ Pedigree collection completed. You can start a new session or download your report below.")
    
    with col2:
        st.markdown("""
        <div class="main-header">
            <h4 style="margin:0;">👨‍👩‍👧‍👦 Family Pedigree</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Pedigree container - FIXED: Improve display
        with st.container():
            st.markdown('<div class="pedigree-container">', unsafe_allow_html=True)
            
            # Generate and display pedigree
            people = st.session_state.backend_state.get('people', [])
            focal_disease = st.session_state.backend_state.get('focal_disease')
            
            if len(people) > 0:
                try:
                    fig = draw_pedigree(people, focal_disease)
                    
                    # FIXED: Use proper method to display matplotlib figure
                    st.pyplot(fig)
                    plt.close(fig)  # Prevent memory leaks
                except Exception as e:
                    st.error(f"Error generating pedigree: {str(e)}")
                    st.info("Displaying family data in table format instead")
                    
                    # Fallback to table display
                    family_data = []
                    for person in people:
                        family_data.append({
                            'Relation': person.get('relation', '').replace('_', ' ').title(),
                            'Name': f"{person.get('first_name', '')} {person.get('last_name', '')}",
                            'Sex': 'Male' if person.get('sex') == '1' else 'Female',
                            'Age': compute_age_from_yyyymmdd(person.get('birthday')) or 'Unknown',
                            'Status': 'Deceased' if person.get('is_dead') == 1 else 'Alive'
                        })
                    
                    st.dataframe(pd.DataFrame(family_data), height=300)
            else:
                st.markdown("""
                <div class="empty-state">
                    <h4>👋 Pedigree Preview</h4>
                    <p>Your family pedigree will appear here as you add family members</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Export options - FIXED: Improve button styling
        if st.session_state.backend_state.get('people'):
            st.subheader("📤 Export Options")
            
            # Download family data as CSV
            # FIXED: Create proper CSV data
            base_columns = ["id", "relation", "first_name", "last_name", "birthday", "sex", "is_dead", "dad_id", "mom_id", "partner_id"]
            disease_cols = sorted(st.session_state.disease_column_names.values())
            all_columns = base_columns + disease_cols
            
            csv_data = []
            for person in st.session_state.people:
                row = {col: person.get(col, 0) for col in base_columns}
                
                person_conditions = person.get("conditions", {})
                for disease_label, col_name in st.session_state.disease_column_names.items():
                    if isinstance(person_conditions, dict):
                        row[col_name] = 1 if person_conditions.get(disease_label, False) else 0
                    else:
                        row[col_name] = 0
                
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="💾 Download Family Data (CSV)",
                data=csv,
                file_name=f"family_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv"
            )
            
            # Generate summary report
            if st.button("📄 Generate Summary Report", use_container_width=True, key="generate_report"):
                with st.spinner("Generating report... This may take a moment"):
                    # Create summary header
                    summary = []
                    summary.append(f"# Family Health History Report")
                    summary.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
                    
                    # Add focal disease info
                    if st.session_state.backend_state.get('focal_disease'):
                        disease_info = st.session_state.backend_state['focal_disease']
                        mondo_code = st.session_state.backend_state.get('mondo_code', 'N/A')
                        if mondo_code and mondo_code != 'N/A':
                            disease_info += f" (MONDO:{mondo_code})"
                        summary.append(f"**Primary Concern:** {disease_info}")
                    
                    # Add family members section
                    summary.append(f"\n## Family Members ({len(st.session_state.backend_state['people'])})")
                    
                    for person in st.session_state.backend_state['people']:
                        relation = person.get('relation', '').replace('_', ' ').title()
                        first_name = person.get('first_name', '')
                        last_name = person.get('last_name', '')
                        name = f"{first_name} {last_name}" if first_name or last_name else relation
                        
                        summary.append(f"\n### {relation}: {name}")
                        
                        # Calculate age
                        birthday = person.get('birthday')
                        age = None
                        if birthday:
                            try:
                                birth_year = int(str(birthday)[:4])
                                current_year = datetime.now().year
                                age = current_year - birth_year
                            except:
                                pass
                        
                        summary.append(f"- **Age:** {age if age else 'Unknown'}")
                        summary.append(f"- **Sex:** {'Male' if person.get('sex') == '1' else 'Female'}")
                        summary.append(f"- **Status:** {'Deceased' if person.get('is_dead') else 'Living'}")
                        
                        conditions = person.get('conditions', {})
                        if conditions and isinstance(conditions, dict):
                            summary.append("- **Medical Conditions:**")
                            for condition, has_condition in conditions.items():
                                if has_condition:
                                    summary.append(f"  - {condition}")
                        else:
                            summary.append("- **Medical Conditions:** None reported")
                    
                    # Add genetic insights
                    summary.append("\n## Genetic Insights")
                    summary.append("Based on the collected family history, here are potential genetic patterns:")
                    
                    # Add testing recommendations
                    summary.append("\n## Genetic Testing Recommendations")
                    summary.append("- Comprehensive genetic testing based on family history")
                    summary.append("- Carrier screening for recessive conditions")
                    summary.append("- Predictive testing for at-risk family members")
                    summary.append("- Consultation with a certified genetic counselor")
                    
                    summary_text = "\n".join(summary)

                    st.download_button(
                        label="📋 Download Summary Report",
                        data=summary_text,
                        file_name=f"genetic_counseling_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                        key="download_report"
                    )

# Handle action states
def handle_actions():
    if st.session_state.action_required == 'confirm_condition':
        context = st.session_state.action_context
        st.warning(f"Is '{context['condition']}' the same condition as '{context['existing_disease']}' that another family member has?")
        confirm = st.radio("Select:", ["Yes", "No"], key="condition_confirm")
        if st.button("Confirm", key="confirm_condition_btn"):
            if confirm == "Yes":
                tool_args = st.session_state.action_context.get("tool_args", {})
                
                # FIX: Handle both list and dictionary formats for conditions
                conditions = tool_args.get("conditions", [])
                
                # If it's a list, convert to dictionary format
                if isinstance(conditions, list):
                    # Create dictionary with existing conditions
                    conditions_dict = {cond: True for cond in conditions}
                    # Replace the user's term with the standardized term
                    if context['condition'] in conditions_dict:
                        del conditions_dict[context['condition']]
                    conditions_dict[context['existing_disease']] = True
                    tool_args["conditions"] = conditions_dict
                # If it's already a dictionary
                elif isinstance(conditions, dict):
                    # Replace the user's term with the standardized term
                    if context['condition'] in conditions:
                        del conditions[context['condition']]
                    conditions[context['existing_disease']] = True
                
                st.session_state.action_required = None
                finalize_person(tool_args)
                st.rerun()
            else:
                st.session_state.action_required = None
                st.rerun()
    
    elif st.session_state.action_required == 'select_mondo':
        context = st.session_state.action_context
        options = [f"{match['label']} ({match['mondo_code']})" for match in context["matches"]]
        options.append("Use original term")
        choice = st.selectbox("Select the best match:", options, key="mondo_select")
        if st.button("Confirm", key="confirm_mondo_btn"):
            if choice == "Use original term":
                disease_label = context["condition"]
                mondo_code = "N/A"
            else:
                idx = options.index(choice)
                disease_label = context["matches"][idx]["label"]
                mondo_code = context["matches"][idx]["mondo_code"]
            
            if disease_label not in st.session_state.disease_columns:
                st.session_state.disease_columns[disease_label] = mondo_code
                st.session_state.disease_column_names[disease_label] = f"{disease_label} ({mondo_code})"
            
            tool_args = st.session_state.action_context.get("tool_args", {})
            if not isinstance(tool_args.get("conditions"), dict):
                tool_args["conditions"] = {}
            tool_args["conditions"][disease_label] = True
            
            st.session_state.action_required = None
            finalize_person(tool_args)
            st.rerun()
    
    elif st.session_state.action_required == 'validate_age':
        context = st.session_state.action_context
        st.warning(context["warning_message"])
        confirm = st.radio("Is this correct?", ["Yes", "No"], key="age_confirm")
        if st.button("Confirm", key="confirm_age_btn"):
            if confirm == "Yes":
                st.session_state.action_required = None
                finalize_person(context["tool_args"])
                st.rerun()
            else:
                st.session_state.action_required = None
                st.session_state.messages = []  # Reset conversation for this person
                st.rerun()

# Run the app
if __name__ == "__main__":
    initialize_session_state()
    if st.session_state.get("action_required"):
        handle_actions()
    else:
        main()