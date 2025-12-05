# Genetic Family History Chatbot (DESN2000 Project)

👩‍⚕️ This is a prototype command-line chatbot designed to collect structured genetic family history from patients - DESN2000 @UNSW.

## 📌 Project Description

This chatbot interacts with users in a natural and professional tone to collect:
- Personal details
- Family relationships (parents, siblings, children, grandparents, partners)
- Up to 4 genetic or medical conditions per family member

The collected data is output as a structured CSV file and a pedigree chart.

## 🔧 Features

- Conversational command-line interface
- Collects detailed personal and family data
- Matches diseases with MONDO ontology codes
- Outputs CSV and pedigree chart ready for analysis

## Prerequisites

### 1. Python Requirements
- Python 3.11+
- pip package manager

### 2. System Packages
- R-base (for pedigree plotting)
- Development headers for Python and R

### 3. API Key
- OpenAI API key (sign up at [platform.openai.com](https://platform.openai.com))

## Installation Steps
### MacOS/Linux
#### Getting started
- Make sure you have python3 installed (`python3 --version` - should output something similar to Python 3.13.5)
- `git clone` Group1_DESN2000 SSH key in terminal
- Open the Group1_DESN2000 folder
- **Generate a virtual environment**: `python3 -m venv venv`
- **Open the virtual environment**: `source venv/bin/activate`
- **Install required packages**: `pip3 install -r requirements.txt`
- **Move to the chatbot folder**: `cd app/chatbot`

#### Running the backend
- In the Group1_DESN2000/app/chatbot/backend folder
- **Open the backend**: `python3 AIchatbot.py`
- **Close the backend**: type "exit" at any time
- **Pedigree maker (when finished chatting)**: `python3 convert_csv_to_R.py`

#### Running the front end
- In the Group1_DESN2000/app/chatbot/frontend folder
- **Open the frontend**: `streamlit run root_app.py`
- **Close the frontend**: control + C 

#### Ending 
- **Close the virtual environment**: `deactivate`

### Windows
#### Getting started
- Make sure you have python3 installed (`python3 --version` - should output something similar to Python 3.13.5)
- `git clone` Group1_DESN2000 SSH key in terminal
- Open the Group1_DESN2000 folder
- **Generate a virtual environment**: `python -m venv venv`
- **Open the virtual environment**: `venv\Scripts\activate`
- **Install required packages**: `pip install -r requirements.txt`
- **Move to the chatbot folder**: `cd app/chatbot`

#### Running the backend
- In the Group1_DESN2000/app/chatbot/backend folder
- **Open the backend**: `python AIchatbot.py`
- **Close the backend**: type "exit" at any time
- **Pedigree maker (when finished chatting)**: `python convert_csv_to_R.py`

#### Running the front end
- In the Group1_DESN2000/app/chatbot/frontend folder
- **Open the frontend**: `streamlit run root_app.py`
- **Close the frontend**: control + C 

#### Ending 
- **Close the virtual environment**: `deactivate`


### Configuration Options

#### Using Different OpenAI Models
Edit the `root_app.py` file and modify:
```python
# Change this line:
model="gpt-4o-mini-2024-07-18"
```
## Troubleshooting

### Common Issues
1. **R Package Installation Failures**:
   ```bash
   sudo R -e "install.packages('kinship2', repos='https://cloud.r-project.org')"
   ```

2. **Missing Python Dependencies**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **API Key Errors**:
   - Verify key in `.env` file
   - Check OpenAI account quota

4. **Streamlit Port Conflicts**:
   ```bash
   streamlit run root_app.py --server.port 8502
   ```

## Running on CSE Servers
Special instructions for UNSW CSE environment:

```bash
# Load Python module
module load python/3.10.4

# Create virtual environment
python -m venv ./venv
source venv/bin/activate

# Install packages offline
pip install --no-index --find-links=./wheelhouse -r requirements.txt

# Set API key in environment
export OPENAI_API_KEY="your_api_key"
```

## Project Structure
```
├── app                     # Main application directory
│   └── chatbot             # Chatbot module
│       ├── backend         # Backend logic (data handling, AI, MONDO API integration)
│       │   ├── AIchatbot.py
│       │   ├── convert_csv_to_R.py
│       │   ├── data_store.py
│       │   ├── mondo_integration.py
│       │   ├── prompts.py
│       │   └── results     # Output results
│       ├── frontend        # Frontend logic and assets
│       │   ├── assets
│       │   │   ├── roots_logo.png
│       │   │   └── roots_logo_banner.png
│       │   ├── patients.csv
│       │   ├── pedigree_plot.R
│       │   └── root_app.py
│       ├── tools.py        # Utility tools for chatbot
│       └── utils.py        # Helper functions for chatbot
├── README.md               # Project documentation
└── requirements.txt        # Python dependencies
```

## Support
For additional help, contact the development team:
- Nick Yen
- Dhruv Sharma
- Minh Le
- Kellie Lai
- Tara Moore
