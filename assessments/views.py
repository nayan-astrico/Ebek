from django.shortcuts import render
import os
import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .forms import ExcelUploadForm
from firebase_admin import firestore
import uuid
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .models import *
from .utils_ses import *
from django.urls import reverse
from assessments.onboarding_views import *
from collections import defaultdict


logger = logging.getLogger(__name__)

# Initialize Firestore client
db = firestore.client()

def parse_excel_to_json(dataframe, procedure_name):
    """Parse the uploaded Excel file to JSON."""
    procedure_json = {
        "procedure_name": procedure_name,  # Procedure Name passed as an argument
        "notes": "",
        "exammetadata": [
            {
                "section_name": "",
                "section_questions": []
            }
        ]
    }

    current_parameter = None
    # Process data from row 4 onward
    for _, row in dataframe.iterrows():
        if not pd.isna(row["Parameters"]):  # Check for Parameters
            if current_parameter:
                if current_parameter["sub_section_questions_present"]:
                    # Sum up all indicator marks for this parameter
                    current_parameter["right_marks_for_question"] = sum(
                        sub_q["right_marks_for_question"] 
                        for sub_q in current_parameter["sub_section_questions"]
                    )
                procedure_json["exammetadata"][0]["section_questions"].append(current_parameter)

            current_parameter = {
                "question": row["Parameters"],  # Parameters column
                "right_marks_for_question": int(row["Marks"]) if not pd.isna(row["Marks"]) else 0,
                "answer_scored": 0,
                "sub_section_questions_present": False,
                "sub_section_questions": [],
                "category": row["Category"] if pd.isna(row["Indicators"]) and not pd.isna(row["Category"]) else "",
                "critical": row["Critical"] == True if not pd.isna(row["Critical"]) else False  # Add critical flag
            }

        if not pd.isna(row["Indicators"]) and current_parameter:  # Check for Indicators
            current_parameter["sub_section_questions_present"] = True
            current_parameter["sub_section_questions"].append({
                "question": row["Indicators"],  # Indicators column
                "right_marks_for_question": float(row["Marks"]) if not pd.isna(row["Marks"]) else 0,
                "answer_scored": 0,
                "category": row["Category"] if not pd.isna(row["Category"]) else "",
                "critical": row["Critical"] == True if not pd.isna(row["Critical"]) else False  # Add critical flag
            })

    # Handle the last parameter
    if current_parameter:
        if current_parameter["sub_section_questions_present"]:
            # Sum up all indicator marks for the last parameter
            current_parameter["right_marks_for_question"] = sum(
                sub_q["right_marks_for_question"] 
                for sub_q in current_parameter["sub_section_questions"]
            )
        procedure_json["exammetadata"][0]["section_questions"].append(current_parameter)

    return procedure_json

def upload_excel_view(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']

            file_name = f"{uuid.uuid4()}_{uploaded_file.name}".replace(" ", "_")
            file_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_excels', file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            try:
                df = pd.read_excel(file_path, header=None)  # Read without header to validate

                # Validate specific cells in row 3
                if not (
                    df.iloc[2, 0] == "Section" and
                    df.iloc[2, 1] == "Parameters" and
                    df.iloc[2, 2] == "Indicators" and
                    df.iloc[2, 4] == "Marks" and  # Add Critical column validation
                    df.iloc[2, 5] == "Critical"
                ):
                    raise ValueError("Excel template is incorrect. Ensure row 3 contains 'Section', 'Parameters', 'Indicators', 'Category','Marks', 'Critical' .")

                # Extract Procedure Name
                procedure_name = df.iloc[0, 1].strip()

                # Process data from row 4 onward
                df_data = pd.read_excel(file_path, skiprows=3, header=None, 
                                      names=["Section", "Parameters", "Indicators", "Category","Marks","Critical"])
                parsed_json = parse_excel_to_json(df_data, procedure_name)

                # Upload to Firebase
                procedure_ref = db.collection('ProcedureTable').document()
                procedure_ref.set({
                    "procedureName": parsed_json['procedure_name'],
                    "examMetaData": parsed_json['exammetadata'],
                    "notes": parsed_json['notes'],
                    "active": True
                })

                logger.info(f"File uploaded successfully - {procedure_ref.id}")
                return JsonResponse({"message": "File processed successfully!"}, status=200)
            except Exception as e:
                logger.error(f"Error processing file for : {str(e)}")
                return JsonResponse({"error": str(e)}, status=400)
        else:
            return JsonResponse({"error": form.errors}, status=400)


def create_assessment(request):
    # Fetch procedures from Firebase
    procedures_ref = db.collection('ProcedureTable')
    procedures = procedures_ref.stream()

    procedure_list = []
    for procedure in procedures:
        data = procedure.to_dict()

        examMetaData = data.get("examMetaData")

        procedure_list.append({
            "id": procedure.id,
            "name": data.get("procedureName", "N/A"),
            "questions": len(examMetaData[0]["section_questions"]),
            "active": data.get("active", True),  # Default to True if not present
        })

    # Search filter
    query = request.GET.get("query", "")
    if query:
        procedure_list = [proc for proc in procedure_list if query.lower() in proc["name"].lower()]

    # Pagination
    paginator = Paginator(procedure_list, 5)  # Show 10 procedures per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'assessments/create_assessment.html', {
        "page_obj": page_obj,
        "query": query,
    })


class ProcedureAPIView(APIView):
    """
    APIView to handle procedure actions: toggle, delete, download.
    """

    def get(self, request, procedure_id, action):
        """
        Handles 'view' and 'download'.
        If 'download', converts metadata to Excel and serves the file.
        """
        if action == "download":
            return self.download_metadata(procedure_id)
        elif action == "view":
            return self.view_metadata(procedure_id)
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, procedure_id, action):
        """
        Handles 'toggle' status and other POST-based actions.
        """
        if action == "toggle":
            return self.toggle_status(procedure_id)
        if action == "delete":
            return self.delete_procedure(procedure_id)
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

    def view_metadata(self, procedure_id):
        """
        Retrieves metadata for a specific procedure.
        """
        try:
            procedure_ref = db.collection('ProcedureTable').document(procedure_id)
            procedure = procedure_ref.get()

            if not procedure.exists:
                return Response({"error": "Procedure not found"}, status=status.HTTP_404_NOT_FOUND)

            
            return Response(procedure.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def toggle_status(self, procedure_id):
        """
        Toggles the 'active' status of a procedure.
        """
        try:
            procedure_ref = db.collection('ProcedureTable').document(procedure_id)
            procedure = procedure_ref.get()

            if not procedure.exists:
                return Response({"error": "Procedure not found"}, status=status.HTTP_404_NOT_FOUND)

            current_status = procedure.to_dict().get("active", True)
            procedure_ref.update({"active": not current_status})

            return Response({"success": True, "active": not current_status}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete_procedure(self, procedure_id):
        """
        Deletes the procedure from Firebase.
        """
        try:
            procedure_ref = db.collection('ProcedureTable').document(procedure_id)
            procedure = procedure_ref.get()

            if not procedure.exists:
                return Response({"error": "Procedure not found"}, status=status.HTTP_404_NOT_FOUND)

            procedure_ref.delete()

            return Response({"success": True, "message": "Procedure deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def download_metadata(self, procedure_id):
        """
        Converts metadata to Excel based on the provided template and serves it as a downloadable file.
        """
        try:
            procedure_ref = db.collection('ProcedureTable').document(procedure_id)
            procedure = procedure_ref.get()

            if not procedure.exists:
                return Response({"error": "Procedure not found"}, status=status.HTTP_404_NOT_FOUND)

            procedure_data = procedure.to_dict()
            procedure_name = procedure_data.get("procedureName", "")
            exam_metadata = procedure_data.get("examMetaData", [])

            # Start creating the data structure
            data = [["Procedure Name", procedure_name]]  # Procedure name row
            data.append([])  # Empty row
            data.append(["Section", "Parameters", "Indicators", "Category"])  # Column headers

            # Populate rows with exam metadata
            for section in exam_metadata:
                for question in section.get("section_questions", []):
                    # Add the main parameter row
                    parameter_row = [
                        section.get("section_name", ""),
                        question.get("question", ""),
                        "",  # Indicators will start on the same row
                        question.get("category", "") if not question.get("sub_section_questions_present", False) else "",
                    ]
                    data.append(parameter_row)

                    # Add indicators aligned to the same row
                    if question.get("sub_section_questions_present", False):
                        indicators = question.get("sub_section_questions", [])
                        for i, indicator in enumerate(indicators):
                            print(indicator)
                            if i == 0:
                                # Place the first indicator on the same row as the parameter
                                data[-1][2] = indicator.get("question", "")  # Add indicator to the "Indicators" column
                                data[-1][3] = indicator.get("category", "")  # Add category
                            else:
                                # For subsequent indicators, create a new row
                                data.append([
                                    "",  # No Section
                                    "",  # No Parameter
                                    indicator.get("question", ""),
                                    indicator.get("category", ""),
                                ])

            # Convert to a DataFrame
            df = pd.DataFrame(data)

            # Generate the Excel file
            file_name = f"{procedure_name.replace(' ', '_')}_metadata.xlsx"
            file_path = os.path.join(settings.MEDIA_ROOT, file_name)
            with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, header=False)

            # Serve the file as a download
            with open(file_path, "rb") as file:
                response = HttpResponse(file.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                response["Content-Disposition"] = f"attachment; filename={file_name}"
                return response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def fetch_institutes(request):
    """Fetch all institutes from the InstituteNames collection."""
    try:
        institutes_ref = db.collection('InstituteNames')
        institutes = []
        for doc in institutes_ref.stream():
            institute_data = doc.to_dict()
            institutes.append({
                'id': doc.id,
                'instituteName': institute_data.get('instituteName', 'Unnamed Institute')
            })

        return JsonResponse({'institutes': institutes}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fetch_cohorts(request):
    """Fetch cohorts based on the selected institute."""
    institute = request.GET.get('institute', None)
    if not institute:
        return JsonResponse({'error': 'Institute not provided'}, status=400)

    try:
        cohorts_ref = db.collection('Cohort').where('instituteName', '==', institute)
        cohorts = []
        for doc in cohorts_ref.stream():
            cohort_data = doc.to_dict()
            cohort_name = cohort_data.get('cohortName', '')
            if cohort_name != "SupervisorCohort":
                cohorts.append({
                    'id': doc.id,
                    'cohortName': cohort_data.get('cohortName', '')
                    })
        return JsonResponse({'cohorts': cohorts}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fetch_assessors(request):
    """Fetch assessors from the 'EbekCohort'."""
    try:
        users_ref = db.collection('Users').where('role', '==', 'ebek_admin')
        print(users_ref)

        assessors = []
        for doc in users_ref.stream():
            print(doc)
            user_data = doc.to_dict()
            assessors.append({
                'id': doc.id,
                'name': user_data.get('name', 'Unknown Assessor')
            })
        print(assessors)
        return JsonResponse({'assessors': assessors}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fetch_procedures(request):
    try:
        procedure_ref = db.collection('ProcedureTable').where('active', '==', True)
        procedures = []
        for doc in procedure_ref.stream():
            procedure_data = doc.to_dict()
            procedure_name = procedure_data.get('procedureName', '')
            procedures.append({
                'id': doc.id,
                'name': procedure_data.get('procedureName', '')
                })
        return JsonResponse({'procedures': procedures}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

import traceback
def create_procedure_assignment_and_test(request):
    if request.method == 'POST':
        try:
            data = request.POST
            print(data)
            # Parse required inputs
            batch_ids = data.getlist('batch_ids')  
            procedure_ids = data.getlist('procedure_ids')  
            test_date = data.get('test_date')  
            assessor_ids = data.getlist('assessor_ids')

            # Convert test_date to datetime object
            test_date_obj = datetime.strptime(test_date, '%Y-%m-%d')

            # Get current user (for now set to null as per your request)
            current_user = None  # Change this as needed based on your auth logic

            created_tests = []  # To store references for created tests

            if batch_ids != []:
                for batch_id in batch_ids:
                    # Fetch cohort document
                    cohort_ref = db.collection('Cohort').document(batch_id)
                    cohort_doc = cohort_ref.get()
                    if not cohort_doc.exists:
                        return JsonResponse({'error': f'Cohort with ID {batch_id} does not exist.'}, status=404)

                    cohort_data = cohort_doc.to_dict()
                    users = cohort_data.get('users', [])

                    # Create Test document
                    test_data = {
                        'createdBy': None if current_user is None else current_user,  # Supervisor user reference
                        'cohort': cohort_ref,
                        'procedureAssignments': [],
                        'creationDate': datetime.now(),
                        'testdate': test_date_obj,
                        'batchname': cohort_data.get('cohortName', ''),
                        'status': 'Not Completed',
                    }
                    test_ref = db.collection('Test').add(test_data)[1]
                    created_tests.append(test_ref.id)

                    # Create ProcedureAssignments
                    procedure_assignment_refs = []
                    for procedure_id in procedure_ids:
                        procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                        procedure_data = procedure_ref.get().to_dict()

                        if not procedure_data:
                            continue

                        # Create ProcedureAssignment for each assessor
                        for assessor_id in assessor_ids:
                            procedure_assignment_data = {
                                'assignmentToBeDoneDate': test_date_obj,
                                'cohort': cohort_ref,
                                'cohortStudentExamTaken': 0,
                                'creationDate': datetime.now(),
                                'procedure': procedure_ref,
                                'status': 'Pending',
                                'typeOfTest': 'Classroom',
                                'supervisor': db.collection('Users').document(assessor_id),  # Now using current assessor
                                'examAssignmentArray': [],
                                'cohortStudentExamStarted': 0,
                                'test': test_ref,
                            }
                            
                            procedure_assignment_ref = db.collection('ProcedureAssignment').add(procedure_assignment_data)[1]
                            procedure_assignment_refs.append(procedure_assignment_ref)

                            # Create ExamAssignments for this procedure assignment
                            exam_assignment_refs = []
                            for user_snapshot in users:
                                exam_meta_data = procedure_data.get('examMetaData', {})
                                notes = procedure_data.get('notes', '')
                                procedure_name = procedure_data.get('procedureName', '')

                                exam_assignment_data = {
                                    'user': user_snapshot.reference,  # Use the document reference instead of snapshot
                                    'examMetaData': exam_meta_data,
                                    'status': 'Pending',
                                    'notes': notes,
                                    'procedure_name': procedure_name,
                                }
                                exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                                exam_assignment_refs.append(exam_assignment_ref)

                            # Update ProcedureAssignment with exam assignments
                            procedure_assignment_ref.update({'examAssignmentArray': firestore.ArrayUnion(exam_assignment_refs)})

                    # Update Test document with all procedure assignments
                    test_ref.update({'procedureAssignments': firestore.ArrayUnion(procedure_assignment_refs)})

                    # Create CohortProcedureAssignments
                    for assessor_id in assessor_ids:
                        db.collection('CohortProcedureAssignments').add({
                            'test': test_ref,
                            'user': db.collection('Users').document(assessor_id),
                            'typeOfTest': 'Classroom',
                        })
            else:
                skillathon_id = data.get('skillathon_id')
                skillathon_ref = db.collection('Skillathon').document(skillathon_id)
                skillathon_name = skillathon_ref.get().to_dict()["skillathonName"]
                test_data = {
                        'createdBy': None if current_user is None else current_user,  # Supervisor user reference
                        'procedureAssignments': [],
                        'creationDate': datetime.now(),
                        'testdate': test_date_obj,
                        'status': 'Not Completed',
                        'skillathon': skillathon_name,
                    }
                print(test_data)
                
                test_ref = db.collection('Test').add(test_data)[1]
                created_tests.append(test_ref.id)

                procedure_assignment_refs = []
                for procedure_id in procedure_ids:
                    try:
                        procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                        procedure_data = procedure_ref.get().to_dict()

                        if not procedure_data:
                            continue
                        
                        procedure_assignment_data = {
                            'assignmentToBeDoneDate': test_date_obj,
                            'creationDate': datetime.now(),
                            'procedure': procedure_ref,
                            'status': 'Pending',
                            'typeOfTest': 'Classroom',
                            'supervisors': [db.collection('Users').document(aid) for aid in assessor_ids],
                            'examAssignmentArray': [],
                            'cohortStudentExamStarted': 0,
                            'test': test_ref,
                        }

                        procedure_assignment_ref = db.collection('ProcedureAssignment').add(procedure_assignment_data)[1]
                        procedure_assignment_refs.append(procedure_assignment_ref)

                        users = db.collection('Users').where("role", "in", ["student", "nurse"]).where("skillathon_event", "==", skillathon_name)

                        exam_assignment_refs = []
                        for user_snapshot in users.stream():
                            exam_meta_data = procedure_data.get('examMetaData', {})
                            notes = procedure_data.get('notes', '')
                            procedure_name = procedure_data.get('procedureName', '')

                            exam_assignment_data = {
                                'user': user_snapshot.reference,  # Use the document reference instead of snapshot
                                'examMetaData': exam_meta_data,
                                'status': 'Pending',
                                'notes': notes,
                                'procedure_name': procedure_name,
                            }
                            exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                            exam_assignment_refs.append(exam_assignment_ref)

                        # Update ProcedureAssignment with exam assignments
                        procedure_assignment_ref.update({'examAssignmentArray': firestore.ArrayUnion(exam_assignment_refs)})

                        # Update Test document with all procedure assignments
                        test_ref.update({'procedureAssignments': firestore.ArrayUnion(procedure_assignment_refs)})
                    except Exception as e:
                        pass
                
                    

            return JsonResponse({'success': True, 'created_tests': created_tests})

        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
            print("HEEEREEEEEE")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

def assign_assessment(request):
    # Initialize Firestore client

    # Fetch data from the 'Test' collection
    test_data = []
    tests_ref = db.collection('Test')
    tests = tests_ref.stream()

    for test in tests:
        test_doc = test.to_dict()
        skillathon = test_doc.get('skillathon', None)
        procedure_assignments = []
        for proc_ref in test_doc.get('procedureAssignments', []):
            proc_doc = proc_ref.get()
            if proc_doc.exists:
                proc_data = proc_doc.to_dict()
                procedure_ref = proc_data.get('procedure')
                procedure_name = "Unknown"
                if procedure_ref:
                    procedure_doc = procedure_ref.get()
                    if procedure_doc.exists:
                        procedure_name = procedure_doc.to_dict().get('procedureName', 'Unknown')
                procedure_assignments.append({
                    'id': proc_ref.id,
                    'procedure_name': procedure_name,
                    'status': proc_data.get('status', 'Unknown'),
                })
        test_data.append({
            'id': test.id,
            'assessment_name': (
                f"{test_doc.get('batchname', skillathon or 'Unknown')} - "
                f"{test_doc.get('testdate').strftime('%d %b') if test_doc.get('testdate') else ''}"
            ),
            'skillathon': skillathon,
            'procedure_assignments': procedure_assignments,
            'status': test_doc.get('status', 'Not Available'),
        })

    # Pagination
    paginator = Paginator(test_data, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'assessments/assign_assessment.html', {
        "page_obj": page_obj,
        "query": request.GET.get("query", ""),
    })

def render_exam_reports_page(request):
    return render(request, 'assessments/exam_reports.html')


@csrf_exempt
def fetch_exam_reports(request):
    try:
        exam_reports = []

        # Handle pagination
        offset = int(request.GET.get("offset", 0))
        limit = int(request.GET.get("limit", 10))
        institute_id = request.GET.get("institute_id")

        # Handle auto-fetch for new data
        auto_fetch = request.GET.get("auto_fetch", "false").lower() == "true"

        # Create base query
        base_query = db.collection('ExamAssignment')

        # Add institute filter if specified
        if institute_id:
            institute_ref = db.collection('InstituteNames').document(institute_id)
            base_query = base_query.where("institute", "==", institute_ref)

        if auto_fetch:
            one_minute_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
            exam_assignments_ref = base_query.where("completed_date", ">=", one_minute_ago)
            exam_assignments_ref = exam_assignments_ref.order_by("completed_date", direction=firestore.Query.DESCENDING)
            exam_assignments = exam_assignments_ref.stream()
        else:
            exam_assignments_ref = base_query.where("status", "==", "Completed")
            exam_assignments_ref = exam_assignments_ref.order_by("completed_date", direction=firestore.Query.DESCENDING)
            exam_assignments = exam_assignments_ref.offset(offset).limit(limit).stream()

        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            student_ref = exam_doc.get('user')
            institute_ref = exam_doc.get('institute')

            if not student_ref:
                continue

            student_id = student_ref.id
            student_data = student_ref.get().to_dict()
            student_name = student_data.get('username', 'Unknown')

            # Get institute name
            institute_name = "Unknown"
            if institute_ref:
                institute_doc = institute_ref.get()
                if institute_doc.exists:
                    institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')

            total_score = exam_doc.get("marks", 0)
            max_marks = sum(
                question.get('right_marks_for_question', 0) 
                for section in exam_doc.get('examMetaData', []) 
                for question in section.get("section_questions", [])
            )

            percentage = round((total_score / max_marks) * 100, 2) if max_marks else 0
            critical_missed, critical_points = calculate_exam_score(exam_doc.get("examMetaData", []))
            procedure_name = exam_doc.get("procedure_name", "Unknown")

            status = "Passed"
            if critical_missed >= 3:
                status = "Retake Required"
            elif critical_missed > 0:
                status = f"{critical_missed} Critical Missed"

            exam_reports.append({
                "exam_id": exam.id,
                "student_id": student_id,
                "student_name": student_name,
                "institute_name": institute_name,
                "total_score": total_score,
                "percentage": percentage,
                "critical_missed": critical_missed,
                "procedure_name": procedure_name,
                "critical_points": critical_points,
                "status": status
            })
        return JsonResponse({"exam_reports": exam_reports})

    except Exception as e:
        print(str(e))
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def fetch_exam_metrics(request):
    try:
        skillathon_name = request.GET.get("skillathon_name")
        institution_name = request.GET.get("institution_name")  # Now using name, not ID

        if not skillathon_name:
            return JsonResponse({"error": "skillathon_name is required"}, status=400)

        # Build query
        base_query = db.collection('ExamAssignment') \
            .where('status', '==', 'Completed') \
            .where('skillathon', '==', skillathon_name)

        if institution_name:
            base_query = base_query.where('institution', '==', institution_name)

        exam_assignments = list(base_query.stream())

        # --- Analytics Calculation ---
        total_students = set()
        procedure_counts = defaultdict(int)
        grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        gender_metrics = {
            "total": {"male": 0, "female": 0, "others": 0},
            "grade_wise": {
                "A": {"male": 0, "female": 0, "others": 0},
                "B": {"male": 0, "female": 0, "others": 0},
                "C": {"male": 0, "female": 0, "others": 0},
                "D": {"male": 0, "female": 0, "others": 0},
                "E": {"male": 0, "female": 0, "others": 0}
            }
        }
        skill_wise_metrics = {}
        
        # Track completed procedures per student
        student_completed_procedures = defaultdict(set)

        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            email = exam_doc.get('emailID')
            if not email:
                continue
            total_students.add(email)

            procedure_name = exam_doc.get('procedureName', 'Unknown')
            if procedure_name == "Unknown":
                procedure_name = exam_doc.get('procedure_name', 'Unknown')
            # Track completed procedure for this student
            student_completed_procedures[email].add(procedure_name)
            
            gender = (exam_doc.get('gender') or 'others').lower()
            percentage = 0
            total_score = exam_doc.get("marks", 0)
            max_marks = sum(
                question.get('right_marks_for_question', 0)
                for section in exam_doc.get('examMetaData', [])
                for question in section.get("section_questions", [])
            )
            if max_marks > 0:
                percentage = round((total_score / max_marks) * 100, 2)
            grade = get_grade_letter(percentage)

            # Procedure counts
            procedure_counts[procedure_name] += 1

            # Grade distribution
            grade_distribution[grade] += 1

            # Gender metrics
            gender_metrics["total"][gender] += 1
            gender_metrics["grade_wise"][grade][gender] += 1

            # Skill-wise metrics
            if procedure_name not in skill_wise_metrics:
                skill_wise_metrics[procedure_name] = {
                    "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0},
                    "critical_steps": {
                        "missed_one": 0,
                        "missed_multiple": 0,
                        "completed_all": 0
                    },
                    "common_missed_steps": {}
                }
            skill_wise_metrics[procedure_name]["grade_distribution"][grade] += 1

            # Critical steps
            critical_missed = 0
            missed_steps = []
            for section in exam_doc.get("examMetaData", []):
                for question in section.get("section_questions", []):
                    if question.get("critical") and question.get("answer_scored", 0) == 0:
                        critical_missed += 1
                        missed_steps.append(question.get('question'))
            if critical_missed == 0:
                skill_wise_metrics[procedure_name]["critical_steps"]["completed_all"] += 1
            elif critical_missed == 1:
                skill_wise_metrics[procedure_name]["critical_steps"]["missed_one"] += 1
            elif critical_missed > 1:
                skill_wise_metrics[procedure_name]["critical_steps"]["missed_multiple"] += 1
            for step in missed_steps:
                if step not in skill_wise_metrics[procedure_name]["common_missed_steps"]:
                    skill_wise_metrics[procedure_name]["common_missed_steps"][step] = 0
                skill_wise_metrics[procedure_name]["common_missed_steps"][step] += 1

        # Calculate completed_all_procedures metric
        all_procedures = set(procedure_counts.keys())
        completed_all_procedures = sum(
            1 for student_procedures in student_completed_procedures.values()
            if student_procedures == all_procedures
        )

        # Finalize all missed critical steps for each procedure
        for proc_name in skill_wise_metrics:
            common_steps = skill_wise_metrics[proc_name]["common_missed_steps"]
            if not common_steps:
                skill_wise_metrics[proc_name]["common_missed_steps"] = {}

        metrics = {
            "total_students": len(total_students),
            "procedure_counts": dict(procedure_counts),
            "grade_distribution": grade_distribution,
            "gender_metrics": gender_metrics,
            "skill_wise_metrics": skill_wise_metrics,
            "completed_all_procedures": completed_all_procedures
        }
        return JsonResponse(metrics)

    except Exception as e:
        print(f"Error in fetch_exam_metrics: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def get_grade_letter(percentage):
    if percentage >= 90:
        return "A"
    elif percentage >= 80:
        return "B"
    elif percentage >= 70:
        return "C"
    elif percentage >= 60:
        return "D"
    return "E"

def fetch_skillathons(request):
    """Fetch all skillathons from the Skillathon collection."""
    try:
        skillathons_ref = db.collection('Skillathon')
        skillathons = []
        for doc in skillathons_ref.stream():
            skillathon_data = doc.to_dict()
            # Parse the full ISO 8601 timestamp
            created_at = datetime.fromisoformat(skillathon_data.get('created_at').replace('Z', '+00:00'))
            skillathons.append({
                'id': doc.id,
                'name': skillathon_data.get('skillathonName', 'Unnamed Skillathon'),
                'date': created_at.strftime('%d-%m-%Y')
            })

        return JsonResponse({'skillathons': skillathons}, status=200)
    except Exception as e:
        print(f"Error in fetch_skillathons: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def exam_to_score_info(exam_doc):
    exam_data = exam_doc.to_dict()
    user_ref = exam_data.get('user')
    student_name = "-"
    institute_name = "-"
    if user_ref:
        student_doc = user_ref.get()
        if student_doc.exists:
            student_data = student_doc.to_dict()
            student_name = student_data.get('name', '-')
            # Get institute from user document
            user_institute_ref = student_data.get('institute')
            if user_institute_ref and hasattr(user_institute_ref, 'get'):
                user_inst_doc = user_institute_ref.get()
                if user_inst_doc.exists:
                    institute_name = user_inst_doc.to_dict().get('instituteName', '-')
            elif isinstance(student_data.get('institution'), str):
                institute_name = student_data.get('institution')
    total_score = exam_data.get("marks", 0)
    max_marks = sum(
        question.get('right_marks_for_question', 0)
        for section in exam_data.get('examMetaData', [])
        for question in section.get("section_questions", [])
    )
    percentage = round((total_score / max_marks) * 100, 2) if max_marks else 0
    return {
        "student_name": student_name,
        "institute_name": institute_name,
        "percentage": percentage
    }

@csrf_exempt
def fetch_student_metrics(request):
    try:
        skillathon_name = request.GET.get("skillathon_name")
        institution_name = request.GET.get("institution_name")  # Now using name, not ID

        if not skillathon_name:
            return JsonResponse({"error": "skillathon_name is required"}, status=400)

        # Build query
        base_query = db.collection('ExamAssignment') \
            .where('status', '==', 'Completed') \
            .where('skillathon', '==', skillathon_name)

        if institution_name:
            base_query = base_query.where('institution', '==', institution_name)

        exam_assignments = list(base_query.stream())

        # Group by emailID
        students = defaultdict(lambda: {
            'name': None,
            'institute': None,
            'grades': {},
            'missed_critical_steps': {},
            'exam_data': {}
        })
        all_procedures = set()

        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            email = exam_doc.get('emailID')
            if not email:
                continue
            procedure_name = exam_doc.get('procedureName', 'Unknown')
            if procedure_name == "Unknown":
                procedure_name = exam_doc.get('procedure_name', 'Unknown')
            all_procedures.add(procedure_name)

            # Student info
            students[email]['name'] = exam_doc.get('name') or exam_doc.get('username') or email
            students[email]['institute'] = exam_doc.get('institution', 'Unknown')

            # Grade calculation
            total_score = exam_doc.get("marks", 0)
            max_marks = sum(
                question.get('right_marks_for_question', 0)
                for section in exam_doc.get('examMetaData', [])
                for question in section.get("section_questions", [])
            )
            percentage = round((total_score / max_marks) * 100, 2) if max_marks else 0
            grade = get_grade_letter(percentage)

            # Missed critical steps and steps info
            missed_critical = []
            steps = []
            critical_missed = 0
            for section in exam_doc.get("examMetaData", []):
                for question in section.get("section_questions", []):
                    step_info = {
                        'description': question.get('question', ''),
                        'completed': question.get('answer_scored', 0) > 0,
                        'critical': question.get('critical', False)
                    }
                    steps.append(step_info)
                    if question.get("critical") and question.get("answer_scored", 0) == 0:
                        missed_critical.append(question.get('question'))
                        critical_missed += 1

            # Store per procedure
            students[email]['grades'][procedure_name] = {
                'grade': grade,
                'percentage': percentage
            }
            students[email]['missed_critical_steps'][procedure_name] = missed_critical
            students[email]['exam_data'][procedure_name] = {
                'steps': steps,
                'critical_missed': critical_missed
            }

        # Prepare students list
        students_list = list(students.values())
        all_procedures = list(all_procedures)

        # Highest/lowest scorecards
        highest_score = -1
        highest_score_student = "-"
        highest_score_institute = "-"
        lowest_score = 101
        lowest_score_student = "-"
        lowest_score_institute = "-"
        for student in students_list:
            for proc in all_procedures:
                grade_info = student['grades'].get(proc)
                if grade_info:
                    pct = grade_info['percentage']
                    if pct > highest_score:
                        highest_score = pct
                        highest_score_student = student['name']
                        highest_score_institute = student['institute']
                    if pct < lowest_score:
                        lowest_score = pct
                        lowest_score_student = student['name']
                        lowest_score_institute = student['institute']

        # Response
        return JsonResponse({
            'students': students_list,
            'procedures': all_procedures,
            'highest_score': highest_score if highest_score != -1 else 0,
            'highest_score_student': highest_score_student,
            'highest_score_institute': highest_score_institute,
            'lowest_score': lowest_score if lowest_score != 101 else 0,
            'lowest_score_student': lowest_score_student,
            'lowest_score_institute': lowest_score_institute
        })
    except Exception as e:
        print(f"Error in fetch_student_metrics: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def fetch_particular_student(request):
    try:
        exam_reports = []
        username = request.GET.get("username")

        if not username:
            return JsonResponse({"error": "Username parameter is required"}, status=400)

        # Fetch user reference from Firestore
        user_query = db.collection('Users').where("username", "==", username).limit(1).stream()
        user_doc = next(user_query, None)

        if not user_doc:
            return JsonResponse({"error": "User not found"}, status=404)

        user_ref = user_doc.reference  # Get the Firestore document reference

        # Fetch exams where user matches and status is "Completed"
        exam_assignments_ref = (
            db.collection('ExamAssignment')
            .where("status", "==", "Completed")
            .where("user", "==", user_ref)  # Filter exams for the specific user
            .order_by("completed_date", direction=firestore.Query.DESCENDING)
        )

        exam_assignments = exam_assignments_ref.stream()

        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            
            total_score = exam_doc.get("marks", 0)
            max_marks = sum(
                question.get('right_marks_for_question', 0) 
                for section in exam_doc.get('examMetaData', []) 
                for question in section.get("section_questions", [])
            )

            percentage = round((total_score / max_marks) * 100, 2) if max_marks else 0
            critical_missed, critical_points = calculate_exam_score(exam_doc.get("examMetaData", []))
            procedure_name = exam_doc.get("procedure_name", "Unknown")

            exam_reports.append({
                "exam_id": exam.id,
                "student_id": user_doc.id,
                "student_name": username,
                "total_score": total_score,
                "percentage": percentage,
                "critical_missed": critical_missed,
                "procedure_name": procedure_name,
                "critical_points": critical_points,
            })

        return render(request, 'assessments/particular_student_report.html', {"exam_reports": exam_reports})
       
    except Exception as e:
        print(str(e))
        return JsonResponse({"error": str(e)}, status=500)

def calculate_exam_score(exam_metadata):
    critical_missed = 0
    critical_points = []
    
    for section in exam_metadata:
        for question in section.get("section_questions", []):
            if question.get("critical") and question.get("answer_scored", 0) == 0:
                critical_missed += 1
                critical_points.append(question.get('question'))
    
    return critical_missed, critical_points

@csrf_exempt
def institute_list(request):
    """View to list all institutes and handle creation."""
    try:
        # Fetch all institutes from Firebase
        institutes_ref = db.collection('InstituteNames')
        institutes = []
        
        # Get query parameter for search
        search_query = request.GET.get('query', '').lower()
        
        for doc in institutes_ref.stream():
            institute_data = doc.to_dict()
            institute_name = institute_data.get('instituteName', '')
            
            # Apply search filter if query exists
            if not search_query or search_query in institute_name.lower():
                institutes.append({
                    'id': doc.id,
                    'name': institute_name
                })
        
        # Sort institutes by name
        institutes.sort(key=lambda x: x['name'])
        
        # Pagination
        paginator = Paginator(institutes, 10)  # Show 10 institutes per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'assessments/institute_list.html', {
            'page_obj': page_obj,
            'query': search_query
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def create_institute(request):
    """API endpoint to create or edit an institute."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            institute_name = data.get('instituteName', '').strip()
            institute_id = data.get('instituteId')  # For editing
            
            if not institute_name:
                return JsonResponse({'error': 'Institute name is required'}, status=400)
            
            # Check if institute already exists (for new creation)
            if not institute_id:
                existing_institute = db.collection('InstituteNames')\
                    .where('instituteName', '==', institute_name)\
                    .limit(1)\
                    .stream()
                
                if list(existing_institute):
                    return JsonResponse({'error': 'Institute already exists'}, status=400)
                
                # Create new institute
                new_institute = {
                    'instituteName': institute_name,
                    'createdAt': firestore.SERVER_TIMESTAMP
                }
                
                # Add to Firebase
                institute_ref = db.collection('InstituteNames').add(new_institute)
                
                return JsonResponse({
                    'success': True,
                    'id': institute_ref[1].id,
                    'message': 'Institute created successfully'
                })
            else:
                # Update existing institute
                institute_ref = db.collection('InstituteNames').document(institute_id)
                institute_ref.update({
                    'instituteName': institute_name,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })
                
                return JsonResponse({
                    'success': True,
                    'id': institute_id,
                    'message': 'Institute updated successfully'
                })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def edit_institute(request, institute_id):
    """API endpoint to edit an institute."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            institute_name = data.get('instituteName', '').strip()
            
            if not institute_name:
                return JsonResponse({'error': 'Institute name is required'}, status=400)
            
            # Check if another institute already exists with the same name
            existing_institute = db.collection('InstituteNames')\
                .where('instituteName', '==', institute_name)\
                .limit(1)\
                .stream()
            
            existing_list = list(existing_institute)
            if existing_list and existing_list[0].id != institute_id:
                return JsonResponse({'error': 'Another institute with this name already exists'}, status=400)
            
            # Update institute
            institute_ref = db.collection('InstituteNames').document(institute_id)
            institute_ref.update({
                'instituteName': institute_name,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': 'Institute updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def parse_users_excel_to_json(dataframe):
    """Parse the uploaded Excel file to JSON for user creation."""
    users_data = []
    validation_errors = []
    
    for index, row in dataframe.iterrows():
        excel_row = index + 1
        
        # Validate required fields
        if pd.isna(row["Username"]) and pd.isna(row["Institute"]):
            validation_errors.append(f"Row {excel_row}: Both Username and Institute are missing")
            continue
        elif pd.isna(row["Username"]):
            validation_errors.append(f"Row {excel_row}: Username is missing")
            continue
        elif pd.isna(row["Institute"]):
            validation_errors.append(f"Row {excel_row}: Institute is missing")
            continue
            
        # Validate role
        role = str(row["Role"]).strip().lower() if not pd.isna(row["Role"]) else "student"
        if role not in ["student", "supervisor"]:
            role = "student"  # Default to student if invalid role
            
        user_data = {
            "username": str(row["Username"]).strip(),
            "emailID": str(row["EmailID"]).strip() if not pd.isna(row["EmailID"]) else "",
            "role": role,
            "institute_name": str(row["Institute"]).strip()
        }
        users_data.append(user_data)
    
    return users_data, validation_errors

def upload_users_excel_view(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            
            file_name = f"{uuid.uuid4()}_{uploaded_file.name}".replace(" ", "_")
            file_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_excels', file_name)
            print(file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            print(file_path)
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            print(file_path)

            try:
                df = pd.read_excel(file_path, header=None)  # Read without header to validate

                # Validate specific cells in row 1
                if not (
                    df.iloc[0, 0] == "Username" and
                    df.iloc[0, 1] == "EmailID" and
                    df.iloc[0, 2] == "Institute" and
                    df.iloc[0, 3] == "Role"  # Add Role column check
                ):
                    raise ValueError("Excel template is incorrect. Ensure first row contains 'Username', 'EmailID', 'Institute', 'Role'")

                # Process data from row 2 onward
                df_data = pd.read_excel(file_path, names=["Username", "EmailID", "Institute", "Role"])
                print(df_data)
                users_data, validation_errors = parse_users_excel_to_json(df_data)
                

                if validation_errors:
                    return JsonResponse({
                        "error": "Validation errors in Excel file",
                        "validation_errors": validation_errors
                    }, status=400)

                # Process each user
                created_users = []
                processing_errors = []
                
                for user_data in users_data:
                    try:
                        # Find institute (case insensitive)
                        institute_query = db.collection('InstituteNames').where(
                            'instituteName', '==', user_data['institute_name']
                        ).limit(1).stream()
                        
                        institute_doc = next(institute_query, None)
                        if not institute_doc:
                            processing_errors.append(f"Institute not found for user {user_data['username']}")
                            continue

                        # Create user document
                        user_ref = db.collection('Users').document()
                        user_ref.set({
                            "username": user_data['username'],
                            "emailID": user_data['emailID'],
                            "role": user_data['role'],
                            "institute": institute_doc.reference,
                            "cohort": None, # Will be updated when added to a batch,
                            "createdAt": firestore.SERVER_TIMESTAMP
                        })
                        
                        created_users.append(user_data['username'])

                    except Exception as e:
                        processing_errors.append(f"Error creating user {user_data['username']}: {str(e)}")

                response_data = {
                    "message": f"Processed {len(created_users)} users successfully",
                    "created_users": created_users
                }
                if processing_errors:
                    response_data["processing_errors"] = processing_errors

                return JsonResponse(response_data, status=200 if created_users else 400)

            except Exception as e:
                print(e)
                logger.error(f"Error processing file: {str(e)}")
                return JsonResponse({"error": str(e)}, status=400)
        else:
            print(form.errors)
            return JsonResponse({"error": form.errors}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def create_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            email_id = data.get('emailID', '').strip()
            institute_id = data.get('instituteId')
            role = data.get('role', 'student')

            if not username or not institute_id:
                return JsonResponse({'error': 'Username and Institute are required'}, status=400)

            # Check if username already exists
            existing_user = db.collection('Users')\
                .where('username', '==', username)\
                .limit(1)\
                .stream()
            
            if list(existing_user):
                return JsonResponse({'error': 'Username already exists'}, status=400)

            # Get institute reference
            institute_ref = db.collection('InstituteNames').document(institute_id)
            if not institute_ref.get().exists:
                return JsonResponse({'error': 'Institute not found'}, status=404)

            # Create new user with createdAt field
            new_user = {
                'username': username,
                'emailID': email_id,
                'role': role,
                'institute': institute_ref,
                'cohort': None,
                'createdAt': firestore.SERVER_TIMESTAMP  # Add creation timestamp
            }

            # Add to Firebase
            user_ref = db.collection('Users').add(new_user)

            return JsonResponse({
                'success': True,
                'id': user_ref[1].id,
                'message': 'User created successfully'
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def users_management(request):
    try:
        # Get query parameters
        query = request.GET.get("query", "")
        offset = int(request.GET.get("offset", 0))
        limit = int(request.GET.get("limit", 10))  # Use the limit from request
        is_load_more = request.GET.get("load_more") == "true"
        
        # Create base query
        users_ref = db.collection('Users')
        
        # Apply sorting (newest first)
        users_ref = users_ref.order_by('createdAt', direction=firestore.Query.DESCENDING)
        
        # For query we still need to fetch all and filter manually
        # since Firestore doesn't support complex text search
        if query:
            all_users = users_ref.stream()
            filtered_users = []
            
            # Manually filter by username or institute
            for doc in all_users:
                user_data = doc.to_dict()
                institute_ref = user_data.get('institute')
                institute_name = "Unknown"
                
                if institute_ref:
                    institute_doc = institute_ref.get()
                    if institute_doc.exists:
                        institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')
                
                # Apply text search
                if (query.lower() in user_data.get('username', '').lower() or 
                    query.lower() in institute_name.lower()):
                    filtered_users.append({
                        'id': doc.id,
                        'username': user_data.get('username', 'N/A'),
                        'emailID': user_data.get('emailID', 'N/A'),
                        'institute': institute_name,
                        'role': user_data.get('role', 'student'),
                        'createdAt': user_data.get('createdAt')
                    })
            
            # Apply offset and limit manually to filtered results
            total_count = len(filtered_users)
            users = filtered_users[offset:offset+limit]
            has_more = total_count > (offset + limit)
            
        else:
            # If no query, use Firestore's native offset and limit
            users_snapshot = users_ref.offset(offset).limit(limit).stream()
            
            # Count total for has_more calculation (can be optimized with a separate count query)
            total_query = users_ref.stream()
            total_count = sum(1 for _ in total_query)  # Count total documents
            
            # Process results
            users = []
            for doc in users_snapshot:
                user_data = doc.to_dict()
                institute_ref = user_data.get('institute')
                institute_name = "Unknown"
                
                if institute_ref:
                    institute_doc = institute_ref.get()
                    if institute_doc.exists:
                        institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')
                
                users.append({
                    'id': doc.id,
                    'username': user_data.get('username', 'N/A'),
                    'emailID': user_data.get('emailID', 'N/A'),
                    'institute': institute_name,
                    'role': user_data.get('role', 'student'),
                    'createdAt': user_data.get('createdAt')
                })
            
            has_more = total_count > (offset + limit)

        if is_load_more:
            return JsonResponse({
                "users": users,
                "has_more": has_more
            })

        return render(request, 'assessments/users_management.html', {
            "initial_users": users,
            "query": query,
        })

    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        if is_load_more:
            return JsonResponse({"error": str(e)}, status=500)
        return render(request, 'assessments/users_management.html', {
            "error": "Failed to fetch users",
            "initial_users": [],
            "query": query,
        })

@csrf_exempt
def edit_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('userId')
            username = data.get('username', '').strip()
            email_id = data.get('emailID', '').strip()
            institute_id = data.get('instituteId')
            role = data.get('role', 'student')  # Get role from request

            if not username or not institute_id:
                return JsonResponse({'error': 'Username and Institute are required'}, status=400)

            # Check if username already exists (excluding current user)
            existing_user = db.collection('Users')\
                .where('username', '==', username)\
                .stream()
            
            for user in existing_user:
                if user.id != user_id:  # If username exists for a different user
                    return JsonResponse({'error': 'Username already exists'}, status=400)

            # Get institute reference
            institute_ref = db.collection('InstituteNames').document(institute_id)
            if not institute_ref.get().exists:
                return JsonResponse({'error': 'Institute not found'}, status=404)

            # Update user
            user_ref = db.collection('Users').document(user_id)
            user_ref.update({
                'username': username,
                'emailID': email_id,
                'institute': institute_ref,
                'role': role  # Add role to update data
            })

            return JsonResponse({
                'success': True,
                'message': 'User updated successfully'
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def cohort_list(request):
    try:
        # Fetch cohorts from Firestore
        cohorts_ref = db.collection('Cohort')
        cohorts = []
        
        # Get search query if any
        query = request.GET.get("query", "")
        
        for doc in cohorts_ref.stream():
            cohort_data = doc.to_dict()
            
            # Get institutes
            institutes = []
            if 'instituteName' in cohort_data:
                institutes.append(cohort_data['instituteName'])
            
            # Get student count
            student_count = len(cohort_data.get('users', []))
            
            cohort = {
                'id': doc.id,
                'name': cohort_data.get('cohortName', 'N/A'),
                'institutes': ', '.join(institutes),
                'student_count': student_count
            }
            
            # Apply search filter if query exists
            if query:
                if query.lower() in cohort['name'].lower():
                    cohorts.append(cohort)
            else:
                cohorts.append(cohort)
        
        # Pagination
        paginator = Paginator(cohorts, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'assessments/cohort_list.html', {
            "page_obj": page_obj,
            "query": query,
        })
        
    except Exception as e:
        logger.error(f"Error fetching cohorts: {str(e)}")
        return render(request, 'assessments/cohort_list.html', {
            "error": "Failed to fetch cohorts",
            "page_obj": [],
            "query": query,
        })

@csrf_exempt
def fetch_institute_students(request):
    institute_id = request.GET.get('institute_id')
    if not institute_id:
        return JsonResponse({'error': 'Institute ID is required'}, status=400)
    
    try:
        institute_ref = db.collection('InstituteNames').document(institute_id)
        students_ref = db.collection('Users').where('institute', '==', institute_ref)
        
        students = []
        for doc in students_ref.stream():
            student_data = doc.to_dict()
            students.append({
                'id': doc.id,
                'username': student_data.get('username', 'N/A')
            })
        
        return JsonResponse({'students': students})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def create_cohort(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            student_ids = data.get('studentIds', [])
            
            if not name or not student_ids:
                return JsonResponse({'error': 'Name and student IDs are required'}, status=400)
            
            # Create student references
            student_refs = [db.collection('Users').document(sid) for sid in student_ids]
            
            # Get institute from first student (assuming all students are from same institute)
            first_student = db.collection('Users').document(student_ids[0]).get()
            institute_ref = first_student.to_dict().get('institute')
            
            # Create cohort
            cohort_ref = db.collection('Cohort').document()
            cohort_data = {
                'cohortName': name,
                'users': student_refs,
                'instituteName': institute_ref.get().to_dict().get('instituteName'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            
            cohort_ref.set(cohort_data)
            
            # Update each student's cohort reference
            for student_id in student_ids:
                db.collection('Users').document(student_id).update({
                    'cohort': cohort_ref
                })
            
            return JsonResponse({
                'success': True,
                'message': 'Cohort created successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def add_students_to_existing_exams(cohort_ref, student_refs):
    """Helper function to add students to all existing exams for a cohort."""
    # Get all tests for this cohort
    tests_ref = db.collection('Test').where('cohort', '==', cohort_ref).stream()
    
    for test in tests_ref:
        test_data = test.to_dict()
        procedure_assignments = test_data.get('procedureAssignments', [])
        
        # For each procedure assignment in the test
        for proc_assignment_ref in procedure_assignments:
            proc_assignment = proc_assignment_ref.get().to_dict()
            procedure_ref = proc_assignment.get('procedure')
            
            if procedure_ref:
                procedure_data = procedure_ref.get().to_dict()
                
                # Create exam assignments for new students
                for student_ref in student_refs:
                    exam_assignment_data = {
                        'user': student_ref,
                        'examMetaData': procedure_data.get('examMetaData', {}),
                        'status': 'Pending',
                        'notes': procedure_data.get('notes', ''),
                        'procedure_name': procedure_data.get('procedureName', '')
                    }
                    
                    # Create new exam assignment
                    exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                    
                    # Add to procedure assignment's examAssignmentArray
                    proc_assignment_ref.update({
                        'examAssignmentArray': firestore.ArrayUnion([exam_assignment_ref])
                    })

@csrf_exempt
def add_student_to_cohort(request, cohort_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_ids = data.get('studentIds', [])
            
            if not student_ids:
                return JsonResponse({'error': 'Student IDs are required'}, status=400)
            
            # Get cohort reference
            cohort_ref = db.collection('Cohort').document(cohort_id)
            cohort_doc = cohort_ref.get()
            
            if not cohort_doc.exists:
                return JsonResponse({'error': 'Cohort not found'}, status=404)
            
            # Get existing students in cohort
            cohort_data = cohort_doc.to_dict()
            existing_student_refs = cohort_data.get('users', [])
            existing_student_ids = [ref.id for ref in existing_student_refs]
            
            # Filter out students that are already in the cohort
            new_student_ids = [sid for sid in student_ids if sid not in existing_student_ids]
            
            if not new_student_ids:
                return JsonResponse({
                    'success': True,
                    'message': 'All students are already in this cohort'
                })
            
            # Create student references for only new students
            new_student_refs = [db.collection('Users').document(sid) for sid in new_student_ids]
            
            # Update cohort with new students
            cohort_ref.update({
                'users': firestore.ArrayUnion(new_student_refs)
            })
            
            # Update each student's cohort reference
            for student_id in new_student_ids:
                db.collection('Users').document(student_id).update({
                    'cohort': cohort_ref
                })
            
            # Add students to existing exams
            add_students_to_existing_exams(cohort_ref, new_student_refs)
            
            return JsonResponse({
                'success': True,
                'message': f'Added {len(new_student_ids)} new students to cohort successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def view_cohort_students(request, cohort_id):
    try:
        # Get cohort reference
        cohort_ref = db.collection('Cohort').document(cohort_id)
        cohort_doc = cohort_ref.get()
        
        if not cohort_doc.exists:
            return JsonResponse({'error': 'Cohort not found'}, status=404)
        
        cohort_data = cohort_doc.to_dict()
        cohort_name = cohort_data.get('cohortName', 'N/A')
        user_refs = cohort_data.get('users', [])
        
        # Get student details
        students = []
        for user_ref in user_refs:
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                institute_ref = user_data.get('institute')
                institute_name = "Unknown"
                
                if institute_ref:
                    institute_doc = institute_ref.get()
                    if institute_doc.exists:
                        institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')
                
                students.append({
                    'id': user_doc.id,
                    'username': user_data.get('username', 'N/A'),
                    'emailID': user_data.get('emailID', 'N/A'),
                    'institute': institute_name
                })
        
        # Sort students by username
        students.sort(key=lambda x: x['username'])
        
        # Pagination
        paginator = Paginator(students, 10)  # Show 10 students per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'assessments/view_cohort_students.html', {
            'cohort_id': cohort_id,
            'cohort_name': cohort_name,
            'page_obj': page_obj
        })
        
    except Exception as e:
        logger.error(f"Error viewing cohort students: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_cohort_students(request, cohort_id):
    try:
        # Get cohort reference
        cohort_ref = db.collection('Cohort').document(cohort_id)
        cohort_doc = cohort_ref.get()
        
        if not cohort_doc.exists:
            return JsonResponse({'error': 'Cohort not found'}, status=404)
        
        cohort_data = cohort_doc.to_dict()
        user_refs = cohort_data.get('users', [])
        
        # Get student details
        students = []
        for user_ref in user_refs:
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                students.append({
                    'id': user_doc.id,
                    'username': user_data.get('username', 'N/A')
                })
        
        return JsonResponse({'students': students})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def login_page(request):
    if request.user.is_authenticated:
        print(request.user.user_role)
        if request.user.user_role == 'ebek_admin' or request.user.user_role == 'super_admin':
            return redirect('exam_reports_page')
        else:
            return redirect('<html>Welcome to EBEK</html>')
    return render(request, 'assessments/login.html')

def login_view(request):
    logout(request)
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = authenticate(request, email=email, password=password)
    if user is not None:
        login(request, user)
            # Update last login in Firebase
        return redirect('exam_reports_page')
    else:
        messages.error(request, 'User not found')
        return redirect('login_page')
    
    return redirect('login_page')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login_page')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email or '@' not in email:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'assessments/forgot_password.html')

        try:
            user = EbekUser.objects.get(email=email)
        except EbekUser.DoesNotExist:
            messages.error(request, 'No user found with this email.')
            return render(request, 'assessments/forgot_password.html')

        # Create a new token
        token = PasswordResetToken.objects.create(user=user)
        reset_link = request.build_absolute_uri(
            reverse('reset_password', args=[str(token.token)])
        )

        # Send email
        send_email(
            'Password Reset Request',
            f'Click the link to reset your password: {reset_link}\nThis link is valid for 5 minutes.',
            [email],
        )
        messages.success(request, 'A password reset link has been sent to your email.')
        return render(request, 'assessments/forgot_password.html')

    return render(request, 'assessments/forgot_password.html')

def reset_password(request, token):
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid or expired reset link.')
        return render(request, 'assessments/reset_password.html', {'invalid': True})

    if not reset_token.is_valid():
        messages.error(request, 'This reset link has expired.')
        return render(request, 'assessments/reset_password.html', {'invalid': True})

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Password validation
        if not password1 or not password2:
            messages.error(request, 'Both password fields are required.')
            return render(request, 'assessments/reset_password.html', {'token': token})
            
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'assessments/reset_password.html', {'token': token})
            
        # Check password length
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'assessments/reset_password.html', {'token': token})
            
        # Check for uppercase letter
        if not any(char.isupper() for char in password1):
            messages.error(request, 'Password must contain at least one uppercase letter.')
            return render(request, 'assessments/reset_password.html', {'token': token})
            
        # Check for lowercase letter
        if not any(char.islower() for char in password1):
            messages.error(request, 'Password must contain at least one lowercase letter.')
            return render(request, 'assessments/reset_password.html', {'token': token})
            
        # Check for number
        if not any(char.isdigit() for char in password1):
            messages.error(request, 'Password must contain at least one number.')
            return render(request, 'assessments/reset_password.html', {'token': token})
            
        # Check for special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in password1):
            messages.error(request, 'Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?).')
            return render(request, 'assessments/reset_password.html', {'token': token})

        # If all validations pass, set new password
        user = reset_token.user
        user.set_password(password1)
        user.save()
        reset_token.is_used = True
        reset_token.save()
        messages.success(request, 'Your password has been reset. You can now log in.')
        return redirect('login_page')

    return render(request, 'assessments/reset_password.html', {'token': token})

@login_required
def onboarding_dashboard(request):
    return render(request, 'assessments/onboarding/onboarding_dashboard.html')

