"""Student class module for the Student Management System."""

import re


class Student:
    """Represents a student with student_code, name, age, course, and email."""

    def __init__(self, student_code, name, age, course, email):
        self.student_code = student_code
        self.name = name
        self.age = age
        self.course = course
        self.email = email

    def validate(self):
        """Validate student data. Returns a list of error messages."""
        errors = []
        if not self.student_code or not str(self.student_code).strip():
            errors.append("Student code cannot be empty.")
        if not self.name or not str(self.name).strip():
            errors.append("Name cannot be empty.")
        try:
            age = int(self.age)
            if age < 5 or age > 100:
                errors.append("Age must be between 5 and 100.")
        except (ValueError, TypeError):
            errors.append("Age must be a valid integer.")
        if not self.course or not str(self.course).strip():
            errors.append("Course cannot be empty.")
        if not self._is_valid_email(self.email):
            errors.append("Invalid email format.")
        return errors

    @staticmethod
    def _is_valid_email(email):
        """Check if email has a valid format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, str(email)) is not None

    def to_dict(self):
        """Convert the student object to a dictionary for database storage."""
        return {
            "student_code": self.student_code,
            "name": self.name,
            "age": self.age,
            "course": self.course,
            "email": self.email
        }

    @classmethod
    def from_dict(cls, data):
        """Create a Student object from a dictionary."""
        return cls(
            student_code=data["student_code"],
            name=data["name"],
            age=data["age"],
            course=data["course"],
            email=data["email"]
        )

    def __str__(self):
        """Return a formatted string representation of the student."""
        return (f"Code: {self.student_code} | Name: {self.name} | Age: {self.age} | "
                f"Course: {self.course} | Email: {self.email}")
