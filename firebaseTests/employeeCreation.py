import firebase_admin
from datetime import datetime, timezone
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from google.cloud.firestore_v1.base_query import FieldFilter, Or
from firebase_admin import credentials
from firebase_admin import firestore
import random
from faker import Faker

cred = credentials.Certificate(r"firebaseTests/firestoreKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# CREATE EMPLOYEE FUNCTIONS

def create_employee(name: str, email: str = None, phone: str = None, date_of_birth: str = None, password: str = None):
    """
    Create an employee record in Firestore.
    :param name: Full name of the employee
    :param email: Employee's email address (auto-generated if not provided)
    :param phone: Employee's phone number
    :param date_of_birth: Employee's date of birth in YYYY-MM-DD format
    :param password: Employee's password (auto-generated if not provided)
    """
    # Generate employee ID with initials and random numbers
    initials = ''.join([part[0].upper() for part in name.split() if part])
    if len(initials) < 2:
        initials = initials + 'X'  # Pad with X if only one initial
    random_numbers = f"{random.randint(100, 999)}_{random.randint(100, 999)}_{random.randint(100, 999)}"
    employee_id = f"{initials}{random_numbers}"
    
    # Generate email based on name if not provided
    if email is None:
        # Convert name to email format: "John Doe" -> "john.doe@company.com"
        email_name = name.lower().replace(' ', '.')
        # Remove any special characters and keep only letters, dots, and numbers
        import re
        email_name = re.sub(r'[^a-z0-9.]', '', email_name)
        email = f"{email_name}@company.com"
    
    # Generate password if not provided
    if password is None:
        # Generate a simple password with name initials + random numbers
        password_initials = ''.join([part[0].upper() for part in name.split() if part])
        password = f"{password_initials}{random.randint(1000, 9999)}"
    
    # Generate Tax File Number in format 000-000-000
    tfn = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"
    
    # Randomly assign a role: 'Entry Level', 'Senior Level', or 'Admin'
    role = random.choice(['Entry Level', 'Senior Level', 'Admin'])
    employee = {
        'employeeID': employee_id,
        'name': name,
        'email': email,
        'phone': phone,
        'dateOfBirth': date_of_birth,
        'password': password,
        'taxFileNumber': tfn,
        'createdAt': datetime.now(timezone.utc),
        'role': role
    }
    
    doc_ref = db.collection('Employees').document(employee_id)  # Use employee_id as document ID
    doc_ref.set(employee)
    print(f"Employee created - ID: {employee_id}, Name: {name}, Email: {email}, Password: {password}, Role: {role}, Document ID: {doc_ref.id}")
    return doc_ref.id, employee_id

def create_multiple_employees(count: int = 20):
    """
    Create multiple employee records using fake data.
    :param count: Number of employees to create (default 20)
    """
    fake = Faker()
    created_employees = []
    
    print(f"Creating {count} employees...")
    for i in range(count):
        # Generate fake employee data
        name = fake.name()
        # Email will be auto-generated based on name in create_employee function
        # Generate Australian format phone number: +61 XXX XXX XXX
        phone = f"+61 {random.randint(200, 599)} {random.randint(100, 999)} {random.randint(100, 999)}"
        date_of_birth = fake.date_of_birth(minimum_age=18, maximum_age=65).strftime('%Y-%m-%d')
        # Password will be auto-generated in create_employee function
        
        # Create the employee (email and password will be auto-generated)
        doc_id, employee_id = create_employee(name, phone=phone, date_of_birth=date_of_birth)
        created_employees.append({
            'doc_id': doc_id,
            'employee_id': employee_id,
            'name': name
        })
    
    print(f"\nSuccessfully created {len(created_employees)} employees!")
    return created_employees

# Uncomment the line below to create 20 employees
# create_multiple_employees(20)
