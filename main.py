from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, json
import logging
from datetime import datetime

# ------------------------ Logger Initialization ------------------------
logging.basicConfig(
    filename="leaves.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------ FastAPI Initialization ------------------------
app = FastAPI(
    title="Employee-based Leave Management POC",
    description="Leave Management API with employee & leave tracking",
    version="1.0.0"
)

# ------------------------ Pydantic Models ------------------------
class Employee(BaseModel):
    emp_id: str
    emp_name: str
    mail_id: str
    emp_role: str
    emp_dept: str
    date_of_joining: str
    leaves: dict = {
        "sick": 24,
        "casual": 12
    }

class Leave(BaseModel):
    leave_id: str
    employee_id: str
    leave_type: str
    from_date: str
    to_date: str
    leave_status: str = "Pending"

# ------------------------ JSON File Paths ------------------------
EMPLOYEE_FILE = "employees.json"
LEAVE_FILE = "leave.json"

# ------------------------ Helper Functions ------------------------
async def load_data(file_path):
    """
    Load data from JSON file. If file not found or corrupted, returns empty list.
    """
    try:
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        return []

async def save_data(file_path, data):
    """
    Save data (list or dict) to JSON file.
    """
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# ------------------------ Employee Operations ------------------------
async def add_employee(employee: Employee):
    """
    Creates new employee. Employee ID must be unique.
    """
    employees = await load_data(EMPLOYEE_FILE)
    if any(e["emp_id"] == employee.emp_id for e in employees):
        logger.error(f"Employee {employee.emp_id} already exists.")
        raise HTTPException(status_code=400, detail="Employee ID already exists.")
    employees.append(employee.dict())
    await save_data(EMPLOYEE_FILE, employees)
    logger.info(f"Employee created with emp_id={employee.emp_id}")
    return {"status_code": 200, "message": "Employee created successfully"}

async def fetch_all_employees():
    """
    Retrieves and returns all employee data.
    """
    employees = await load_data(EMPLOYEE_FILE)
    if not employees:
        logger.warning("No employees found.")
        return {"total_employees": 0, "employees": []}
    logger.info(f"Retrieved {len(employees)} employees.")
    return {
        "status_code": 200,
        "message": "Employee data fetched successfully",
        "total_employees": len(employees),
        "employees": employees
    }

async def fetch_employee_by_id(emp_id: str):
    """
    Retrieves details of a single employee by ID.
    """
    employees = await load_data(EMPLOYEE_FILE)
    employee = next((e for e in employees if e["emp_id"] == emp_id), None)
    if not employee:
        logger.error(f"Employee ID {emp_id} not found.")
        raise HTTPException(status_code=404, detail="Employee not found.")
    logger.info(f"Fetched employee data for emp_id={emp_id}")
    return {"status_code": 200, "employee": employee}

# ------------------------ Leave Operations ------------------------
async def apply_employee_leave(leave: Leave):
    """
    Allows employee to apply for leave. Starts with status 'Pending'.
    """
    employees = await load_data(EMPLOYEE_FILE)
    if not any(e["emp_id"] == leave.employee_id for e in employees):
        logger.error(f"Employee {leave.employee_id} not found.")
        raise HTTPException(status_code=404, detail="Employee not found.")
    leaves = await load_data(LEAVE_FILE)
    leaves.append(leave.dict())
    await save_data(LEAVE_FILE, leaves)
    logger.info(f"Leave applied for emp_id={leave.employee_id}, leave_id={leave.leave_id}")
    return {"status_code": 200, "message": "Leave applied, pending approval"}

async def fetch_employee_leaves(emp_id: str):
    """
    Lists all leaves taken or applied by an employee.
    """
    leaves = await load_data(LEAVE_FILE)
    emp_leaves = [l for l in leaves if l['employee_id'] == emp_id]
    logger.info(f"Fetched {len(emp_leaves)} leaves for emp_id={emp_id}")
    return {
        "status_code": 200,
        "total_leaves": len(emp_leaves),
        "leaves": emp_leaves
    }

async def update_leave_status_info(leave_id: str, status: str):
    """
    Updates leave status (Approved, Cancelled, Rejected).
    Handles leave balance adjustment.
    """
    leaves = await load_data(LEAVE_FILE)
    employees = await load_data(EMPLOYEE_FILE)

    leave = next((l for l in leaves if l["leave_id"] == leave_id), None)
    if not leave:
        logger.error(f"Leave ID {leave_id} not found.")
        raise HTTPException(status_code=404, detail="Leave not found.")

    employee = next((e for e in employees if e["emp_id"] == leave["employee_id"]), None)
    if not employee:
        logger.error(f"Employee for leave_id {leave_id} not found.")
        raise HTTPException(status_code=404, detail="Employee not found for this leave.")

    prev_status = leave["leave_status"]
    leave["leave_status"] = status
    await save_data(LEAVE_FILE, leaves)
    
    logger.info(f"Leave status updated to {status} for leave_id={leave_id}")
    return {"status_code": 200, "message": f"Leave status updated to {status}"}

# ------------------------ API Endpoints ------------------------
@app.post("/employees")
async def create_employee(employee: Employee):
    """API: Create a new employee"""
    return await add_employee(employee)

@app.get("/employees")
async def list_employees():
    """API: List all employees"""
    return await fetch_all_employees()

@app.get("/employees/{emp_id}")
async def get_employee(emp_id: str):
    """API: Get single employee by ID"""
    return await fetch_employee_by_id(emp_id)

@app.post("/employees/leaves")
async def create_leave(leave: Leave):
    """API: Apply for a leave for an employee"""
    return await apply_employee_leave(leave)

@app.get("/employees/{emp_id}/leaves")
async def list_employee_leaves(emp_id: str):
    """API: List all leaves for an employee"""
    return await fetch_employee_leaves(emp_id)

@app.put("/leaves/{leave_id}")
async def update_leave(leave_id: str, status: str):
    """API: Update leave status"""
    return await update_leave_status_info(leave_id, status)
