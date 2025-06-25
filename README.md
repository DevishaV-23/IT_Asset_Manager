# IT_Asset_Manager# IT Asset Manager

**Project: Software Engineering & Agile**

This project is a full-stack web application designed to provide a robust platform for tracking and managing IT equipment and resources. Built with Python and the Flask framework, it serves as a centralised inventory system where assets can be cataloged, monitored, and managed throughout their lifecycle.

The application was developed following modern Agile and software engineering principles, resulting in a modular, maintainable, and scalable application. Key professional practices demonstrated include a structured project architecture using Flask Blueprints, version control via Git/GitHub, database schema management with Flask-Migrate, automated testing with Pytest, Continuous Integration (CI) with GitHub Actions, and deployment to a live web server.

## Live Application

The application is deployed on Render and can be accessed here: (https://it-asset-manager-tosd.onrender.com/auth/login)

## Key Features

* **Role-Based Access Control (RBAC):** A secure authentication system provides two distinct user roles:
    * **Admin:** Full user privileges, including complete CRUD (Create, Read, Update, Delete) capabilities over all users, assets, and asset categories.
    * **Regular User:** Can view all assets and categories, create and edit assets, and fully manage their own profile.

* **Interactive Dashboard:** A dynamic landing page for logged-in users that provides a real-time statistical overview of the asset inventory, including total assets, counts by status (Active, In Repair, Retired), new assets added this month.

* **Full CRUD Functionality:**
    * **Assets:** Users can manage a detailed inventory of IT assets, with each asset linked to a category and the user who created it for clear accountability.
    * **Asset Categories:** A dedicated interface showing a summary of asset counts for each category and admins can create, edit, and delete asset categories.
    * **User Management:** Admins can perform full CRUD operations on user accounts, including creating new users, editing details, promoting/demoting users, and deleting users, with safeguards to prevent self-deletion or deletion of the last administrator.
    * **Profile Management:** All users can edit their own profile information, including their full name, username, and password, with appropriate security checks.

## Technical Architecture & DevOps

* **Backend:**
    * **Language & Framework:** Python & Flask
    * **Architecture:** Application Factory pattern with Flask Blueprints to separate concerns (`auth`, `assets`, `admin`).
    * **Database:** SQLAlchemy (ORM) with a SQLite backend.
    * **Authentication:** Flask-Login for secure session management.
    * **Security:** Passwords are fully hashed using Werkzeug.

* **Frontend:**
    * **Structure:** HTML5 with Jinja2 Templating.
    * **Styling:** Custom CSS.

* **Development & DevOps Workflow:**
    * **Version Control:** Hosted on GitHub with a history of feature branches, commits, and pull requests demonstrating an Agile workflow.
    * **Database Migrations:** Flask-Migrate is used to manage all database schema changes without data loss.
    * **Automated Testing:** A comprehensive test suite using `pytest` covers models, authentication, and application routes.
    * **Continuous Integration (CI):** A GitHub Actions pipeline automatically runs the full test suite, and deploys the application on every push and pull request to the `main` branch, ensuring code quality and preventing regressions.
    * **Deployment:** The application is deployed to a live production environment on **Render**.

## Setup and Installation

Follow these steps to set up and run the project locally.

### Prerequisites
* Python 3.8+
* Git

### 1. Clone the Repository
```bash
git clone https://github.com/DevishaV-23/IT_Asset_Manager.git

2. Create and Activate a Virtual Environment
It is highly recommended to use a virtual environment.

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
venv\Scripts\Activate.ps1

3. Install Dependencies

#Install all required packages from requirements.txt.

pip install -r requirements.txt

4. Set Up the Database

## This project uses Flask-Migrate. After cloning, you need to set up your local database.

# Set the FLASK_APP environment variable
# On macOS/Linux:
export FLASK_APP=app.py
# On Windows PowerShell:
$env:FLASK_APP = "app.py"

# Apply the latest migration to create all tables
flask db upgrade

# (Optional) Seed the database with sample data
python seed.py

Note: The seed.py script will create an initial admin user, default categories, and 10+ sample users and assets.

5. Run the Application
python app.py

The application will be available at http://127.0.0.1:5000.

Usage
# Admin Account: An administrator account is created by the seeding script.

Username: admin

Password: admin1

# Sample User Accounts: The seeding script also creates regular user accounts, below is a regular user account:

Username: Jane3

Password: password123

# Automated Testing
# The project includes a suite of automated tests. To run them, navigate to the project's root directory and run:

pytest