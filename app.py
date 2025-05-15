from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Google Forms + Drive API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly"
]

# Load credentials from downloaded service account file
SERVICE_ACCOUNT_FILE = "credentials.json"  # Make sure this file is in the same folder

# Authenticate with Google
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Test route to check if backend is working
@app.route("/")
def home():
    return "✅ Formlo backend is running!"

# Main route to generate form
@app.route("/generate_form", methods=["POST"])
def generate_form():
    data = request.get_json()
    mcq_text = data.get("text", "")

    try:
        # Parse text into questions
        questions = parse_mcqs(mcq_text)

        # Initialize Google Forms API
        service = build("forms", "v1", credentials=creds)

        # Create an empty form first
        form_data = {
            "info": {
                "title": "Formlo Quiz",
                "documentTitle": "Formlo Quiz"
            }
        }
        created_form = service.forms().create(body=form_data).execute()
        form_id = created_form["formId"]

        # Add questions using batchUpdate
        requests = []
        for q in questions:
            requests.append({
                "createItem": {
                    "item": {
                        "title": q["question"],
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [{"value": opt} for opt in q["options"]],
                                    "shuffle": False
                                }
                            }
                        }
                    },
                    "location": {"index": 0}
                }
            })

        # Send questions to form
        service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

        # Return the form's edit URL
        form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        return jsonify({"success": True, "form_url": form_url})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Simple MCQ parser from raw text
def parse_mcqs(text):
    questions = []
    current_q = {}
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("Q"):
            if current_q:
                questions.append(current_q)
            current_q = {
                "question": line.split(":", 1)[1].strip(),
                "options": []
            }
        elif any(line.startswith(prefix) for prefix in ["A.", "B.", "C.", "D."]):
            current_q["options"].append(line[2:].strip())

    if current_q:
        questions.append(current_q)

    return questions

# Start the Flask app
if __name__ == "__main__":
    app.run(debug=True)
