import os
import re
from datetime import datetime
import pdfplumber
from flask import Flask, request, jsonify, make_response
from werkzeug.utils import secure_filename

# --- Flask App Setup ---
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Your Analysis Functions (Copied from your script) ---

# --- Extract text from PDF ---
def extract_text_from_pdf(pdf_path):
    print(f"[+] Reading file: {pdf_path}")
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        print(f"[+] Successfully extracted text.")
        return full_text
    except Exception as e:
        print(f"[!] Error: {e}")
        return None

# --- Extract info ---
def extract_deadline(text):
    match = re.search(r"(deadline|submission date).{0,50}(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.IGNORECASE)
    if match:
        date_str = match.group(2)
        # Try multiple formats
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return date_str  # Return as string if no format matches
    return None

def extract_budget(text):
    match = re.search(r"(budget|amount).{0,50}([\d,]+)", text, re.IGNORECASE)
    if match:
        number_str = match.group(2).replace(",", "").strip()
        if number_str.isdigit():
            return int(number_str)
    return None

def extract_contact(text):
    match = re.search(r"(contact|email).{0,50}([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text, re.IGNORECASE)
    return match.group(2) if match else None

# --- Detect missing sections ---
def detect_missing_sections(text):
    sections = {
        "Scope": ["scope of work", "project scope", "services required"],
        "Evaluation Criteria": ["evaluation criteria", "award criteria", "how bids will be evaluated"],
        "Eligibility": ["eligibility", "who can apply", "required qualifications"]
    }
    missing = []
    lower_text = text.lower()
    for sec_name, keywords in sections.items():
        if not any(k in lower_text for k in keywords):
            missing.append(f"Missing section: {sec_name}")
    return missing

# --- Detect risks ---
def detect_risks(deadline, budget, contact, missing_sections):
    risks = []
    today = datetime.today()
    
    if not deadline:
        risks.append("Missing submission deadline")
    elif isinstance(deadline, datetime) and deadline < today:
        risks.append(f"Deadline already passed: {deadline.strftime('%d-%m-%Y')}")
    
    if not budget:
        risks.append("Missing tender budget")
    else:
        if budget < 1000:
            risks.append(f"Unusually low budget: {budget}")
        elif budget > 1_000_000:
            risks.append(f"Unusually high budget: {budget}")
    
    if not contact:
        risks.append("Missing contact info")
    
    risks.extend(missing_sections)
    
    return risks if risks else ["No immediate risks detected"]

# --- Automatic risk scoring ---
def score_tender(risks):
    risk_count = sum(1 for r in risks if "Missing" in r or "Unusually" in r or "Deadline already passed" in r)
    if risk_count == 0:
        return "Low"
    elif risk_count <= 3:
        return "Medium"
    else:
        return "High"

# --- Fast summary (first 100 lines) ---
def fast_summary(text, max_lines=100):
    lines = text.split("\n")
    return "\n".join(lines[:max_lines])

# --- Main API Endpoint ---
@app.route('/analyze', methods=['POST'])
def analyze_pdf():
    # 1. Check if file exists
    if 'pdf_file' not in request.files:
        return make_response(jsonify({"error": "No file part"}), 400)
    
    file = request.files['pdf_file']
    
    if file.filename == '':
        return make_response(jsonify({"error": "No selected file"}), 400)
    
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            # 2. Save the file temporarily
            file.save(pdf_path)
            
            # 3. Run your analysis
            text = extract_text_from_pdf(pdf_path)
            if not text:
                return make_response(jsonify({"error": "Could not extract text from PDF"}), 500)
            
            deadline = extract_deadline(text)
            budget = extract_budget(text)
            contact = extract_contact(text)
            missing_sections = detect_missing_sections(text)
            risks = detect_risks(deadline, budget, contact, missing_sections)
            risk_level = score_tender(risks)
            summary = fast_summary(text)
            
            # 4. Format the response
            # IMPORTANT: Convert datetime to string for JSON
            deadline_str = None
            if isinstance(deadline, datetime):
                deadline_str = deadline.strftime('%d-%m-%Y')
            elif isinstance(deadline, str):
                deadline_str = deadline
            
            result = {
                "risk_level": risk_level,
                "deadline": deadline_str,
                "budget": budget,
                "contact": contact,
                "risks": risks,
                "summary": summary
            }
            
            # 5. Return JSON response
            return jsonify(result)
        
        except Exception as e:
            print(f"[!] Server Error: {e}")
            return make_response(jsonify({"error": f"An internal error occurred: {e}"}), 500)
        
        finally:
            # 6. Clean up the uploaded file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
    
    else:
        return make_response(jsonify({"error": "Invalid file type, please upload a PDF"}), 400)

# --- Route to serve the HTML page ---
@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    # Set the static folder so Flask can find index.html, css, and js
    
    # Get the port number from the environment variable (set by Render)
    # Default to 10000 if not found (for local testing)
    port = int(os.environ.get('PORT', 10000))
    # Run on 0.0.0.0 to be accessible externally (as required by Render)
    app.run(host='0.0.0.0', port=port)
