import os
import sqlite3
import pandas as pd
import fitz  # PyMuPDF for PDF extraction
import spacy
from fuzzywuzzy import fuzz
import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import random

# Load NLP model for text processing
nlp = spacy.load("en_core_web_sm")

# ------------------ DATABASE SETUP ------------------
def init_db():
    """Initialize SQLite database with jobs and candidates tables."""
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()

    # Create jobs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY,
                        title TEXT,
                        skills TEXT,
                        qualifications TEXT)''')

    # Create candidates table
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        email TEXT,
                        education TEXT,
                        experience TEXT,
                        skills TEXT,
                        certifications TEXT,
                        match_score INTEGER,
                        shortlisted INTEGER DEFAULT 0)''')

    conn.commit()
    conn.close()

# ------------------ JOB DESCRIPTION PROCESSING ------------------
def process_job_descriptions(csv_file):
    """Extract job titles, skills, and qualifications from a CSV file and store them in the database."""
    df = pd.read_csv(csv_file, encoding="latin1")
    df = df.iloc[:, :2]  # Keep only first two columns (Job Title, Job Description)
    df.columns = ["Job Title", "Job Description"]
    
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()
    
    skill_keywords = ["Python", "Machine Learning", "AI", "Cloud", "Cybersecurity", "SQL"]
    degree_keywords = ["bachelor", "master", "phd", "degree", "certification"]
    
    data_to_insert = []
    for _, row in df.iterrows():
        job_title = row["Job Title"]
        doc = nlp(row["Job Description"])
        skills = ", ".join([word for word in doc.text.split() if word in skill_keywords])
        qualifications = " ".join([sent.text for sent in doc.sents if any(deg in sent.text.lower() for deg in degree_keywords)])
        
        data_to_insert.append((job_title, skills, qualifications))
    
    cursor.executemany("INSERT INTO jobs (title, skills, qualifications) VALUES (?, ?, ?)", data_to_insert)
    conn.commit()
    conn.close()

# ------------------ PDF TEXT EXTRACTION ------------------
def extract_text_from_pdf(pdf_path):
    """Extract text content from a given PDF resume."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text() # type: ignore
    return text

# ------------------ CANDIDATE DATA EXTRACTION ------------------
import re  # Import Regular Expressions module

def extract_email(text):
    """Extract the first email found in the resume text."""
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(email_pattern, text)
    return match.group(0) if match else "Unknown"

def extract_education(text):
    """Extract education details from resume text."""
    education_keywords = ["Bachelor", "Master", "PhD", "Diploma", "Engineering", "Degree"]
    education_matches = [line for line in text.split("\n") if any(word in line for word in education_keywords)]
    return " | ".join(education_matches) if education_matches else "Unknown"

def extract_experience(text):
    """Extract experience section from resume text."""
    lines = text.split("\n")
    experience_section = [line for line in lines if "Experience" in line or "Work Experience" in line]
    return " ".join(experience_section) if experience_section else "Unknown"

skill_keywords = ["Python", "Machine Learning", "AI", "Deep Learning", "TensorFlow", "SQL", "Java", "Cloud", 
                 "Cybersecurity", "Data Science", "NLP", "Big Data", "DevOps"]


def extract_skills(text):
    """Extract skills from resume text."""
    found_skills = [skill for skill in skill_keywords if skill.lower() in text.lower()]
    return ", ".join(found_skills) if found_skills else "Unknown"

def extract_certifications(text):
    """Extract certifications from resume text."""
    certs = [line for line in text.split("\n") if "Certified" in line or "Certification" in line]
    return " | ".join(certs) if certs else "None" 

# ------------------ PROCESSING CVS AND STORING IN DATABASE ------------------
def process_cvs(cv_folder):
    """Extract candidate details from resumes and store them in the database."""
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()
    
    for file in os.listdir(cv_folder):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(cv_folder, file)
            text = extract_text_from_pdf(pdf_path)
            doc = nlp(text)
            
            name = next((ent.text for ent in doc.ents if ent.label_ == "PERSON"), "Unknown")
            email = extract_email(text)  # Extract Email
            education = extract_education(text)
            experience = extract_experience(text)
            skills = extract_skills(text)
            certifications = extract_certifications(text)

             # ✅ Check if candidate already exists
            cursor.execute("SELECT id FROM candidates WHERE name = ? AND education = ?", (name, education))
            existing_candidate = cursor.fetchone()

            if not existing_candidate:  # Insert only if candidate does not exist
                cursor.execute(
                    "INSERT INTO candidates (name, email, education, experience, skills, certifications, match_score, shortlisted) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, email, education, experience, skills, certifications, 0, 0)
                )
    
    conn.commit()
    conn.close()

# ------------------ MATCHING CANDIDATES TO JOBS ------------------
def compute_match_scores():
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs")
    jobs = cursor.fetchall()
    
    cursor.execute("SELECT * FROM candidates")
    candidates = cursor.fetchall()
    
    for candidate in candidates:
        best_match = 0
        for job in jobs:
            skill_score = fuzz.token_set_ratio(candidate[5], job[2])  # Skills match
            education_score = fuzz.token_set_ratio(candidate[3], job[3])  # Education match
            cert_score = fuzz.token_set_ratio(candidate[6], job[3])  # Certification match
            
            # **Bonus** for Exact Skill Match
            exact_skill_bonus = 5 if set(candidate[5].split(", ")).intersection(set(job[2].split(", "))) else 0
            
            # **Final Weighted Score**
            final_score = (skill_score * 0.65) + (education_score * 0.15) + (cert_score * 0.15) + exact_skill_bonus

            if final_score > best_match:
                best_match = final_score

        cursor.execute("UPDATE candidates SET match_score = ? WHERE id = ?", (best_match, candidate[0]))
    
    conn.commit()
    conn.close()



# ------------------ SHORTLISTING CANDIDATES ------------------
def shortlist_candidates(threshold=80):
    """Retrieve candidates who meet or exceed the match score threshold."""
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()

    # Update candidates who meet the threshold to 'shortlisted = 1'
    cursor.execute("UPDATE candidates SET shortlisted = 1 WHERE match_score >= ?", (threshold,))
    conn.commit()

    # Fetch shortlisted candidates including email
    cursor.execute("SELECT name, email FROM candidates WHERE shortlisted = 1 AND match_score >= ?", (threshold,))
    shortlisted = cursor.fetchall()

    conn.commit()
    conn.close()

    return shortlisted
    

# Gmail Configuration
EMAIL_ADDRESS = "rajakarthick.0405@gmail.com"
EMAIL_PASSWORD = "cvyd alif zzzm loqp"

# Generate random interview dates and times
def get_interview_schedule():
    today = datetime.today()
    interview_date = today + timedelta(days=random.randint(2, 7))  # Random date in next 7 days
    interview_time = random.choice(["10:00 AM", "2:00 PM", "4:00 PM"])  # Choose time slot
    return interview_date.strftime("%A, %B %d, %Y"), interview_time

# Send Email Function
def send_email(name, email):
    """Sends an interview invitation email."""
    interview_date, interview_time = get_interview_schedule()
    interview_format = "Virtual (Google Meet)"  # Change as needed

    subject = f"Interview Invitation - {name}"
    body = f"""\
Dear {name},

Congratulations! You have been shortlisted for the next round of interviews for our open positions.

Interview Date: {interview_date}  
Interview Time: {interview_time}  
Interview Format: {interview_format}  

Please confirm your availability by replying to this email. We look forward to speaking with you.

Best regards,  
ABC Company
Karthick Raja  
HR Team
www.abccompany.com
Phone: +1 (123) 456-7890
"""

    # Email Setup
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        print(f"✅ Email sent successfully to {name} ({email})")
    except Exception as e:
        print(f"❌ Failed to send email to {name} ({email}): {e}")

# Fetch shortlisted candidates from the database
def send_interview_invites():
    """Fetch shortlisted candidates and send interview invitations."""
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, email FROM candidates WHERE shortlisted = 1 AND match_score >= 80")
    shortlisted_candidates = cursor.fetchall()
    conn.close()

    for name, email in shortlisted_candidates:
        send_email(name, email)

def count_qualified_candidates():
    """Count the number of shortlisted candidates who meet the required criteria."""
    conn = sqlite3.connect("recruitment.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM candidates WHERE shortlisted = 1 AND match_score >= 80")
    result = cursor.fetchone()[0]  # Fetch count
    
    conn.close()
    return result


# ------------------ MAIN EXECUTION ------------------
if __name__ == "__main__":
    init_db()  # Step 1: Initialize database
    
    process_job_descriptions("D:\\VScode\\Project\\Hackathon\\Job_screening\\job_description.csv")  # Step 2: Process job descriptions
    process_cvs("D:\\VScode\\Project\\Hackathon\\Job_screening\\CVs1")  # Step 3: Process resumes

    compute_match_scores()  # Step 4: Compute match scores
    shortlisted = shortlist_candidates(80)  # Step 5: Shortlist candidates
    
    count = count_qualified_candidates()
    print(f"\n✅ Total number of Shortlisted Candidates: {count}")

    if count > 0:
        print("\n✅ Shortlisting completed. Sending interview emails...")
        send_interview_invites()
        print("\n✅ All interview invitations sent successfully.")
    else:
        print("\n❌ No candidates met the criteria. No emails sent.")

    print("-----------------------------------------------------")


    

