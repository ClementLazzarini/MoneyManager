# 💰 MoneyManager

*A comprehensive, multi-user personal finance and wealth management system built with Django.*

## 📌 Table of Contents
* [About the Project](#-about-the-project)
* [Key Features](#-key-features)
* [Data Architecture](#️-data-architecture)
* [Tech Stack](#-tech-stack)
* [Installation & Setup](#-installation--setup)
* [Usage Flow](#-usage-flow)

## 📖 About the Project
MoneyManager is a secure, user-centric web application designed to streamline personal finance tracking and wealth management. By utilizing the "envelope system" alongside automated categorization rules, it allows users to gain granular control over their monthly budgets, long-term savings goals, and daily expenses. The application supports distinct owner profiles, ensuring that user data, transactions, and private categories are strictly isolated. 

## ✨ Key Features
* **Advanced Transaction Processing:** Import transactions via CSV files or add them manually. Users can split transactions into multiple custom amounts and reassign custom dates for accurate monthly budgeting.
* **Automated Categorization Engine:** Define intelligent rules using keywords (e.g., "NETFLIX", "EDF") to automatically sort incoming bank transactions into specific categories during CSV imports.
* **Dynamic Envelope System (Wealth Management):** Create global envelopes for savings goals (e.g., "Holidays 2025", "Emergency Fund"). These envelopes feature automated progress tracking calculations to monitor goal completion.
* **Category-Envelope Bridging:** Link standard monthly categories directly to global envelopes. Transactions can automatically provision (add to) or consume (subtract from) an envelope based on the configured link type.
* **Comprehensive Dashboard:** View monthly insights, savings capacity, real-time comparisons between default/monthly budgets and real expenses, and manage unprocessed bank transactions.
* **Multi-User Privacy:** Supports shared (common) categories alongside strictly private, user-specific categories and rules.

## 🏗️ Data Architecture
The system revolves around several core database models designed for flexibility and accuracy:

| Model | Description |
|---|---|
| **Owner** | An extension of the standard `User` model, isolating all financial data per user. |
| **Transaction** | Stores both raw bank data (reference, date, amount) and user-adjusted data (custom date, split amounts, status). |
| **Category** | Classification tags for transactions. Can be public (shared) or private (owner-specific), featuring customizable icons and color codes. |
| **Budgets** | Split into `DefaultBudget` (baseline allocations) and `MonthlyBudget` (month-specific overrides). |
| **GlobalEnvelope** | Virtual sub-accounts for tracking long-term targets, advances, or savings. |
| **CategoryEnvelopeLink** | The logical bridge defining if a category acts as a PROVISION (savings) or an EXPENSE (consumption) for a specific envelope. |
| **AutoCategoryRule** | Keyword-based triggers to automate the classification of raw bank strings. |

## 🛠️ Tech Stack
The project relies on a modern, robust Python ecosystem:
* **Backend Framework:** Django `==6.0.3`
* **Asynchronous Support:** asgiref `==3.11.1`
* **Frontend Styling:** django-tailwind `==4.4.2` & pytailwindcss `==0.3.0`
* **Environment Management:** python-decouple `==3.8`
* **Database Utilities:** sqlparse `==0.5.5`

## 🚀 Installation & Setup
Follow these steps to get the development environment running locally.

**1. Clone the repository**
```bash
git clone [https://github.com/clementlazzarini/moneymanager.git](https://github.com/clementlazzarini/moneymanager.git)
cd moneymanager
```
**2. Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Tailwind CSS**
Initialize the Tailwind process to compile your stylesheets:
```bash
python manage.py tailwind install
python manage.py tailwind start
```

**5. Run Database Migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

**6. Start the Development Server**
```bash
python manage.py runserver
```
*Access the application at http://127.0.0.1:8000/*

## 💡 Usage Flow

1. **Onboarding:** Create an account and ensure your `Owner` profile is linked. Set your overall current account balance in the Wealth Dashboard. 
2. **Settings & Rules:** Navigate to `/settings/` to establish your custom categories and define `AutoCategoryRules` for recurring merchants. 
3. **Budgeting:** Set up `GlobalEnvelopes` for your savings goals and link them to your categories.
4. **Import Data:** Go to `/import/` and upload your bank's CSV export. The system uses MD5 hashing on the transaction string to completely prevent duplicate entries. 
5. **Processing:** Return to your Dashboard to review the unprocessed inbox. Categorize remaining items manually or split transactions as needed to maintain a perfectly balanced budget.

## 👨‍💻 Author

Clément Lazzarini