# app.py (Updated)

# Imports Used
# Import the new Legacy Data Adapter
import os
import sys
from datetime import datetime

from bson.objectid import ObjectId
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo

# Add the current directory to the path to ensure legacy_parser can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from legacy_parser import PickRecord  # <-- NEW IMPORT

# Creating an instance of a flask appliation
app = Flask(__name__)

# MongoDB configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/school'
# Initialize MongoDB connection (connect app to MongoDB)
mongo = PyMongo(app)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ API Methods for the Legacy Data Adapter (Pick/Universe Simulation) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@app.route('/get_legacy_client/<client_id>', methods=['GET'])
def get_legacy_client(client_id):
    """
    Retrieves data from the simulated Pick/Universe flat file.
    This demonstrates understanding of Dynamic Arrays and Unibasic logic.
    """
    # 1. Simulate the READ operation on the Legacy Flat File
    client_record = PickRecord.read(client_id)
    
    # 2. Check if the record was found (i.e., the key exists)
    if client_record.raw_data:
        # Query params controls: parse_numbers, parse_dates, latest
        parse_numbers = request.args.get('parse_numbers', 'true').lower() != 'false'
        parse_dates = request.args.get('parse_dates', 'true').lower() != 'false'
        latest = request.args.get('latest', 'last')
        # 3. Use the PickRecord class to EXTRACT attributes and convert the structure
        client_data = client_record.to_json(parse_numbers=parse_numbers, parse_dates=parse_dates, latest_balance=latest)
        return jsonify(client_data), 200
    else:
        # Return a 404 if the key (ID) was not found in the flat file
        return not_found()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ API Methods for the MongoDB "students" collection ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# changing route to add a new student
@app.route('/add_student', methods=['POST'])
def add_student():
    _json = request.json  # store and convert coming json information from the request

    _studentId = _json["student_id"]
    _fName = _json["first_name"]
    _lName = _json["last_name"]
    _age = _json["age"]
    _gender = _json["gender"]
    _imageURL = _json["image"]
    _active = _json["active"]
    _isDeleted = _json["is_deleted"]

    # Parse the date string from the request and convert it into a Python datetime object
    date_format = "%Y-%m-%d"
    _created = datetime.strptime(_json["created"], date_format)
    _lastUpdated = datetime.strptime(_json["last_updated"], date_format)

    _createdBy = _json["created_by"]
    _lastUpdatedBy = _json["last_updated_by"]

    # Validation (Check if method is POST)
    if request.method == 'POST':
        
        # Inserting the variables into the "students" database
        # Removed 'id =' assignment as it's not used immediately, improved insert for clarity
        mongo.db.students.insert_one(
            {'student_id': _studentId, 
             'first_name': _fName, 
             'last_name': _lName,
             'age': _age,
             'gender': _gender,
             'image': _imageURL,
             'active': _active,
             'is_deleted': _isDeleted,
             'created': _created,
             'created_by': _createdBy,
             'last_updated': _lastUpdated,
             'last_updated_by': _lastUpdatedBy
             }
             )
        # Generate a response
        response = jsonify("Student added successfully!")

        # Return the response and status code
        return response, 200

    else:
        return not_found()
    

# Changing route to a POST (add) request to add multiple students
@app.route('/add_students', methods=['POST'])
def add_students():
    students_list = request.json  # Store and convert incoming JSON from the request

    if students_list:
        insert_list = []
        # Loop over each student in the list
        for student_data in students_list:
            _studentId = student_data.get("student_id")
            _fName = student_data.get("first_name")
            _lName = student_data.get("last_name")
            _age = student_data.get("age")
            _gender = student_data.get("gender")
            _imageURL = student_data.get("image")
            _active = student_data.get("active")
            _isDeleted = student_data.get("is_deleted")
            # Added error handling for missing date fields
            try:
                _created = datetime.strptime(student_data.get("created"), "%Y-%m-%d")
                _lastUpdated = datetime.strptime(student_data.get("last_updated"), "%Y-%m-%d")
            except (TypeError, ValueError):
                return jsonify({'message': 'Invalid or missing date format in one or more student records (expected YYYY-MM-DD)'}), 400

            _createdBy = student_data.get("created_by")
            _lastUpdatedBy = student_data.get("last_updated_by")

            # Prepare document for bulk insertion
            insert_list.append(
                {
                    'student_id': _studentId,
                    'first_name': _fName,
                    'last_name': _lName,
                    'age': _age,
                    'gender': _gender,
                    'image': _imageURL,
                    'active': _active,
                    'is_deleted': _isDeleted,
                    'created': _created,
                    'created_by': _createdBy,
                    'last_updated': _lastUpdated,
                    'last_updated_by': _lastUpdatedBy
                }
            )

        # Insert all prepared documents into the "students" database
        if insert_list:
            mongo.db.students.insert_many(insert_list)

        # Generate a response
        response = 'Students added successfully'
        return jsonify(response), 200
    else:
        return not_found()


# Helper function to serialize MongoDB object
def serialize_doc(doc):
    """Converts MongoDB document to JSON serializable dictionary."""
    doc['_id'] = str(doc['_id'])
    # Convert datetime objects to string format for JSON
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.strftime("%Y-%m-%d %H:%M:%S")
    return doc

# Get a student by student_id
@app.route('/get_student/<student_id>', methods=['GET'])
def get_single_student(student_id):
    student = mongo.db.students.find_one({'student_id': student_id})
    if student:
        return jsonify(serialize_doc(student)), 200
    else:
        return not_found()
    
# Get all students
@app.route('/get_students', methods=['GET'])
def get_all_students():
    students = list(mongo.db.students.find())

    if students:
        # Convert ObjectId and datetime for each student
        students_list = [serialize_doc(student) for student in students]
        return jsonify(students_list), 200
    else:
        return jsonify([]), 200 # Return empty list instead of 404 for 'all'


# Update a student by student_id
@app.route('/update_student/<student_id>', methods=['PUT'])
def update_student(student_id):
    _json = request.json
    date_format = "%Y-%m-%d"
    
    # Safely convert dates
    try:
        created_date = datetime.strptime(_json["created"], date_format)
        last_updated_date = datetime.strptime(_json["last_updated"], date_format)
    except (TypeError, ValueError):
        return jsonify({'message': 'Invalid date format (expected YYYY-MM-DD)'}), 400
        
    updated_student = {
        'student_id': _json["student_id"],
        'first_name': _json["first_name"],
        'last_name': _json["last_name"],
        'age': _json["age"],
        'gender': _json["gender"],
        'image': _json["image"],
        'active': _json["active"],
        'created': created_date,
        'created_by': _json["created_by"],
        'last_updated': last_updated_date,
        'last_updated_by': _json["last_updated_by"]
    }
    result = mongo.db.students.update_one(
        {'student_id': student_id},
        {'$set': updated_student}
    )
    if result.modified_count:
        return jsonify('Student updated successfully'), 200
    # Check if the document existed but no change was made
    elif result.matched_count:
        return jsonify('Student found, but no changes applied'), 200
    else:
        return not_found()

# Soft delete a student by student_id
@app.route('/soft_delete_student/<student_id>', methods=['DELETE'])
def soft_delete_student(student_id):
    result = mongo.db.students.update_one(
        {'student_id': student_id},
        # Setting the is_deleted flag to True
        {'$set': {'is_deleted': True}}
    )
    if result.modified_count:
        return jsonify('Student soft deleted successfully'), 200
    else:
        return not_found()
    
# Hard delete a student by student_id
@app.route('/hard_delete_student/<student_id>', methods=['DELETE'])
def hard_delete_student(student_id):
    result = mongo.db.students.delete_one({'student_id': student_id})
    if result.deleted_count:
        return jsonify('Student hard deleted successfully'), 200
    else:
        return not_found()
    
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ API Methods for the 2nd collection "student_tasks" ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Get a students' task (using task ID)
@app.route('/get_student_task/<task_id>', methods=['GET'])
def get_student_task(task_id):
    task = mongo.db.student_tasks.find_one({'task_id': task_id})
    if task:
        return jsonify(serialize_doc(task)), 200
    else:
        return not_found()
    
# Get a students' tasks (using student ID)
@app.route('/get_student_tasks/<student_id>', methods=['GET'])
def get_student_tasks(student_id):
    tasks = list(mongo.db.student_tasks.find({'student_id': student_id}))

    if tasks:
        # Convert ObjectId and datetime for each task
        tasks_list = [serialize_doc(task) for task in tasks]
        return jsonify(tasks_list), 200
    else:
        return jsonify([]), 200 # Return empty list instead of 404


# Inserting a new task (Single task) for a student
@app.route('/add_student_task', methods=['POST'])
def add_student_task():
    # Storing all the supplied JSON from the request
    _json = request.json
    date_format = "%Y-%m-%d"
    
    _task_id = _json.get("task_id")
    _student_id = _json.get("student_id")
    _score = _json.get("score")
    _is_deleted = _json.get("is_deleted")
    _created = _json.get("created")
    _created_by = _json.get("created_by")
    last_updated = _json.get("last_updated")
    last_updated_by = _json.get("last_updated_by")

    # Safely convert dates
    try:
        created_date = datetime.strptime(_created, date_format)
        last_updated_date = datetime.strptime(last_updated, date_format)
    except (TypeError, ValueError):
        return jsonify({'message': 'Invalid date format (expected YYYY-MM-DD)'}), 400
        

    if request.method == 'POST':
        mongo.db.student_tasks.insert_one(
            {
                'task_id': _task_id,
                'student_id': _student_id,
                'score': _score,
                'is_deleted': _is_deleted,
                'created': created_date,
                'created_by': _created_by,
                'last_updated': last_updated_date,
                'last_updated_by': last_updated_by
            }
        )
        return jsonify('Task added successfully'), 200
    else:
        return not_found()
    
# Updating a single student task (Using Task ID):
@app.route('/update_student_task/<task_id>', methods=['PUT'])
def update_student_task(task_id):
    #collect information from the request 
    _json = request.json
    date_format = "%Y-%m-%d"

    # Safely convert dates
    try:
        created_date = datetime.strptime(_json["created"], date_format)
        last_updated_date = datetime.strptime(_json["last_updated"], date_format)
    except (TypeError, ValueError):
        return jsonify({'message': 'Invalid date format (expected YYYY-MM-DD)'}), 400

    updated_student_task = {
        'task_id': _json["task_id"],
        'student_id': _json["student_id"],
        'score': _json["score"],
        'is_deleted': _json["is_deleted"],
        'created': created_date,
        'created_by': _json["created_by"],
        'last_updated': last_updated_date,
        'last_updated_by': _json["last_updated_by"]
    }
    result = mongo.db.student_tasks.update_one(
        {'task_id': task_id},
        {'$set': updated_student_task}
    )

    if result.modified_count:
        return jsonify('Task updated successfully'), 200
    # Check if the document existed but no change was made
    elif result.matched_count:
        return jsonify('Task found, but no changes applied'), 200
    else:
        return not_found()
    
# Soft Deleting a single task for a student (using task id)
@app.route('/soft_delete_student_task/<task_id>', methods=['DELETE'])
def soft_delete_student_task(task_id):
    result = mongo.db.student_tasks.update_one(
        {'task_id': task_id},
        {'$set': {'is_deleted': True}}
    )
    if result.modified_count:
        return jsonify('Task soft deleted successfully'), 200
    else:
        return not_found()

# Hard Deleting a single task for a student (using task id)
@app.route('/hard_delete_student_task/<task_id>', methods=['DELETE'])
def hard_delete_student_task(task_id):
    result = mongo.db.student_tasks.delete_one({'task_id': task_id})
    if result.deleted_count:
        return jsonify('Task hard deleted successfully'), 200
    else:
        return not_found()


# New endpoint: Update legacy record attributes in the flat file
@app.route('/update_legacy_client/<client_id>', methods=['POST'])
def update_legacy_client(client_id):
    # Expect JSON mapping of attribute_pos -> value (string or list for VM)
    data = request.json
    if not data:
        return jsonify({'message': 'Missing JSON body with attribute mapping'}), 400
    try:
        record = PickRecord.read(client_id)
        if not record.raw_data:
            return not_found()
        # Validate keys are positive ints
        attr_map = {}
        for k, v in data.items():
            try:
                pos = int(k)
                attr_map[pos] = v
            except Exception:
                return jsonify({'message': f'Invalid attribute key: {k} (must be integer)'}), 400
        record.update(attr_map)
        return jsonify({'message': 'Legacy record updated successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Error updating legacy record', 'detail': str(e)}), 500

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ For Error Handling ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@app.errorhandler(404)
def not_found(error=None):
    message = {
        'status': 404,
        'message': 'Not found ' + request.url
    }
    response = jsonify(message)
    return response, 404

if __name__ == '__main__':
    app.run(debug=True)