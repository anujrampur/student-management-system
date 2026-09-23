# Student Management System

A desktop-based Student Management System built with Python and Tkinter, using SQLite for persistent local data storage.

The project provides a graphical user interface (GUI) for administrator authentication, student record management, search, dashboard statistics, data export, and database backup/restore operations. An optional command-line interface (CLI) is also included.

## Features

### Administrator Authentication

- Administrator login through the GUI
- First-run administrator account setup
- Passwords protected using PBKDF2-HMAC-SHA256
- Unique random salt for password hashing
- Stored PBKDF2 iteration count for password verification
- No hard-coded default administrator credentials

### Student Management

The GUI supports:

- Add student
- View students
- Update student records
- Delete student records
- View student details
- Refresh student records
- Student-code uniqueness enforcement

Student information includes:

- Student Code
- Name
- Age
- Course
- Email

### Search

The GUI provides search options for:

- Name
- Student Code
- Course
- Email
- All Fields

Search results can be refreshed or cleared from the dashboard.

### Dashboard

The GUI dashboard provides:

- Total student count
- Course statistics
- Student records table
- Search controls
- Sorting support
- Add, update, delete and view operations
- Export controls
- Backup / Restore access

### Data Export

The GUI supports:

- CSV export
- Excel (`.xlsx`) export

CSV export uses UTF-8 encoding.

Excel export uses `openpyxl` and includes workbook formatting functionality such as column sizing, filtering, and frozen headers.

Excel export requires the optional `openpyxl` package.

### Database Backup and Restore

The GUI provides a dedicated Backup / Restore dialog.

Backup functionality:

- Creates a database backup at a user-selected location
- Uses SQLite's backup API
- Supports timestamped backup filenames

Restore functionality:

- Allows selection of a SQLite backup file
- Validates the selected database
- Creates a safety backup before replacing the current database
- Restores using SQLite's backup API
- Verifies the restored database
- Attempts recovery from the safety backup if the restore process fails

### Legacy JSON Migration

The application supports migration of legacy student data from:

```text
data/students.json
```

## Technology Stack

- Python 3
- Tkinter
- SQLite
- PBKDF2-HMAC-SHA256
- CSV
- openpyxl (optional, for Excel export)


## Requirements

- Python 3
- Tkinter support

Excel export requires the optional `openpyxl` package.

Install it with:

    python -m pip install openpyxl


## Installation

Open a terminal in the project directory:

    cd student_management

Optional virtual environment:

### Windows PowerShell

    python -m venv .venv
    .venv\Scripts\Activate.ps1

### macOS / Linux

    python3 -m venv .venv
    source .venv/bin/activate


## Running the Application

### Graphical Interface

The primary application interface is the Tkinter GUI:

    python gui.py

### First Run

If no administrator account exists, the application opens the Administrator Setup dialog.

Create the first administrator account with a username, password, and password confirmation.

After successful setup, the normal login screen is displayed.

### Existing Installation

If an administrator account already exists, the normal login screen is displayed.

The application does not automatically create a default administrator password.


## Command-Line Interface

An optional command-line interface is also included.

    python main.py

The CLI provides flows for:
- Adding students
- Viewing all students
- Searching by student code
- Searching by name
- Updating students
- Deleting students

The CLI is separate from the GUI administrator authentication flow.


## Project Structure

    student_management/
    |-- gui.py
    |-- main.py
    |-- student.py
    |-- database.py
    |-- utils.py
    |-- data/
    |   |-- students.db
    |   |-- students.json
    |-- README.md
    |-- PHASE1_CHANGELOG.md
    |-- REVIEW_REPORT.md

### Main Files

- `gui.py` - Primary Tkinter graphical application
- `main.py` - Optional command-line interface
- `database.py` - SQLite database, authentication, search, backup and restore
- `student.py` - Student model and validation
- `utils.py` - CLI input, display and utility functions


## Database

The application uses SQLite for persistent local storage.

### Students Table

The students table contains:
- id
- student_code
- name
- age
- course
- email

### Admins Table

The admins table contains:
- id
- username
- password_hash
- salt
- iterations

Passwords are not stored as plain text.

## Security

Administrator authentication uses PBKDF2-HMAC-SHA256 password hashing with a unique random salt.

The database stores the password hash, salt, and PBKDF2 iteration count.

Database operations use parameterized SQL queries.

The application does not contain hard-coded default administrator credentials.

For deployment, use a strong unique administrator password and keep database backups secure.


## Data Validation

Student data is validated before database insertion or update.

Validation includes student information and email format checks.

The database also enforces required student fields and unique student codes.

## Backup and Restore Safety

Database restore replaces the current database contents with the selected backup.

Before an important restore operation:
1. Create a backup of the current database.
2. Select a known-good SQLite backup.
3. Keep independent copies of important student data.

The application creates a safety backup before a restore operation.


## Troubleshooting

### GUI does not start

Check the Python installation:

    python --version

Run a syntax check:

    python -m py_compile database.py gui.py student.py utils.py main.py

### Excel Export Is Unavailable

Install `openpyxl`:

    python -m pip install openpyxl

Then restart the application.

### Login Fails

Verify the administrator username and password.

For an existing installation, create a database backup before making any manual database changes.

### Database Problems

Use the GUI Backup / Restore functionality with a known-good SQLite backup.

## Development and Release Checklist

Before publishing or distributing a release, verify:

- Application starts successfully
- First-run administrator setup works
- Valid administrator login works
- Invalid login is rejected
- Add, update, delete and view operations work
- All GUI search modes work
- CSV export works
- Excel export works when `openpyxl` is installed
- Database backup works
- Database restore works with a test backup
- Safety backup is created before restore
- JSON migration works when applicable
- Python syntax checks pass
- No default administrator credentials are present in source code
- Private student data and runtime backups are excluded from the public release package

## Important Release Notes

Review the following files before publishing the project publicly:

    data/students.db
    data/students.json
    data/student_management_before_restore_*.db

These files may contain local student information or database backups and should not be included in a public repository unless they contain intentionally sanitized sample data.

Never publish real student information or administrator credentials.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Before publishing the project as an open-source repository, add an appropriate `LICENSE` file and update this section accordingly.

## Project Status

The project is currently under development, testing, and release-readiness review.

The GUI is the primary application interface. The CLI is retained as an optional interface for basic student management.




