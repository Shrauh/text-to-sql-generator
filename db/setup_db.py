import sqlite3
import random
import logging
from pathlib import Path
from faker import Faker
from typing import List, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def setup_database(db_path: Path) -> None:
    """
    Creates the database schema and populates it with realistic fake data.
    
    Args:
        db_path: Path to the SQLite database file.
    """
    # Create directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize Faker and seed for reproducibility
    fake = Faker('en_IN')
    Faker.seed(42)
    random.seed(42)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # 1. Create Tables
            create_tables(cursor)
            
            # 2. Generate Data
            generate_data(cursor, fake)
            
            conn.commit()
            
            # 3. Print Summary Stats
            print_summary(cursor)
            
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

def create_tables(cursor: sqlite3.Cursor) -> None:
    """Creates the tables for the placement database."""
    # Drop existing tables to start fresh if needed
    cursor.executescript('''
        DROP TABLE IF EXISTS enrollments;
        DROP TABLE IF EXISTS placements;
        DROP TABLE IF EXISTS courses;
        DROP TABLE IF EXISTS companies;
        DROP TABLE IF EXISTS students;
    ''')

    cursor.executescript('''
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            branch TEXT NOT NULL,
            cgpa REAL NOT NULL,
            batch_year INTEGER NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            package_lpa REAL NOT NULL
        );

        CREATE TABLE placements (
            placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            placement_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies (company_id) ON DELETE CASCADE
        );

        CREATE TABLE courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            credits INTEGER NOT NULL,
            branch TEXT NOT NULL
        );

        CREATE TABLE enrollments (
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            grade TEXT NOT NULL,
            PRIMARY KEY (student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (course_id) ON DELETE CASCADE
        );
    ''')
    logging.info("Tables created successfully.")

def generate_data(cursor: sqlite3.Cursor, fake: Faker) -> None:
    """Generates and inserts fake data into the database."""
    # Constants
    BRANCHES = ['Computer Science', 'Electronics', 'Mechanical', 'Civil', 'Electrical', 'Information Technology']
    SECTORS = ['IT', 'Finance', 'Consulting', 'Manufacturing', 'Healthcare', 'E-commerce']
    STATUS_VALUES = ['Accepted', 'Rejected', 'Pending']
    GRADES = ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F']
    CITIES = ['Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Ahmedabad', 'Chennai', 'Kolkata', 'Surat', 'Pune', 'Jaipur']
    
    # 1. Insert Students (~50 rows)
    num_students = 50
    students_data = []
    for _ in range(num_students):
        # Varied CGPA
        cgpa_rand = random.random()
        if cgpa_rand < 0.15:
            cgpa = round(random.uniform(5.0, 6.5), 2) # Low
        elif cgpa_rand < 0.85:
            cgpa = round(random.uniform(6.5, 9.0), 2) # Mid
        else:
            cgpa = round(random.uniform(9.0, 10.0), 2) # High
            
        students_data.append((
            fake.name(),
            random.choice(BRANCHES),
            cgpa,
            random.randint(2021, 2025),
            random.choice(CITIES)
        ))
    cursor.executemany("INSERT INTO students (name, branch, cgpa, batch_year, city) VALUES (?, ?, ?, ?, ?)", students_data)
    
    # 2. Insert Companies (~50 rows)
    num_companies = 50
    companies_data = []
    for _ in range(num_companies):
        companies_data.append((
            fake.company(),
            random.choice(SECTORS),
            round(random.uniform(3.0, 40.0), 1)
        ))
    cursor.executemany("INSERT INTO companies (name, sector, package_lpa) VALUES (?, ?, ?)", companies_data)
    
    # 3. Insert Placements
    # Some students have no placements. Let's pick 35 out of 50 to have 1 or more placements.
    student_ids = list(range(1, num_students + 1))
    placed_students = random.sample(student_ids, k=35)
    
    placements_data = []
    company_ids = list(range(1, num_companies + 1))
    for student_id in placed_students:
        # A student can have 1 to 3 placements
        num_apps = random.randint(1, 3)
        applied_companies = random.sample(company_ids, k=num_apps)
        for comp_id in applied_companies:
            placements_data.append((
                student_id,
                comp_id,
                fake.job(),
                fake.date_between(start_date='-2y', end_date='today').isoformat(),
                random.choice(STATUS_VALUES)
            ))
    cursor.executemany("INSERT INTO placements (student_id, company_id, role, placement_date, status) VALUES (?, ?, ?, ?, ?)", placements_data)
    
    # 4. Insert Courses (~50 rows)
    courses_data = []
    for i in range(1, 51):
        branch = random.choice(BRANCHES)
        # Generate some tech-sounding course names based on branch
        course_subjects = {
            'Computer Science': ['Algorithms', 'Data Structures', 'OS', 'Databases', 'AI', 'Networks'],
            'Electronics': ['VLSI', 'Signals', 'Microprocessors', 'Circuits', 'Communication', 'Embedded Systems'],
            'Mechanical': ['Thermodynamics', 'Fluid Mechanics', 'Robotics', 'CAD', 'Manufacturing', 'Kinematics'],
            'Civil': ['Structural Analysis', 'Geotech', 'Transportation', 'Surveying', 'Environment', 'Hydraulics'],
            'Electrical': ['Power Systems', 'Control Systems', 'Machines', 'Power Electronics', 'High Voltage', 'Drives'],
            'Information Technology': ['Web Dev', 'Cloud Computing', 'Cybersecurity', 'Software Engineering', 'IoT', 'Mobile Dev']
        }
        subject = random.choice(course_subjects[branch])
        course_name = f"{subject} {random.randint(101, 499)}"
        courses_data.append((
            course_name,
            random.randint(2, 4),
            branch
        ))
    cursor.executemany("INSERT INTO courses (course_name, credits, branch) VALUES (?, ?, ?)", courses_data)
    
    # 5. Insert Enrollments
    # Each student enrolled in 3-5 courses
    enrollments_data = set()
    course_ids = list(range(1, 51))
    
    for student_id in student_ids:
        num_courses = random.randint(3, 5)
        student_courses = random.sample(course_ids, k=num_courses)
        for course_id in student_courses:
            enrollments_data.add((
                student_id,
                course_id,
                random.choice(GRADES)
            ))
            
    cursor.executemany("INSERT INTO enrollments (student_id, course_id, grade) VALUES (?, ?, ?)", list(enrollments_data))
    logging.info("Data generated and inserted successfully.")

def print_summary(cursor: sqlite3.Cursor) -> None:
    """Prints the row count summary of all tables."""
    tables = ['students', 'companies', 'placements', 'courses', 'enrollments']
    print("\n--- Database Summary ---")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Total rows in {table}: {count}")
    print("------------------------\n")

if __name__ == "__main__":
    db_file_path = Path(__file__).parent / "placements.db"
    setup_database(db_file_path)
    print(f"Database created successfully at: {db_file_path.absolute()}")
