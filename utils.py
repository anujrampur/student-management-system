"""Utility functions for the Student Management System."""

import re


def display_menu():
    """Display the main menu options."""
    print("\n" + "=" * 45)
    print("       STUDENT MANAGEMENT SYSTEM")
    print("=" * 45)
    print("  1. Add Student")
    print("  2. View All Students")
    print("  3. Search Student by Code")
    print("  4. Update Student")
    print("  5. Delete Student")
    print("  6. Search by Name")
    print("  7. Exit")
    print("=" * 45)


def get_numeric_input(prompt, min_val=None, max_val=None):
    """Safely get a numeric input from the user with optional min/max validation."""
    while True:
        try:
            value = input(prompt)
            number = int(value)
            if min_val is not None and number < min_val:
                print(f"Value must be at least {min_val}.")
                continue
            if max_val is not None and number > max_val:
                print(f"Value must be at most {max_val}.")
                continue
            return number
        except ValueError:
            print("Invalid input. Please enter a valid number.")


def validate_email(email):
    """Validate email format. Returns True if valid, False otherwise."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, str(email)) is not None


def display_student(student):
    """Display a single student's information in a formatted way."""
    print(f"\n{'-' * 40}")
    print(f"  Code  : {student['student_code']}")
    print(f"  Name  : {student['name']}")
    print(f"  Age   : {student['age']}")
    print(f"  Course: {student['course']}")
    print(f"  Email : {student['email']}")
    print(f"{'-' * 40}")


def display_all_students(students):
    """Display all students in the list."""
    if not students:
        print("\nNo students found in the database.")
        return
    print(f"\n{'=' * 40}")
    print(f"  TOTAL STUDENTS: {len(students)}")
    print(f"{'=' * 40}")
    for student in students:
        display_student(student)


def get_user_input(prompt, allow_empty=False):
    """Safely get string input from the user. Rejects empty input unless allowed."""
    while True:
        value = input(prompt).strip()
        if not value and not allow_empty:
            print("This field cannot be empty. Please try again.")
            continue
        return value
