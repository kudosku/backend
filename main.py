import pdfplumber
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# --- Extract text from PDF ---
def extract_text_from_pdf(pdf_path):
    console.print(f"[bold green][+] Reading file:[/] {pdf_path}")
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        console.print(f"[bold green][+] Successfully extracted text.[/]")
        return full_text
    except Exception as e:
        console.print(f"[bold red][!] Error:[/] {e}")
        return None

# --- Extract info ---
def extract_deadline(text):
    match = re.search(r"(deadline|submission date).{0,50}(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text, re.IGNORECASE)
    if match:
        date_str = match.group(2)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        return date_str
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
            missing.append(sec_name)
    return missing

# --- Detect risks and highlight issues ---
def detect_risks(deadline, budget, contact, missing_sections):
    risks = []
    today = datetime.today()
    
    if not deadline:
        risks.append("[red]Missing submission deadline[/red]")
    elif isinstance(deadline, datetime) and deadline < today:
        risks.append(f"[red]Deadline already passed: {deadline.strftime('%d-%m-%Y')}[/red]")
    
    if not budget:
        risks.append("[red]Missing tender budget[/red]")
    else:
        if budget < 1000:
            risks.append(f"[yellow]Unusually low budget: {budget}[/yellow]")
        elif budget > 1_000_000:
            risks.append(f"[yellow]Unusually high budget: {budget}[/yellow]")
    
    if not contact:
        risks.append("[red]Missing contact info[/red]")

    for section in missing_sections:
        risks.append(f"[red]Missing section: {section}[/red]")

    return risks if risks else ["[green]No immediate risks detected[/green]"]

# --- Automatic risk scoring ---
def score_tender(risks):
    risk_count = sum(1 for r in risks if "Missing" in r or "Unusually" in r or "Deadline already passed" in r)
    if risk_count == 0:
        return "[green]Low[/green]"
    elif risk_count <= 3:
        return "[yellow]Medium[/yellow]"
    else:
        return "[red]High[/red]"

# --- Fast summary (first 100 lines) ---
def fast_summary(text, max_lines=100):
    lines = text.split("\n")
    return "\n".join(lines[:max_lines])

# --- Main workflow ---
pdf_file_path = "/content/NYERI-TENDER-DOCUMENT.pdf"  # Replace with your PDF
text = extract_text_from_pdf(pdf_file_path)

if text:
    # Extract info
    deadline = extract_deadline(text)
    budget = extract_budget(text)
    contact = extract_contact(text)
    
    # Detect missing sections
    missing_sections = detect_missing_sections(text)
    
    # Detect risks
    risks = detect_risks(deadline, budget, contact, missing_sections)
    
    # Auto score
    risk_level = score_tender(risks)
    
    # --- Report ---
    console.print("\n[bold cyan]--- Tender Analysis Report ---[/bold cyan]")
    console.print(fast_summary(text)[:2000])

    # Table for extracted info
    table = Table(title="Extracted Information", box=box.ROUNDED)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Submission Deadline", str(deadline) if deadline else "[red]Not found[/red]")
    table.add_row("Tender Budget", str(budget) if budget else "[red]Not found[/red]")
    table.add_row("Contact Email", contact if contact else "[red]Not found[/red]")
    console.print(table)

    # Table for risks
    risk_table = Table(title="Detected Risks & Missing Sections", box=box.ROUNDED)
    risk_table.add_column("Issue", style="bold")
    for r in risks:
        risk_table.add_row(r)
    console.print(risk_table)

    # Risk level
    console.print(f"\n[bold magenta]Automatic Tender Risk Level:[/] {risk_level}")
