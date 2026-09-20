# Student Management System - Code Audit Report

**Project**: Student Management System (GUI + CLI)  
**Date**: 2025  
**Status**: Working application with identified issues  
**Files Analyzed**: `gui.py`, `student.py`, `database.py`, `utils.py`, `main.py`, `README.md`

---

## 1. CRITICAL ISSUES

### 1.1 LoginDialog Missing `transient(parent)` - GUI Hang Risk
**File**: `gui.py` (lines 37-50)  
**Severity**: Critical

```python
self.dialog = tk.Toplevel(parent)
self.dialog.title("Student Management System - Login")
self.dialog.resizable(False, False)
# Don't use transient(parent) when parent may be withdrawn  <-- COMMENT ADDED TO JUSTIFY REMOVAL
self.dialog.grab_set()
```

**Problem**: The `LoginDialog` explicitly removed `transient(parent)` with a comment claiming it causes issues when parent is withdrawn. However:
- `main()` calls `root.withdraw()` BEFORE creating `LoginDialog(root)`
- A `Toplevel` without `transient()` to a withdrawn parent becomes a **top-level window with no parent relationship**
- On some window managers (especially Linux/WSL), this causes the dialog to appear behind other windows or become inaccessible
- The `grab_set()` without `transient()` creates a modal dialog that may not properly block the hidden root

**Impact**: Potential application hang on startup, dialog not visible, or focus issues.

**Fix**: Keep `transient(parent)` but ensure parent is NOT withdrawn when dialog is created, OR use a different approach (see Medium issues).

---

### 1.2 Duplicate `_get_visible_students()` Method
**File**: `gui.py` (lines 714-727 AND 832-845)  
**Severity**: Critical

The exact same 14-line method appears **twice** in `StudentManagementApp` class:
- First at line 714 (inside class, after `clear_search`)
- Second at line 832 (after `_on_database_restored`)

The second definition **overwrites** the first at runtime. This is a copy-paste error that could cause confusion during maintenance.

---

### 1.3 SQL Injection Vulnerability in Search Functions
**File**: `database.py` (lines 238-334)  
**Severity**: Critical

All search functions use f-strings to build LIKE patterns:

```python
# Line 243
"SELECT ... WHERE LOWER(name) LIKE LOWER(?)", (f"%{name}%",)

# Line 324
(f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
```

**Problem**: While parameterized queries are used (the `?` placeholder), the `%` wildcards are concatenated in Python **before** being passed as parameters. This is actually **safe** from SQL injection because the wildcards are part of the parameter value, not the SQL string.

**Wait - re-analyzing**: The parameters ARE passed as `?` placeholders. The f-string only constructs the parameter VALUE, not the SQL. This is **NOT** a SQL injection vulnerability. The parameters are properly escaped by SQLite.

**Correction**: This is actually SAFE. The f-string builds the search pattern (`%term%`) which is then passed as a parameter. No SQL injection possible.

**However**: There's a **LOGIC BUG** in `search_students_all_fields` (line 324) - it searches `age` as text with LIKE, which makes no sense for an integer field. Also, the query doesn't search `age` at all despite the comment saying "all fields".

---

### 1.4 Default Admin Password Hardcoded and Weak
**File**: `database.py` (line 78)  
**Severity**: Critical

```python
_create_admin(conn, "admin", "admin123")
```

**Problems**:
1. Hardcoded default credentials (`admin`/`admin123`)
2. Weak password (no complexity requirements)
3. No mechanism to force password change on first login
4. No way to disable default admin after setup
5. Password visible in source code

---

### 1.5 Database Connection Leaks in Error Paths
**File**: `database.py` (multiple functions)

Multiple functions open connections but may not close them on early returns or exceptions:

```python
def add_student(student_dict):
    conn = _get_conn()
    try:
        # ... execute ...
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # conn NOT closed here!
    except sqlite3.Error as e:
        print(f"Database error while adding: {e}")
        return False  # conn NOT closed here!
    finally:
        conn.close()  # Only runs if no early return
```

**Problem**: The `finally` block only executes if no `return` in `except` blocks. But wait - `finally` ALWAYS executes in Python, even after `return` in `try` or `except`. So this is actually **SAFE** in Python.

**Correction**: Python's `finally` executes regardless of `return` in `try`/`except`. Connection closing is correct.

---

### 1.6 Race Condition in `restore_database`
**File**: `database.py` (lines 415-430)  
**Severity**: Critical

```python
# Close any existing connections by getting a fresh one and closing immediately
try:
    temp_conn = _get_conn()
    temp_conn.close()
except Exception:
    pass

# Now restore by copying the backup file over the main DB
try:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    shutil.copy2(backup_path, DB_PATH)
```

**Problem**: 
1. Getting a fresh connection and closing it does NOT close OTHER existing connections to the same database file
2. If the GUI app has open connections (which it does - `StudentManagementApp` keeps the app running), `os.remove(DB_PATH)` will fail on Windows (file locked) or succeed but corrupt the database on Unix
3. The safety backup restore logic is also racy

**Impact**: Database corruption, restore failures, data loss.

---

### 1.7 JSON Migration Uses Wrong Key
**File**: `database.py` (lines 55-60)  
**Severity**: Critical

```python
conn.execute(
    """INSERT OR IGNORE INTO students
    (student_code, name, age, course, email)
    VALUES (?, ?, ?, ?, ?)""",
    (record["id"], record["name"], record["age"],
     record["course"], record["email"])
)
```

The JSON field is `"id"` but the database column is `student_code`. This works only if the JSON used `"id"` as the student code field. If the JSON used `"student_code"`, this would fail silently (KeyError caught and ignored).

---

## 2. MEDIUM-PRIORITY ISSUES

### 2.1 Login Flow Architecture Flaw
**File**: `gui.py` (lines 914-959)

```python
def main():
    root = tk.Tk()
    root.withdraw()  # Hide root
    success, username = show_login(root)  # Create LoginDialog with hidden parent
    if not success:
        root.destroy()
        return
    root.deiconify()  # Show root AFTER login
    app = StudentManagementApp(root)
    root.mainloop()
```

**Problems**:
1. Root window created hidden, then login dialog shown as child of hidden window
2. `LoginDialog` removed `transient(parent)` to work around this (see Critical #1.1)
3. If login fails, `root.destroy()` is called but root was never shown - awkward
4. No clean way to handle "Exit" from login dialog (calls `root.destroy()` from `show_login`)

**Better pattern**: Create login dialog FIRST (with no parent or a temporary hidden root), then create main window only on success.

---

### 2.2 Inconsistent Error Handling - Mixed `print()` and `messagebox`
**File**: `database.py` (multiple lines) vs `gui.py`

**Database module**: Uses `print(f"Database error: {e}")` for errors  
**GUI module**: Uses `messagebox.showerror()` for user-facing errors

**Problem**: 
- Console errors invisible in GUI mode (no console)
- No logging framework
- Errors in database operations during GUI use are silently printed to nowhere
- GUI doesn't know when database operations fail silently (returns empty list/False)

---

### 2.3 Duplicate `_center_dialog()` Method Across Dialog Classes
**File**: `gui.py` (lines 52-58, 174-180, 447-453?)

Three dialog classes (`LoginDialog`, `BackupRestoreDialog`, `StudentFormDialog`, `StudentDetailsDialog`) each have their own identical `_center_dialog()` method. Code duplication.

---

### 2.4 `_create_card()` Uses Fragile `card.children['!label']`
**File**: `gui.py` (lines 621-634)

```python
ttk.Label(card, text=value, style="CardValue.TLabel").grid(row=0, column=0, sticky=tk.EW)
ttk.Label(card, text=label, style="CardLabel.TLabel").grid(row=1, column=0, sticky=tk.EW, pady=(5, 0))

if column == 0:
    self.card_total_value = card.children['!label']
elif column == 1:
    self.card_courses_value = card.children['!label']
else:
    self.card_avg_age_value = card.children['!label']
```

**Problem**: 
- Relies on Tkinter's auto-generated widget names (`!label`, `!label2`, etc.)
- Fragile - breaks if widget order changes
- Not explicit - hard to understand and maintain

**Fix**: Store references directly when creating labels.

---

### 2.5 Search on Every Keystroke (Performance)
**File**: `gui.py` (lines 549-550)

```python
self.search_entry.bind("<KeyRelease>", lambda e: self.search_students())
self.search_entry.bind("<Return>", lambda e: self.search_students())
```

**Problem**: 
- Triggers database query on EVERY keystroke
- No debouncing
- Can cause UI lag with large datasets
- Database connection opened/closed per keystroke

---

### 2.6 Age Validation Allows Empty String in Update Mode
**File**: `gui.py` (lines 344-352)

```python
age = None
if not age_str:
    if self.mode == "update" and self.student_data:
        age = self.student_data["age"]  # Keeps old age
    else:
        messagebox.showerror(...)
        return
```

**Problem**: In update mode, empty age keeps old value. But the `Student.validate()` method (student.py line 23-28) requires age to be valid integer 5-100. If old age was somehow invalid, it persists.

---

### 2.7 No Input Sanitization for Student Code
**File**: `gui.py` (line 338) and `student.py` (line 19)

```python
# gui.py
if not student_code.isalnum():
    messagebox.showerror("Validation Error", "Student code must be alphanumeric.")

# student.py - validate() only checks not empty
```

**Problem**: 
- GUI restricts to alphanumeric, but database/CLI don't enforce this
- `Student.validate()` doesn't check alphanumeric
- Inconsistent validation across entry points

---

### 2.8 `StudentDetailsDialog` Doesn't Handle Missing Keys
**File**: `gui.py` (line 438)

```python
value = data[label.lower().replace(" ", "_")]
```

**Problem**: Direct dictionary access without `.get()` - will raise `KeyError` if data dict missing expected keys. No defensive coding.

---

### 2.9 `initialize_database()` Called Multiple Times
**File**: `gui.py` (line 928), `main.py` (line 158 - via `load_students()`)

- GUI: `main()` calls `initialize_database()` explicitly
- CLI: `main()` calls `load_students()` which calls `_migrate_from_json()` which calls `_get_conn()` which creates tables
- `initialize_database()` only calls `_ensure_default_admin()`

Not a bug but redundant/confusing architecture.

---

### 2.10 `StudentFormDialog` Creates Temporary Student for Validation
**File**: `gui.py` (lines 375-382)

```python
temp_student = Student(
    student_code=student_code, name=name, age=age,
    course=course, email=email
)
errors = temp_student.validate()
```

**Problem**: Creates a `Student` object just to call `validate()`. The validation logic is duplicated between `Student.validate()` and GUI checks. Should use `Student.from_dict()` or pass dict to a static validation method.

---

## 3. MINOR ISSUES

### 3.1 Unused Import: `datetime` in `gui.py`
**File**: `gui.py` (line 8) - Only used in `BackupRestoreDialog._on_backup()` for timestamp

### 3.2 Unused Import: `Student` in `gui.py`
**File**: `gui.py` (line 18) - Imported but only used in `StudentFormDialog._on_save()` to create temp object for validation

### 3.3 Duplicate `_center_window()` in `StudentManagementApp`
**File**: `gui.py` - Defined at line 474, but also appears to be defined again? Actually only once now (was duplicate in earlier version).

### 3.4 `load_students()` vs `get_all_students()` - Duplicate Functions
**File**: `database.py` (lines 134-148 and 222-235)

```python
def load_students():  # Used by CLI (main.py)
    _migrate_from_json()
    # ... same query as get_all_students ...

def get_all_students():  # Used by GUI (gui.py)
    # ... identical query ...
```

Both do the exact same thing except `load_students()` calls `_migrate_from_json()`. Should consolidate.

---

### 3.5 `utils.py` Functions Unused in GUI
**File**: `utils.py` - All functions only used by CLI (`main.py`)

- `display_menu()`, `get_numeric_input()`, `validate_email()`, `display_student()`, `display_all_students()`, `get_user_input()`
- GUI has its own validation logic (duplicate)

---

### 3.6 Inconsistent Naming: `student_code` vs `id` in JSON Migration
**File**: `database.py` (line 59) - Uses `record["id"]` for `student_code` column

### 3.7 `search_students_all_fields` Doesn't Search Age
**File**: `database.py` (lines 318-324)

```sql
WHERE LOWER(student_code) LIKE LOWER(?)
   OR LOWER(name) LIKE LOWER(?)
   OR LOWER(course) LIKE LOWER(?)
   OR LOWER(email) LIKE LOWER(?)
```

Comment says "all fields" but `age` (integer) not included. Searching integer with LIKE is odd anyway.

---

### 3.8 Redundant `sys.path.insert()` in Multiple Files
**Files**: `gui.py` (16), `main.py` (6), `database.py` (not needed)

All three files add the project directory to `sys.path`. Only needed in entry points (`gui.py`, `main.py`).

---

### 3.9 `HAS_OPENPYXL` Check at Module Level
**File**: `gui.py` (lines 10-14)

```python
try:
    from openpyxl import Workbook
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
```

Then re-imports inside `export_excel()` (line 876). Module-level check is fine but re-import is redundant.

---

### 3.10 Commented Code / Dead Code
**File**: `gui.py` - Comment at line 40: `# Don't use transient(parent) when parent may be withdrawn` - this is a code smell indicating a workaround rather than proper fix.

---

## 4. SECURITY CONCERNS

### 4.1 Default Admin Credentials in Source Code
**File**: `database.py` line 78  
**Risk**: Anyone with source code knows default login. No forced password change.

### 4.2 No Password Complexity Requirements
**File**: `database.py` - `_create_admin()` accepts any password

### 4.3 No Session Management / Timeout
**File**: `gui.py` - Once logged in, session lasts forever until app close

### 4.4 No Brute Force Protection
**File**: `database.py` - `authenticate_admin()` allows unlimited attempts

### 4.5 Password Hash Iterations Fixed at 100,000
**File**: `database.py` line 89

```python
hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
```

**Issue**: Hardcoded iterations. Should be configurable and increase over time. 100k is low by 2025 standards (OWASP recommends 310k+ for PBKDF2-SHA256).

### 4.6 No SQL Injection Protection Audit
**Status**: Actually OK - all queries use parameterized `?` placeholders correctly.

### 4.7 File Path Traversal in Backup/Restore
**File**: `database.py` lines 357, 390-393, 418-420

```python
os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
# ...
shutil.copy2(backup_path, DB_PATH)
```

**Risk**: `backup_path` comes from `filedialog.asksaveasfilename()` / `askopenfilename()` - user controlled. Using `os.path.abspath()` helps but no validation that path stays within expected directory.

---

## 5. DATABASE CONCERNS

### 5.1 No Indexes on Search Columns
**File**: `database.py` (lines 20-27)

```sql
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT UNIQUE NOT NULL,  -- Indexed by UNIQUE
    name TEXT NOT NULL,                  -- NO INDEX
    age INTEGER NOT NULL,                -- NO INDEX
    course TEXT NOT NULL,                -- NO INDEX
    email TEXT NOT NULL                  -- NO INDEX
)
```

**Impact**: All search functions (`LIKE %term%`) do full table scans. Will be slow with >10k records.

---

### 5.2 No Foreign Keys / Referential Integrity
**File**: `database.py` - No foreign keys defined. Not critical for this simple schema but worth noting.

---

### 5.3 `backup_database()` Uses SQLite Online Backup API Correctly
**File**: `database.py` lines 359-367 - This is GOOD practice. Uses `source_conn.backup(dest_conn)`.

---

### 5.4 `restore_database()` Dangerous File Replacement
**File**: `database.py` lines 415-430 - As noted in Critical #1.6, this approach is fundamentally flawed for a running application.

---

### 5.5 No Transaction Rollback on Multi-Step Operations
**File**: `database.py` - Most operations are single statements so auto-commit is fine. But `restore_database` does multiple steps without transaction.

---

### 5.6 JSON Migration Runs on Every `load_students()` Call
**File**: `database.py` line 136

```python
def load_students():
    _migrate_from_json()  # Runs every time!
```

**Problem**: Migration check runs on every CLI menu load. Should run once at startup.

---

### 5.7 Connection Per Operation - No Connection Pooling
**File**: `database.py` - Every function calls `_get_conn()` and closes it. OK for SQLite but not scalable.

---

### 5.8 No VACUUM / Maintenance
**File**: `database.py` - No database maintenance functions.

---

## 6. GUI CONCERNS

### 6.1 LoginDialog Modal Blocking Issue (Root Cause of Startup Hang)
**File**: `gui.py` lines 32-50

As analyzed in Critical #1.1, the combination of:
1. `root.withdraw()` before dialog creation
2. `Toplevel(root)` without `transient()`
3. `grab_set()` + `wait_window()`

Creates a fragile modal dialog that may not display properly.

---

### 6.2 No Keyboard Navigation / Accessibility
**File**: `gui.py` - No `tabindex`, no ARIA, no focus management beyond basic `focus()` calls.

---

### 6.3 Hardcoded Font "Segoe UI" - Windows Only
**File**: `gui.py` (lines 66, 68, 72, 81, 89, 94, 101, 111, 113, 167, 188, 190, 198, 209, 279, 301, 304, 330, 430, 435, 439, 484, 485, 487, 488, 489, 490, 491, 492, 505, 508, 544, 547, 555, 559, 579, 608, 609, 611, 618, 626, 627, 659, 664, 729, 748, 774, 811, 831, 835, 843, 866, 875, 885, 886, 890, 891, 892, 893, 894, 909)

**Problem**: "Segoe UI" is Windows-only font. On Linux/macOS, falls back to default (may look different). Should use system-agnostic fonts like `("TkDefaultFont", 10)` or detect platform.

---

### 6.4 No Responsive Layout for Small Windows
**File**: `gui.py` - `minsize(900, 600)` but layout uses fixed padding/grid. May break on smaller screens.

---

### 6.5 Treeview Column Sorting - String vs Numeric
**File**: `gui.py` lines 729-749

```python
def sort_key(s):
    val = s[list(s.keys())[col_index]]
    if column == "age":
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0
    return str(val).lower()
```

**Problem**: Only handles `age` as numeric. `student_code` may contain numbers (S001, S002) but sorts as string. Should detect numeric columns automatically.

---

### 6.6 Status Bar Message Auto-Clear Uses `after()` with Lambda Capturing Stale Values
**File**: `gui.py` lines 779, 790, 812

```python
self.root.after(3000, lambda: self.status_var.set(f"Total Students: {len(self._get_visible_students())}"))
```

**Problem**: Lambda captures `self._get_visible_students()` at execution time (3 seconds later), not at creation time. This is actually correct behavior (shows current count), but the pattern is confusing.

---

### 6.7 Double-Click to Update Binds to Same Handler as Button
**File**: `gui.py` line 600

```python
self.tree.bind("<Double-1>", lambda e: self.open_update_dialog())
```

**Problem**: No check if a row is actually selected. Opens empty update dialog if double-click on empty space.

---

### 6.8 No Confirmation on "Clear Search"
**File**: `gui.py` line 708-712 - Immediately clears and refreshes. Minor UX issue.

---

### 6.9 Export Functions Don't Handle Large Datasets
**File**: `gui.py` lines 824-911 - Loads all visible students into memory, then writes. OK for small datasets but could OOM with large data.

---

### 6.10 `StudentFormDialog` - Student Code Field Readonly in Update but Not Validated
**File**: `gui.py` line 319

```python
self.fields["student_code"].config(state="readonly")
```

**Problem**: In update mode, student_code is readonly but the `_on_save()` still reads it and passes to `update_student()`. If somehow modified (e.g., via accessibility tools), could cause issues. Not a real vulnerability but inconsistent.

---

## 7. RECOMMENDED IMPROVEMENTS

### 7.1 Architecture: Separate GUI and CLI Entry Points Cleanly
- Create `gui_main.py` and `cli_main.py` instead of overloading `gui.py` and `main.py`
- Share a common `app_core.py` for business logic

### 7.2 Add Logging Framework
- Replace all `print()` with `logging` module
- Configurable log levels
- File + console output

### 7.3 Implement Debounced Search
```python
# Add debounce timer
self._search_timer = None
def on_search_key(self, event):
    if self._search_timer:
        self.root.after_cancel(self._search_timer)
    self._search_timer = self.root.after(300, self.search_students)
```

### 7.4 Add Database Indexes
```sql
CREATE INDEX IF NOT EXISTS idx_students_name ON students(name);
CREATE INDEX IF NOT EXISTS idx_students_course ON students(course);
CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
```

### 7.5 Create Base Dialog Class
Extract common dialog functionality:
- `_center_dialog()`
- `wait_window()` pattern
- `transient()` + `grab_set()` handling
- Escape/Enter key bindings

### 7.6 Add Configuration Module
- Database path configurable
- Font configuration
- Password policy (min length, iterations)
- Default admin credentials from environment/config

### 7.7 Add Unit Tests
- Test `Student.validate()`
- Test database CRUD operations
- Test search functions
- Test backup/restore

### 7.8 Add Type Hints
- All functions missing type hints (except some in database.py)
- Add `from __future__ import annotations` for Python 3.7+ compatibility

### 7.9 Improve Error Messages
- User-friendly messages (not "sqlite3.IntegrityError: UNIQUE constraint failed")
- Log technical details, show friendly messages

### 7.10 Add "Change Password" Feature
- Admin can change password after login
- Force change on first login

---

## 8. FILES AFFECTED SUMMARY

| File | Critical | Medium | Minor | Security | DB | GUI |
|------|----------|--------|-------|----------|-----|-----|
| `gui.py` | 2 | 6 | 3 | 1 | 0 | 10 |
| `database.py` | 3 | 1 | 4 | 3 | 8 | 0 |
| `student.py` | 0 | 1 | 1 | 0 | 0 | 0 |
| `utils.py` | 0 | 0 | 1 | 0 | 0 | 0 |
| `main.py` | 0 | 1 | 1 | 0 | 0 | 0 |
| `README.md` | 0 | 0 | 0 | 0 | 0 | 0 |

**Total Issues**: 5 Critical, 9 Medium, 10 Minor, 4 Security, 8 Database, 10 GUI

---

## 9. EXACT PROPOSED CHANGES

### gui.py

| Line | Change | Priority |
|------|--------|----------|
| 37-50 | Fix LoginDialog: remove workaround comment, add proper transient handling | Critical |
| 714-727 / 832-845 | Remove duplicate `_get_visible_students()` (keep first, delete second) | Critical |
| 621-634 | Fix `_create_card()` to store label references directly | Medium |
| 549-550 | Add debounce to search (300ms) | Medium |
| 52-58, 174-180, (StudentFormDialog), (StudentDetailsDialog) | Extract `_center_dialog()` to base class or utility | Medium |
| 375-382 | Use `Student.from_dict()` + validate instead of manual temp object | Minor |
| 438 | Use `.get()` with default in `StudentDetailsDialog` | Minor |
| 600 | Add selection check in double-click handler | Minor |
| 66, 68, 72... | Replace "Segoe UI" with cross-platform font tuple | Minor |
| 729-749 | Improve column sorting to detect numeric columns | Minor |
| 914-923 | Refactor login flow: create login dialog first, then main window | Medium |
| 876 | Remove redundant openpyxl import | Minor |
| 16 | Remove `sys.path.insert()` if not needed (entry point only) | Minor |

### database.py

| Line | Change | Priority |
|------|--------|----------|
| 78 | Remove hardcoded default admin; add config/env-based setup | Critical |
| 89 | Increase PBKDF2 iterations to 310,000+ (configurable) | Security |
| 136 | Move `_migrate_from_json()` to `initialize_database()` only | Medium |
| 134-148 / 222-235 | Consolidate `load_students()` and `get_all_students()` | Minor |
| 318-324 | Fix `search_students_all_fields` - remove age or handle properly | Minor |
| 415-430 | Rewrite `restore_database()` to use SQLite backup API correctly | Critical |
| 20-27 | Add indexes on name, course, email columns | Database |
| 357, 390-393, 418-420 | Validate backup/restore paths stay in safe directory | Security |
| All print() | Replace with logging module | Medium |

### student.py

| Line | Change | Priority |
|------|--------|----------|
| 19 | Add alphanumeric check to `validate()` for consistency | Medium |
| 35-39 | Make email regex a module constant | Minor |
| All | Add type hints | Minor |

### utils.py

| Line | Change | Priority |
|------|--------|----------|
| All | Add type hints | Minor |
| 38-41 | Move email validation to shared constant with student.py | Minor |

### main.py

| Line | Change | Priority |
|------|--------|----------|
| 6 | Keep `sys.path.insert()` (entry point) | - |
| 158 | Call `initialize_database()` explicitly instead of relying on `load_students()` | Minor |
| All | Add type hints | Minor |

### README.md

| Line | Change | Priority |
|------|--------|----------|
| 63 | Update "No external dependencies" - openpyxl needed for Excel export | Minor |
| Add | Document GUI entry point (`python gui.py`) | Minor |
| Add | Document default admin credentials and security notes | Security |

---

## APPROVAL REQUEST

**Please review this report and approve which issues to fix.** 

Recommended priority order:
1. **Critical**: Fix LoginDialog transient issue, remove duplicate method, fix restore_database race condition, secure default admin
2. **Security**: Increase PBKDF2 iterations, add password policy, path validation
3. **Database**: Add indexes, consolidate duplicate functions, fix migration frequency
4. **Medium GUI**: Debounced search, base dialog class, card label references
5. **Minor**: Type hints, cross-platform fonts, code cleanup

Would you like me to proceed with fixes? If so, please specify which priority levels to address.