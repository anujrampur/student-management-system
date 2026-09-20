"""Main entry point for the Student Management System."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from student import Student
from database import (
    load_students, add_student, update_student,
    delete_student, find_student_by_id, get_all_students, search_students_by_name
)
from utils import (
    display_menu, get_numeric_input, validate_email, display_student,
    display_all_students, get_user_input
)


def add_student_flow():
    """Handle the add student workflow."""
    print("\n--- Add New Student ---")
    student_code = get_user_input("Enter Student Code: ")

    existing = find_student_by_id(student_code)
    if existing:
        print(f"Error: A student with code '{student_code}' already exists!")
        return

    name = get_user_input("Enter Name: ")
    age = get_numeric_input("Enter Age: ")
    course = get_user_input("Enter Course: ")
    email = get_user_input("Enter Email: ")

    if not validate_email(email):
        print("Error: Invalid email format. Please use format like user@example.com")
        return

    student_dict = {
        "student_code": student_code,
        "name": name,
        "age": age,
        "course": course,
        "email": email
    }

    temp_student = Student.from_dict(student_dict)
    errors = temp_student.validate()
    if errors:
        for err in errors:
            print(f"Error: {err}")
        return

    if add_student(student_dict):
        print(f"\nSuccess: Student '{name}' (Code: {student_code}) added successfully!")
    else:
        print("Error: Failed to add student.")


def view_all_students_flow():
    """Handle viewing all students."""
    print("\n--- All Students ---")
    students_list = get_all_students()
    display_all_students(students_list)


def search_student_flow():
    """Handle searching for a student by student_code."""
    print("\n--- Search Student by Code ---")
    student_code = get_user_input("Enter Student Code to search: ")
    student = find_student_by_id(student_code)
    if student:
        display_student(student)
    else:
        print(f"\nError: No student found with code '{student_code}'.")


def search_by_name_flow():
    """Handle searching for students by name."""
    print("\n--- Search Students by Name ---")
    name = get_user_input("Enter name to search: ")
    results = search_students_by_name(name)
    if results:
        print(f"\nFound {len(results)} matching student(s):")
        display_all_students(results)
    else:
        print(f"\nNo students found with name containing '{name}'.")


def update_student_flow():
    """Handle updating a student."""
    print("\n--- Update Student ---")
    student_code = get_user_input("Enter Student Code to update: ")
    student = find_student_by_id(student_code)
    if not student:
        print(f"\nError: No student found with code '{student_code}'.")
        return

    print(f"\nCurrent details:")
    display_student(student)
    print("\nEnter new values (press Enter to keep current value):")

    name_input = get_user_input("  Name: ", allow_empty=True)
    name = name_input if name_input else student["name"]
    age_str = input("  Age (current: {}): ".format(student["age"])).strip()
    if age_str:
        try:
            age = int(age_str)
            if age < 5 or age > 100:
                print("Age must be between 5 and 100. Keeping current age.")
                age = student["age"]
        except ValueError:
            print("Invalid age. Keeping current age.")
            age = student["age"]
    else:
        age = student["age"]
    course_input = get_user_input("  Course: ", allow_empty=True)
    course = course_input if course_input else student["course"]
    email_input = get_user_input("  Email: ", allow_empty=True)
    email = email_input if email_input else student["email"]

    updated_data = {"name": name, "age": age, "course": course, "email": email}

    temp_student = Student(student_code=student_code, name=name, age=age, course=course, email=email)
    errors = temp_student.validate()
    if errors:
        for err in errors:
            print(f"Error: {err}")
        return

    if update_student(student_code, updated_data):
        print(f"\nSuccess: Student '{student_code}' updated successfully!")
    else:
        print("Error: Failed to update student.")


def delete_student_flow():
    """Handle deleting a student."""
    print("\n--- Delete Student ---")
    student_code = get_user_input("Enter Student Code to delete: ")
    student = find_student_by_id(student_code)
    if not student:
        print(f"\nError: No student found with code '{student_code}'.")
        return

    display_student(student)
    confirm = get_user_input("  Are you sure you want to delete this student? (yes/no): ")
    if confirm.lower() in ("yes", "y"):
        if delete_student(student_code):
            print(f"\nSuccess: Student '{student_code}' deleted successfully!")
        else:
            print("Error: Failed to delete student.")
    else:
        print("Deletion cancelled.")


def main():
    """Main application loop."""
    students = load_students()
    print(f"\nLoaded {len(students)} student(s) from database.")

    while True:
        display_menu()
        choice = get_numeric_input("\nChoose an option (1-7): ", min_val=1, max_val=7)

        if choice == 1:
            add_student_flow()
        elif choice == 2:
            view_all_students_flow()
        elif choice == 3:
            search_student_flow()
        elif choice == 4:
            update_student_flow()
        elif choice == 5:
            delete_student_flow()
        elif choice == 6:
            search_by_name_flow()
        elif choice == 7:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
