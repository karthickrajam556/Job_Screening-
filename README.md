Job Screening & Resume Matching System
A Python-based Automated Resume Screening system that extracts job descriptions, processes candidate resumes, matches skills, and sends interview invitations via email.

📂 Features
✅ Job Description Processing – Extracts required skills & qualifications from a CSV file
✅ Resume Parsing – Extracts candidate details (Name, Email, Skills, Education, etc.) from PDFs
✅ Matching Algorithm – Uses NLP and fuzzy matching to compare resumes with job requirements
✅ Database Storage – Stores jobs & candidates in an SQLite database
✅ Email Notifications – Sends interview invitations to shortlisted candidates via Gmail

🛠 Tech Stack
Python (Core Logic)

SQLite (Database)

spaCy (NLP for Resume Processing)

FuzzyWuzzy (Skill & Qualification Matching)

PyMuPDF (fitz) (PDF Text Extraction)

pandas (CSV Handling)

smtplib (Email Sending)

⚡ Installation
Clone the Repository

bash
Copy
Edit
git clone https://github.com/your-username/JobScreening.git
cd JobScreening
Install Dependencies

bash
Copy
Edit
pip install -r requirements.txt
Run the Project

bash
Copy
Edit
python job_screening.py
📜 Usage
Add job descriptions in job_description.csv

Place candidate resumes in the CVs1/ folder

Run the script, and it will:

Extract and analyze job descriptions

Process resumes & store data in the database

Match candidates and shortlist them

Send interview invitations to qualified candidates

📧 Email Configuration
Update the EMAIL_ADDRESS and EMAIL_PASSWORD in the script to enable email notifications.
Use App Passwords for Gmail (Avoid using your real password).

🛠 To-Do / Future Enhancements
 Add a Web Dashboard for easier management

 Integrate with LinkedIn API for auto-importing resumes

 Implement Machine Learning-based Matching

💡 Contributors
👤 Karthick Raja (Project Lead)
📧 karthickrajam556@gmail.com
