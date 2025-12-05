import requests
from backend import data_store

# --- MONDO API Search Utilities ---

def extract_mondo_code(iri):
    """
    Extract the MONDO code from the IRI.
    Example: 'http://purl.obolibrary.org/obo/MONDO_0005148' -> 'MONDO_0005148'
    """
    if iri and "MONDO_" in iri:
        return iri.split("/")[-1]
    return "N/A"

def is_likely_human_disease(label):
    """
    Exclude labels that contain a comma anywhere.
    """
    return "," not in label

def get_mondo_matches(disease_name, max_results=10):
    """
    Search MONDO ontology for disease_name and return top matches (label + MONDO code).
    Returns a list of dicts: [{"label": ..., "mondo_code": ...}, ...]
    """
    url = "https://www.ebi.ac.uk/ols4/api/search"
    params = {
        "q": disease_name,
        "ontology": "mondo"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"[MONDO API ERROR] Status code: {response.status_code}")
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

# --- Integration with data store ---

def process_medical_conditions(input_text, person_relation=""):
    conditions = [c.strip() for c in input_text.split(',') if c.strip()]
    person_diseases = {}  # Will store disease_label: True/False for this person
    
    for condition in conditions[:4]:  # max 4 conditions
        # Check if this disease was already mentioned by another family member
        existing_match = None
        for existing_disease in data_store.disease_columns.keys():
            if condition.lower() in existing_disease.lower() or existing_disease.lower() in condition.lower():
                confirm = input(f"Is this the same condition as the {existing_disease} that another family member has? ").strip().lower()
                if confirm in ("yes", "y", "yeah"):
                    existing_match = existing_disease
                    break
        if existing_match:
            person_diseases[existing_match] = True
            continue
            
        print(f"\n🔍 Searching MONDO matches for: {condition}")
        matches = get_mondo_matches(condition, max_results=10)

        if not matches:
            print(f"⚠️ No MONDO matches found for '{condition}', recording as free text.")
            disease_label = condition
            mondo_code = "N/A"
        else:
            print("💡 Please select the best match:")
            for i, match in enumerate(matches):
                print(f"{i+1}. {match['label']} ({match['mondo_code']})")

            while True:
                choice = input(f"Enter 1-{len(matches)} to select, or 0 to use original term: ")
                if choice.isdigit() and 0 <= int(choice) <= len(matches):
                    choice = int(choice)
                    break
                else:
                    print("❌ Invalid input, try again.")

            if choice == 0:
                disease_label = condition
                mondo_code = "N/A"
            else:
                disease_label = matches[choice - 1]['label']
                mondo_code = matches[choice - 1]['mondo_code']
        
        # Add to global disease tracking if new
        if disease_label not in data_store.disease_columns:
            data_store.disease_columns[disease_label] = mondo_code
            data_store.disease_column_names[disease_label] = f"{disease_label} ({mondo_code})"
        
        person_diseases[disease_label] = True
    
    return person_diseases