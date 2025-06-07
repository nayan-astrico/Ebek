from django.contrib.auth import get_user_model
from assessments.models import Learner, SkillathonEvent, Institution, EbekUser
from firebase_admin import firestore
from datetime import datetime
import random
import os
import django



db = firestore.client()

# Constants
SKILLATHON_NAME = "Guwahati Skillathon"
INSTITUTES = [
    "Neelima CON",
    "Ebek Med College",
    "KJ Somaiya Hospital",
    "AIIMS",
    "KEM"
]
GENDERS = ["male", "female", "others"]
PROCEDURE_NAMES = [
    "Communication skills",
    "Cardiopulmonary Resuscitation",
    "Intradermal Injection"
]

def get_or_create_skillathon():
    # Get or create Django SkillathonEvent
    skillathon, _ = SkillathonEvent.objects.get_or_create(
        name=SKILLATHON_NAME,
        defaults={
            'date': datetime.now().date(),
            'state': 'Assam',
            'city': 'Guwahati'
        }
    )

    # Get Firestore skillathon
    skillathon_doc = db.collection('Skillathon').where('skillathonName', '==', SKILLATHON_NAME).limit(1).get()
    if not skillathon_doc:
        print("Skillathon not found in Firestore!")
        return None
    return skillathon_doc[0].id, skillathon

def get_or_create_institutions():
    institutions = {}
    for inst_name in INSTITUTES:
        inst, _ = Institution.objects.get_or_create(
            name=inst_name,
            defaults={
                'onboarding_type': 'B2C',  # College type
                'is_active': True,
                'state': 'Assam',
                'district': 'Kamrup'
            }
        )
        institutions[inst_name] = inst
    return institutions

def get_or_create_test():
    test_docs = db.collection('Test').where('skillathon', '==', SKILLATHON_NAME).limit(1).get()
    if test_docs:
        return test_docs[0].reference
    
    test_data = {
        'createdBy': None,
        'procedureAssignments': [],
        'creationDate': datetime.now(),
        'testdate': datetime.now(),
        'status': 'Not Completed',
        'skillathon': SKILLATHON_NAME,
    }
    return db.collection('Test').add(test_data)[1]

def get_procedures():
    procedures = []
    for proc_name in PROCEDURE_NAMES:
        proc_docs = db.collection('ProcedureTable').where('procedureName', '==', proc_name).limit(1).get()
        if proc_docs:
            procedures.append(proc_docs[0].reference)
    return procedures

def create_procedure_assignments(test_ref, procedure_refs):
    procedure_assignment_refs = []
    for proc_ref in procedure_refs:
        proc_assignment_data = {
            'assignmentToBeDoneDate': datetime.now(),
            'creationDate': datetime.now(),
            'procedure': proc_ref,
            'status': 'In Progress',
            'typeOfTest': 'Classroom',
            'supervisors': [],
            'examAssignmentArray': [],
            'cohortStudentExamStarted': 0,
            'test': test_ref,
        }
        proc_assignment_ref = db.collection('ProcedureAssignment').add(proc_assignment_data)[1]
        procedure_assignment_refs.append(proc_assignment_ref)
    
    test_ref.update({'procedureAssignments': procedure_assignment_refs})
    return procedure_assignment_refs

def create_student_and_assignments(i, procedure_assignment_refs, institutions, skillathon):
    email = f'student{i}@test.com'
    name = f'Student {i}'
    gender = random.choice(GENDERS)
    institution_name = random.choice(INSTITUTES)
    institution = institutions[institution_name]
    
    # Create Django User
    user, _ = EbekUser.objects.get_or_create(
        email=email,
        defaults={
            'full_name': name,
            'phone_number': f'9876543{i:03d}',
            'is_active': True,
            'user_role': 'student'
        }
    )

    # Create Django Learner
    learner, _ = Learner.objects.get_or_create(
        learner_user=user,
        skillathon_event=skillathon,
        defaults={
            'learner_type': 'student',
            'onboarding_type': 'B2C',
            'college': institution,
            'learner_gender': gender,
            'state': 'Assam',
            'district': 'Kamrup',
            'is_active': True
        }
    )
    
    # Create Firestore user
    user_data = {
        'emailID': email,
        'name': name,
        'role': 'student',
        'skillathon_event': SKILLATHON_NAME,
        'learner_type': 'student',
        'learner_gender': gender,
        'institution': institution_name,
        'is_active': True,
        'date_joined': datetime.now().isoformat(),
        'phone_number': f'9876543{i:03d}'
    }
    user_ref = db.collection('Users').add(user_data)[1]

    # Create exam assignments for each procedure
    for proc_assignment_ref in procedure_assignment_refs:
        proc_assignment = proc_assignment_ref.get()
        proc_data = proc_assignment.to_dict()
        procedure_ref = proc_data.get('procedure')
        procedure = procedure_ref.get()
        procedure_data = procedure.to_dict()
        
        status = 'Completed' if i < 500 else 'Pending'
        marks = random.randint(0, 30) if status == 'Completed' else 0
        
        exam_assignment_data = {
            'user': user_ref,
            'examMetaData': procedure_data.get('examMetaData', {}),
            'status': status,
            'notes': procedure_data.get('notes', ''),
            'procedure_name': procedure_data.get('procedureName', ''),
            'marks': marks,
            'studentId': str(i),
            'studentName': name,
            'emailID': email,
            'gender': gender,
            'institution': institution_name,
            'skillathon': SKILLATHON_NAME,
            'completed_date': datetime.now() if status == 'Completed' else None,
            'username': email
        }
        
        exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
        proc_assignment_ref.update({
            'examAssignmentArray': firestore.ArrayUnion([exam_assignment_ref])
        })

def main():
    # 1. Get or create skillathon
    skillathon_result = get_or_create_skillathon()
    if not skillathon_result:
        return
    skillathon_firestore_id, skillathon = skillathon_result

    # 2. Get or create institutions
    institutions = get_or_create_institutions()

    # 3. Get or create test
    test_ref = get_or_create_test()

    # 4. Get procedures
    procedure_refs = get_procedures()
    if not procedure_refs:
        print("No procedures found!")
        return

    # 5. Create procedure assignments
    procedure_assignment_refs = create_procedure_assignments(test_ref, procedure_refs)

    # 6. Create students and their exam assignments
    for i in range(700):
        create_student_and_assignments(i, procedure_assignment_refs, institutions, skillathon)
        if i % 50 == 0:
            print(f'Processed {i} students...')

    print('Done!')

main()