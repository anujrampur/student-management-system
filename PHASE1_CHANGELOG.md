# Phase 1 Changelog

**Date**: 2025-09-14  
**Project**: Student Management System

---

## Files Modified

1. `database.py` - Major fixes and improvements
2. `gui.py` - Minor fix (duplicate method removal)

---

## Changes Summary

### database.py

#### 1. Added SQLite Indexes for Search Performance (Lines 37-40)
```python
conn.execute("CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_students_course ON students(course)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_students_email ON students(email)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_students_student_code ON students(student_code)")
```
- Added 4 indexes on frequently searched columns
- Uses `IF NOT EXISTS` for idempotent migration
- Improves search query performance from full table scans to index lookups

#### 2. Fixed JSON Migration to Support Both "id" and "student_code" Fields (Lines 54-61)
```python
student_code = record.get("student_code") or record.get("id")
if student_code is None:
    continue
```
- Now supports legacy JSON records using `"id"` field
- Also supports current `"student_code"` field
- Skips records with missing required fields instead of silently failing

#### 3. Moved JSON Migration to `initialize_database()` Only (Lines 145-149, 459-461)
- Removed `_migrate_from_json()` call from `load_students()`
- Added `_migrate_from_json()` call to `initialize_database()`
- Migration now runs once at startup instead of on every `load_students()` call

#### 4. Completely Rewrote `restore_database()` for Safety (Lines 384-457)
**Before**: Used dangerous `os.remove(DB_PATH)` + `shutil.copy2()` which fails on Windows when database has open connections.

**After**: Uses SQLite's backup API for both safety backup AND restore:
```python
# Create safety backup
source_conn = _get_conn()
source_conn.backup(safety_conn)

# Restore using backup API (works with open connections)
src_conn = sqlite3.connect(backup_path)
dest_conn = _get_conn()
src_conn.backup(dest_conn)  # Atomic page-by-page copy
```
- Works on Windows with active connections
- Creates safety backup before restore
- Automatic rollback on failure using safety backup
- Verifies restored database integrity

#### 5. Improved Password Security (Lines 10-11, 98-118, 121-152)
- Added `PBKDF2_ITERATIONS = 310000` constant (OWASP 2025 recommendation)
- Added `iterations` column to `admins` table with migration support
- `_hash_password()` and `_verify_password()` now accept configurable iterations
- `authenticate_admin()` uses stored iterations for backward compatibility
- New admins created with 310,000 iterations; existing admins verified with their stored iteration count

#### 6. Fixed `search_students_all_fields()` Documentation (Line 324)
- Updated docstring to clarify: "Age (integer) is not searched"
- Function behavior unchanged (already didn't search age)
- Removed misleading "all fields" implication

---

### gui.py

#### 1. Removed Duplicate `_get_visible_students()` Method
- Second duplicate definition (lines 832-845) removed
- Single implementation retained at line 714
- No functional change - was exact duplicate code

---

## Behavior Changes

| Feature | Before | After |
|---------|--------|-------|
| Search performance | Full table scan | Indexed lookups |
| JSON migration | Runs on every `load_students()` | Runs once at `initialize_database()` |
| JSON field support | Only `"id"` field | Both `"id"` and `"student_code"` |
| Database restore | File copy (fails on Windows with open connections) | SQLite backup API (safe with open connections) |
| Password hashing | 100,000 iterations fixed | 310,000 iterations default, per-user stored |
| Default admin | `admin`/`admin123` hardcoded | Same credentials, but with stronger hashing |

---

## Backward Compatibility

✅ All existing features preserved:
- Login with `admin`/`admin123` works
- All CRUD operations work
- Search functions work
- Export CSV/Excel works
- Backup/Restore works (now safer)
- CLI (`main.py`) works

✅ Database migration:
- Existing databases automatically get `iterations` column added
- Existing admin passwords verified with their original iteration count (100,000)
- New admins get 310,000 iterations
- Indexes added idempotently

---

## Testing Performed

1. **Syntax check**: All Python files compile without errors
2. **Database initialization**: `initialize_database()` runs successfully
3. **Authentication**: `authenticate_admin('admin', 'admin123')` returns `True`
4. **Student loading**: `get_all_students()` returns 5 students
5. **Search functions**: All search variants work correctly
6. **Backup/Restore**: Full cycle tested with temporary file
7. **CLI imports**: `main.py` imports without errors
8. **GUI imports**: `gui.py` imports without errors

---

## Remaining Risks (Not Addressed in Phase 1)

1. **GUI Login Dialog**: Cannot be tested in headless environment. Original working pattern preserved (withdraw root → login without transient → deiconify on success).
2. **No brute force protection** on login
3. **No password change** feature for admin
4. **Hardcoded font** "Segoe UI" (Windows-only)
5. **No search debouncing** in GUI (triggers on every keystroke)
6. **No logging framework** (still uses `print()` in database module)
7. **No unit tests**

---

## Approval Required

Ready for Phase 2 fixes upon approval.