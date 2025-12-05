# 🔧 Tool schema for patient and family info extraction
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
                        "birthday": {"type": "integer"},
                        "sex": {"type": "string", "enum": ["1", "2"]},
                        # remove height and weight here
                        # "height_cm": {"type": "number"},
                        # "weight_kg": {"type": "number"},
                        "conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Medical conditions or known diagnoses"
                        },
                        "is_dead": {
                            "type": "integer",
                            "description": "Whether the person has died"
                        }
                    },
                    # removed height and weight here
                    "required": ["relation", "first_name", "last_name", "birthday", "sex", "is_dead"]
                }
            }
        }
    ]
