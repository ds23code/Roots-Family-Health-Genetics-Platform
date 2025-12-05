import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
import json
from prompts import get_base_system_prompt_template, get_role_specific_prompt_self, get_role_specific_prompt_relative
from backend import data_store
from utils import compute_age_from_yyyymmdd, finalize_person
from tools import get_tools
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")

# 🔑 Initialize OpenAI API client
client = OpenAI(api_key=api_key)

def interview_person(messages, tools, relation_label, patient_name=None):
    # Normalize relation_label for internal use
    relation_label = relation_label.replace(' ', '_')

    # 🚫 Step 1: Skip if person with same relation already exists
    if any(p["relation"] == relation_label for p in data_store.people):
        return

    # 🧠 Step 2: Retrieve patient's age (for biological plausibility checks)
    self_data = next((p for p in data_store.people if p["relation"] == "self"), None)
    patient_age = compute_age_from_yyyymmdd(self_data["birthday"]) if self_data else None

    # Access the global focal_disease
    global focal_disease # - Declare global focal_disease

    # 🧾 Step 3: Construct system prompt based on who we're interviewing
    # Replace underscores in relation_label for natural phrasing
    relation_label_clean = relation_label.replace('_', ' ')
    base_system_prompt_template = get_base_system_prompt_template(patient_name, relation_label_clean, focal_disease)
    if relation_label == "self":
        role_specific_prompt = get_role_specific_prompt_self()
    else:
        # Prompt for relatives (e.g., father, mother, child_1)
        role_specific_prompt = get_role_specific_prompt_relative(patient_age, relation_label)

    # 📌 Step 6: Add system message to conversation
    # 🧠 Load memory facts from CSV
    memory = data_store.seed_memory_from_csv()

    # 🧾 Compose full system prompt
    combined_prompt = (
        memory + "\n\n" +
        base_system_prompt_template.format(
            relation_label_clean=relation_label_clean,
            focal_disease=focal_disease,
            patient_name=patient_name if patient_name else "the patient"
        ) +
        role_specific_prompt
    )
    # 📌 Add system message to conversation
    messages.append({
        "role": "system",
        "content": combined_prompt
    })

    # 🚀 Step 7: Start conversation by sending messages to OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    reply = response.choices[0].message

    # 🛠️ Step 8: If GPT triggers a tool call (i.e., data is complete and structured)
    if reply.tool_calls:
        for tool_call in reply.tool_calls:
            tool_args = json.loads(tool_call.function.arguments)
            # if tool_args.get("relation") != relation_label:
            #     continue
            # finalize_person(tool_args, relation_label)
            # return
            # Normalize tool_args relation for comparison
            tool_relation = tool_args.get("relation", "").replace(' ', '_')
            if tool_relation != relation_label:
                continue
            finalize_person(tool_args, relation_label)
            return
    else:
        # 🤖 If no tool call yet, show the first assistant message (question)
        assistant_message = reply.content.strip()
        print(f"\n👨‍⚕️ {assistant_message}")
        messages.append({"role": "assistant", "content": assistant_message})

    # 🔁 Step 9: Interactive loop for user to respond and GPT to ask follow-up questions
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            exit()
        
        # Add user response to conversation
        messages.append({"role": "user", "content": user_input})

        # Send updated messages to GPT
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        reply = response.choices[0].message

        # 🛠️ Check if GPT is ready to invoke the function (tool)
        if reply.tool_calls:
            processed_a_valid_call = False
            for tool_call in reply.tool_calls:
                tool_args = json.loads(tool_call.function.arguments)


                # --- ADD THIS DEBUG BLOCK --- if needed
                #print("="*20)
                #print(f"DEBUG: AI attempted tool call for relation: '{tool_args.get('relation')}'")
                #print(f"DEBUG: Current target relation is: '{relation_label.replace('_', ' ')}'")
                #print("="*20)
                # ✅ Make sure tool call matches the correct relation
                # if not relation_label.replace('_', ' ').startswith(tool_args.get('relation', "")):
                #     continue
                # Normalize both sides to underscores for consistent comparison
                tool_relation = tool_args.get('relation', '').replace(' ', '_')
                if relation_label != tool_relation:
                    continue

                # Finalize and store the collected data
                processed_a_valid_call = True
                finalize_person(tool_args, relation_label)
                return
            # If the loop finishes and we haven't processed a valid call, it means all calls were wrong.
            if not processed_a_valid_call:
                recovery_message = "I apologize, I seem to have gotten my notes mixed up. Let's get back on track. Could you please repeat the answer?"
                print(f"\n👨‍⚕️ {recovery_message}")
                messages.append({"role": "assistant", "content": recovery_message})
        else:
            # 🤖 Continue the chat with next assistant question
            assistant_message = reply.content.strip()
            messages.append({"role": "assistant", "content": assistant_message})
            print(f"\n👨‍⚕️ {assistant_message}")

def interview_multiple(base_context, tools, relation_base, patient_name=None):
    count = 1
    while True:
        confirm = input(f"\n🧑‍⚕️ Do you have any {relation_base.replace('_', ' ')} to add? ").strip().lower()
        if confirm not in ("yes", "y", "yeah", 'i do'):
            break
        label = f"{relation_base}_{count}"

        # Create a fresh, clean message list for this specific person
        # by copying the base context.
        person_messages = base_context.copy()

        interview_person(person_messages, tools, label, patient_name)
        # # If user says "I don't have..." after assistant asks about a new sibling, let them break
        # last_user_msg = messages[-1]["content"].lower()
        # if "don't have" in last_user_msg or "no more" in last_user_msg:
        #     break
        count += 1

def main():
    global focal_disease
    focal_disease = None
    has_partner = False
    print("\nWelcome to ROOTS, your online medical chatbot. I'll guide you through a few simple steps to collect key information including:\n" \
    "  * Names\n" \
    "  * Birth dates\n" \
    "  * Sexes\n" \
    "  * Living status\n" \
    "  * Medical conditions\n" \
    "\nYou don’t need to have everything - just share what you know, and we’ll grow your family tree together. \n\n" \
    "Type 'exit' to quit or ask for a summary of your information at any time.\n\n" \
    "Let's begin!")
    tools = get_tools()
    messages = [
        {"role": "system", "content": "You are a medical assistant conducting a patient intake interview. Ask one question at a time. Extract structured data using tool calling when ready."}
    ]

     # --- NEW: Capture and Standardize Focal Disease ---
    print("\n👨‍⚕️ To start, what was the doctor's recommendation or the reason for this visit? (e.g., concern about breast cancer, family history of heart disease)")
    
    raw_focal_disease_input = ""
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            exit()
        if user_input:
            raw_focal_disease_input = user_input
            break
        else:
            print("Please provide a reason for the visit to continue.")

    # --- LLM Call to Standardize Focal Disease ---
    print("\n🧑‍⚕️ Just a moment, I'm processing that reason to ensure clarity for the interview...")
    
    # Create a specific, isolated message list for this standardization call
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
        {"role": "user", "content": raw_focal_disease_input}
    ]

    try:
        # Call OpenAI API for standardization (no tools needed here)
        standardization_response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14", # Use a capable model
            messages=standardization_messages,
            max_tokens=30, # Keep response very short
            temperature=0.2 # Make it deterministic
        )
        standardized_focal_disease = standardization_response.choices[0].message.content.strip()
        
        # Validate standardization: if LLM generates something nonsensical or too long, revert to raw
        if not standardized_focal_disease or len(standardized_focal_disease.split()) > 20:
            print("⚠️ Standardization failed or was too vague. Using original input.")
            focal_disease = raw_focal_disease_input
        else:
            focal_disease = standardized_focal_disease
        
        print(f"🧑‍⚕️ Okay, for the interview, we'll focus on: '{focal_disease}'.")

    except Exception as e:
        print(f"❌ Error during focal disease standardization: {e}. Using original input.")
        focal_disease = raw_focal_disease_input # Fallback to original input if LLM call fails

    # Add the standardized focal disease to the main conversation history
    # This helps the main LLM (in interview_person) to remember it.
    messages.append({"role": "user", "content": f"The reason for this visit is: {focal_disease}"})
    messages.append({"role": "assistant", "content": f"Okay, I understand the visit is about: '{focal_disease}'. Now, let's begin the family history interview."})

    interview_person(messages, tools, "self")

    self_person = next((p for p in data_store.people if p["relation"] == "self"), None)
    # Use the extracted name, with "you" as a fallback
    patient_name = self_person['first_name'] 


    father_context = [
        {"role": "system", "content": f"The patient you are speaking with is named {patient_name}. The visit is focused on '{focal_disease}'. You will now collect information about the patient's father."}
    ]
    print("\n--- Now gathering information about the Father. ---")
    interview_person(father_context, tools, "father", patient_name)

    mother_context = [
        {"role": "system", "content": f"The patient you are speaking with is named {patient_name}. The visit is focused on '{focal_disease}'. You will now collect information about the patient's mother."}
    ]
    print("\n--- Now gathering information about the Mother. ---")
    interview_person(mother_context, tools, "mother", patient_name)

    sibling_base_context = [
        {"role": "system", "content": f"The patient you are speaking with is named {patient_name}. The visit is focused on '{focal_disease}'. You will now collect information about one of the patient's siblings."}
    ]
    interview_multiple(sibling_base_context, tools, "sibling", patient_name)


    confirm = input("\n🧑‍⚕️ Do you have a partner? ").strip().lower()
    if confirm in ("yes", "y", "yeah"):
        has_partner = True
        partner_context = [
            {"role": "system", "content": f"The patient you are speaking with is named {patient_name}. The visit is focused on '{focal_disease}'. You will now collect information about the patient's partner."}
        ]
        print("\n--- Now gathering information about the Partner. ---")
        interview_person(partner_context, tools, "partner", patient_name)

    if has_partner:
        partner_person = next((p for p in data_store.people if p["relation"] == "partner"), None)
        child_base_context_prompt = (
        f"The patient is {patient_name} (sex: {'male' if self_person['sex'] == '1' else 'female'}). "
        f"The visit is focused on '{focal_disease}'. "
        f"The patient's partner is {partner_person['first_name']} "
        f"(sex: {'male' if partner_person['sex'] == '1' else 'female'})."
        "You will now collect information about one of the patient's children"
        )
        child_base_context = [{"role": "system", "content": child_base_context_prompt}]
        interview_multiple(child_base_context, tools, "child", patient_name)

    # --- Now gathering information about Paternal Grandparents ---
    paternal_grandfather_context = [
        {"role": "system", "content": f"You are now collecting information about the patient's paternal grandfather (father's father)."}
    ]
    print("\n--- Now gathering information about the Paternal Grandfather. ---")
    interview_person(paternal_grandfather_context, tools, "paternal_grandfather", patient_name)

    paternal_grandmother_context = [
        {"role": "system", "content": f"You are now collecting information about the patient's paternal grandmother (father's mother)."}
    ]
    print("\n--- Now gathering information about the Paternal Grandmother. ---")
    interview_person(paternal_grandmother_context, tools, "paternal_grandmother", patient_name)

    # --- Now gathering information about Maternal Grandparents ---
    maternal_grandfather_context = [
        {"role": "system", "content": f"You are now collecting information about the patient's maternal grandfather (mother's father)."}
    ]
    print("\n--- Now gathering information about the Maternal Grandfather. ---")
    interview_person(maternal_grandfather_context, tools, "maternal_grandfather", patient_name)

    maternal_grandmother_context = [
        {"role": "system", "content": f"You are now collecting information about the patient's maternal grandmother (mother's mother)."}
    ]
    print("\n--- Now gathering information about the Maternal Grandmother. ---")
    interview_person(maternal_grandmother_context, tools, "maternal_grandmother", patient_name)

    print("\n👋 Interview complete for patient and family. Goodbye!")

if __name__ == "__main__":
    main()