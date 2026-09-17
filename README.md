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
- **Lead Scoring**: Hot, Warm and Cold priority labels with next-best-action recommendations.
- **Automatic Follow-up Reminders**: Overdue and due-today leads are grouped automatically.
- **Source Analytics**: Compare Instagram, Google, Referral and Website performance.
- **Counsellor Dashboard**: Assigned, interested and converted lead performance.
- **Student Requirements**: Capture goals, budget, batch preference and counselling notes.
- **Conversion Funnel**: Track movement from New enquiry to Converted admission.
- **CSV Export**: Download the full lead pipeline for Excel and reporting.
- **Role-based Login**: Admin and Counsellor access with protected actions.
- **WhatsApp Follow-up**: Open a direct WhatsApp conversation from a lead record.
- **AI-assisted Recommendations**: Explainable priority and next-step suggestions based on lead signals.

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

### Demo accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Counsellor | `priya` | `priya123` |

## Deploy

The repository includes a `Procfile` for hosts such as Render, Railway, and Heroku. Use:

```bash
pip install -r requirements.txt
gunicorn infinity_education_crm_app:app
```

Set the application port from the hosting platform. The app uses SQLite and creates its database automatically on first start.
