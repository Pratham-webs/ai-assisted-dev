def determine_grade(mark):
    """Return the grade for a valid mark between 0 and 100."""
    if 90 <= mark <= 100:
        return "A"
    elif 80 <= mark <= 89:
        return "B"
    elif 70 <= mark <= 79:
        return "C"
    elif 60 <= mark <= 69:
        return "D"
    elif 0 <= mark < 60:
        return "F"
    else:
        raise ValueError("Mark must be between 0 and 100.")


def get_valid_mark(student_name):
    """Keep asking until a valid numeric mark in the range 0-100 is entered."""
    while True:
        try:
            mark = float(input(f"Enter the mark for {student_name}: "))
        except ValueError:
            print("Invalid numeric input. Please enter a number.")
            continue

        if not 0 <= mark <= 100:
            print("Invalid mark. Marks must be between 0 and 100.")
            continue

        return mark


print("Student Grade Calculator")
print("Grade boundaries: A = 90-100, B = 80-89, C = 70-79, D = 60-69, F = 0-59")
print("=" * 60)

students = []

for i in range(1, 6):
    while True:
        name = input(f"Enter the name of student {i}: ").strip()
        if name:
            break
        print("Student name cannot be empty. Please enter a valid name.")

    mark = get_valid_mark(name)
    grade = determine_grade(mark)
    students.append((name, mark, grade))

print("\nFormatted Student Results")
print("-" * 60)
print(f"{'Name':<15} {'Mark':>8} {'Grade':>8}")
print("-" * 60)

for name, mark, grade in students:
    print(f"{name:<15} {mark:>8.1f} {grade:>8}")

print("-" * 60)
