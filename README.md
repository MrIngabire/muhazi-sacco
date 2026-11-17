```markdown
# MUHAZI SACCO — Web-Based Cooperative Contribution and Loan Management System

<div align="center">

![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.15-A30000?style=for-the-badge&logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-Academic-yellow?style=for-the-badge)

**A full-stack web application for managing Savings and Credit Cooperative (SACCO) operations**

*Case Study: MUHAZI SACCO (IMBADUKO MUHAZI SACCO), Rwanda*

[Overview](#-overview) • [Features](#-features) • [Tech Stack](#-tech-stack) • [Setup](#-setup) • [Demo Logins](#-demo-login-credentials) • [API](#-api-endpoints) • [Author](#-author)

</div>

---

## 📋 Overview

MUHAZI SACCO is a comprehensive web-based platform designed to digitize the operations of a Rwandan Savings and Credit Cooperative. The system replaces manual paper-based bookkeeping with a centralized, real-time, role-aware financial management platform.

The application implements **Role-Based Access Control (RBAC)** with 9 distinct roles and enforces **separation of duties** required by the National Bank of Rwanda (BNR) regulations for SACCOs.

### Key Objectives

- ✅ Automate contribution tracking and loan lifecycle management
- ✅ Enforce multi-step loan approval workflows
- ✅ Generate real-time financial analytics and reports
- ✅ Maintain an immutable audit trail for regulatory compliance
- ✅ Support Rwandan cooperative operations (RWF currency, Kinyarwanda names, mobile money references)

---

## ✨ Features

### 👥 Member Portal

| Feature | Description |
|---|---|
| **Dashboard** | Real-time savings, active loans, and 3× loan eligibility |
| **Contributions** | Submit deposits with MoMo reference codes, view transaction ledger |
| **Loan Application** | Apply for loans with automatic eligibility checking |
| **Repayment Schedule** | View installment calendar, pay installments, track progress |

### 🏢 Staff Portal

| Role | Features |
|---|---|
| **Teller** | Record deposits at the counter, disburse approved loans |
| **Accountant** | Verify contributions against MoMo statements, generate reports |
| **Loan Officer** | Review loan applications, forward to management |
| **Manager** | Approve loans (< RWF 2M), view analytics, manage members |
| **Credit Committee** | Approve large loans (≥ RWF 2M) |
| **Board Member** | Read-only oversight of analytics and reports |
| **Supervisor** | View full audit trail for BNR compliance |
| **System Admin** | Full access, user management, system oversight |

### 🔐 Security & Compliance

- **JWT authentication** with refresh tokens
- **Role-Based Access Control** — 9 roles with granular permissions
- **Separation of duties** — teller ≠ verifier, reviewer ≠ approver, approver ≠ disburser
- **Immutable audit log** — every sensitive action recorded with actor, role, IP, timestamp
- **Two-step contribution verification** — members/tellers record, accountants verify
- **Multi-step loan workflow** — PENDING → UNDER_REVIEW → APPROVED → DISBURSED → CLOSED
- **Committee approval** for loans above the threshold

### 📊 Analytics

- Real-time KPIs (liquidity, disbursed loans, interest revenue, pending items)
- **Interactive charts** powered by Recharts:
  - Member growth vs loan disbursements (12-month dual-axis line chart)
  - Contribution inflow (area chart)
  - Loan status distribution (donut chart)
  - Top 10 members by savings (horizontal bar chart)
- CSV export of full financial statements

---

## 🛠️ Tech Stack

### Backend
- **Django 5.0** — Web framework
- **Django REST Framework 3.15** — API layer
- **SimpleJWT** — JWT authentication
- **PostgreSQL 16** (production) / **SQLite** (development)
- **django-cors-headers** — CORS management

### Frontend
- **React 18** — UI library
- **Vite 5** — Build tool
- **Tailwind CSS v4** — Styling
- **Recharts** — Interactive charts
- **Lucide React** — Icon library
- **Axios** — HTTP client

### DevOps
- **Git** — Version control
- **GitHub Actions** — CI/CD (optional)

---

## 🚀 Setup

### Prerequisites

| Tool | Minimum Version | Download |
|---|---|---|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Git | 2.40+ | [git-scm.com](https://git-scm.com/) |
| PostgreSQL | 16+ (optional — SQLite works for dev) | [postgresql.org](https://www.postgresql.org/download/) |

### 1. Clone the Repository

```powershell
git clone https://github.com/YOUR_USERNAME/muhazi-sacco.git
cd muhazi-sacco
```

### 2. Backend Setup

```powershell
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
# source venv/bin/activate         # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment template and edit values
Copy-Item .env.example .env

# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Seed demo data (creates 53 members, 200+ contributions, 80+ loans, etc.)
python manage.py seed_heavy --fresh

# Start the development server
python manage.py runserver
```

The backend will be available at **http://127.0.0.1:8000**.

### 3. Frontend Setup

Open a **new terminal**:

```powershell
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at **http://localhost:5173**.

### 4. Access the Application

Open your browser to **http://localhost:5173** and log in with any of the demo credentials below.

---

## 🔑 Demo Login Credentials

The seeded database includes **9 pre-configured accounts**, one for each role:

| Role | Username | Password | Landing Page |
|---|---|---|---|
| 🟢 **Member** | `gentil` | `password123` | Member Dashboard |
| 🟢 **Member** | `sarah` | `password123` | Pending loan (valid) |
| 🟢 **Member** | `eric` | `password123` | Pending loan (exceeds limit) |
| 🔵 **Teller** | `teller` | `password123` | Record Deposit |
| 🔵 **Accountant** | `accountant` | `password123` | Verify Contributions |
| 🔵 **Loan Officer** | `loanofficer` | `password123` | Review Queue |
| 🟣 **Manager** | `manager` | `password123` | Analytics Dashboard |
| 🟣 **Credit Committee** | `credit` | `password123` | Committee Queue |
| ⚪ **Board Member** | `board` | `password123` | Analytics (read-only) |
| ⚪ **Supervisor** | `supervisor` | `password123` | Audit Log |
| 🔴 **System Admin** | `admin` | `admin123` | Full Analytics |

> 💡 **Tip:** Use the "Quick Login" buttons on the login screen to switch between roles for demonstration.

---

## 📁 Project Structure

```
muhazi-sacco/
│
├── backend/
│   ├── backend/
│   │   ├── settings.py              # Django settings (env-driven)
│   │   ├── urls.py                  # Project URL configuration
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── core/
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── seed_heavy.py    # Seeder with 53 members, 200+ contributions
│   │   ├── migrations/
│   │   ├── models.py                # 7 models (Member, Contribution, Loan, etc.)
│   │   ├── views.py                 # All API endpoints
│   │   ├── serializers.py           # DRF serializers
│   │   ├── urls.py                  # App URL configuration
│   │   ├── permissions.py           # RBAC decorators
│   │   ├── admin.py
│   │   └── apps.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   ├── manage.py
│   └── db.sqlite3                   # Not committed (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Main React app (all views)
│   │   ├── main.jsx
│   │   ├── index.css                # Tailwind v4 import
│   │   └── assets/
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js               # Vite + Tailwind v4
│   └── node_modules/                # Not committed (gitignored)
│
├── docs/
│   └── traceability.md              # Book requirements → implementation
│
├── .gitignore
├── README.md
└── LICENSE
```

---

## 📡 API Endpoints

All endpoints are prefixed with `/api/` and require JWT authentication (except `/auth/login/`).

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login/` | Login with username + password |
| `GET` | `/api/auth/me/` | Current user identity + permissions |

### Member Portal

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/member/dashboard/` | Dashboard data (savings, loans, eligibility) |
| `GET` `POST` | `/api/member/contributions/` | List / submit contributions |
| `POST` | `/api/member/loan/apply/` | Apply for a loan |
| `GET` | `/api/member/repayments/` | Active loan repayment schedule |
| `POST` | `/api/member/pay-installment/` | Pay an installment |
| `GET` `PATCH` | `/api/member/notifications/` | List / mark notifications read |

### Staff Portal

| Method | Endpoint | Allowed Roles |
|---|---|---|
| `GET` | `/api/admin/analytics/` | Manager, Accountant, Board, Supervisor, Admin |
| `GET` | `/api/admin/analytics/charts/` | (same as above) |
| `GET` | `/api/admin/loans/review-queue/` | Loan Officer, Manager, Admin |
| `GET` | `/api/admin/loans/approval-queue/` | Manager, Credit Committee, Admin |
| `PATCH` | `/api/admin/loans/workflow/` | Role-specific per action |
| `GET` | `/api/admin/contributions/pending/` | Accountant, Manager, Admin |
| `PATCH` | `/api/admin/contributions/verify/` | Accountant, Manager, Admin |
| `POST` | `/api/admin/contributions/record/` | Teller, Accountant, Admin |
| `GET` | `/api/admin/reports/` | Manager, Accountant, Board, Supervisor, Admin |
| `GET` | `/api/admin/reports/export/` | (same as above) — CSV download |
| `GET` | `/api/admin/arrears/` | Manager, Loan Officer, Supervisor, Admin |
| `GET` | `/api/admin/audit-log/` | Supervisor, System Admin only |
| `GET` `POST` | `/api/admin/users/` | System Admin only |
| `GET` | `/api/admin/members/` | All staff |

For full documentation including request/response examples, see [docs/traceability.md](docs/traceability.md).

---

## 🧪 Testing

### Run Django Tests

```powershell
cd backend
python manage.py test
```

### Manual Smoke Test

```powershell
# Login
curl -X POST http://127.0.0.1:8000/api/auth/login/ `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"gentil\",\"password\":\"password123\"}'

# Use the returned access token in subsequent requests
curl http://127.0.0.1:8000/api/member/dashboard/ `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🎬 Demo Walkthrough (Defense Script)

Follow this sequence to demonstrate **every use case** from the book:

1. **Login as `gentil`** (Member)
   - Show dashboard: RWF 1.45M savings, RWF 500K active loan, RWF 4.35M eligibility
   - Submit a contribution → status = `PENDING_VERIFICATION`
   - Show loan application form

2. **Login as `teller`**
   - Record a deposit on behalf of a member
   - Show disbursement queue (if any loans are approved)

3. **Login as `accountant`**
   - Verify the pending contribution Gentil just submitted
   - Show rejection flow with reason capture
   - Export the financial statement CSV

4. **Login as `loanofficer`**
   - Review Sarah's pending loan application
   - Show the 3× eligibility validation (Eric's loan shows "Exceeds")

5. **Login as `manager`**
   - Approve Sarah's reviewed loan
   - Show the same action fails for Eric's loan (> RWF 2M threshold blocks it)

6. **Login as `credit`** (Credit Committee)
   - Approve Eric's loan (only committee can approve ≥ RWF 2M)

7. **Login as `teller`** again
   - Disburse both approved loans

8. **Login as `supervisor`**
   - Show the audit log with every action from steps 1–7 recorded

9. **Login as `admin`**
   - Show the analytics dashboard with interactive charts
   - Show the member directory (53 members)
   - Show user management

**Key points to mention during defense:**
- ✅ Separation of duties is enforced (teller can't verify their own deposit)
- ✅ Loans ≥ RWF 2M require committee approval
- ✅ Every action is logged in the immutable audit trail
- ✅ The charts use real aggregated data, not hardcoded values

---

## 🔒 Environment Variables

The backend reads configuration from `backend/.env`. Copy from `.env.example` and adjust:

```bash
# Django
DJANGO_SECRET_KEY=change-me-to-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite by default; set engine to 'postgresql' for production)
DJANGO_DB_ENGINE=sqlite
# DJANGO_DB_ENGINE=postgresql
# DJANGO_DB_NAME=muhazi_sacco
# DJANGO_DB_USER=postgres
# DJANGO_DB_PASSWORD=your-secure-password
# DJANGO_DB_HOST=localhost
# DJANGO_DB_PORT=5432

# JWT
JWT_ACCESS_MINUTES=60
JWT_REFRESH_DAYS=7

# CORS (production)
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> ⚠️ **Never commit `.env` to Git.** It contains secrets.

---

## 🐛 Troubleshooting

### `ModuleNotFoundError: No module named 'django'`

**Cause:** Virtual environment not activated.

**Fix:**
```powershell
cd backend
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### `Connection refused` on frontend

**Cause:** Backend not running.

**Fix:**
```powershell
cd backend
python manage.py runserver
```

### `CORS policy` error in browser

**Cause:** Frontend port doesn't match `CORS_ALLOWED_ORIGINS`.

**Fix:** Either
- Ensure frontend runs on `http://localhost:5173` (Vite default), OR
- Update `settings.py` to allow your actual frontend origin

### `python manage.py shell < seed.py` fails on PowerShell

**Cause:** PowerShell doesn't support `<` redirection.

**Fix:** Use the management command instead:
```powershell
python manage.py seed_heavy --fresh
```

### `timezone.utc` AttributeError

**Cause:** Django 5 removed `timezone.utc`. Use `timezone.UTC` or `datetime.timezone.utc`.

**Fix:** Already resolved in this codebase — if you see this, you're on old code.

### `401 Unauthorized` everywhere

**Cause:** Token expired or not attached.

**Fix:** Log out and log back in. The frontend auto-clears expired tokens.

---

## 🚢 Deployment

### Backend (Railway / Render / Heroku)

1. Set environment variables in the platform's dashboard
2. Add `gunicorn` to `requirements.txt`
3. Add `Procfile`: `web: gunicorn backend.wsgi --bind 0.0.0.0:$PORT`
4. Run migrations: `python manage.py migrate --noinput`
5. Collect static files: `python manage.py collectstatic --noinput`

### Frontend (Vercel / Netlify)

1. Set `VITE_API_URL` environment variable to your backend URL
2. Build command: `npm run build`
3. Output directory: `dist`

---

## 📚 Documentation

- [**Traceability Matrix**](docs/traceability.md) — Map of every book requirement to its implementation
- [**API Reference**](docs/api.md) — Full endpoint documentation (if available)

---

## 🤝 Contributing

This is an academic project submitted to Mount Kigali University. Contributions are welcome for educational purposes:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is submitted as partial fulfillment of the requirements for the **Bachelor of Business Information Communication Technology** degree at **Mount Kigali University**.

**Academic Use Only.** © 2026 NIYIBIZI Gentil. All rights reserved.

---

## 👨‍💻 Author

**NIYIBIZI Gentil**
- 🎓 BBICTR/2024/48075
- 🏛️ Mount Kigali University
- 📧 [your.email@example.com](mailto:your.email@example.com)
- 🐙 [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)

**Supervisor:** Mr. Emmanuel Manyange

---

## 🙏 Acknowledgments

- **Mount Kigali University** — Faculty of Business and Information Technology
- **MUHAZI SACCO** — Case study organization
- **National Bank of Rwanda (BNR)** — Regulatory framework reference
- **Open Source Community** — Django, React, Tailwind, and Recharts teams

---

<div align="center">

**⭐ If this project helped you, please give it a star! ⭐**

Made with ❤️ in Kigali, Rwanda 🇷🇼

</div>
```