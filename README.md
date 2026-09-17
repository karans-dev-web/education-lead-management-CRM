# education-lead-management-CRM
# EduLead CRM

Student Enquiry, Counselling & Lead Conversion Management System

## Features
- **Lead Management**: Efficiently handle and organize student leads.
- **Student Enquiry Tracking**: Monitor incoming enquiries in real-time.
- **Follow-up Management**: Schedule and manage candidate follow-ups.
- **Lead Status Pipeline**: Track lead progression through various stages.
- **Search & Filtering**: Quick filter and search options for candidate records.
- **Conversion Tracking**: Measure conversion rates from enquiry to admission.
- **Dashboard**: Comprehensive visual overview of key metrics.
- **CRUD Operations**: Complete Create, Read, Update, Delete capabilities.

## Tech Stack
- **Backend**: Python, Flask
- **Database**: SQLite, SQL
- **Frontend**: HTML, CSS, JavaScript

## How to Run Locally

Clone the repository:

```bash
git clone https://github.com/karans-dev-web/education-lead-management-CRM.git
cd education-lead-management-CRM
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install dependencies and start the app:

```powershell
pip install -r requirements.txt
python infinity_education_crm_app.py
```

Open `http://127.0.0.1:5000` in your browser. The SQLite database is created automatically.

## Deploy

The repository includes a `Procfile` for hosts such as Render, Railway, and Heroku. Use:

```bash
pip install -r requirements.txt
gunicorn infinity_education_crm_app:app
```

Set the application port from the hosting platform. The app uses SQLite and creates its database automatically on first start.
