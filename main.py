from fastapi import FastAPI, File, UploadFile
import pdfplumber
import os
import re

app = FastAPI()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Extract text from PDF ---
def extract_text_from_pdf(pdf_path):
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        return full_text
    except Exception as e:
        return f"Error: {e}"

# --- Analyze key info ---
def extract_deadline(text):
    match = re.search(r"(deadline|submission date).{0,50}(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.IGNORECASE)
    return match.group(2) if match else None

def extract_budget(text):
    match = re.search(r"(budget|amount).{0,50}([\d,]+)", text, re.IGNORECASE)
    if match:
        val = match.group(2).replace(",", "")
        return int(val) if val.isdigit() else None
    return None

def detect_missing_sections(text):
    sections = ["scope", "evaluation criteria", "eligibility"]
    missing = [s for s in sections if s.lower() not in text.lower()]
    return missing

def score_risk(deadline, budget, missing_sections):
    score = 0
    if not deadline:
        score += 1
    if not budget:
        score += 1
    score += len(missing_sections)
    
    if score == 0:
        return "Low"
    elif score <= 2:
        return "Medium"
    else:
        return "High"

# --- API endpoint ---
@app.post("/analyze")
async def analyze_tender(file: UploadFile = File(...)):
    pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    
    text = extract_text_from_pdf(pdf_path)
    deadline = extract_deadline(text)
    budget = extract_budget(text)
    missing_sections = detect_missing_sections(text)
    risk_level = score_risk(deadline, budget, missing_sections)
    
    report = {
        "filename": file.filename,
        "deadline": deadline or "Missing",
        "budget": budget or "Missing",
        "missing_sections": missing_sections,
        "risk_level": risk_level,
        "preview": text[:1500] + "..." if len(text) > 1500 else text
    }
    return report
