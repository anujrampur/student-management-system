"""Database module using SQLite for persistent student data storage."""

import sqlite3
import os
import json
import hashlib
import secrets
import shutil
from datetime import datetime

# Security configuration
PBKDF2_ITERATIONS = 310000  # OWASP 2025 recommendation for PBKDF2-SHA256

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "students.db")
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "students.json")


def _get_conn():
    """Return a database connection with the table ensured to exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            course TEXT NOT NULL,
            email TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            iterations INTEGER NOT NULL DEFAULT 100000
        )"""
    )
    # Add iterations column if missing (migration for existing databases)
    try:
        conn.execute("ALTER TABLE admins ADD COLUMN iterations INTEGER NOT NULL DEFAULT 100000")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    # Add indexes for frequently searched columns (idempotent)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_course ON students(course)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_email ON students(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_student_code ON students(student_code)")
    conn.commit()
    return conn


def _migrate_from_json():
    """Migrate students.json data to SQLite if records don't already exist.
    Keeps students.json intact as a backup. Idempotent: safe to run multiple times.
    Supports both legacy "id" field and current "student_code" field for student code."""
    if not os.path.exists(JSON_PATH):
        return
    try:
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
        if not data:
            return
        conn = _get_conn()
        try:
            for record in data:
                try:
                    # Support both "id" (legacy) and "student_code" (current) field names
                    student_code = record.get("student_code") or record.get("id")
                    if student_code is None:
                        continue
                    conn.execute(
                        """INSERT OR IGNORE INTO students
                        (student_code, name, age, course, email)
                        VALUES (?, ?, ?, ?, ?)""",
                        (student_code, record["name"], record["age"],
                         record["course"], record["email"])
                    )
                except KeyError:
                    # Skip records with missing required fields
                    pass
            conn.commit()
        finally:
            conn.close()
    except (json.JSONDecodeError, IOError):
        pass


def has_admin_accounts() -> bool:
    """Return True if at least one administrator account exists."""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM admins")
        return cursor.fetchone()[0] > 0
    finally:
        conn.close()


def _ensure_default_admin():
    """Legacy compatibility hook; default credentials are no longer created automatically."""
    return None


def _hash_password(password: str, salt: bytes = None, iterations: int = PBKDF2_ITERATIONS) -> tuple:
    """Hash password using PBKDF2 with SHA-256.
    Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hash_bytes.hex(), salt.hex()


def _verify_password(password: str, stored_hash_hex: str, salt_hex: str, iterations: int = PBKDF2_ITERATIONS) -> bool:
    """Verify a password against stored hash and salt."""
    salt = bytes.fromhex(salt_hex)
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hash_bytes.hex() == stored_hash_hex


def _create_admin(conn, username: str, password: str) -> bool:
    """Create a new admin account."""
    try:
        hash_hex, salt_hex = _hash_password(password)
        conn.execute(
            "INSERT INTO admins (username, password_hash, salt, iterations) VALUES (?, ?, ?, ?)",
            (username, hash_hex, salt_hex, PBKDF2_ITERATIONS)
        )
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error:
        return False


def create_admin(username: str, password: str) -> tuple:
    """Create a new administrator account securely.
    Returns (success: bool, message: str)."""
    username = str(username).strip()

    if not username:
        return False, "Username cannot be empty."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(username) > 50:
        return False, "Username must not exceed 50 characters."

    if not password:
        return False, "Password cannot be empty."

    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    conn = _get_conn()
    try:
        if _create_admin(conn, username, password):
            conn.commit()
            return True, "Administrator account created successfully."
        return False, "Username already exists or account could not be created."
    finally:
        conn.close()


def authenticate_admin(username: str, password: str) -> bool:
    """Verify admin credentials. Returns True if valid."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT password_hash, salt, iterations FROM admins WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        stored_hash, salt, iterations = row
        # Use stored iterations for verification (backward compatible)
        return _verify_password(password, stored_hash, salt, iterations)
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def load_students():
    """Load all students from the SQLite database. Returns a list of dicts."""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT student_code, name, age, course, email FROM students")
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while loading: {e}")
        return []
    finally:
        conn.close()


def add_student(student_dict):
    """Add a new student directly to SQLite. Returns True if successful, False if duplicate."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO students (student_code, name, age, course, email) VALUES (?, ?, ?, ?, ?)",
            (student_dict["student_code"], student_dict["name"], student_dict["age"],
             student_dict["course"], student_dict["email"])
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"Database error while adding: {e}")
        return False
    finally:
        conn.close()


def update_student(student_code, updated_data):
    """Update a student by student_code in SQLite. Returns True if found and updated."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "UPDATE students SET name=?, age=?, course=?, email=? WHERE student_code=?",
            (updated_data["name"], updated_data["age"], updated_data["course"],
             updated_data["email"], student_code)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error while updating: {e}")
        return False
    finally:
        conn.close()


def delete_student(student_code):
    """Delete a student by student_code from SQLite. Returns True if found and deleted."""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM students WHERE student_code=?", (student_code,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error while deleting: {e}")
        return False
    finally:
        conn.close()


def find_student_by_id(student_code):
    """Find and return a student by student_code from SQLite. Returns None if not found."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT student_code, name, age, course, email FROM students WHERE student_code=?",
            (student_code,)
        )
        row = cursor.fetchone()
        if row:
            return {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
        return None
    except sqlite3.Error as e:
        print(f"Database error while searching: {e}")
        return None
    finally:
        conn.close()


def get_all_students():
    """Return all students from SQLite."""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT student_code, name, age, course, email FROM students")
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while loading all: {e}")
        return []
    finally:
        conn.close()


def search_students_by_name(name):
    """Search students by name using SQLite LIKE (case-insensitive partial match)."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT student_code, name, age, course, email FROM students WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{name}%",)
        )
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while searching by name: {e}")
        return []
    finally:
        conn.close()


def search_students_by_code(code):
    """Search students by student_code using SQLite LIKE (case-insensitive partial match)."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT student_code, name, age, course, email FROM students WHERE LOWER(student_code) LIKE LOWER(?)",
            (f"%{code}%",)
        )
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while searching by code: {e}")
        return []
    finally:
        conn.close()


def search_students_by_course(course):
    """Search students by course using SQLite LIKE (case-insensitive partial match)."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT student_code, name, age, course, email FROM students WHERE LOWER(course) LIKE LOWER(?)",
            (f"%{course}%",)
        )
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while searching by course: {e}")
        return []
    finally:
        conn.close()


def search_students_by_email(email):
    """Search students by email using SQLite LIKE (case-insensitive partial match)."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT student_code, name, age, course, email FROM students WHERE LOWER(email) LIKE LOWER(?)",
            (f"%{email}%",)
        )
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while searching by email: {e}")
        return []
    finally:
        conn.close()


def search_students_all_fields(query):
    """Search students across all text fields (student_code, name, course, email)
    using SQLite LIKE (case-insensitive partial match). Age (integer) is not searched."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """SELECT student_code, name, age, course, email FROM students 
               WHERE LOWER(student_code) LIKE LOWER(?)
                  OR LOWER(name) LIKE LOWER(?)
                  OR LOWER(course) LIKE LOWER(?)
                  OR LOWER(email) LIKE LOWER(?)""",
            (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
        )
        return [
            {"student_code": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4]}
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        print(f"Database error while searching all fields: {e}")
        return []
    finally:
        conn.close()


def get_course_statistics():
    """Get course statistics (course name and student count)."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT course, COUNT(*) as count FROM students GROUP BY course ORDER BY count DESC"
        )
        return [{"course": row[0], "count": row[1]} for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error while getting course statistics: {e}")
        return []
    finally:
        conn.close()


def backup_database(backup_path: str) -> tuple:
    """Create a backup of the database using SQLite's backup API.
    Returns (success: bool, message: str)."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
        
        source_conn = _get_conn()
        try:
            dest_conn = sqlite3.connect(backup_path)
            try:
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            source_conn.close()
        return True, f"Database backup created successfully at {backup_path}"
    except Exception as e:
        return False, f"Failed to create backup: {e}"


def restore_database(backup_path: str) -> tuple:
    """Restore database from backup file using SQLite's backup API.
    Creates a safety backup before restoring.
    Works safely even with other connections open (Windows-compatible).
    Returns (success: bool, message: str)."""
    if not os.path.exists(backup_path):
        return False, "Backup file not found."
    
    # Validate it's a valid SQLite file
    try:
        test_conn = sqlite3.connect(backup_path)
        test_conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        test_conn.close()
    except Exception:
        return False, "Invalid or corrupted backup file."
    
    # Create safety backup before restore (using backup API)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safety_backup = os.path.join(
        os.path.dirname(DB_PATH),
        f"student_management_before_restore_{timestamp}.db"
    )
    
    try:
        source_conn = _get_conn()
        try:
            safety_conn = sqlite3.connect(safety_backup)
            try:
                source_conn.backup(safety_conn)
            finally:
                safety_conn.close()
        finally:
            source_conn.close()
    except Exception as e:
        return False, f"Failed to create safety backup: {e}"
    
    # Restore using SQLite's backup API: backup FROM backup_path TO main DB
    # This works even if other connections are open (they'll see the changes on next operation)
    try:
        # Open backup as source, main DB as destination
        src_conn = sqlite3.connect(backup_path)
        try:
            dest_conn = _get_conn()
            try:
                # This copies all pages from backup into main DB
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            src_conn.close()
    except Exception as e:
        # Try to restore from safety backup
        try:
            src_conn = sqlite3.connect(safety_backup)
            try:
                dest_conn = _get_conn()
                try:
                    src_conn.backup(dest_conn)
                finally:
                    dest_conn.close()
            finally:
                src_conn.close()
        except Exception:
            pass
        return False, f"Failed to restore database: {e}"
    
    # Verify the restored database
    try:
        test_conn = _get_conn()
        test_conn.execute("SELECT 1 FROM students LIMIT 1")
        test_conn.close()
    except Exception:
        # Try to restore from safety backup
        try:
            src_conn = sqlite3.connect(safety_backup)
            try:
                dest_conn = _get_conn()
                try:
                    src_conn.backup(dest_conn)
                finally:
                    dest_conn.close()
            finally:
                src_conn.close()
        except Exception:
            pass
        return False, "Restored database is invalid."
    
    return True, f"Database restored successfully from {backup_path}. Safety backup created at {safety_backup}."


def initialize_database():
    """Initialize database tables, run JSON migration, and ensure default admin.
    Call on application startup."""
    _migrate_from_json()
    _ensure_default_admin()