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
from django.db.models import Count
from .utils_ses import *
from django.urls import reverse
from assessments.onboarding_views import *
from collections import defaultdict
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import xlsxwriter
from io import BytesIO

logger = logging.getLogger(__name__)

# Initialize Firestore client
from django.conf import settings
import os
from dotenv import load_dotenv

load_dotenv()
firebase_database = os.getenv('FIREBASE_DATABASE')

db = firestore.client(database_id=firebase_database)

def parse_excel_to_json(dataframe, procedure_name,category):
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
                "category": category,
                # "category": row["Category"] if pd.isna(row["Indicators"]) and not pd.isna(row["Category"]) else "",
                "critical": row["Critical"] == True if not pd.isna(row["Critical"]) else False  # Add critical flag
            }

        if not pd.isna(row["Indicators"]) and current_parameter:  # Check for Indicators
            current_parameter["sub_section_questions_present"] = True
            current_parameter["sub_section_questions"].append({
                "question": row["Indicators"],  # Indicators column
                "right_marks_for_question": float(row["Marks"]) if not pd.isna(row["Marks"]) else 0,
                "answer_scored": 0,
                "category": category,

                # "category": row["Category"] if not pd.isna(row["Category"]) else "",
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
            data.append(["Section", "Parameters", "Indicators", "Category (i.e C for Communication, K for Knowledge and D for Documentation)", "Marks", "Critical"])  # Column headers

            # Populate rows with exam metadata
            for section in exam_metadata:
                for question in section.get("section_questions", []):
                    # Add the main parameter row
                    parameter_row = [
                        section.get("section_name", ""),
                        question.get("question", ""),
                        "",  # Indicators will start on the same row
                        question.get("category", "") if not question.get("sub_section_questions_present", False) else "",
                        question.get("right_marks_for_question", 0) if not question.get("sub_section_questions_present", False) else "",
                        str(question.get("critical", False)).lower() if not question.get("sub_section_questions_present", False) else "",
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
                                data[-1][4] = indicator.get("right_marks_for_question", 0)  # Add marks
                                data[-1][5] = str(indicator.get("critical", False)).lower()  # Add critical
                            else:
                                # For subsequent indicators, create a new row
                                data.append([
                                    "",  # No Section
                                    "",  # No Parameter
                                    indicator.get("question", ""),
                                    indicator.get("category", ""),
                                    indicator.get("right_marks_for_question", 0),
                                    str(indicator.get("critical", False)).lower(),
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
    """Fetch institutes from both Django and Firebase, with optional B2B and unit_type filtering."""
    try:
        # Check if we need B2B filtering
        onboarding_type = request.GET.get('onboarding_type', '').lower()
        unit_type = request.GET.get('unit_type', '').lower()  # 'institution' or 'hospital'

        institutes = []

        if onboarding_type == 'b2b':
            # For B2B, fetch from Django Institution/Hospital models with B2B filtering

            # If unit_type is specified, only fetch that type
            if unit_type == 'institution':
                # Only fetch institutions
                django_institutions = Institution.objects.filter(
                    is_active=True,
                    onboarding_type='b2b'
                )

                for inst in django_institutions:
                    institutes.append({
                        'id': inst.id,
                        'instituteName': inst.name,
                        'type': 'institution'
                    })

            elif unit_type == 'hospital':
                # Only fetch hospitals
                django_hospitals = Hospital.objects.filter(
                    is_active=True,
                    onboarding_type='b2b'
                )

                for hosp in django_hospitals:
                    institutes.append({
                        'id': hosp.id,
                        'instituteName': hosp.name,
                        'type': 'hospital'
                    })
            else:
                # No unit_type specified, fetch both
                django_institutions = Institution.objects.filter(
                    is_active=True,
                    onboarding_type='b2b'
                )

                for inst in django_institutions:
                    institutes.append({
                        'id': inst.id,
                        'instituteName': inst.name,
                        'type': 'institution'
                    })

                # Also fetch B2B hospitals
                django_hospitals = Hospital.objects.filter(
                    is_active=True,
                    onboarding_type='b2b'
                )

                for hosp in django_hospitals:
                    institutes.append({
                        'id': hosp.id,
                        'instituteName': hosp.name,
                        'type': 'hospital'
                    })
        else:
            # Default behavior: fetch from Firebase InstituteNames collection
            institutes_ref = db.collection('InstituteNames')
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
        # First query: Get all ebek_admin users
        users_ref = db.collection('Users').where('role', '==', 'ebek_admin')
        print(users_ref)

        all_assessors = []
        all_assessor_ids = set()
        
        for doc in users_ref.stream():
            print(doc)
            user_data = doc.to_dict()
            all_assessors.append({
                'id': doc.id,
                'name': user_data.get('name', 'Unknown Assessor')
            })
            all_assessor_ids.add(doc.id)
        
        print(f"Found {len(all_assessors)} ebek_admin assessors")
        

        # Second query: Get users with institution/hospital if institution_id is provided
        if "institution_id" in request.GET:
            institution_id = request.GET.get('institution_id')
            unit_type = request.GET.get('unit_type', 'institution')  # Default to institution
            print(institution_id)
            print(f"Filtering by {unit_type}: {institution_id}")

            # Query from the correct collection based on unit_type
            if unit_type == 'hospital':
                unit_doc = db.collection('HospitalNames').document(institution_id).get()
                unit_name = unit_doc.to_dict().get('hospitalName', '') if unit_doc.exists else ''
            else:  # institution
                unit_doc = db.collection('InstituteNames').document(institution_id).get()
                unit_name = unit_doc.to_dict().get('institutionName', '') if unit_doc.exists else ''

            print(f"Unit name: {unit_name}")
            institution_name = unit_name  # Keep variable name for compatibility
            # Query 1: Users with institution in institutions_list
            users_in_institutions = db.collection('Users').where('institutions_list', 'array_contains', institution_name).stream()
            
            # Process first query
            for doc in users_in_institutions:
                if doc.id not in all_assessor_ids:  # Avoid duplicates
                    user_data = doc.to_dict()
                    institutions_list = user_data.get('institutions_list', [])
                    hospitals_list = user_data.get('hospitals_list', [])
                    
                    # Only add if lists are not empty
                    if institutions_list or hospitals_list:
                        all_assessor_ids.add(doc.id)
                        all_assessors.append({
                            'id': doc.id,
                            'name': user_data.get('name', 'Unknown User')
                        })
            
            # Query 2: Users with institution in hospitals_list
            users_in_hospitals = db.collection('Users').where('hospitals_list', 'array_contains', institution_name).stream()
            
            # Process second query (avoid duplicates)
            for doc in users_in_hospitals:
                if doc.id not in all_assessor_ids:
                    user_data = doc.to_dict()
                    institutions_list = user_data.get('institutions_list', [])
                    hospitals_list = user_data.get('hospitals_list', [])
                    
                    # Only add if lists are not empty
                    if institutions_list or hospitals_list:
                        all_assessor_ids.add(doc.id)
                        all_assessors.append({
                            'id': doc.id,
                            'name': user_data.get('name', 'Unknown User')
                        })
            
            print(f"Total assessors after filtering: {len(all_assessors)}")

        # Return combined list
        return JsonResponse({
            'assessors': all_assessors,
            'total_count': len(all_assessors)
        }, status=200)
        
    except Exception as e:
        print(f"Error: {str(e)}")
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

@csrf_exempt
def fetch_course_procedures(request, course_id):
    """API endpoint to fetch procedures for a specific course."""
    try:
        # Get the course document
        course_ref = db.collection('Courses').document(course_id)
        course_doc = course_ref.get()
        
        if not course_doc.exists:
            return JsonResponse({'success': False, 'error': 'Course not found'}, status=404)
        
        course_data = course_doc.to_dict()
        procedure_refs = course_data.get('procedures', [])
        
        # Get procedure details
        procedures = []
        for proc_ref in procedure_refs:
            proc_doc = proc_ref.get()
            if proc_doc.exists:
                proc_data = proc_doc.to_dict()
                procedures.append({
                    'id': proc_ref.id,
                    'name': proc_data.get('procedureName', 'Unknown')
                })
        
        return JsonResponse({
            'success': True,
            'procedures': procedures
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

import traceback
def create_procedure_assignment_and_test(request):
    if request.method == 'POST':
        try:
            data = request.POST
            print(data)
            
            # Parse required inputs
            test_type = data.get('test_type', 'B2C')
            batch_ids = [bid for bid in data.getlist('batch_ids', []) if bid]
            test_date = data.get('test_date', None)
            assessor_ids = [aid for aid in data.getlist('assessor_ids', []) if aid]
            skillathon_id = data.get('skillathon_id', None)
            course_id = data.get('course_id', None)
            exam_type = data.get('exam_type', 'final')
            institution_id = data.get('institution_id', None)
            unit_type = data.get('unit_type', None)  # 'institution' or 'hospital'

            
            
            # Parse inputs based on test type
            if test_type == 'B2B':
                # B2B: Use procedure-assessor mappings
                import json
                procedure_assessor_mappings_str = data.get('procedure_assessor_mappings', '[]')
                try:
                    raw_mappings = json.loads(procedure_assessor_mappings_str)
                    # Normalize and filter invalid mappings
                    procedure_assessor_mappings = []
                    for m in raw_mappings or []:
                        pid = (m.get('procedureId') or '').strip()
                        if not pid:
                            continue
                        assessor_list = [aid for aid in (m.get('assessorIds') or []) if aid]
                        procedure_assessor_mappings.append({
                            'procedureId': pid,
                            'procedureName': m.get('procedureName') or '',
                            'assessorIds': assessor_list,
                        })
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid procedure-assessor mappings format'}, status=400)
            else:
                # B2C: Use original procedure_ids and assessor_ids (legacy)
                procedure_ids = [pid for pid in data.getlist('procedure_ids') if pid]
                procedure_assessor_mappings = None  # Keep original logic for B2C

            # Convert test_date to datetime object
            if not test_date:
                return JsonResponse({'error': 'Test date is required'}, status=400)
            test_date_obj = datetime.strptime(test_date, '%Y-%m-%d')

            # Get current user (for now set to null as per your request)
            current_user = None  # Change this as needed based on your auth logic

            created_tests = []  # To store references for created tests

            if test_type == 'B2B':
                # B2B Workflow: Create batchassignment objects
                if not course_id:
                    return JsonResponse({'error': 'Course ID is required'}, status=400)
                if not institution_id:
                    return JsonResponse({'error': 'Institution/Hospital ID is required'}, status=400)
                if not unit_type or unit_type not in ['institution', 'hospital']:
                    return JsonResponse({'error': 'Unit type is required and must be either "institution" or "hospital"'}, status=400)
                if not batch_ids:
                    return JsonResponse({'error': 'At least one batch must be selected'}, status=400)
                if not procedure_assessor_mappings:
                    return JsonResponse({'error': 'At least one procedure must be selected'}, status=400)
                created_batchassignments = []
                created_examassignments_all = []
                try:
                    for batch_id in batch_ids:
                        # Fetch batch document
                        batch_ref = db.collection('Batches').document(batch_id)
                        batch_doc = batch_ref.get()
                        if not batch_doc.exists:
                            return JsonResponse({'error': f'Batch with ID {batch_id} does not exist.'}, status=404)

                        batch_data = batch_doc.to_dict()
                        learners = batch_data.get('learners', [])
                        
                        # Get course reference
                        course_ref = db.collection('Courses').document(course_id)
                        course_doc = course_ref.get()
                        if not course_doc.exists:
                            return JsonResponse({'error': f'Course with ID {course_id} does not exist.'}, status=404)
                        
                        # Get unit information based on unit_type
                        unit_ref = None
                        unit_name = None

                        try:
                            if unit_type == 'institution':
                                institution = Institution.objects.get(id=institution_id, is_active=True, onboarding_type='b2b')
                                unit_ref = db.collection('InstituteNames').document(str(institution.id))
                                unit_name = institution.name
                            elif unit_type == 'hospital':
                                hospital = Hospital.objects.get(id=institution_id, is_active=True, onboarding_type='b2b')
                                unit_ref = db.collection('HospitalNames').document(str(hospital.id))
                                unit_name = hospital.name
                        except (Institution.DoesNotExist, Hospital.DoesNotExist):
                            return JsonResponse({'error': f'{unit_type.title()} with ID {institution_id} does not exist.'}, status=404)
                    # Create batchassignment for each procedure with its specific assessors
                    processed_mappings = []  # Track successfully processed mappings
                    for mapping in procedure_assessor_mappings:
                        procedure_id = mapping.get('procedureId')
                        if not procedure_id:
                            continue
                        procedure_assessor_ids = [aid for aid in mapping.get('assessorIds', []) if aid]
                        if len(procedure_assessor_ids) == 0:
                            return JsonResponse({'error': f'Please select at least one assessor for procedure {mapping.get("procedureName") or procedure_id}'}, status=400)
                        
                        procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                        procedure_data = procedure_ref.get().to_dict()

                        if not procedure_data:
                            continue

                        # Create batchassignment object with procedure-specific assessors
                        batchassignment_data = {
                            'batch': batch_ref,
                            'course': course_ref,
                            'assessorlist': [db.collection('Users').document(str(aid)) for aid in procedure_assessor_ids],
                            'procedure': procedure_ref,
                            'examassignment': [],  # Will be populated with exam assignments for each learner
                            'examType': exam_type,
                            'testDate': test_date_obj,
                            'createdAt': datetime.now(),
                            'status': 'Pending',
                            'unitType': unit_type,  # "institution" or "hospital"
                            'unit': unit_ref,      # Reference to institution or hospital
                            'unit_name': unit_name, # Name of institution or hospital
                        }
                        
                        # Add year and semester from batch
                        year_of_batch = batch_data.get('yearOfBatch', '')
                        semester = batch_data.get('semester', '')
                        if year_of_batch:
                            batchassignment_data['yearOfBatch'] = year_of_batch
                        if semester:
                            batchassignment_data['semester'] = semester

                        batchassignment_ref = db.collection('BatchAssignment').add(batchassignment_data)[1]
                        created_batchassignments.append(batchassignment_ref)

                        # Create examassignment for each learner in the batch
                        exam_assignment_refs = []
                        for learner_ref in learners:
                            learner_doc = learner_ref.get()
                            if learner_doc.exists:
                                learner_data = learner_doc.to_dict()
                                
                                exam_assignment_data = {
                                    'user': learner_ref,
                                    'examMetaData': procedure_data.get('examMetaData', {}),
                                    'status': 'Pending',
                                    'notes': procedure_data.get('notes', ''),
                                    'procedure_name': procedure_data.get('procedureName', ''),
                                    'unitType': unit_type,  # "institution" or "hospital"
                                    'unit': unit_ref,      # Reference to institution or hospital
                                    'unit_name': unit_name, # Name of institution or hospital
                                    'examType': exam_type,
                                    'batchassignment': batchassignment_ref,
                                    'createdAt': datetime.now()
                                }
                                
                                exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                                exam_assignment_refs.append(exam_assignment_ref)
                                created_examassignments_all.append(exam_assignment_ref)

                        # Update batchassignment with exam assignments (avoid ArrayUnion on empty list)
                        if exam_assignment_refs:
                            batchassignment_ref.update({'examassignment': firestore.ArrayUnion(exam_assignment_refs)})
                        else:
                            batchassignment_ref.update({'examassignment': []})
                        mapping['batchassignment_id'] = batchassignment_ref.id
                        created_tests.append(batchassignment_ref.id)
                        # Track this successfully processed mapping
                        processed_mappings.append({
                            'procedure_id': mapping['procedureId'],
                            'procedure_name': mapping['procedureName'],
                            'assessor_ids': mapping['assessorIds'],
                            'batchassignment_id': batchassignment_ref.id
                        })

                    # Create a summary document after processing all mappings for this batch
                    if processed_mappings:
                        summary_data = {
                            'batch_id': batch_id,
                            'course_id': course_id,
                            'unit_id': institution_id,
                            'unitType': unit_type,  # "institution" or "hospital"
                            'unit_name': unit_name, # Name of institution or hospital
                            'exam_type': exam_type,
                            'test_date': test_date_obj,
                            'procedure_assessor_mappings': processed_mappings,
                            'created_at': datetime.now(),
                            'status': 'Not Completed',
                            'semester': semester,
                            'yearOfBatch': year_of_batch,
                        }
                        
                        # Create summary document
                        summary_ref = db.collection('BatchAssignmentSummary').add(summary_data)[1]
                        print(f"Created summary document: {summary_ref.id}")
                except Exception as e:
                    # Rollback any created refs if an error occurs
                    try:
                        for ref in created_examassignments_all:
                            try:
                                ref.delete()
                            except Exception:
                                pass
                        for ref in created_batchassignments:
                            try:
                                ref.delete()
                            except Exception:
                                pass
                    finally:
                        return JsonResponse({'error': str(e)}, status=500)

            else:
                # B2C Workflow: Original logic
                if batch_ids != []:
                    created_tests_refs = []
                    created_procassign_refs = []
                    created_examassign_refs = []
                    try:
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
                            created_tests_refs.append(test_ref)

                            # Create ProcedureAssignments
                            procedure_assignment_refs = []
                            for procedure_id in procedure_ids:
                                procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                                procedure_data = procedure_ref.get().to_dict()

                                if not procedure_data:
                                    continue

                                # Create ProcedureAssignment for each assessor
                                for assessor_id in assessor_ids:
                                    if not assessor_id:
                                        continue
                                    procedure_assignment_data = {
                                        'assignmentToBeDoneDate': test_date_obj,
                                        'cohort': cohort_ref,
                                        'cohortStudentExamTaken': 0,
                                        'creationDate': datetime.now(),
                                        'procedure': procedure_ref,
                                        'status': 'Pending',
                                        'typeOfTest': 'Classroom',
                                        'supervisor': db.collection('Users').document(str(assessor_id)),  # Now using current assessor
                                        'examAssignmentArray': [],
                                        'cohortStudentExamStarted': 0,
                                        'test': test_ref,
                                    }
                                    
                                    procedure_assignment_ref = db.collection('ProcedureAssignment').add(procedure_assignment_data)[1]
                                    procedure_assignment_refs.append(procedure_assignment_ref)
                                    created_procassign_refs.append(procedure_assignment_ref)

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

                                        try:
                                            user_data = user_snapshot.to_dict()
                                            exam_assignment_data['institute'] = user_data.get('institution', '')
                                        except (AttributeError, TypeError) as e:
                                            logger.warning(f"Failed to get institution for user {user_snapshot.id}: {str(e)}")
                                        
                                        exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                                        exam_assignment_refs.append(exam_assignment_ref)
                                        created_examassign_refs.append(exam_assignment_ref)

                                # Update ProcedureAssignment with exam assignments (avoid ArrayUnion on empty list)
                                if exam_assignment_refs:
                                    procedure_assignment_ref.update({'examAssignmentArray': firestore.ArrayUnion(exam_assignment_refs)})
                                else:
                                    procedure_assignment_ref.update({'examAssignmentArray': []})

                        # Update Test document with all procedure assignments (avoid ArrayUnion on empty list)
                        if procedure_assignment_refs:
                            test_ref.update({'procedureAssignments': firestore.ArrayUnion(procedure_assignment_refs)})
                        else:
                            test_ref.update({'procedureAssignments': []})

                            # Create CohortProcedureAssignments
                            for assessor_id in assessor_ids:
                                db.collection('CohortProcedureAssignments').add({
                                    'test': test_ref,
                                    'user': db.collection('Users').document(assessor_id),
                                    'typeOfTest': 'Classroom',
                                })
                    except Exception as e:
                        # Rollback created docs
                        try:
                            for ref in created_examassign_refs:
                                try:
                                    ref.delete()
                                except Exception:
                                    pass
                            for ref in created_procassign_refs:
                                try:
                                    ref.delete()
                                except Exception:
                                    pass
                            for ref in created_tests_refs:
                                try:
                                    ref.delete()
                                except Exception:
                                    pass
                        finally:
                            return JsonResponse({'error': str(e)}, status=500)
                else:
                    logger.info("Here in else")
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
                    logger.info(test_data)
                    # Safe create with rollback
                    test_ref = None
                    single_created_procassign_refs = []
                    single_created_examassign_refs = []
                    try:
                        test_ref = db.collection('Test').add(test_data)[1]
                        created_tests.append(test_ref.id)

                        procedure_assignment_refs = []
                        for procedure_id in procedure_ids:
                            try:
                                procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                                procedure_data = procedure_ref.get().to_dict()

                                logger.info("PROCEDURE DATA", procedure_data)

                                if not procedure_data:
                                    logger.info("NO PROCEDURE DATA")
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
                                single_created_procassign_refs.append(procedure_assignment_ref)

                                users = db.collection('Users').where("role", "in", ["student", "nurse"]).where("skillathon_event", "==", skillathon_name)

                                exam_assignment_refs = []
                                # for user_snapshot in users.stream():
                                #     exam_meta_data = procedure_data.get('examMetaData', {})
                                #     notes = procedure_data.get('notes', '')
                                #     procedure_name = procedure_data.get('procedureName', '')

                                #     exam_assignment_data = {
                                #         'user': user_snapshot.reference,  # Use the document reference instead of snapshot
                                #         'examMetaData': exam_meta_data,
                                #         'status': 'Pending',
                                #         'notes': notes,
                                #         'procedure_name': procedure_name,
                                #     }

                                #     try:
                                #         user_data = user_snapshot.to_dict()
                                #         exam_assignment_data['institute'] = user_data.get('institution', '')
                                #     except (AttributeError, TypeError) as e:
                                #         print(f"Failed to get institution for user {user_snapshot.id}: {str(e)}")
                                
                                #     exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                                #     exam_assignment_refs.append(exam_assignment_ref)

                                # # Update ProcedureAssignment with exam assignments
                                # procedure_assignment_ref.update({'examAssignmentArray': firestore.ArrayUnion(exam_assignment_refs)})

                            except Exception as e:
                                logger.error("ERROR IN ELSE", traceback.format_exc())
                                logger.error("ERROR IN ELSE", str(e))
                                # rollback
                                try:
                                    for ref in single_created_examassign_refs:
                                        try:
                                            ref.delete()
                                        except Exception:
                                            pass
                                    for ref in single_created_procassign_refs:
                                        try:
                                            ref.delete()
                                        except Exception:
                                            pass
                                    if test_ref:
                                        try:
                                            test_ref.delete()
                                        except Exception:
                                            pass
                                finally:
                                    return JsonResponse({'error': str(e)}, status=500)
                        # After processing all procedures, update Test with procedure assignments
                        if procedure_assignment_refs:
                            test_ref.update({'procedureAssignments': firestore.ArrayUnion(procedure_assignment_refs)})
                        else:
                            test_ref.update({'procedureAssignments': []})
                    except Exception as e:
                        # If creating the Test itself fails, return immediately
                        return JsonResponse({'error': str(e)}, status=500)

            return JsonResponse({'success': True, 'created_tests': created_tests})

        except Exception as e:
            print(str(e))
            logger.error(str(e))
            logger.error(traceback.format_exc())
            logger.error("HEEEREEEEEE")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

def assign_assessment(request):

    test_data = []
    
    # FETCH B2C ASSESSMENTS FROM 'Test' 
    try:
        tests_ref = db.collection('Test')
        tests = tests_ref.limit(100).stream()
        
        for test in tests:
            try:
                test_doc = test.to_dict()
                test_type = test_doc.get('type', 'B2C')
                skillathon = test_doc.get('skillathon', None)
                batch_name = test_doc.get('batchname', '')
                
                # Get procedures
                procedure_assignments = []
                assessors_list = []
                
                for proc_ref in test_doc.get('procedureAssignments', [])[:10]:
                    try:
                        proc_doc = proc_ref.get()
                        if proc_doc.exists:
                            proc_data = proc_doc.to_dict()
                            procedure_ref = proc_data.get('procedure')
                            procedure_name = "Unknown"
                            if procedure_ref:
                                try:
                                    procedure_doc = procedure_ref.get()
                                    if procedure_doc.exists:
                                        procedure_name = procedure_doc.to_dict().get('procedureName', 'Unknown')
                                except Exception:
                                    pass
                            
                            procedure_assignments.append({
                                'id': proc_ref.id,
                                'procedure_name': procedure_name,
                                'status': proc_data.get('status', 'Unknown'),
                            })
                            
                            # Get assessors for this procedure
                            if 'supervisors' in proc_data and isinstance(proc_data['supervisors'], list):
                                for sup_ref in proc_data['supervisors']:
                                    try:
                                        sup_doc = sup_ref.get()
                                        if sup_doc.exists:
                                            sup_data = sup_doc.to_dict()
                                            assessor_name = sup_data.get('name', sup_data.get('username', 'Assessor'))
                                            if assessor_name not in assessors_list:
                                                assessors_list.append(assessor_name)
                                    except Exception:
                                        pass
                    except Exception as e:
                        logger.error(f"Error loading procedure: {e}")
                        continue
                
                # Determine entity based on type
                entity = "-"
                if test_type == "B2C":
                    entity = skillathon or "Skillathon"
                else:
                    entity = test_doc.get('institution_name', batch_name or 'Institution')
                
                # Assessment name
                assessment_name = (
                    f"{batch_name or skillathon or 'Unknown'} - "
                    f"{test_doc.get('testdate').strftime('%d %b %Y') if test_doc.get('testdate') else ''}"
                )
                
                test_data.append({
                    'id': test.id,
                    'assessment_name': assessment_name,
                    'type': test_type,
                    'mode': test_doc.get('examType', 'Skillathon' if test_type == 'B2C' else 'Final OSCE'),
                    'entity': entity,
                    'batch': batch_name or '-',
                    'skillathon': skillathon,
                    'procedure_assignments': procedure_assignments,
                    'assessors': ', '.join(assessors_list) if assessors_list else '-',
                    'status': test_doc.get('status', 'Not Available'),
                    'testdate': test_doc.get('testdate'),
                })
            except Exception as e:
                logger.error(f"Error processing test: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error fetching B2C tests: {e}")
    
    # FETCH B2B ASSESSMENTS FROM 'BatchAssignmentSummary' (grouped)
    try:
        summary_ref = db.collection('BatchAssignmentSummary')
        summaries = summary_ref.limit(100).stream()

        for summary in summaries:
            try:
                summary_doc = summary.to_dict()

                # Get batch information
                batch_id = summary_doc.get('batch_id')
                batch_name = '-'
                if batch_id:
                    try:
                        batch_ref = db.collection('Batches').document(batch_id)
                        batch_doc = batch_ref.get()
                        if batch_doc.exists:
                            batch_name = batch_doc.to_dict().get('batchName', '-')
                    except Exception:
                        pass

                # Get unit (institution/hospital) information
                entity = summary_doc.get('unit_name', '-')
                unit_type = summary_doc.get('unitType', 'institution')

                # Get procedure and assessor information from mappings
                procedure_assessor_mappings = summary_doc.get('procedure_assessor_mappings', [])

                # Collect all procedures from the summary
                procedure_assignments = []
                all_assessors = set()

                for mapping in procedure_assessor_mappings:
                    procedure_name = mapping.get('procedure_name', 'Unknown')
                    batchassignment_id = mapping.get('batchassignment_id')

                    # Add procedure to list
                    if batchassignment_id:
                        # Check status from actual BatchAssignment
                        status = 'Pending'
                        try:
                            ba_ref = db.collection('BatchAssignment').document(batchassignment_id)
                            ba_doc = ba_ref.get()
                            if ba_doc.exists:
                                status = ba_doc.to_dict().get('status', 'Pending')
                        except Exception:
                            pass

                        procedure_assignments.append({
                            'id': batchassignment_id,
                            'procedure_name': procedure_name,
                            'status': status,
                        })

                    # Collect assessors for this procedure
                    assessor_ids = mapping.get('assessor_ids', [])
                    for assessor_id in assessor_ids:
                        try:
                            assessor_ref = db.collection('Users').document(str(assessor_id))
                            assessor_doc = assessor_ref.get()
                            if assessor_doc.exists:
                                assessor_data = assessor_doc.to_dict()
                                assessor_name = (
                                    assessor_data.get('full_name') or
                                    assessor_data.get('name') or
                                    assessor_data.get('username', 'Assessor')
                                )
                                all_assessors.add(assessor_name)
                        except Exception as e:
                            logger.error(f"Error fetching assessor: {e}")
                            pass

                # Get exam type and test date from summary
                exam_type = summary_doc.get('exam_type', 'Final')
                test_date = summary_doc.get('test_date')

                # Assessment name
                assessment_name = (
                    f"{batch_name} - "
                    f"{test_date.strftime('%d %b %Y') if test_date else ''}"
                )

                # Determine overall status
                status = summary_doc.get('status', 'Active')

                test_data.append({
                    'id': summary.id,
                    'assessment_name': assessment_name,
                    'type': 'B2B',
                    'mode': exam_type,
                    'entity': entity,
                    'batch': batch_name,
                    'skillathon': None,
                    'procedure_assignments': procedure_assignments,
                    'assessors': ', '.join(sorted(all_assessors)) if all_assessors else '-',
                    'status': status,
                    'testdate': test_date,
                    'is_summary': True,  # Flag to indicate this is a summary entry
                })
            except Exception as e:
                logger.error(f"Error processing batch assignment summary: {e}")
                continue

    except Exception as e:
        logger.error(f"Error fetching B2B batch assignment summaries: {e}")
    
    # Sort by test date (most recent first)
    # Handle timezone-aware and timezone-naive datetime comparison
    def get_comparable_date(test_item):
        test_date = test_item.get('testdate')
        if test_date is None:
            return datetime.min
        # Convert timezone-aware datetime to naive for comparison
        if hasattr(test_date, 'tzinfo') and test_date.tzinfo is not None:
            return test_date.replace(tzinfo=None)
        return test_date
    
    try:
        test_data.sort(key=get_comparable_date, reverse=True)
    except Exception as e:
        logger.error(f"Error sorting test data: {e}")
        # If sorting fails, just keep the original order
        pass
    
    # No pagination: show all, newest first
    page_obj = test_data
    
    return render(request, 'assessments/assign_assessment.html', {
        "page_obj": page_obj,
        "query": request.GET.get("query", ""),
    })
    
    # No pagination: show all, newest first
    page_obj = test_data
    
    return render(request, 'assessments/assign_assessment.html', {
        "page_obj": page_obj,
        "query": request.GET.get("query", ""),
    })

@csrf_exempt
def get_test(request, test_id):
    """Return consolidated details for a Test including procedures and assessors."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)
    try:
        if not test_id:
            print(test_id)
            return JsonResponse({'error': 'Test ID is required'}, status=400)
        
        test_ref = db.collection('Test').document(test_id)
        test_doc = test_ref.get()
        if not test_doc.exists:
            return JsonResponse({'error': 'Test not found'}, status=404)
        
        test_data = test_doc.to_dict()
        if not test_data:
            return JsonResponse({'error': 'Test data is empty'}, status=404)

        # Process procedure-assessor mappings
        procedure_assessor_mappings = []
        all_assessors_map = {}

        # Safely get procedureAssignments
        procedure_assignments = test_data.get('procedureAssignments', []) or []
        if not isinstance(procedure_assignments, list):
            procedure_assignments = []

        for proc_ref in procedure_assignments:
            if not proc_ref:
                continue
            try:
                proc_doc = proc_ref.get()
                if not proc_doc.exists:
                    continue
                proc_data = proc_doc.to_dict()
                if not proc_data:
                    continue

                # Get procedure details
                procedure_ref = proc_data.get('procedure')
                procedure_id = None
                procedure_name = 'Unknown'

                if procedure_ref:
                    try:
                        pdoc = procedure_ref.get()
                        if pdoc.exists:
                            pdata = pdoc.to_dict()
                            if pdata:
                                procedure_id = procedure_ref.id
                                procedure_name = pdata.get('procedureName', 'Unknown')
                    except Exception as e:
                        # If procedure fetch fails, continue without it
                        continue

                # Supervisors can be single 'supervisor' or list 'supervisors'
                sup_list = []
                if 'supervisors' in proc_data and isinstance(proc_data['supervisors'], list):
                    sup_list = [s for s in proc_data['supervisors'] if s]  # Filter out None values
                elif 'supervisor' in proc_data:
                    sup = proc_data.get('supervisor')
                    if sup:
                        sup_list = [sup]

                # Get assessors for this procedure
                procedure_assessors = []
                assessor_ids = []
                for sref in sup_list:
                    if not sref:
                        continue
                    try:
                        sdoc = sref.get()
                        if sdoc.exists:
                            sdata = sdoc.to_dict()
                            if sdata:
                                assessor_id = sref.id
                                assessor_name = (
                                    sdata.get('full_name') or
                                    sdata.get('name') or
                                    sdata.get('username', 'Assessor')
                                )
                                procedure_assessors.append({
                                    'id': assessor_id,
                                    'name': assessor_name
                                })
                                assessor_ids.append(assessor_id)
                                all_assessors_map[assessor_id] = {
                                    'id': assessor_id,
                                    'name': assessor_name
                                }
                    except Exception as e:
                        # If assessor fetch fails, continue without it
                        continue

                # Add to procedure-assessor mappings
                if procedure_id:
                    procedure_assessor_mappings.append({
                        'procedure_id': procedure_id,
                        'procedure_name': procedure_name,
                        'procedureassignment_id': proc_ref.id,
                        'assessor_ids': assessor_ids,
                        'assessors': procedure_assessors
                    })

            except Exception as e:
                # If procedure assignment processing fails, continue to next one
                continue

        # Safely format date
        testdate_str = None
        try:
            testdate = test_data.get('testdate')
            if testdate:
                if hasattr(testdate, 'strftime'):
                    testdate_str = testdate.strftime('%Y-%m-%d')
                elif isinstance(testdate, str):
                    testdate_str = testdate
        except Exception as e:
            # If date formatting fails, leave it as None
            testdate_str = None

        response = {
            'id': test_id,
            'assessment_name': test_data.get('batchname') or test_data.get('skillathon') or '',
            'status': test_data.get('status', 'Not Completed'),
            'testdate': testdate_str,
            'procedure_assessor_mappings': procedure_assessor_mappings,
            'assessors': list(all_assessors_map.values()),
            'skillathon': test_data.get('skillathon') or '',
            'examType': test_data.get('examType', 'Classroom')
        }
        return JsonResponse({'success': True, 'data': response})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in get_test: {str(e)}\n{error_trace}")
        return JsonResponse({'error': 'Failed to retrieve test data. Please try again.'}, status=500)

@csrf_exempt
def get_batch_assignment_summary(request, summary_id):
    """Return consolidated details for a BatchAssignmentSummary including procedures and assessors."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)
    try:
        if not summary_id:
            return JsonResponse({'error': 'Summary ID is required'}, status=400)

        summary_ref = db.collection('BatchAssignmentSummary').document(summary_id)
        summary_doc = summary_ref.get()
        if not summary_doc.exists:
            return JsonResponse({'error': 'Batch assignment summary not found'}, status=404)

        summary_data = summary_doc.to_dict()
        if not summary_data:
            return JsonResponse({'error': 'Summary data is empty'}, status=404)

        # Get batch information
        batch_id = summary_data.get('batch_id')
        batch_name = ''
        if batch_id:
            try:
                batch_ref = db.collection('Batches').document(batch_id)
                batch_doc = batch_ref.get()
                if batch_doc.exists:
                    batch_name = batch_doc.to_dict().get('batchName', '')
            except Exception:
                pass

        # Get unit information
        unit_name = summary_data.get('unit_name', '')
        unit_type = summary_data.get('unitType', 'institution')
        unit_id = summary_data.get('unit_id','')

        # Get course information
        course_id = summary_data.get('course_id')
        course_name = ''
        if course_id:
            try:
                course_ref = db.collection('Courses').document(course_id)
                course_doc = course_ref.get()
                if course_doc.exists:
                    course_name = course_doc.to_dict().get('courseName', '')
            except Exception:
                pass

        # Process procedure-assessor mappings
        procedure_assessor_mappings = summary_data.get('procedure_assessor_mappings', []) or []

        procedures_with_assessors = []
        all_assessors_map = {}

        for mapping in procedure_assessor_mappings:
            procedure_id = mapping.get('procedure_id')
            procedure_name = mapping.get('procedure_name', 'Unknown')
            assessor_ids = mapping.get('assessor_ids', [])
            batchassignment_id = mapping.get('batchassignment_id')

            # Collect assessors for this procedure
            procedure_assessors = []
            for assessor_id in assessor_ids:
                try:
                    assessor_ref = db.collection('Users').document(str(assessor_id))
                    assessor_doc = assessor_ref.get()
                    if assessor_doc.exists:
                        assessor_data = assessor_doc.to_dict()
                        assessor_name = (
                            assessor_data.get('full_name') or
                            assessor_data.get('name') or
                            assessor_data.get('username', 'Assessor')
                        )
                        procedure_assessors.append({
                            'id': str(assessor_id),
                            'name': assessor_name
                        })
                        # Add to global assessors map
                        all_assessors_map[str(assessor_id)] = {
                            'id': str(assessor_id),
                            'name': assessor_name
                        }
                except Exception as e:
                    logger.error(f"Error fetching assessor {assessor_id}: {e}")
                    continue

            procedures_with_assessors.append({
                'procedure_id': procedure_id,
                'procedure_name': procedure_name,
                'batchassignment_id': batchassignment_id,
                'assessors': procedure_assessors
            })

        # Format date
        testdate_str = None
        try:
            testdate = summary_data.get('test_date')
            if testdate:
                if hasattr(testdate, 'strftime'):
                    testdate_str = testdate.strftime('%Y-%m-%d')
                elif isinstance(testdate, str):
                    testdate_str = testdate
        except Exception:
            testdate_str = None

        response = {
            'id': summary_id,
            'batch_id': batch_id,
            'batch_name': batch_name,
            'course_id': course_id,
            'course_name': course_name,
            'unit_id': unit_id,
            'unit_name': unit_name,
            'unit_type': unit_type,
            'exam_type': summary_data.get('exam_type', 'Final'),
            'status': summary_data.get('status', 'Active'),
            'testdate': testdate_str,
            'semester': summary_data.get('semester', ''),
            'yearOfBatch': summary_data.get('yearOfBatch', ''),
            'procedure_assessor_mappings': procedures_with_assessors,
            'assessors': list(all_assessors_map.values()),
        }
        return JsonResponse({'success': True, 'summary': response})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in get_batch_assignment_summary: {str(e)}\n{error_trace}")
        return JsonResponse({'error': 'Failed to retrieve batch assignment summary. Please try again.'}, status=500)

@csrf_exempt
def delete_test(request, test_id):
    """Delete a Test and its nested ProcedureAssignment and ExamAssignment documents."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        test_ref = db.collection('Test').document(test_id)
        test_doc = test_ref.get()
        if not test_doc.exists:
            return JsonResponse({'error': 'Test not found'}, status=404)

        test_data = test_doc.to_dict()
        proc_refs = test_data.get('procedureAssignments', []) or []
        # Delete children first
        for proc_ref in proc_refs:
            try:
                proc_doc = proc_ref.get()
                if proc_doc.exists:
                    proc_data = proc_doc.to_dict()
                    exam_refs = proc_data.get('examAssignmentArray', []) or []
                    for exam_ref in exam_refs:
                        try:
                            exam_ref.delete()
                        except Exception:
                            pass
                proc_ref.delete()
            except Exception:
                pass

        # Finally delete test
        test_ref.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_batch_assignment(request, ba_id):
    """Delete a BatchAssignment document (B2B assessment)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        ba_ref = db.collection('BatchAssignment').document(ba_id)
        ba_doc = ba_ref.get()
        if not ba_doc.exists:
            return JsonResponse({'error': 'Batch assignment not found'}, status=404)

        # If BatchAssignment contains nested references you want to clean up,
        # do it here. For now, delete the document.
        ba_ref.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_batch_assignment_summary(request, summary_id):
    """Delete a BatchAssignmentSummary and all associated BatchAssignments and ExamAssignments."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        summary_ref = db.collection('BatchAssignmentSummary').document(summary_id)
        summary_doc = summary_ref.get()
        if not summary_doc.exists:
            return JsonResponse({'error': 'Batch assignment summary not found'}, status=404)

        summary_data = summary_doc.to_dict()

        # Get all BatchAssignment IDs from procedure_assessor_mappings
        procedure_assessor_mappings = summary_data.get('procedure_assessor_mappings', [])

        # Delete all associated BatchAssignments and their ExamAssignments
        for mapping in procedure_assessor_mappings:
            ba_id = mapping.get('batchassignment_id')
            if ba_id:
                try:
                    ba_ref = db.collection('BatchAssignment').document(ba_id)
                    ba_doc = ba_ref.get()
                    if ba_doc.exists:
                        ba_data = ba_doc.to_dict()

                        # Delete ExamAssignments first
                        exam_refs = ba_data.get('examassignment', []) or []
                        for exam_ref in exam_refs:
                            try:
                                exam_ref.delete()
                            except Exception:
                                pass

                        # Delete BatchAssignment
                        ba_ref.delete()
                except Exception as e:
                    logger.error(f"Error deleting BatchAssignment {ba_id}: {e}")
                    pass

        # Note: We intentionally do NOT delete UnitMetrics or SemesterMetrics here.
        # Multiple exam types (Mock, Final, etc.) for the same batch/semester share the same metrics.
        # Deleting metrics when removing one exam type would incorrectly remove data for other exams.

        # Finally delete the summary document
        summary_ref.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in delete_batch_assignment_summary: {str(e)}\n{error_trace}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def update_test(request, test_id):
    """Update Test fields: testdate, status, procedures, and assessors (B2C)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        body = json.loads(request.body or '{}')
        testdate_str = body.get('testdate')
        status_val = body.get('status')
        procedure_ids = body.get('procedure_ids', [])
        assessor_ids = body.get('assessor_ids', [])

        test_ref = db.collection('Test').document(test_id)
        test_doc = test_ref.get()
        if not test_doc.exists:
            return JsonResponse({'error': 'Test not found'}, status=404)

        test_data = test_doc.to_dict()
        update_payload = {}

        # Update test date
        if testdate_str:
            try:
                new_date = datetime.strptime(testdate_str, '%Y-%m-%d')
                update_payload['testdate'] = new_date
            except Exception:
                return JsonResponse({'error': 'Invalid date format, expected YYYY-MM-DD'}, status=400)

        # Update status
        if status_val:
            update_payload['status'] = status_val

        if update_payload:
            test_ref.update(update_payload)

        # Handle procedure and assessor updates if provided
        if procedure_ids is not None:
            logger.info(f"[B2C Update] Received procedure_ids: {procedure_ids}, assessor_ids: {assessor_ids}")

            # Get test date for ProcedureAssignments
            test_date_obj = test_data.get('testdate')
            if testdate_str:
                try:
                    test_date_obj = datetime.strptime(testdate_str, '%Y-%m-%d')
                except Exception:
                    pass

            # Get learners for this skillathon event
            skillathon_name = test_data.get('skillathon')
            learner_refs = []
            logger.info(f"[B2C Update] Skillathon name: {skillathon_name}")

            if skillathon_name:
                try:
                    learners_query = db.collection('Learners').where('skillathon_event', '==', skillathon_name).stream()
                    for learner_doc in learners_query:
                        learner_refs.append(learner_doc.reference)
                    logger.info(f"[B2C Update] Found {len(learner_refs)} learners for skillathon")
                except Exception as e:
                    logger.error(f"Error fetching learners for skillathon {skillathon_name}: {e}")

            # Get existing ProcedureAssignments and build a map
            existing_proc_refs = test_data.get('procedureAssignments', []) or []
            existing_proc_map = {}  # Maps procedure_id to ProcedureAssignment ref

            for proc_ref in existing_proc_refs:
                try:
                    proc_doc = proc_ref.get()
                    if proc_doc.exists:
                        proc_data = proc_doc.to_dict()
                        procedure_ref = proc_data.get('procedure')
                        if procedure_ref:
                            existing_proc_map[procedure_ref.id] = proc_ref
                except Exception:
                    continue

            # Determine which procedures to add and which to remove
            new_procedure_ids = set(str(pid) for pid in procedure_ids)
            existing_procedure_ids = set(existing_proc_map.keys())

            procedures_to_add = new_procedure_ids - existing_procedure_ids
            procedures_to_remove = existing_procedure_ids - new_procedure_ids
            procedures_to_keep = new_procedure_ids & existing_procedure_ids

            logger.info(f"[B2C Update] Procedures - Add: {procedures_to_add}, Remove: {procedures_to_remove}, Keep: {procedures_to_keep}")

            new_proc_refs = []

            # Update assessors for existing procedures that are kept
            for proc_id in procedures_to_keep:
                proc_ref = existing_proc_map[proc_id]
                try:
                    proc_ref.update({
                        'supervisors': [db.collection('Users').document(str(aid)) for aid in assessor_ids]
                    })
                    new_proc_refs.append(proc_ref)
                except Exception as e:
                    logger.error(f"Error updating ProcedureAssignment: {e}")

            # Add new procedures
            for proc_id in procedures_to_add:
                try:
                    logger.info(f"[B2C Update] Adding procedure with ID: {proc_id}")
                    procedure_ref = db.collection('ProcedureTable').document(proc_id)
                    procedure_doc = procedure_ref.get()
                    if not procedure_doc.exists:
                        logger.warning(f"[B2C Update] Procedure {proc_id} does not exist in ProcedureTable")
                        continue

                    procedure_data = procedure_doc.to_dict()
                    if not procedure_data:
                        logger.warning(f"[B2C Update] Procedure {proc_id} has no data")
                        continue

                    logger.info(f"[B2C Update] Found procedure: {procedure_data.get('procedureName', 'Unknown')}")

                    # Create new ProcedureAssignment
                    proc_assignment_data = {
                        'assignmentToBeDoneDate': test_date_obj,
                        'creationDate': datetime.now(),
                        'procedure': procedure_ref,
                        'status': 'Pending',
                        'typeOfTest': test_data.get('examType', 'Classroom'),
                        'supervisors': [db.collection('Users').document(str(aid)) for aid in assessor_ids],
                        'examAssignmentArray': [],
                        'cohortStudentExamStarted': 0,
                        'test': test_ref,
                    }
                    proc_assignment_ref = db.collection('ProcedureAssignment').add(proc_assignment_data)[1]
                    logger.info(f"[B2C Update] Created ProcedureAssignment: {proc_assignment_ref.id}")

                    # Create ExamAssignments for each learner
                    exam_assignment_refs = []
                    logger.info(f"[B2C Update] Creating ExamAssignments for {len(learner_refs)} learners")
                    for learner_ref in learner_refs:
                        try:
                            learner_doc = learner_ref.get()
                            if not learner_doc.exists:
                                continue

                            learner_data = learner_doc.to_dict()
                            learner_user_ref = learner_data.get('learner_user')
                            if not learner_user_ref:
                                continue

                            exam_assignment_data = {
                                'user': learner_user_ref,
                                'examMetaData': procedure_data.get('examMetaData', {}),
                                'status': 'Pending',
                                'notes': procedure_data.get('notes', ''),
                                'procedure_name': procedure_data.get('procedureName', ''),
                            }

                            # Get institution from learner
                            institution = learner_data.get('college') or learner_data.get('hospital')
                            if institution:
                                try:
                                    inst_doc = institution.get()
                                    if inst_doc.exists:
                                        inst_data = inst_doc.to_dict()
                                        exam_assignment_data['institute'] = inst_data.get('institutionName') or inst_data.get('hospitalName', '')
                                except Exception:
                                    pass

                            exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                            exam_assignment_refs.append(exam_assignment_ref)
                        except Exception as e:
                            logger.error(f"Error creating ExamAssignment: {e}")
                            continue

                    # Update ProcedureAssignment with exam assignments
                    if exam_assignment_refs:
                        proc_assignment_ref.update({'examAssignmentArray': firestore.ArrayUnion(exam_assignment_refs)})
                        logger.info(f"[B2C Update] Created {len(exam_assignment_refs)} ExamAssignments for procedure {proc_id}")
                    else:
                        logger.warning(f"[B2C Update] No ExamAssignments created for procedure {proc_id}")

                    new_proc_refs.append(proc_assignment_ref)
                except Exception as e:
                    logger.error(f"Error adding procedure {proc_id}: {e}")
                    continue

            # Delete removed procedures
            for proc_id in procedures_to_remove:
                proc_ref = existing_proc_map[proc_id]
                try:
                    proc_doc = proc_ref.get()
                    if proc_doc.exists:
                        proc_data = proc_doc.to_dict()
                        # Delete associated ExamAssignments
                        for exam_ref in proc_data.get('examAssignmentArray', []) or []:
                            try:
                                exam_ref.delete()
                            except Exception:
                                pass
                    proc_ref.delete()
                except Exception as e:
                    logger.error(f"Error deleting ProcedureAssignment: {e}")

            # Update Test with new procedure list
            if new_proc_refs:
                test_ref.update({'procedureAssignments': new_proc_refs})

        return JsonResponse({'success': True})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in update_test: {str(e)}\n{error_trace}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def update_batch_assignment_summary(request, summary_id):
    """Update BatchAssignmentSummary fields: test_date, status, and procedure-assessor mappings."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        body = json.loads(request.body or '{}')
        testdate_str = body.get('testdate')
        status_val = body.get('status')
        procedure_assessor_mappings = body.get('procedure_assessor_mappings', [])

        summary_ref = db.collection('BatchAssignmentSummary').document(summary_id)
        summary_doc = summary_ref.get()
        if not summary_doc.exists:
            return JsonResponse({'error': 'Batch assignment summary not found'}, status=404)

        summary_data = summary_doc.to_dict()
        update_payload = {}

        # Update test date
        if testdate_str:
            try:
                new_date = datetime.strptime(testdate_str, '%Y-%m-%d')
                update_payload['test_date'] = new_date
            except Exception:
                return JsonResponse({'error': 'Invalid date format, expected YYYY-MM-DD'}, status=400)

        # Update status
        if status_val:
            update_payload['status'] = status_val

        # Apply basic updates
        if update_payload:
            summary_ref.update(update_payload)

        # Handle procedure-assessor mappings updates
        if procedure_assessor_mappings:
            old_mappings = summary_data.get('procedure_assessor_mappings', [])

            # Create a map of old batchassignments to potentially delete
            old_ba_ids = {m.get('batchassignment_id') for m in old_mappings if m.get('batchassignment_id')}

            # Process new mappings
            new_processed_mappings = []
            batch_id = summary_data.get('batch_id')
            course_id = summary_data.get('course_id')
            unit_id = summary_data.get('unit_id')
            unit_type = summary_data.get('unitType', 'institution')
            unit_name = summary_data.get('unit_name', '')
            exam_type = summary_data.get('exam_type', 'Final')
            year_of_batch = summary_data.get('yearOfBatch', '')
            semester = summary_data.get('semester', '')

            # Get references
            batch_ref = db.collection('Batches').document(batch_id)
            course_ref = db.collection('Courses').document(course_id)

            # Determine unit reference based on type
            if unit_type == 'hospital':
                unit_ref = db.collection('Hospitals').document(unit_id)
            else:
                unit_ref = db.collection('Institutions').document(unit_id)

            # Get test date for BatchAssignments
            test_date_obj = summary_data.get('test_date')
            if testdate_str:
                try:
                    test_date_obj = datetime.strptime(testdate_str, '%Y-%m-%d')
                except Exception:
                    pass

            # Get learners from batch
            batch_doc = batch_ref.get()
            learners = []
            if batch_doc.exists:
                learners = batch_doc.to_dict().get('learners', [])

            logger.info(f"[B2B Edit] Batch ID: {batch_id}, Learners count: {len(learners)}")

            # For each procedure-assessor mapping
            logger.info(f"[B2B Edit] Processing {len(procedure_assessor_mappings)} procedure-assessor mappings")
            for mapping in procedure_assessor_mappings:
                procedure_id = mapping.get('procedure_id')
                assessor_ids = mapping.get('assessor_ids', [])
                old_ba_id = mapping.get('batchassignment_id') or None  # Convert empty string to None
                logger.info(f"[B2B Edit] Processing mapping - procedure_id: {procedure_id}, old_ba_id: {old_ba_id}, assessor_ids: {assessor_ids}")

                # Get procedure data
                procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                procedure_doc = procedure_ref.get()
                procedure_data = procedure_doc.to_dict() if procedure_doc.exists else {}

                # Check if we can reuse existing BatchAssignment
                batchassignment_ref = None
                if old_ba_id:
                    # Try to update existing BatchAssignment
                    try:
                        ba_ref = db.collection('BatchAssignment').document(old_ba_id)
                        ba_doc = ba_ref.get()
                        if ba_doc.exists:
                            # Update assessorlist and testDate
                            ba_ref.update({
                                'assessorlist': [db.collection('Users').document(str(aid)) for aid in assessor_ids],
                                'testDate': test_date_obj,
                            })
                            batchassignment_ref = ba_ref
                            # Remove from deletion list
                            old_ba_ids.discard(old_ba_id)
                    except Exception as e:
                        logger.error(f"Error updating existing BatchAssignment: {e}")

                # If no existing BA or update failed, create new one
                if not batchassignment_ref:
                    logger.info(f"[B2B Edit] Creating new BatchAssignment for procedure_id: {procedure_id}, assessor count: {len(assessor_ids)}")

                    # Create new BatchAssignment
                    batchassignment_data = {
                        'batch': batch_ref,
                        'course': course_ref,
                        'assessorlist': [db.collection('Users').document(str(aid)) for aid in assessor_ids],
                        'procedure': procedure_ref,
                        'examassignment': [],
                        'examType': exam_type,
                        'testDate': test_date_obj,
                        'createdAt': datetime.now(),
                        'status': 'Pending',
                        'unitType': unit_type,
                        'unit': unit_ref,
                        'unit_name': unit_name,
                        'yearOfBatch': year_of_batch,
                        'semester': semester,
                    }
                    batchassignment_ref = db.collection('BatchAssignment').add(batchassignment_data)[1]
                    logger.info(f"[B2B Edit] Created BatchAssignment: {batchassignment_ref.id}")

                    # Create ExamAssignments for each learner
                    exam_assignment_refs = []
                    logger.info(f"[B2B Edit] Creating ExamAssignments for {len(learners)} learners")
                    for learner_ref in learners:
                        exam_assignment_data = {
                            'user': learner_ref,
                            'examMetaData': procedure_data.get('examMetaData', {}),
                            'status': 'Pending',
                            'procedure_name': procedure_data.get('procedureName', ''),
                            'unitType': unit_type,
                            'unit': unit_ref,
                            'unit_name': unit_name,
                            'examType': exam_type,
                            'batchassignment': batchassignment_ref,
                            'createdAt': datetime.now()
                        }
                        exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                        exam_assignment_refs.append(exam_assignment_ref)

                    logger.info(f"[B2B Edit] Created {len(exam_assignment_refs)} ExamAssignments")

                    # Update BatchAssignment with ExamAssignments
                    if exam_assignment_refs:
                        batchassignment_ref.update({'examassignment': firestore.ArrayUnion(exam_assignment_refs)})
                        logger.info(f"[B2B Edit] Updated BatchAssignment with {len(exam_assignment_refs)} ExamAssignment references")

                # Add to new mappings
                new_processed_mappings.append({
                    'procedure_id': procedure_id,
                    'procedure_name': procedure_data.get('procedureName', 'Unknown'),
                    'assessor_ids': assessor_ids,
                    'batchassignment_id': batchassignment_ref.id
                })

            # Delete orphaned BatchAssignments
            for old_ba_id in old_ba_ids:
                try:
                    ba_ref = db.collection('BatchAssignment').document(old_ba_id)
                    ba_doc = ba_ref.get()
                    if ba_doc.exists:
                        # Delete associated ExamAssignments
                        ba_data = ba_doc.to_dict()
                        for exam_ref in ba_data.get('examassignment', []) or []:
                            try:
                                exam_ref.delete()
                            except Exception:
                                pass
                        ba_ref.delete()
                except Exception as e:
                    logger.error(f"Error deleting orphaned BatchAssignment {old_ba_id}: {e}")

            # Update summary with new mappings
            summary_ref.update({'procedure_assessor_mappings': new_processed_mappings})

        return JsonResponse({'success': True})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in update_batch_assignment_summary: {str(e)}\n{error_trace}")
        return JsonResponse({'error': str(e)}, status=500)

def render_exam_reports_page(request):
    if not request.user.check_icon_navigation_permissions('reports'):
        return HttpResponse('You are not authorized to access this page')
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
            one_minute_ago = datetime.now() - timedelta(minutes=1)
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

       # --- Institute Table Calculation ---
       institute_metrics = {}

       for exam in exam_assignments:
           exam_doc = exam.to_dict()
           institute = exam_doc.get('institution', 'Unknown')
           procedure = exam_doc.get('procedureName', exam_doc.get('procedure_name', 'Unknown'))
           email = exam_doc.get('emailID')
           total_score = exam_doc.get("marks", 0)
           max_marks = sum(
               question.get('right_marks_for_question', 0)
               for section in exam_doc.get('examMetaData', [])
               for question in section.get("section_questions", [])
           )
           percentage = (total_score / max_marks) * 100 if max_marks > 0 else 0

           if institute not in institute_metrics:
               institute_metrics[institute] = {
                   "overall": {"students": set(), "total_score": 0, "count": 0},
                   "stations": {}
               }
           # Overall
           institute_metrics[institute]["overall"]["students"].add(email)
           institute_metrics[institute]["overall"]["total_score"] += percentage
           institute_metrics[institute]["overall"]["count"] += 1

           # Per station
           if procedure not in institute_metrics[institute]["stations"]:
               institute_metrics[institute]["stations"][procedure] = {"students": set(), "total_score": 0, "count": 0}
           institute_metrics[institute]["stations"][procedure]["students"].add(email)
           institute_metrics[institute]["stations"][procedure]["total_score"] += percentage
           institute_metrics[institute]["stations"][procedure]["count"] += 1

       # Prepare for JSON
       institute_table = []
       for institute, data in institute_metrics.items():
           row = {
               "institute": institute,
               "overall": {
                   "students": len(data["overall"]["students"]),
                   "avg_score": round(data["overall"]["total_score"] / data["overall"]["count"], 2) if data["overall"]["count"] else 0
               },
               "stations": {}
           }
           for station, sdata in data["stations"].items():
               row["stations"][station] = {
                   "students": len(sdata["students"]),
                   "avg_score": round(sdata["total_score"] / sdata["count"], 2) if sdata["count"] else 0
               }
           institute_table.append(row)

       # Calculate overall averages for each procedure across all institutes
       procedure_averages = {}
       for institute_data in institute_metrics.values():
           for procedure, data in institute_data["stations"].items():
               if data["count"] > 0:
                   avg_score = data["total_score"] / data["count"]
                   if procedure not in procedure_averages:
                       procedure_averages[procedure] = {"total_score": 0, "total_count": 0}
                   procedure_averages[procedure]["total_score"] += avg_score * data["count"]
                   procedure_averages[procedure]["total_count"] += data["count"]

       # Calculate final averages and find top/bottom performing skills
       final_averages = {
           proc: round(data["total_score"] / data["total_count"], 2)
           for proc, data in procedure_averages.items()
       }
       sorted_procedures = sorted(final_averages.items(), key=lambda x: x[1], reverse=True)
       top_performing_skill = sorted_procedures[0] if sorted_procedures else None
       lowest_performing_skill = sorted_procedures[-1] if sorted_procedures else None

       metrics = {
           "total_students": len(total_students),
           "procedure_counts": dict(procedure_counts),
           "grade_distribution": grade_distribution,
           "gender_metrics": gender_metrics,
           "skill_wise_metrics": skill_wise_metrics,
           "completed_all_procedures": completed_all_procedures,
           "institute_table": institute_table,
           "top_performing_skill": {"name": top_performing_skill[0], "average_score": top_performing_skill[1]} if top_performing_skill else None,
           "lowest_performing_skill": {"name": lowest_performing_skill[0], "average_score": lowest_performing_skill[1]} if lowest_performing_skill else None
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
        if request.user.is_superuser or request.user.has_all_permissions() or request.user.access_all_skillathons:
            print("here")
            assigned_skillathons = SkillathonEvent.objects.all().values_list('name', flat=True)
        else:
            assigned_skillathons = list(request.user.assigned_skillathons.values_list('name', flat=True))
        
        # Helper function to chunk lists
        def chunk(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i+n]
        
        skillathons = []
        
        if assigned_skillathons:
            # Firestore 'in' supports up to 10 values – chunk queries and merge results
            for skillathon_chunk in chunk(assigned_skillathons, 10):
                skillathons_ref = db.collection('Skillathon').where('skillathonName', 'in', skillathon_chunk)
                for doc in skillathons_ref.stream():
                    skillathon_data = doc.to_dict()
                    # Parse the full ISO 8601 timestamp
                    created_at = datetime.fromisoformat(skillathon_data.get('created_at').replace('Z', '+00:00'))
                    skillathons.append({
                        'id': doc.id,
                        'name': skillathon_data.get('skillathonName', 'Unnamed Skillathon'),
                        'date': created_at.strftime('%d-%m-%Y')
                    })
        else:
            # If no assigned skillathons, return empty list
            pass

        return JsonResponse({'skillathons': skillathons}, status=200)
    except Exception as e:
        print(f"Error in fetch_skillathons: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def institute_based_skillathon(request):
    """API endpoint to handle skillathon selection and return related institutions."""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            skillathon_name = data.get('skillathon_name')
            
            print(f"Institute-based skillathon API called with: {skillathon_name}")
            
            if not skillathon_name:
                return JsonResponse({'error': 'Skillathon name is required'}, status=400)
            
            # Query Firestore for institutes with this skillathon
            institutes = []
            
            # Query InstituteNames collection for institutes with matching skillathon_event
            institutes_ref = db.collection('InstituteNames')
            query = institutes_ref.where('skillathon_event', '==', skillathon_name)
            docs = query.get()
            
            print(f"Found {len(docs)} institutes for skillathon: {skillathon_name}")
            
            for doc in docs:
                institute_data = doc.to_dict()
                institutes.append({
                    'id': doc.id,
                    'name': institute_data.get('instituteName', 'Unknown Institute')
                })
            
            print(f"Processed {len(institutes)} institutes")
                
            # Response structure
            response_data = {
                'skillathon_name': skillathon_name,
                'institutes': institutes,
                'count': len(institutes),
                'message': f'Found {len(institutes)} institutes for skillathon: {skillathon_name}',
                'status': 'success'
            }
            
            print(f"Institute-based skillathon API response: {response_data}")
            return JsonResponse(response_data, status=200)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"Error in institute_based_skillathon: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

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

# def parse_users_excel_to_json(dataframe):
#     """Parse the uploaded Excel file to JSON for user creation."""
#     users_data = []
#     validation_errors = []
    
#     for index, row in dataframe.iterrows():
#         excel_row = index + 1
        
#         # Validate required fields
#         if pd.isna(row["Username"]) and pd.isna(row["Institute"]):
#             validation_errors.append(f"Row {excel_row}: Both Username and Institute are missing")
#             continue
#         elif pd.isna(row["Username"]):
#             validation_errors.append(f"Row {excel_row}: Username is missing")
#             continue
#         elif pd.isna(row["Institute"]):
#             validation_errors.append(f"Row {excel_row}: Institute is missing")
#             continue
            
#         # Validate role
#         role = str(row["Role"]).strip().lower() if not pd.isna(row["Role"]) else "student"
#         if role not in ["student", "supervisor"]:
#             role = "student"  # Default to student if invalid role
            
#         user_data = {
#             "username": str(row["Username"]).strip(),
#             "emailID": str(row["EmailID"]).strip() if not pd.isna(row["EmailID"]) else "",
#             "role": role,
#             "institute_name": str(row["Institute"]).strip()
#         }
#         users_data.append(user_data)
    
#     return users_data, validation_errors

# def upload_users_excel_view(request):
#     if request.method == 'POST':
#         form = ExcelUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             uploaded_file = form.cleaned_data['file']
            
#             file_name = f"{uuid.uuid4()}_{uploaded_file.name}".replace(" ", "_")
#             file_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_excels', file_name)
#             print(file_path)
#             os.makedirs(os.path.dirname(file_path), exist_ok=True)
#             print(file_path)
            
#             with open(file_path, 'wb+') as destination:
#                 for chunk in uploaded_file.chunks():
#                     destination.write(chunk)
#             print(file_path)

#             try:
#                 df = pd.read_excel(file_path, header=None)  # Read without header to validate

#                 # Validate specific cells in row 1
#                 if not (
#                     df.iloc[0, 0] == "Username" and
#                     df.iloc[0, 1] == "EmailID" and
#                     df.iloc[0, 2] == "Institute" and
#                     df.iloc[0, 3] == "Role"  # Add Role column check
#                 ):
#                     raise ValueError("Excel template is incorrect. Ensure first row contains 'Username', 'EmailID', 'Institute', 'Role'")

#                 # Process data from row 2 onward
#                 df_data = pd.read_excel(file_path, names=["Username", "EmailID", "Institute", "Role"])
#                 print(df_data)
#                 users_data, validation_errors = parse_users_excel_to_json(df_data)
                

#                 if validation_errors:
#                     return JsonResponse({
#                         "error": "Validation errors in Excel file",
#                         "validation_errors": validation_errors
#                     }, status=400)

#                 # Process each user
#                 created_users = []
#                 processing_errors = []
                
#                 for user_data in users_data:
#                     try:
#                         # Find institute (case insensitive)
#                         institute_query = db.collection('InstituteNames').where(
#                             'instituteName', '==', user_data['institute_name']
#                         ).limit(1).stream()
                        
#                         institute_doc = next(institute_query, None)
#                         if not institute_doc:
#                             processing_errors.append(f"Institute not found for user {user_data['username']}")
#                             continue

#                         # Create user document
#                         user_ref = db.collection('Users').document()
#                         user_ref.set({
#                             "username": user_data['username'],
#                             "emailID": user_data['emailID'],
#                             "role": user_data['role'],
#                             "institute": institute_doc.reference,
#                             "cohort": None, # Will be updated when added to a batch,
#                             "createdAt": firestore.SERVER_TIMESTAMP
#                         })
                        
#                         created_users.append(user_data['username'])

#                     except Exception as e:
#                         processing_errors.append(f"Error creating user {user_data['username']}: {str(e)}")

#                 response_data = {
#                     "message": f"Processed {len(created_users)} users successfully",
#                     "created_users": created_users
#                 }
#                 if processing_errors:
#                     response_data["processing_errors"] = processing_errors

#                 return JsonResponse(response_data, status=200 if created_users else 400)

#             except Exception as e:
#                 print(e)
#                 logger.error(f"Error processing file: {str(e)}")
#                 return JsonResponse({"error": str(e)}, status=400)
#         else:
#             print(form.errors)
#             return JsonResponse({"error": form.errors}, status=400)

#     return JsonResponse({"error": "Invalid request method"}, status=405)

# @csrf_exempt
# def create_user(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             username = data.get('username', '').strip()
#             email_id = data.get('emailID', '').strip()
#             institute_id = data.get('instituteId')
#             role = data.get('role', 'student')

#             if not username or not institute_id:
#                 return JsonResponse({'error': 'Username and Institute are required'}, status=400)

#             # Check if username already exists
#             existing_user = db.collection('Users')\
#                 .where('username', '==', username)\
#                 .limit(1)\
#                 .stream()
            
#             if list(existing_user):
#                 return JsonResponse({'error': 'Username already exists'}, status=400)

#             # Get institute reference
#             institute_ref = db.collection('InstituteNames').document(institute_id)
#             if not institute_ref.get().exists:
#                 return JsonResponse({'error': 'Institute not found'}, status=404)

#             # Create new user with createdAt field
#             new_user = {
#                 'username': username,
#                 'emailID': email_id,
#                 'role': role,
#                 'institute': institute_ref,
#                 'cohort': None,
#                 'createdAt': firestore.SERVER_TIMESTAMP  # Add creation timestamp
#             }

#             # Add to Firebase
#             user_ref = db.collection('Users').add(new_user)

#             return JsonResponse({
#                 'success': True,
#                 'id': user_ref[1].id,
#                 'message': 'User created successfully'
#             })

#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

#     return JsonResponse({'error': 'Invalid request method'}, status=405)

# def users_management(request):
#     try:
#         # Get query parameters
#         query = request.GET.get("query", "")
#         offset = int(request.GET.get("offset", 0))
#         limit = int(request.GET.get("limit", 10))  # Use the limit from request
#         is_load_more = request.GET.get("load_more") == "true"
        
#         # Create base query
#         users_ref = db.collection('Users')
        
#         # Apply sorting (newest first)
#         users_ref = users_ref.order_by('createdAt', direction=firestore.Query.DESCENDING)
        
#         # For query we still need to fetch all and filter manually
#         # since Firestore doesn't support complex text search
#         if query:
#             all_users = users_ref.stream()
#             filtered_users = []
            
#             # Manually filter by username or institute
#             for doc in all_users:
#                 user_data = doc.to_dict()
#                 institute_ref = user_data.get('institute')
#                 institute_name = "Unknown"
                
#                 if institute_ref:
#                     institute_doc = institute_ref.get()
#                     if institute_doc.exists:
#                         institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')
                
#                 # Apply text search
#                 if (query.lower() in user_data.get('username', '').lower() or 
#                     query.lower() in institute_name.lower()):
#                     filtered_users.append({
#                         'id': doc.id,
#                         'username': user_data.get('username', 'N/A'),
#                         'emailID': user_data.get('emailID', 'N/A'),
#                         'institute': institute_name,
#                         'role': user_data.get('role', 'student'),
#                         'createdAt': user_data.get('createdAt')
#                     })
            
#             # Apply offset and limit manually to filtered results
#             total_count = len(filtered_users)
#             users = filtered_users[offset:offset+limit]
#             has_more = total_count > (offset + limit)
            
#         else:
#             # If no query, use Firestore's native offset and limit
#             users_snapshot = users_ref.offset(offset).limit(limit).stream()
            
#             # Count total for has_more calculation (can be optimized with a separate count query)
#             total_query = users_ref.stream()
#             total_count = sum(1 for _ in total_query)  # Count total documents
            
#             # Process results
#             users = []
#             for doc in users_snapshot:
#                 user_data = doc.to_dict()
#                 institute_ref = user_data.get('institute')
#                 institute_name = "Unknown"
                
#                 if institute_ref:
#                     institute_doc = institute_ref.get()
#                     if institute_doc.exists:
#                         institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')
                
#                 users.append({
#                     'id': doc.id,
#                     'username': user_data.get('username', 'N/A'),
#                     'emailID': user_data.get('emailID', 'N/A'),
#                     'institute': institute_name,
#                     'role': user_data.get('role', 'student'),
#                     'createdAt': user_data.get('createdAt')
#                 })
            
#             has_more = total_count > (offset + limit)

#         if is_load_more:
#             return JsonResponse({
#                 "users": users,
#                 "has_more": has_more
#             })

#         return render(request, 'assessments/users_management.html', {
#             "initial_users": users,
#             "query": query,
#         })

#     except Exception as e:
#         logger.error(f"Error fetching users: {str(e)}")
#         if is_load_more:
#             return JsonResponse({"error": str(e)}, status=500)
#         return render(request, 'assessments/users_management.html', {
#             "error": "Failed to fetch users",
#             "initial_users": [],
#             "query": query,
#         })

# @csrf_exempt
# def edit_user(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             user_id = data.get('userId')
#             username = data.get('username', '').strip()
#             email_id = data.get('emailID', '').strip()
#             institute_id = data.get('instituteId')
#             role = data.get('role', 'student')  # Get role from request

#             if not username or not institute_id:
#                 return JsonResponse({'error': 'Username and Institute are required'}, status=400)

#             # Check if username already exists (excluding current user)
#             existing_user = db.collection('Users')\
#                 .where('username', '==', username)\
#                 .stream()
            
#             for user in existing_user:
#                 if user.id != user_id:  # If username exists for a different user
#                     return JsonResponse({'error': 'Username already exists'}, status=400)

#             # Get institute reference
#             institute_ref = db.collection('InstituteNames').document(institute_id)
#             if not institute_ref.get().exists:
#                 return JsonResponse({'error': 'Institute not found'}, status=404)

#             # Update user
#             user_ref = db.collection('Users').document(user_id)
#             user_ref.update({
#                 'username': username,
#                 'emailID': email_id,
#                 'institute': institute_ref,
#                 'role': role  # Add role to update data
#             })

#             return JsonResponse({
#                 'success': True,
#                 'message': 'User updated successfully'
#             })

#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

#     return JsonResponse({'error': 'Invalid request method'}, status=405)

# @csrf_exempt
# def cohort_list(request):
#     try:
#         # Fetch cohorts from Firestore
#         cohorts_ref = db.collection('Cohort')
#         cohorts = []
        
#         # Get search query if any
#         query = request.GET.get("query", "")
        
#         for doc in cohorts_ref.stream():
#             cohort_data = doc.to_dict()
            
#             # Get institutes
#             institutes = []
#             if 'instituteName' in cohort_data:
#                 institutes.append(cohort_data['instituteName'])
            
#             # Get student count
#             student_count = len(cohort_data.get('users', []))
            
#             cohort = {
#                 'id': doc.id,
#                 'name': cohort_data.get('cohortName', 'N/A'),
#                 'institutes': ', '.join(institutes),
#                 'student_count': student_count
#             }
            
#             # Apply search filter if query exists
#             if query:
#                 if query.lower() in cohort['name'].lower():
#                     cohorts.append(cohort)
#             else:
#                 cohorts.append(cohort)
        
#         # Pagination
#         paginator = Paginator(cohorts, 10)
#         page_number = request.GET.get("page")
#         page_obj = paginator.get_page(page_number)
        
#         return render(request, 'assessments/cohort_list.html', {
#             "page_obj": page_obj,
#             "query": query,
#         })
        
#     except Exception as e:
#         logger.error(f"Error fetching cohorts: {str(e)}")
#         return render(request, 'assessments/cohort_list.html', {
#             "error": "Failed to fetch cohorts",
#             "page_obj": [],
#             "query": query,
#         })

# @csrf_exempt
# def fetch_institute_students(request):
#     institute_id = request.GET.get('institute_id')
#     if not institute_id:
#         return JsonResponse({'error': 'Institute ID is required'}, status=400)
    
#     try:
#         institute_ref = db.collection('InstituteNames').document(institute_id)
#         students_ref = db.collection('Users').where('institute', '==', institute_ref)
        
#         students = []
#         for doc in students_ref.stream():
#             student_data = doc.to_dict()
#             students.append({
#                 'id': doc.id,
#                 'username': student_data.get('username', 'N/A')
#             })
        
#         return JsonResponse({'students': students})
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

# @csrf_exempt
# def create_cohort(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             name = data.get('name')
#             student_ids = data.get('studentIds', [])
            
#             if not name or not student_ids:
#                 return JsonResponse({'error': 'Name and student IDs are required'}, status=400)
            
#             # Create student references
#             student_refs = [db.collection('Users').document(sid) for sid in student_ids]
            
#             # Get institute from first student (assuming all students are from same institute)
#             first_student = db.collection('Users').document(student_ids[0]).get()
#             institute_ref = first_student.to_dict().get('institute')
            
#             # Create cohort
#             cohort_ref = db.collection('Cohort').document()
#             cohort_data = {
#                 'cohortName': name,
#                 'users': student_refs,
#                 'instituteName': institute_ref.get().to_dict().get('instituteName'),
#                 'createdAt': firestore.SERVER_TIMESTAMP
#             }
            
#             cohort_ref.set(cohort_data)
            
#             # Update each student's cohort reference
#             for student_id in student_ids:
#                 db.collection('Users').document(student_id).update({
#                     'cohort': cohort_ref
#                 })
            
#             return JsonResponse({
#                 'success': True,
#                 'message': 'Cohort created successfully'
#             })
            
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)
    
#     return JsonResponse({'error': 'Invalid request method'}, status=405)

# def add_students_to_existing_exams(cohort_ref, student_refs):
#     """Helper function to add students to all existing exams for a cohort."""
#     # Get all tests for this cohort
#     tests_ref = db.collection('Test').where('cohort', '==', cohort_ref).stream()
    
#     for test in tests_ref:
#         test_data = test.to_dict()
#         procedure_assignments = test_data.get('procedureAssignments', [])
        
#         # For each procedure assignment in the test
#         for proc_assignment_ref in procedure_assignments:
#             proc_assignment = proc_assignment_ref.get().to_dict()
#             procedure_ref = proc_assignment.get('procedure')
            
#             if procedure_ref:
#                 procedure_data = procedure_ref.get().to_dict()
                
#                 # Create exam assignments for new students
#                 for student_ref in student_refs:
#                     exam_assignment_data = {
#                         'user': student_ref,
#                         'examMetaData': procedure_data.get('examMetaData', {}),
#                         'status': 'Pending',
#                         'notes': procedure_data.get('notes', ''),
#                         'procedure_name': procedure_data.get('procedureName', '')
#                     }
                    
#                     # Create new exam assignment
#                     exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                    
#                     # Add to procedure assignment's examAssignmentArray
#                     proc_assignment_ref.update({
#                         'examAssignmentArray': firestore.ArrayUnion([exam_assignment_ref])
#                     })

# @csrf_exempt
# def add_student_to_cohort(request, cohort_id):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             student_ids = data.get('studentIds', [])
            
#             if not student_ids:
#                 return JsonResponse({'error': 'Student IDs are required'}, status=400)
            
#             # Get cohort reference
#             cohort_ref = db.collection('Cohort').document(cohort_id)
#             cohort_doc = cohort_ref.get()
            
#             if not cohort_doc.exists:
#                 return JsonResponse({'error': 'Cohort not found'}, status=404)
            
#             # Get existing students in cohort
#             cohort_data = cohort_doc.to_dict()
#             existing_student_refs = cohort_data.get('users', [])
#             existing_student_ids = [ref.id for ref in existing_student_refs]
            
#             # Filter out students that are already in the cohort
#             new_student_ids = [sid for sid in student_ids if sid not in existing_student_ids]
            
#             if not new_student_ids:
#                 return JsonResponse({
#                     'success': True,
#                     'message': 'All students are already in this cohort'
#                 })
            
#             # Create student references for only new students
#             new_student_refs = [db.collection('Users').document(sid) for sid in new_student_ids]
            
#             # Update cohort with new students
#             cohort_ref.update({
#                 'users': firestore.ArrayUnion(new_student_refs)
#             })
            
#             # Update each student's cohort reference
#             for student_id in new_student_ids:
#                 db.collection('Users').document(student_id).update({
#                     'cohort': cohort_ref
#                 })
            
#             # Add students to existing exams
#             add_students_to_existing_exams(cohort_ref, new_student_refs)
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'Added {len(new_student_ids)} new students to cohort successfully'
#             })
            
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)
    
#     return JsonResponse({'error': 'Invalid request method'}, status=405)

# @csrf_exempt
# def view_cohort_students(request, cohort_id):
#     try:
#         # Get cohort reference
#         cohort_ref = db.collection('Cohort').document(cohort_id)
#         cohort_doc = cohort_ref.get()
        
#         if not cohort_doc.exists:
#             return JsonResponse({'error': 'Cohort not found'}, status=404)
        
#         cohort_data = cohort_doc.to_dict()
#         cohort_name = cohort_data.get('cohortName', 'N/A')
#         user_refs = cohort_data.get('users', [])
        
#         # Get student details
#         students = []
#         for user_ref in user_refs:
#             user_doc = user_ref.get()
#             if user_doc.exists:
#                 user_data = user_doc.to_dict()
#                 institute_ref = user_data.get('institute')
#                 institute_name = "Unknown"
                
#                 if institute_ref:
#                     institute_doc = institute_ref.get()
#                     if institute_doc.exists:
#                         institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')
                
#                 students.append({
#                     'id': user_doc.id,
#                     'username': user_data.get('username', 'N/A'),
#                     'emailID': user_data.get('emailID', 'N/A'),
#                     'institute': institute_name
#                 })
        
#         # Sort students by username
#         students.sort(key=lambda x: x['username'])
        
#         # Pagination
#         paginator = Paginator(students, 10)  # Show 10 students per page
#         page_number = request.GET.get("page")
#         page_obj = paginator.get_page(page_number)
        
#         return render(request, 'assessments/view_cohort_students.html', {
#             'cohort_id': cohort_id,
#             'cohort_name': cohort_name,
#             'page_obj': page_obj
#         })
        
#     except Exception as e:
#         logger.error(f"Error viewing cohort students: {str(e)}")
#         return JsonResponse({'error': str(e)}, status=500)

# @csrf_exempt
# def get_cohort_students(request, cohort_id):
#     try:
#         # Get cohort reference
#         cohort_ref = db.collection('Cohort').document(cohort_id)
#         cohort_doc = cohort_ref.get()
        
#         if not cohort_doc.exists:
#             return JsonResponse({'error': 'Cohort not found'}, status=404)
        
#         cohort_data = cohort_doc.to_dict()
#         user_refs = cohort_data.get('users', [])
        
#         # Get student details
#         students = []
#         for user_ref in user_refs:
#             user_doc = user_ref.get()
#             if user_doc.exists:
#                 user_data = user_doc.to_dict()
#                 students.append({
#                     'id': user_doc.id,
#                     'username': user_data.get('username', 'N/A')
#                 })
        
#         return JsonResponse({'students': students})
        
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

def base(request):
    return render(request, 'assessments/welcome.html')

def login_page(request):
    if request.user.is_authenticated:
        return redirect('base')
    return render(request, 'assessments/login.html')

def login_view(request):
    logout(request)
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = authenticate(request, email=email, password=password)
    if user is not None:
        login(request, user)
            # Update last login in Firebase
        return redirect('base')
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

def course_management(request):
    """
    View function for the course management page.
    """
    if not request.user.check_icon_navigation_permissions('courses'):
        return HttpResponse('You are not authorized to access this page')
    
    # Get user's permissions
    user_permissions = request.user.get_all_permissions if hasattr(request.user, 'get_all_permissions') else []
    
    context = {
        'user_permissions': user_permissions,
    }
    
    return render(request, 'assessments/course_management.html', context)

def course_detail(request, course_id):
    """
    View function for individual course detail page.
    """
    try:
        # Fetch course data from Firebase
        course_ref = db.collection('Courses').document(course_id)
        course_doc = course_ref.get()
        
        if not course_doc.exists:
            # Course not found, redirect to course management
            return redirect('course_management')
        
        course_data = course_doc.to_dict()
        procedure_refs = course_data.get('procedures', [])
        
        # Get procedure details
        procedures = []
        for proc_ref in procedure_refs:
            proc_doc = proc_ref.get()
            if proc_doc.exists:
                proc_data = proc_doc.to_dict()
                procedures.append({
                    'id': proc_ref.id,
                    'name': proc_data.get('procedureName', 'Unknown'),
                    'category': 'General',  # Default category
                    'status': 'active'  # Default status
                })
        
        # Prepare course data for template
        course_context = {
            'id': course_id,
            'name': course_data.get('courseName', 'N/A'),
            'description': course_data.get('description', ''),
            'total_procedures': len(procedures),
            'osce_types': course_data.get('osceTypes', []),
            'verification_required': course_data.get('verificationRequired', False),
            'created_date': course_data.get('createdAt'),
            'last_modified': course_data.get('updatedAt'),
            'procedures': procedures
        }
        
        return render(request, 'assessments/course_detail.html', {'course': course_context})
        
    except Exception as e:
        print(f"Error fetching course details: {str(e)}")
        # Redirect to course management on error
        return redirect('course_management')

@login_required
def batch_management(request):
    """
    View for managing batches. Displays a list of all batches and provides functionality
    to create, edit, and delete batches.
    """
    return render(request, 'assessments/batch_management.html')

@login_required
def batch_detail(request, batch_id):
    """
    View for displaying and managing details of a specific batch.
    """
    try:
        # Fetch batch data from Firebase
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            # Batch not found, redirect to batch management
            return redirect('batch_management')
        
        batch_data = batch_doc.to_dict()
        
        # Get unit details
        unit_name = "Unknown"
        unit_id = None
        unit_ref = batch_data.get('unit')
        if unit_ref:
            unit_doc = unit_ref.get()
            if unit_doc.exists:
                unit_id = unit_doc.id
                if batch_data.get('unitType') == 'institution':
                    unit_name = unit_doc.to_dict().get('instituteName', 'Unknown')
                else:
                    unit_name = unit_doc.to_dict().get('hospitalName', 'Unknown')
        
        # Get learner details
        learners = []
        learner_refs = batch_data.get('learners', [])
        for learner_ref in learner_refs:
            learner_doc = learner_ref.get()
            if learner_doc.exists:
                learner_data = learner_doc.to_dict()
                learners.append({
                    'id': learner_doc.id,
                    'name': learner_data.get('username', 'N/A'),
                    'email': learner_data.get('emailID', 'N/A')
                })
        
        # Get course details
        courses = []
        course_refs = batch_data.get('courses', [])
        for course_ref in course_refs:
            course_doc = course_ref.get()
            if course_doc.exists:
                course_data = course_doc.to_dict()
                procedure_refs = course_data.get('procedures', [])
                
                # Get procedure names
                procedure_names = []
                for proc_ref in procedure_refs:
                    proc_doc = proc_ref.get()
                    if proc_doc.exists:
                        procedure_names.append(proc_doc.to_dict().get('procedureName', 'Unknown'))
                
                courses.append({
                    'id': course_ref.id,
                    'name': course_data.get('courseName', 'N/A'),
                    'description': course_data.get('description', ''),
                    'procedures': procedure_names,
                    'procedure_count': len(procedure_names),
                    'osce_types': course_data.get('osceTypes', []),
                    'verification_required': course_data.get('verificationRequired', False),
                    'status': course_data.get('status', 'active')
                })
        
        # Prepare batch context for template
        batch_context = {
            'id': batch_id,
            'name': batch_data.get('batchName', 'N/A'),
            'unit_type': batch_data.get('unitType', 'N/A'),
            'unit_name': unit_name,
            'unit_id': unit_id,
            'learners': learners,
            'learner_count': len(learners),
            'courses': courses,
            'course_count': len(courses),
            'status': batch_data.get('status', 'active'),
            'created_at': batch_data.get('createdAt'),
            'year_of_batch': batch_data.get('yearOfBatch', ''),
            'semester': batch_data.get('semester', '')
        }
        
        return render(request, 'assessments/batch_detail.html', {'batch': batch_context})
        
    except Exception as e:
        print(f"Error fetching batch details: {str(e)}")
        # Redirect to batch management on error
        return redirect('batch_management')

@csrf_exempt
def create_course(request):
    """API endpoint to create a new course."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            course_name = data.get('courseName', '').strip()
            description = data.get('description', '').strip()
            procedure_ids = data.get('procedures', [])
            verification_required = data.get('verificationRequired', False)
            
            if not course_name:
                return JsonResponse({'error': 'Course name is required'}, status=400)
            
            if not procedure_ids:
                return JsonResponse({'error': 'At least one procedure is required'}, status=400)
            
            
            # Check if course already exists
            existing_course = db.collection('Courses')\
                .where('courseName', '==', course_name)\
                .limit(1)\
                .stream()
            
            if list(existing_course):
                return JsonResponse({'error': 'Course with this name already exists'}, status=400)
            
            # Create procedure references
            procedure_refs = [db.collection('ProcedureTable').document(pid) for pid in procedure_ids]
            
            # Create new course
            new_course = {
                'courseName': course_name,
                'description': description,
                'procedures': procedure_refs,
                'status': 'active',
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'verificationRequired': verification_required,
            }
            
            # Add to Firebase
            course_ref = db.collection('Courses').add(new_course)
            
            return JsonResponse({
                'success': True,
                'id': course_ref[1].id,
                'message': 'Course created successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def fetch_courses(request):
    """API endpoint to fetch all courses, with optional offset/limit for lazy loading and filtering."""
    try:
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 10))
        search = request.GET.get('search', '').strip().lower()
        status_filters = request.GET.getlist('status')
        status_filters = [s.lower() for s in status_filters if s]
        courses_ref = db.collection('Courses')
        courses = []
        all_docs = list(courses_ref.stream())
        filtered_docs = []
        for doc in all_docs:
            course_data = doc.to_dict()
            name = course_data.get('courseName', '').lower()
            status = course_data.get('status', 'active').lower()
            # Filter by search
            if search and search not in name:
                continue
            # Filter by status
            if status_filters and status not in status_filters:
                continue
            filtered_docs.append(doc)
        total_courses = len(filtered_docs)
        paginated_docs = filtered_docs[offset:offset+limit]
        for doc in paginated_docs:
            course_data = doc.to_dict()
            procedure_refs = course_data.get('procedures', [])
            # Get procedure names
            procedure_names = []
            for proc_ref in procedure_refs:
                proc_doc = proc_ref.get()
                if proc_doc.exists:
                    procedure_names.append(proc_doc.to_dict().get('procedureName', 'Unknown'))
            courses.append({
                'id': doc.id,
                'name': course_data.get('courseName', 'N/A'),
                'description': course_data.get('description', ''),
                'procedures': procedure_names,
                'procedure_count': len(procedure_names),
                'osce_types': course_data.get('osceTypes', []),
                'verification_required': course_data.get('verificationRequired', False),
                'status': course_data.get('status', 'active'),
                'created_at': course_data.get('createdAt'),
                'updated_at': course_data.get('updatedAt')
            })
        all_loaded = offset + limit >= total_courses
        return JsonResponse({'courses': courses, 'all_loaded': all_loaded}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_course(request, course_id):
    """API endpoint to delete a course."""
    if request.method == 'POST':
        try:
            course_ref = db.collection('Courses').document(course_id)
            course_doc = course_ref.get()
            
            if not course_doc.exists:
                return JsonResponse({'error': 'Course not found'}, status=404)
            
            # Delete the course
            course_ref.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Course deleted successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def toggle_course_status(request, course_id):
    """API endpoint to toggle course status."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status', 'active')

            course_ref = db.collection('Courses').document(course_id)
            course_doc = course_ref.get()

            if not course_doc.exists:
                return JsonResponse({'error': 'Course not found'}, status=404)

            # Update the course status
            course_ref.update({
                'status': new_status,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })

            # If course is being marked as inactive, remove it from all batches
            if new_status == 'inactive':
                print(f"[COURSE STATUS] Course {course_id} marked as inactive, removing from all batches")

                # Query all batches that have this course
                batches_query = db.collection('Batches').where('courses', 'array_contains', course_ref).stream()
                removed_from_batches = 0

                for batch_doc in batches_query:
                    batch_id = batch_doc.id
                    batch_ref = db.collection('Batches').document(batch_id)
                    batch_data = batch_doc.to_dict()

                    # Remove the course reference from the batch
                    batch_ref.update({
                        'courses': firestore.ArrayRemove([course_ref])
                    })
                    removed_from_batches += 1
                    print(f"[COURSE STATUS] Removed course {course_id} from batch: {batch_id} ({batch_data.get('batchName', 'Unknown')})")

                print(f"[COURSE STATUS] Removed course from {removed_from_batches} batch(es)")

                return JsonResponse({
                    'success': True,
                    'status': new_status,
                    'message': f'Course status updated to inactive and removed from {removed_from_batches} batch(es)'
                }, status=200)

            return JsonResponse({
                'success': True,
                'status': new_status,
                'message': 'Course status updated successfully'
            }, status=200)

        except Exception as e:
            print(f"[COURSE STATUS] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def update_course(request, course_id):
    """API endpoint to update a course."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            course_name = data.get('courseName', '').strip()
            description = data.get('description', '').strip()
            procedure_ids = data.get('procedures', [])
            verification_required = data.get('verificationRequired', False)
            if not course_name:
                return JsonResponse({'error': 'Course name is required'}, status=400)
            
            if not procedure_ids:
                return JsonResponse({'error': 'At least one procedure is required'}, status=400)
            
            
            # Check if course exists
            course_ref = db.collection('Courses').document(course_id)
            course_doc = course_ref.get()
            
            if not course_doc.exists:
                return JsonResponse({'error': 'Course not found'}, status=404)
            
            # Check if another course already exists with the same name (excluding current course)
            existing_course = db.collection('Courses')\
                .where('courseName', '==', course_name)\
                .stream()
            
            for doc in existing_course:
                if doc.id != course_id:
                    return JsonResponse({'error': 'Another course with this name already exists'}, status=400)
            
            # Create procedure references
            procedure_refs = [db.collection('ProcedureTable').document(pid) for pid in procedure_ids]
            
            # Update course
            course_ref.update({
                'courseName': course_name,
                'description': description,
                'procedures': procedure_refs,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'verificationRequired': verification_required,
            })
            
            return JsonResponse({
                'success': True,
                'message': 'Course updated successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def add_procedures_to_course(request, course_id):
    """API endpoint to add procedures to a course."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            procedure_ids = data.get('procedureIds', [])
            
            if not procedure_ids:
                return JsonResponse({'error': 'At least one procedure is required'}, status=400)
            
            # Check if course exists
            course_ref = db.collection('Courses').document(course_id)
            course_doc = course_ref.get()
            
            if not course_doc.exists:
                return JsonResponse({'error': 'Course not found'}, status=404)
            
            # Get current course data
            course_data = course_doc.to_dict()
            current_procedures = course_data.get('procedures', [])
            
            # Create new procedure references
            new_procedure_refs = [db.collection('ProcedureTable').document(pid) for pid in procedure_ids]
            
            # Check if procedures already exist in the course
            existing_procedure_ids = [ref.id for ref in current_procedures]
            procedures_to_add = []
            
            for proc_ref in new_procedure_refs:
                if proc_ref.id not in existing_procedure_ids:
                    procedures_to_add.append(proc_ref)
            
            if not procedures_to_add:
                return JsonResponse({
                    'success': True,
                    'message': 'All selected procedures are already in the course'
                }, status=200)
            
            # Add new procedures to the course
            course_ref.update({
                'procedures': firestore.ArrayUnion(procedures_to_add),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(procedures_to_add)} procedure(s) added successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def remove_procedure_from_course(request, course_id):
    """API endpoint to remove a procedure from a course."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            procedure_id = data.get('procedureId')
            
            if not procedure_id:
                return JsonResponse({'error': 'Procedure ID is required'}, status=400)
            
            # Check if course exists
            course_ref = db.collection('Courses').document(course_id)
            course_doc = course_ref.get()
            
            if not course_doc.exists:
                return JsonResponse({'error': 'Course not found'}, status=404)
            
            # Get current course data
            course_data = course_doc.to_dict()
            current_procedures = course_data.get('procedures', [])
            
            # Find the procedure to remove
            procedure_to_remove = None
            for proc_ref in current_procedures:
                if proc_ref.id == procedure_id:
                    procedure_to_remove = proc_ref
                    break
            
            if not procedure_to_remove:
                return JsonResponse({'error': 'Procedure not found in course'}, status=404)
            
            # Remove the procedure from the course
            course_ref.update({
                'procedures': firestore.ArrayRemove([procedure_to_remove]),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': 'Procedure removed successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

# Batch API endpoints
@csrf_exempt
def fetch_batches(request):
    """API endpoint to fetch all batches, with optional filtering by unitType and status."""
    try:
        # Get filter parameters from query string
        unit_type_param = request.GET.get('unitType', '').strip()
        status_param = request.GET.get('status', '').strip()
        search = request.GET.get('search', '').strip().lower()
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        include_inactive = request.GET.get('include_inactive', '').lower() == 'true'

        unit_types = [u.strip().lower() for u in unit_type_param.split(',') if u.strip()] if unit_type_param else []
        # Default to active batches only unless status is explicitly provided or include_inactive is true
        if status_param:
            statuses = [s.strip().lower() for s in status_param.split(',') if s.strip()]
        elif include_inactive:
            statuses = []  # No status filter, show all
        else:
            statuses = ['active']  # Default to active batches only


        # Limit batches to units assigned to current user (by reference)
        assigned_institutions = list(Institution.objects.all().values_list('name', flat=True)) if request.user.has_all_permissions() else list(request.user.assigned_institutions.values_list('name', flat=True))
        assigned_hospitals = list(Hospital.objects.all().values_list('name', flat=True)) if request.user.has_all_permissions() else list(request.user.assigned_hospitals.values_list('name', flat=True))
        print(assigned_institutions)
        print(assigned_hospitals)
        unit_refs = []
        # Resolve institute name -> doc reference
        for inst in assigned_institutions:
            try:
                snap_list = db.collection('InstituteNames').where('instituteName', '==', inst).limit(1).get()
                if snap_list:
                    print(snap_list[0].reference)
                    unit_refs.append(snap_list[0].reference)
            except Exception:
                continue
        # Resolve hospital name -> doc reference
        for hosp in assigned_hospitals:
            try:
                snap_list = db.collection('HospitalNames').where('hospitalName', '==', hosp).limit(1).get()
                if snap_list:
                    print(snap_list[0].reference)
                    unit_refs.append(snap_list[0].reference)
            except Exception:
                continue

        batches = []
        def chunk(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i+n]

        if unit_refs:
            # Firestore 'in' supports up to 10 values – chunk queries and merge results
            for refs_chunk in chunk(unit_refs, 10):
                query = db.collection('Batches').where('unit', 'in', refs_chunk)
                print(refs_chunk)
                for doc in query.stream():
                    batches.append((doc.id, doc.to_dict()))


        # Filter batches by unitName if provided
        unit_name_param = request.GET.get('unitName', '').strip()
        if unit_name_param:
            print(f"Filtering batches by unitName: {unit_name_param}")
            filtered_batches = []
            
            for doc_id, batch_data in batches:
                # Get the unit reference and fetch its names
                batch_unit_ref = batch_data.get('unit')
                if batch_unit_ref:
                    try:
                        batch_unit_doc = batch_unit_ref.get()
                        if batch_unit_doc.exists:
                            batch_unit_data = batch_unit_doc.to_dict()
                            
                            # Get the unit name based on unit type
                            batch_unit_type = batch_data.get('unitType', '')
                            if batch_unit_type == 'institution':
                                batch_unit_name = batch_unit_data.get('instituteName', '')
                            else:  # hospital
                                batch_unit_name = batch_unit_data.get('hospitalName', '')
                            
                            print(f"Batch '{batch_data.get('batchName')}' belongs to: {batch_unit_name}")
                            
                            # Compare names (case-insensitive)
                            if batch_unit_name.lower() == unit_name_param.lower():
                                filtered_batches.append((doc_id, batch_data))
                                print(f"  ✓ Match! Including this batch")
                            else:
                                print(f"  ✗ No match (expected: {unit_name_param})")
                    except Exception as e:
                        print(f"Error checking batch unit: {e}")
            
            print(f"Batches before filter: {len(batches)}, after filter: {len(filtered_batches)}")
            batches = filtered_batches

        # Transform and filter
        formatted_batches = []
        print(batches)
        for doc_id, batch_data in batches:

            # Filtering logic
            batch_unit_type = batch_data.get('unitType', '').lower()
            batch_status = batch_data.get('status', 'active').lower()
            batch_name = batch_data.get('batchName', '').lower()
            
            # Apply filters
            if unit_types and batch_unit_type not in unit_types:
                continue
            if statuses and batch_status not in statuses:
                continue
            if search and search not in batch_name:
                continue

            # Get unit name
            unit_name = "Unknown"
            unit_ref = batch_data.get('unit')
            if unit_ref:
                unit_doc = unit_ref.get()
                if unit_doc.exists:
                    if batch_data.get('unitType') == 'institution':
                        unit_name = unit_doc.to_dict().get('instituteName', 'Unknown')
                    else:
                        unit_name = unit_doc.to_dict().get('hospitalName', 'Unknown')

            # Get learner count
            learners = batch_data.get('learners', [])
            learner_count = len(learners)

            formatted_batches.append({
                'id': doc_id,
                'batchName': batch_data.get('batchName', 'N/A'),
                'unitType': batch_data.get('unitType', 'N/A'),
                'unitName': unit_name,
                'learnerCount': learner_count,
                'status': batch_data.get('status', 'active'),
                'createdAt': batch_data.get('createdAt'),
                'yearOfBatch': batch_data.get('yearOfBatch', ''),
                'semester': batch_data.get('semester', '')
            })

        print(formatted_batches)
        # Apply pagination
        total_count = len(formatted_batches)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_batches = formatted_batches[start_index:end_index]

        return JsonResponse({
            'success': True,
            'batches': paginated_batches,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'has_next': end_index < total_count
        }, status=200)
    except Exception as e:
        print(str(e))
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def create_batch(request):
    """API endpoint to create a new batch."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            batch_name = data.get('batchName', '').strip()
            unit_type = data.get('unitType')
            unit_id = data.get('unitId')
            learner_ids = data.get('learnerIds', [])
            year_of_batch = data.get('yearOfBatch', '').strip()
            semester = data.get('semester', '').strip()
            
            if not batch_name:
                return JsonResponse({'error': 'Batch name is required'}, status=400)
            
            if not unit_type:
                return JsonResponse({'error': 'Unit type is required'}, status=400)
            
            if not unit_id:
                return JsonResponse({'error': 'Unit is required'}, status=400)
            
            # Only require learners for institutions
            if unit_type == 'institution' and not learner_ids:
                return JsonResponse({'error': 'At least one learner is required for institutions'}, status=400)
            
            # Check if batch already exists
            existing_batch = db.collection('Batches')\
                .where('batchName', '==', batch_name)\
                .limit(1)\
                .stream()
            
            if list(existing_batch):
                return JsonResponse({'error': 'Batch with this name already exists'}, status=400)
            
            # Get unit reference based on type
            if unit_type == 'hospital':
                unit_ref = db.collection('HospitalNames').document(unit_id)
            else:
                unit_ref = db.collection('InstituteNames').document(unit_id)
            
            if not unit_ref.get().exists:
                return JsonResponse({'error': 'Unit not found'}, status=404)
            
            # Get learner references (only for institutions)
            learner_refs = []
            for learner_id in learner_ids:
                learner_ref = db.collection('Users').document(learner_id)
                if learner_ref.get().exists:
                    learner_refs.append(learner_ref)
            
            if not learner_refs:
                return JsonResponse({'error': 'No valid learners found'}, status=400)
            
            # Create new batch
            new_batch = {
                'batchName': batch_name,
                'unitType': unit_type,
                'unit': unit_ref,
                'learners': learner_refs,
                'status': 'active',
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            
            # Add year and semester if provided
            if year_of_batch:
                new_batch['yearOfBatch'] = year_of_batch
            if semester:
                new_batch['semester'] = semester
            
            # Add to Firebase
            batch_ref = db.collection('Batches').add(new_batch)
            
            return JsonResponse({
                'success': True,
                'id': batch_ref[1].id,
                'message': 'Batch created successfully'
            }, status=201)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def fetch_hospitals(request):
    """API endpoint to fetch all hospitals."""
    try:
        hospitals_ref = db.collection('HospitalNames')
        hospitals = []
        
        for doc in hospitals_ref.stream():
            hospital_data = doc.to_dict()
            hospitals.append({
                'id': doc.id,
                'name': hospital_data.get('hospitalName', 'N/A')
            })
        
        return JsonResponse({
            'success': True,
            'units': hospitals
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)



@csrf_exempt
def fetch_learners(request, unit_type, unit_id):
    """API endpoint to fetch learners (students and nurses) from a specific institution or hospital by name (string)."""
    try:
        # Get the unit name from the relevant collection
        if unit_type == 'institution':
            unit_ref = db.collection('InstituteNames').document(unit_id)
            unit_doc = unit_ref.get()
            if not unit_doc.exists:
                return JsonResponse({'success': False, 'error': 'Institute not found'}, status=404)
            unit_name = unit_doc.to_dict().get('instituteName', '')
            user_field = 'institution'
        elif unit_type == 'hospital':
            unit_ref = db.collection('HospitalNames').document(unit_id)
            unit_doc = unit_ref.get()
            if not unit_doc.exists:
                return JsonResponse({'success': False, 'error': 'Hospital not found'}, status=404)
            unit_name = unit_doc.to_dict().get('hospitalName', '')
            user_field = 'hospital'
        else:
            return JsonResponse({'success': False, 'error': 'Invalid unit type'}, status=400)

        # Query users by string field
        learners_ref = db.collection('Users').where(user_field, '==', unit_name).where('role', 'in', ['student', 'nurse'])
        learners = []
        for doc in learners_ref.stream():
            learner_data = doc.to_dict()
            learners.append({
                'id': doc.id,
                'name': learner_data.get('name', 'N/A'),
                'email': learner_data.get('emailID', 'N/A')
            })
        return JsonResponse({'success': True, 'learners': learners, 'unit_name': unit_name}, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def fetch_batch_details(request, batch_id):
    """API endpoint to fetch detailed information about a specific batch."""
    try:
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            return JsonResponse({'success': False, 'error': 'Batch not found'}, status=404)
        
        batch_data = batch_doc.to_dict()
        
        # Get unit details
        unit_name = "Unknown"
        unit_id = None
        unit_ref = batch_data.get('unit')
        if unit_ref:
            unit_doc = unit_ref.get()
            if unit_doc.exists:
                unit_id = unit_doc.id
                if batch_data.get('unitType') == 'institution':
                    unit_name = unit_doc.to_dict().get('instituteName', 'Unknown')
                else:
                    unit_name = unit_doc.to_dict().get('hospitalName', 'Unknown')
        
        # Get learner details
        learners = []
        learner_refs = batch_data.get('learners', [])
        for learner_ref in learner_refs:
            learner_doc = learner_ref.get()
            if learner_doc.exists:
                learner_data = learner_doc.to_dict()
                learners.append({
                    'id': learner_doc.id,
                    'name': learner_data.get('username', 'N/A'),
                    'email': learner_data.get('emailID', 'N/A')
                })
        
        batch_details = {
            'id': batch_id,
            'batchName': batch_data.get('batchName', 'N/A'),
            'unitType': batch_data.get('unitType', 'N/A'),
            'unitName': unit_name,
            'unitId': unit_id,
            'learners': learners,
            'learnerCount': len(learners),
            'status': batch_data.get('status', 'active'),
            'createdAt': batch_data.get('createdAt'),
            'yearOfBatch': batch_data.get('yearOfBatch', ''),
            'semester': batch_data.get('semester', '')
        }
        
        return JsonResponse({'success': True, 'batch': batch_details}, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def update_batch(request, batch_id):
    """API endpoint to update a batch."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            batch_name = data.get('batchName', '').strip()
            unit_type = data.get('unitType', None)
            unit_id = data.get('unitId', None)
            learner_ids = data.get('learnerIds', [])

            # Check if only updating batch name, year, or semester
            if data.get('updateOnlyBatchName', False):
                batch_ref = db.collection('Batches').document(batch_id)
                update_data = {'batchName': batch_name}
                year_of_batch = data.get('yearOfBatch', '').strip()
                semester = data.get('semester', '').strip()
                if year_of_batch:
                    update_data['yearOfBatch'] = year_of_batch
                if semester:
                    update_data['semester'] = semester
                batch_ref.update(update_data)
                return JsonResponse({
                    'success': True,
                    'message': 'Batch updated successfully'
                }, status=200)
            
            
            if not batch_name:
                return JsonResponse({'error': 'Batch name is required'}, status=400)
            
            if not unit_type:
                return JsonResponse({'error': 'Unit type is required'}, status=400)
            
            if not unit_id:
                return JsonResponse({'error': 'Unit is required'}, status=400)
            
            # Only require learners for institutions
            if unit_type == 'institution' and not learner_ids:
                return JsonResponse({'error': 'At least one learner is required for institutions'}, status=400)
            
            # Check if batch exists
            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)
            
            # Check if another batch already exists with the same name (excluding current batch)
            existing_batch = db.collection('Batches')\
                .where('batchName', '==', batch_name)\
                .stream()
            
            for doc in existing_batch:
                if doc.id != batch_id:
                    return JsonResponse({'error': 'Another batch with this name already exists'}, status=400)
            
            # Get unit reference based on type
            if unit_type == 'hospital':
                unit_ref = db.collection('Hospitals').document(unit_id)
            else:
                unit_ref = db.collection('InstituteNames').document(unit_id)
            
            if not unit_ref.get().exists:
                return JsonResponse({'error': 'Unit not found'}, status=404)
            
            # Get learner references (only for institutions)
            learner_refs = []
            if unit_type == 'institution':
                for learner_id in learner_ids:
                    learner_ref = db.collection('Users').document(learner_id)
                    if learner_ref.get().exists:
                        learner_refs.append(learner_ref)
                
                if not learner_refs:
                    return JsonResponse({'error': 'No valid learners found'}, status=400)
            
            # Update batch
            update_data = {
                'batchName': batch_name,
                'unitType': unit_type,
                'unit': unit_ref,
                'learners': learner_refs,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            # Add year and semester if provided
            year_of_batch = data.get('yearOfBatch', '').strip()
            semester = data.get('semester', '').strip()
            if year_of_batch:
                update_data['yearOfBatch'] = year_of_batch
            if semester:
                update_data['semester'] = semester
            
            batch_ref.update(update_data)
            
            return JsonResponse({
                'success': True,
                'message': 'Batch updated successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def delete_batch(request, batch_id):
    """API endpoint to delete a batch."""
    if request.method == 'POST':
        try:
            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)
            
            # Delete the batch
            batch_ref.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Batch deleted successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def toggle_batch_status(request, batch_id):
    """API endpoint to toggle batch status between active and inactive."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status', '').strip().lower()

            if new_status not in ['active', 'inactive']:
                return JsonResponse({'error': 'Invalid status. Must be "active" or "inactive"'}, status=400)

            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()

            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)

            # Update the batch status
            batch_ref.update({'status': new_status})

            message = f'Batch marked as {new_status} successfully'
            if new_status == 'inactive':
                message += '. This batch will no longer appear in the create assessment dropdown.'

            return JsonResponse({
                'success': True,
                'message': message
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def remove_learners_from_batch(request, batch_id):
    """API endpoint to remove learners from a batch."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            learner_ids = data.get('learnerIds', [])
            
            if not learner_ids:
                return JsonResponse({'error': 'At least one learner ID is required'}, status=400)
            
            # Check if batch exists
            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)
            
            batch_data = batch_doc.to_dict()
            current_learners = batch_data.get('learners', [])
            
            # Find learners to remove
            learners_to_remove = []
            for learner_ref in current_learners:
                if learner_ref.id in learner_ids:
                    learners_to_remove.append(learner_ref)
            
            if not learners_to_remove:
                return JsonResponse({
                    'success': True,
                    'message': 'No learners found to remove'
                }, status=200)
            
            # Remove learners from batch
            batch_ref.update({
                'learners': firestore.ArrayRemove(learners_to_remove),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(learners_to_remove)} learner(s) removed successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def add_learners_to_batch(request, batch_id):
    """API endpoint to add learners to a batch."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            learner_ids = data.get('learnerIds', [])
            
            if not learner_ids:
                return JsonResponse({'error': 'At least one learner ID is required'}, status=400)
            
            # Check if batch exists
            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)
            
            batch_data = batch_doc.to_dict()
            current_learners = batch_data.get('learners', [])
            current_learner_ids = [ref.id for ref in current_learners]
            
            # Filter out learners that are already in the batch
            new_learner_ids = [lid for lid in learner_ids if lid not in current_learner_ids]
            
            if not new_learner_ids:
                return JsonResponse({
                    'success': True,
                    'message': 'All selected learners are already in the batch'
                }, status=200)
            
            # Get learner references
            new_learner_refs = []
            for learner_id in new_learner_ids:
                learner_ref = db.collection('Users').document(learner_id)
                if learner_ref.get().exists:
                    new_learner_refs.append(learner_ref)
            
            if not new_learner_refs:
                return JsonResponse({'error': 'No valid learners found'}, status=400)
            
            # Add learners to batch
            batch_ref.update({
                'learners': firestore.ArrayUnion(new_learner_refs),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(new_learner_refs)} learner(s) added successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def fetch_available_learners_for_batch(request, batch_id):
    """API endpoint to fetch available learners for a batch (excluding current learners)."""
    try:
        # Check if batch exists
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            return JsonResponse({'success': False, 'error': 'Batch not found'}, status=404)
        
        batch_data = batch_doc.to_dict()
        unit_type = batch_data.get('unitType')
        unit_ref = batch_data.get('unit')
        current_learners = batch_data.get('learners', [])
        current_learner_ids = [ref.id for ref in current_learners]
        
        if not unit_ref:
            return JsonResponse({'success': False, 'error': 'Batch has no unit assigned'}, status=400)
        
        unit_doc = unit_ref.get()
        if not unit_doc.exists:
            return JsonResponse({'success': False, 'error': 'Unit not found'}, status=404)
        
        # Get unit name
        if unit_type == 'institution':
            unit_name = unit_doc.to_dict().get('instituteName', '')
            user_field = 'institution'
        else:
            unit_name = unit_doc.to_dict().get('hospitalName', '')
            user_field = 'hospital'
        
        # Query all learners from the unit
        learners_ref = db.collection('Users').where(user_field, '==', unit_name).where('role', 'in', ['student', 'nurse'])
        available_learners = []
        
        for doc in learners_ref.stream():
            learner_data = doc.to_dict()
            is_current_learner = doc.id in current_learner_ids
            
            available_learners.append({
                'id': doc.id,
                'name': learner_data.get('name', 'N/A'),
                'email': learner_data.get('emailID', 'N/A'),
                'isCurrentLearner': is_current_learner
            })
        
        return JsonResponse({
            'success': True,
            'learners': available_learners,
            'unit_name': unit_name
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def fetch_batch_courses(request, batch_id):
    """API endpoint to fetch courses assigned to a batch."""
    try:
        # Check if batch exists
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            return JsonResponse({'success': False, 'error': 'Batch not found'}, status=404)
        
        batch_data = batch_doc.to_dict()
        course_refs = batch_data.get('courses', [])
        
        # Get course details
        courses = []
        for course_ref in course_refs:
            course_doc = course_ref.get()
            if course_doc.exists:
                course_data = course_doc.to_dict()
                if course_data.get("status").lower() != "active":
                    continue
                procedure_refs = course_data.get('procedures', [])
                
                # Get procedure names
                procedure_names = []
                for proc_ref in procedure_refs:
                    proc_doc = proc_ref.get()
                    if proc_doc.exists:
                        procedure_names.append(proc_doc.to_dict().get('procedureName', 'Unknown'))
                
                courses.append({
                    'id': course_ref.id,
                    'name': course_data.get('courseName', 'N/A'),
                    'description': course_data.get('description', ''),
                    'procedures': procedure_names,
                    'procedure_count': len(procedure_names),
                    'osce_types': course_data.get('osceTypes', []),
                    'verification_required': course_data.get('verificationRequired', False),
                    'status': course_data.get('status', 'active')
                })
        
        return JsonResponse({
            'success': True,
            'courses': courses
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def add_courses_to_batch(request, batch_id):
    """API endpoint to add courses to a batch."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            course_ids = data.get('courseIds', [])
            
            if not course_ids:
                return JsonResponse({'error': 'At least one course ID is required'}, status=400)
            
            # Check if batch exists
            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)
            
            batch_data = batch_doc.to_dict()
            current_courses = batch_data.get('courses', [])
            current_course_ids = [ref.id for ref in current_courses]
            
            # Filter out courses that are already in the batch
            new_course_ids = [cid for cid in course_ids if cid not in current_course_ids]
            
            if not new_course_ids:
                return JsonResponse({
                    'success': True,
                    'message': 'All selected courses are already in the batch'
                }, status=200)
            
            # Get course references
            new_course_refs = []
            for course_id in new_course_ids:
                course_ref = db.collection('Courses').document(course_id)
                if course_ref.get().exists:
                    new_course_refs.append(course_ref)
            
            if not new_course_refs:
                return JsonResponse({'error': 'No valid courses found'}, status=400)
            
            # Add courses to batch
            batch_ref.update({
                'courses': firestore.ArrayUnion(new_course_refs),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(new_course_refs)} course(s) added successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def remove_courses_from_batch(request, batch_id):
    """API endpoint to remove courses from a batch."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            course_ids = data.get('courseIds', [])
            
            if not course_ids:
                return JsonResponse({'error': 'At least one course ID is required'}, status=400)
            
            # Check if batch exists
            batch_ref = db.collection('Batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return JsonResponse({'error': 'Batch not found'}, status=404)
            
            batch_data = batch_doc.to_dict()
            current_courses = batch_data.get('courses', [])
            
            # Find courses to remove
            courses_to_remove = []
            for course_ref in current_courses:
                if course_ref.id in course_ids:
                    courses_to_remove.append(course_ref)
            
            if not courses_to_remove:
                return JsonResponse({
                    'success': True,
                    'message': 'No courses found to remove'
                }, status=200)
            
            # Remove courses from batch
            batch_ref.update({
                'courses': firestore.ArrayRemove(courses_to_remove),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(courses_to_remove)} course(s) removed successfully'
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def fetch_available_courses_for_batch(request, batch_id):
    """API endpoint to fetch available courses for a batch (excluding current courses)."""
    try:
        # Check if batch exists
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            return JsonResponse({'success': False, 'error': 'Batch not found'}, status=404)
        
        batch_data = batch_doc.to_dict()
        current_courses = batch_data.get('courses', [])
        current_course_ids = [ref.id for ref in current_courses]
        
        # Query all active courses
        courses_ref = db.collection('Courses').where('status', '==', 'active')
        available_courses = []
        
        for doc in courses_ref.stream():
            course_data = doc.to_dict()
            is_current_course = doc.id in current_course_ids
            
            procedure_refs = course_data.get('procedures', [])
            procedure_names = []
            for proc_ref in procedure_refs:
                proc_doc = proc_ref.get()
                if proc_doc.exists:
                    procedure_names.append(proc_doc.to_dict().get('procedureName', 'Unknown'))
            
            available_courses.append({
                'id': doc.id,
                'name': course_data.get('courseName', 'N/A'),
                'description': course_data.get('description', ''),
                'procedures': procedure_names,
                'procedure_count': len(procedure_names),
                'osce_types': course_data.get('osceTypes', []),
                'verification_required': course_data.get('verificationRequired', False),
                'isCurrentCourse': is_current_course
            })
        
        return JsonResponse({
            'success': True,
            'courses': available_courses
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def fetch_batches_for_course(request, course_id):
    """
    API endpoint to fetch all batches assigned to a course, with optional filters and pagination.
    """
    try:
        # Get filter parameters
        search = request.GET.get('search', '').strip().lower()
        unit_type = request.GET.get('unit_type', '').strip().lower()
        unit_name = request.GET.get('unit_name', '').strip().lower()
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        # Get the course document
        course_ref = db.collection('Courses').document(course_id)
        course_doc = course_ref.get()
        if not course_doc.exists:
            return JsonResponse({'success': False, 'error': 'Course not found'}, status=404)
        course_data = course_doc.to_dict()

        # Get all batches that have this course in their 'courses' array
        batches_ref = db.collection('Batches')
        batches = []
        for doc in batches_ref.stream():
            batch_data = doc.to_dict()
            course_refs = batch_data.get('courses', [])
            # Check if this batch has the course
            if any(ref.id == course_id for ref in course_refs):
                # Filtering
                batch_name = batch_data.get('batchName', '').lower()
                batch_unit_type = batch_data.get('unitType', '').lower()
                unit_ref = batch_data.get('unit')
                unit_name_val = ''
                if unit_ref:
                    unit_doc = unit_ref.get()
                    if unit_doc.exists:
                        if batch_unit_type == 'institution':
                            unit_name_val = unit_doc.to_dict().get('instituteName', '').lower()
                        else:
                            unit_name_val = unit_doc.to_dict().get('hospitalName', '').lower()
                if search and search not in batch_name:
                    continue
                if unit_type and unit_type != batch_unit_type:
                    continue
                if unit_name and unit_name != unit_name_val:
                    continue

                learners = batch_data.get('learners', [])
                batches.append({
                    'id': doc.id,
                    'batchName': batch_data.get('batchName', ''),
                    'unitType': batch_data.get('unitType', ''),
                    'unitName': unit_name_val.title(),
                    'learnerCount': len(learners),
                })

        # Pagination
        total_batches = len(batches)
        total_pages = (total_batches + page_size - 1) // page_size
        start = (page - 1) * page_size
        end = start + page_size
        paginated_batches = batches[start:end]

        return JsonResponse({
            'success': True,
            'batches': paginated_batches,
            'page': page,
            'total_pages': total_pages,
            'total_batches': total_batches
        }, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def fetch_batch_learners(request, batch_id):
    """API endpoint to fetch learners assigned to a batch with search and pagination."""
    try:
        # Get pagination and search parameters
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 10))
        search = request.GET.get('search', '').strip().lower()
        
        # Check if batch exists
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            return JsonResponse({'success': False, 'error': 'Batch not found'}, status=404)
        
        batch_data = batch_doc.to_dict()
        learner_refs = batch_data.get('learners', [])
        
        # Get learner details with filtering
        learners = []
        for learner_ref in learner_refs:
            learner_doc = learner_ref.get()
            if learner_doc.exists:
                learner_data = learner_doc.to_dict()
                learner_name = learner_data.get('name', '')
                learner_email = learner_data.get('emailID', '').lower()
                
                # Apply search filter
                if search and search not in learner_name and search not in learner_email:
                    continue
                
                learners.append({
                    'id': learner_doc.id,
                    'name': learner_name,
                    'email':learner_email
                })
        
        # Apply pagination
        total_learners = len(learners)
        paginated_learners = learners[offset:offset+limit]
        
        return JsonResponse({
            'success': True,
            'learners': paginated_learners,
            'total': total_learners,
            'offset': offset,
            'limit': limit
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def fetch_batch_courses_paginated(request, batch_id):
    """API endpoint to fetch courses assigned to a batch with search and pagination."""
    try:
        # Get pagination and search parameters
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 10))
        search = request.GET.get('search', '').strip().lower()
        
        # Check if batch exists
        batch_ref = db.collection('Batches').document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            return JsonResponse({'success': False, 'error': 'Batch not found'}, status=404)
        
        batch_data = batch_doc.to_dict()
        course_refs = batch_data.get('courses', [])
        
        # Get course details with filtering
        courses = []
        for course_ref in course_refs:
            course_doc = course_ref.get()
            if course_doc.exists:
                course_data = course_doc.to_dict()
                course_name = course_data.get('courseName', '').lower()
                
                # Apply search filter
                if search and search not in course_name:
                    continue
                
                procedure_refs = course_data.get('procedures', [])
                
                # Get procedure names
                procedure_names = []
                for proc_ref in procedure_refs:
                    proc_doc = proc_ref.get()
                    if proc_doc.exists:
                        procedure_names.append(proc_doc.to_dict().get('procedureName', 'Unknown'))
                
                courses.append({
                    'id': course_ref.id,
                    'name': course_data.get('courseName', 'N/A'),
                    'description': course_data.get('description', ''),
                    'procedures': procedure_names,
                    'procedure_count': len(procedure_names),
                    'osce_types': course_data.get('osceTypes', []),
                    'verification_required': course_data.get('verificationRequired', False),
                    'status': course_data.get('status', 'active')
                })
        
        # Apply pagination
        total_courses = len(courses)
        paginated_courses = courses[offset:offset+limit]
        
        return JsonResponse({
            'success': True,
            'courses': paginated_courses,
            'total': total_courses,
            'offset': offset,
            'limit': limit
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def fetch_student_report_data(skillathon_name, institute_name=None):
    """Helper function to fetch student report data from Firestore"""
    students = {}
    all_procedures = set()
    
    # Query Firestore for exam assignments
    exam_assignments_ref = db.collection('ExamAssignment')
    
    # Apply filters
    if skillathon_name:
        exam_assignments_ref = exam_assignments_ref.where('skillathon', '==', skillathon_name)
    if institute_name:
        exam_assignments_ref = exam_assignments_ref.where('institution', '==', institute_name)
    
    exam_assignments = exam_assignments_ref.stream()
    
    for exam in exam_assignments:
        exam_doc = exam.to_dict()
        email = exam_doc.get('emailID')
        if not email:
            continue
            
        if email not in students:
            students[email] = {
                'name': '',
                'institute': '',
                'grades': {},
                'missed_critical_steps': {},
                'exam_data': {}
            }
        
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
        
        # Missed critical steps
        missed_critical = []
        for section in exam_doc.get("examMetaData", []):
            for question in section.get("section_questions", []):
                if question.get("critical") and question.get("answer_scored", 0) == 0:
                    missed_critical.append(question.get('question'))
        
        # Store per procedure
        students[email]['grades'][procedure_name] = {
            'grade': grade,
            'percentage': percentage
        }
        students[email]['missed_critical_steps'][procedure_name] = missed_critical
    
    return students, all_procedures


def generate_pdf_report(students, all_procedures, skillathon_name, institute_name=None):
    """Generate PDF report from student data"""
    # Create PDF with landscape orientation for better table display
    from reportlab.lib.pagesizes import landscape, A4
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=36, leftMargin=36, topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=0  # Left alignment
    )
    
    # Build content
    story = []
    
    # Title
    title = Paragraph(f"Candidate Performance Report - {skillathon_name}", title_style)
    story.append(title)
    
    # Report info
    report_info = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if institute_name:
        report_info += f"<br/>Institute: {institute_name}"
    story.append(Paragraph(report_info, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Create table data
    table_data = [['Candidate Name', 'Institute'] + list(all_procedures)]
    
    for email, student in students.items():
        row = [student['name'], student['institute']]
        for procedure in all_procedures:
            if procedure in student['grades']:
                grade_info = student['grades'][procedure]
                missed_steps = student['missed_critical_steps'].get(procedure, [])
                cell_text = f"{grade_info['grade']} ({grade_info['percentage']}%)"
                if missed_steps:
                    cell_text += f" ⚠"
                row.append(cell_text)
            else:
                row.append('-')
        table_data.append(row)
    
    # Create table with better column sizing
    table = Table(table_data, repeatRows=1)
    
    # Calculate column widths dynamically
    num_cols = len(table_data[0]) if table_data else 0
    available_width = landscape(A4)[0] - 72  # Total width minus margins
    
    if num_cols > 2:
        student_width = available_width * 0.20
        institute_width = available_width * 0.25
        procedure_width = (available_width * 0.55) / (num_cols - 2)
        col_widths = [student_width, institute_width] + [procedure_width] * (num_cols - 2)
    else:
        col_widths = [available_width * 0.5, available_width * 0.5]
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer


def generate_excel_report(students, all_procedures, skillathon_name, institute_name=None):
    """Generate Excel report from student data"""
    # Create Excel file
    buffer = BytesIO()
    workbook = xlsxwriter.Workbook(buffer)
    worksheet = workbook.add_worksheet('Candidate Performance Report')
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    warning_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#FFE6E6'
    })
    
    # Write title
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center'
    })
    worksheet.merge_range('A1:D1', f'Candidate Performance Report - {skillathon_name}', title_format)
    
    # Write report info
    info_row = 2
    worksheet.write(info_row, 0, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    if institute_name:
        worksheet.write(info_row + 1, 0, f'Institute: {institute_name}')
        info_row += 1
    
    # Write headers
    header_row = info_row + 2
    headers = ['Candidate Name', 'Institute'] + list(all_procedures)
    for col, header in enumerate(headers):
        worksheet.write(header_row, col, header, header_format)
    
    # Write data
    data_row = header_row + 1
    for email, student in students.items():
        worksheet.write(data_row, 0, student['name'], cell_format)
        worksheet.write(data_row, 1, student['institute'], cell_format)
        
        for col, procedure in enumerate(all_procedures, 2):
            if procedure in student['grades']:
                grade_info = student['grades'][procedure]
                missed_steps = student['missed_critical_steps'].get(procedure, [])
                cell_text = f"{grade_info['grade']} ({grade_info['percentage']}%)"
                if missed_steps:
                    cell_text += f" ⚠"
                    worksheet.write(data_row, col, cell_text, warning_format)
                else:
                    worksheet.write(data_row, col, cell_text, cell_format)
            else:
                worksheet.write(data_row, col, '-', cell_format)
        data_row += 1
    
    # Auto-adjust column widths
    worksheet.set_column('A:A', 20)  # Student Name
    worksheet.set_column('B:B', 25)  # Institute
    for col in range(2, len(headers)):
        worksheet.set_column(col, col, 50)  # Procedure columns
    
    workbook.close()
    buffer.seek(0)
    
    return buffer


@login_required
@csrf_exempt
def download_student_report(request):
    """Download student performance report as PDF or Excel based on format parameter"""
    try:
        # Get parameters from request
        skillathon_name = request.GET.get('skillathon_name', '')
        institute_name = request.GET.get('institute_name', '')
        format_type = request.GET.get('format', 'pdf').lower()
        
        if not skillathon_name:
            return JsonResponse({'error': 'Skillathon name is required'}, status=400)
        
        if format_type not in ['pdf', 'excel']:
            return JsonResponse({'error': 'Format must be either pdf or excel'}, status=400)
        
        # Fetch student data
        students, all_procedures = fetch_student_report_data(skillathon_name, institute_name)
        
        # Generate file based on format
        if format_type == 'pdf':
            buffer = generate_pdf_report(students, all_procedures, skillathon_name, institute_name)
            content_type = 'application/pdf'
            file_extension = 'pdf'
        else:  # excel
            buffer = generate_excel_report(students, all_procedures, skillathon_name, institute_name)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            file_extension = 'xlsx'
        
        # Create filename
        filename = f"candidate_report_{skillathon_name}.{file_extension}"
        if institute_name:
            filename = f"candidate_report_{skillathon_name}_{institute_name}.{file_extension}"
        
        # Create response
        response = HttpResponse(buffer.getvalue(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"Report generation error: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def create_roles(request):
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_name = data.get('name').strip()
            description = data.get('description', '').strip()
            permission_codes = data.get('permissions', [])
            
            if not role_name:
                return JsonResponse({'error': 'Role name is required'}, status=400)
            
            # Get permission objects
            permissions = Permission.objects.filter(code__in=permission_codes, is_active=True)

            # Ensure exact set uniqueness
            requested_permission_ids = set(permissions.values_list('id', flat=True))
            existing_same_permissions = CustomRole.objects.annotate(perm_count=Count('permissions')).filter(perm_count=len(requested_permission_ids))
            for role in existing_same_permissions:
                if set(role.permissions.order_by('id').values_list('id', flat=True)) == requested_permission_ids:
                    return JsonResponse({'error': 'Role with the same set of permissions already exists'}, status=400)
            
            # Create CustomRole
            custom_role, created = CustomRole.objects.get_or_create(
                name=role_name,
                defaults={
                    'description': description,
                    'created_by': request.user if request.user.is_authenticated else None
                }
            )
            
            if not created:
                return JsonResponse({'error': 'Role with this name already exists'}, status=400)
            
            # Add permissions to the role
            custom_role.permissions.set(permissions)
            
            return JsonResponse({
                'success': True,
                'message': f'Role "{role_name}" created successfully',
                'role_id': custom_role.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - render the form
    permissions = Permission.objects.filter(is_active=True).order_by('category', 'name')
    return render(request, 'assessments/create_roles.html', {
        'permissions': permissions
    })

def get_roles(request):
    """API endpoint to fetch all roles"""
    try:
        roles = []
        for role in CustomRole.objects.all():
            role_data = {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'permissions': role.get_permission_codes(),
                'permissions_count': role.permissions.count()
            }
            roles.append(role_data)
        return JsonResponse({
            'success': True,
            'roles': roles
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def edit_role(request, role_id):
    """API endpoint to edit a role"""
    import json
    
    if request.method == 'GET':
        try:
            role = CustomRole.objects.get(id=role_id)
            role_data = {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'permissions': role.get_permission_codes()
            }
            
            return JsonResponse({'role': role_data})
        except CustomRole.DoesNotExist:
            return JsonResponse({'error': 'Role not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            role_name = data.get('name').strip()
            description = data.get('description', '').strip()
            permission_codes = data.get('permissions', [])
            
            if not role_name:
                return JsonResponse({'error': 'Role name is required'}, status=400)
            
            try:
                role = CustomRole.objects.get(id=role_id)
            except CustomRole.DoesNotExist:
                return JsonResponse({'error': 'Role not found'}, status=404)
            
            # Check if another role with the same name exists (excluding current role)
            if CustomRole.objects.filter(name=role_name).exclude(id=role_id).exists():
                return JsonResponse({'error': 'Role with this name already exists'}, status=400)
            
            # Get permission objects
            permissions = Permission.objects.filter(code__in=permission_codes, is_active=True)
            
            # Update role
            role.name = role_name
            role.description = description
            role.save()
            
            # Update permissions
            role.permissions.set(permissions)

            all_users = EbekUser.objects.filter(custom_roles__in=[role])
            for u in all_users:
                u.user_permissions_custom.set(role.permissions.all())
                u.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Role "{role_name}" updated successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def delete_role(request, role_id):
    """API endpoint to delete a role"""
    if request.method == 'POST':
        try:
            role = CustomRole.objects.get(id=role_id)
            role_name = role.name
            all_users = EbekUser.objects.filter(custom_roles__in=[role])
            for u in all_users:
                u.user_permissions_custom.set([])
                u.custom_roles = None
                u.save()
            role.delete()
            return JsonResponse({
                'success': True,
                'message': f'Role "{role_name}" deleted successfully'
            })
        except CustomRole.DoesNotExist:
            return JsonResponse({'error': 'Role not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def assign_roles(request):
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            role_ids = data.get('role_ids', [])
            
            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)
            
            try:
                user = EbekUser.objects.get(id=user_id)
            except EbekUser.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Add new custom roles
            for role_id in role_ids:
                try:
                    custom_role = CustomRole.objects.get(id=role_id)
                    user.custom_roles.add(custom_role)
                except CustomRole.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'Roles assigned successfully to {user.email}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - render the form
    # Build users with custom roles via model helper (no extra API needed)
    users_qs = EbekUser.objects.exclude(user_role__in=['nurse', 'student'])
    users = []
    for u in users_qs:
        users.append({
            'id': u.id,
            'email': u.email,
            'full_name': u.full_name or u.email,
            'is_active': u.is_active,
            'access_all_institutes': u.access_all_institutions,
            'access_all_hospitals': u.access_all_hospitals,
            'access_all_skillathons': u.access_all_skillathons,
            'custom_roles': [{'id': r.id, 'name': r.name, 'description': r.description} for r in u.get_all_roles()],
        })

    roles = CustomRole.objects.all().values('id', 'name', 'description')
    import json
    users_json = json.dumps(users)
    
    return render(request, 'assessments/assign_roles.html', {
        'users': users,
        'users_json': users_json,
        'roles': list(roles)
    })

@csrf_exempt
def get_user(request, user_id):
    """Fetch single user with custom roles, access flags and assigned units."""
    try:
        user = EbekUser.objects.get(id=user_id)
        data = {
            'id': user.id,
            'name': user.full_name or '',
            'email': user.email,
            'phone': user.phone_number or '',
            'access_types': [t for t in ['osce' if user.allowed_to_take_osce else None, 'skillathon' if user.allowed_to_take_skillathon else None] if t],
            'institution_ids': list(user.assigned_institutions.values_list('id', flat=True)),
            'hospital_ids': list(user.assigned_hospitals.values_list('id', flat=True)),
            'skillathon_ids': list(user.assigned_skillathons.values_list('id', flat=True)),
            'access_all_institutes': user.access_all_institutions,
            'access_all_hospitals': user.access_all_hospitals,
            'access_all_skillathons': user.access_all_skillathons,
            'custom_roles': {'id': user.custom_roles.id, 'name': user.custom_roles.name, 'description': user.custom_roles.description} if user.custom_roles else []
        }
        return JsonResponse({'user': data})
    except EbekUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_user(request, user_id):
    """Delete a user from Django and Firebase."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        user = EbekUser.objects.get(id=user_id)
        user.delete()
        return JsonResponse({'success': True, 'message': f'User {user.email} deleted'})
    except EbekUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def create_user(request):
    """Comprehensive user creation API with Firebase integration"""
    import json
    import threading
    from django.core.mail import send_mail
    from django.conf import settings
    from .firebase_sync import sync_user_to_firestore, sync_user_to_firebase_auth
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        # Extract basic user data
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        if EbekUser.objects.filter(email=email, phone_number=phone).exists():
            return JsonResponse({'error': 'User with this email and mobile number already exists'}, status=400)
        access_types = data.get('access_types', [])
        institution_ids = data.get('institution_ids', [])  
        hospital_ids = data.get('hospital_ids', [])  
        skillathon_ids = data.get('skillathon_ids', [])  
        access_all_institutes = data.get('access_all_institutes', False)
        access_all_hospitals = data.get('access_all_hospitals', False)
        access_all_skillathons = data.get('access_all_skillathons', False)
        role_id = data.get('role_id')
        # Derive permission ids from selected role if provided; otherwise keep empty
        try:
            permission_ids = list(CustomRole.objects.get(id=role_id).permissions.values_list('id', flat=True)) if role_id else []
        except CustomRole.DoesNotExist:
            permission_ids = []
        
        # Validation (institutions/hospitals/skillathons are optional)
        if not all([name, email, phone]):
            return JsonResponse({'error': 'Name, email, and phone are required'}, status=400)
        
        if not email or '@' not in email:
            return JsonResponse({'error': 'Valid email is required'}, status=400)
        
        # Check if user already exists
        if EbekUser.objects.filter(email=email).exists():
            return JsonResponse({'error': 'User with this email already exists'}, status=400)
        
        
        # For regular users, determine permissions based on access types
        allowed_to_take_osce = 'osce' in access_types
        allowed_to_take_skillathon = 'skillathon' in access_types
        
        # Get institution, hospital, and skillathon objects
        institutions = []
        hospitals = []
        skillathons = []
        permissions = []
        
        # Validate and get institutions (optional)
        for inst_id in institution_ids or []:
            try:
                institution = Institution.objects.get(id=inst_id)
                institutions.append(institution)
            except Institution.DoesNotExist:
                return JsonResponse({'error': f'Institution with ID {inst_id} not found'}, status=400)
        
        # Validate and get hospitals
        for hosp_id in hospital_ids or []:
            try:
                hospital = Hospital.objects.get(id=hosp_id)
                hospitals.append(hospital)
            except Hospital.DoesNotExist:
                return JsonResponse({'error': f'Hospital with ID {hosp_id} not found'}, status=400)
        
        # Validate and get skillathons
        for skill_id in skillathon_ids or []:
            try:
                skillathon = SkillathonEvent.objects.get(id=skill_id)
                skillathons.append(skillathon)
            except SkillathonEvent.DoesNotExist:
                return JsonResponse({'error': f'Skillathon with ID {skill_id} not found'}, status=400)
        
        # Validate and get permissions
        for perm_id in permission_ids:
            try:
                permission = Permission.objects.get(id=perm_id)
                permissions.append(permission)
            except Permission.DoesNotExist:
                return JsonResponse({'error': f'Permission with ID {perm_id} not found'}, status=400)
        
        # Create user with temporary password
        temp_password = "TempPass123!"
        # Assign custom role if provided
        if role_id:
            custom_role = CustomRole.objects.get(id=role_id)
        else:
            custom_role = None

        user = EbekUser.objects.create_user(
            email=email,
            password=temp_password,
            full_name=name,
            phone_number=phone,
            allowed_to_take_osce=allowed_to_take_osce,
            allowed_to_take_skillathon=allowed_to_take_skillathon,
            access_all_institutions=access_all_institutes,
            access_all_hospitals=access_all_hospitals,
            access_all_skillathons=access_all_skillathons,
            custom_roles=custom_role
        )
        
        # Assign many-to-many relationships
        if access_all_institutes:
            user.assigned_institutions.set(Institution.objects.all())
        else:
            user.assigned_institutions.set(institutions)
        if access_all_hospitals:
            user.assigned_hospitals.set(Hospital.objects.all())
        else:
            user.assigned_hospitals.set(hospitals)
        if access_all_skillathons:
            user.assigned_skillathons.set(SkillathonEvent.objects.all())
        else:
            user.assigned_skillathons.set(skillathons)
        if permissions:
            user.user_permissions_custom.set(permissions)
        
        # Send welcome email in a separate thread
        def send_welcome_email():
            try:
                subject = 'Welcome to EBEK Platform'
                message = f'''
                Hello {name},
                
                Your account has been created successfully!
                
                Login Details:
                Email: {email}
                Temporary Password: {temp_password}
                
                Please change your password after first login.
                
                Access Permissions:
                - Take OSCE: {'Yes' if allowed_to_take_osce else 'No'}
                - Take Skillathon: {'Yes' if allowed_to_take_skillathon else 'No'}
                
                {f'Assigned Institutions: {", ".join([inst.name for inst in institutions])}' if institutions else ''}
                {f'Assigned Hospitals: {", ".join([hosp.name for hosp in hospitals])}' if hospitals else ''}
                {f'Assigned Skillathons: {", ".join([skill.name for skill in skillathons])}' if skillathons else ''}
                {f'Assigned Permissions: {", ".join([perm.name for perm in permissions])}' if permissions else ''}
                
                Best regards,
                EBEK Team
                '''
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Email sending error: {e}")
        
        # Start email sending in background thread
        email_thread = threading.Thread(target=send_welcome_email)
        email_thread.daemon = True
        email_thread.start()
        
        return JsonResponse({
            'success': True,
            'message': f'User "{name}" created successfully',
            'user_id': user.id,
            'email': user.email,
            'temporary_password': temp_password
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        try:
            import traceback as _tb
            _tb.print_exc()
        except Exception:
            pass
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def update_user(request, user_id):
    """API to update user information including permissions and assignments"""
    import json
    import threading
    from django.core.mail import send_mail
    from django.conf import settings
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Get user
        try:
            user = EbekUser.objects.get(id=user_id)
        except EbekUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Extract data
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        access_types = data.get('access_types', [])
        institution_ids = data.get('institution_ids', [])
        hospital_ids = data.get('hospital_ids', [])
        skillathon_ids = data.get('skillathon_ids', [])
        role_id = data.get('role_id')
        permission_ids = data.get('permission_ids', [])
        access_all_institutes = data.get('access_all_institutes', False)
        access_all_hospitals = data.get('access_all_hospitals', False)
        access_all_skillathons = data.get('access_all_skillathons', False)
        # Align permission derivation with create_user: if role provided, derive permissions
        if role_id:
            try:
                permission_ids = list(CustomRole.objects.get(id=role_id).permissions.values_list('id', flat=True))
                print(permission_ids)
            except CustomRole.DoesNotExist:
                permission_ids = []
        is_active = data.get('is_active', True)
        
        # Update basic fields
        if name:
            user.full_name = name
        if email and email != user.email:
            # Check if new email already exists
            if EbekUser.objects.filter(email=email).exclude(id=user_id).exists():
                return JsonResponse({'error': 'User with this email already exists'}, status=400)
            user.email = email
        if phone:
            user.phone_number = phone
        
        user.is_active = is_active
        
        # Update permissions
        user.allowed_to_take_osce = 'osce' in access_types
        user.allowed_to_take_skillathon = 'skillathon' in access_types
        user.access_all_institutions = access_all_institutes
        user.access_all_hospitals = access_all_hospitals
        user.access_all_skillathons = access_all_skillathons
        
        # Update many-to-many assignments
        institutions = []
        hospitals = []
        skillathons = []
        permissions = []
        
        # Validate and get institutions
        for inst_id in institution_ids or []:
            try:
                institution = Institution.objects.get(id=inst_id)
                institutions.append(institution)
            except Institution.DoesNotExist:
                return JsonResponse({'error': f'Institution with ID {inst_id} not found'}, status=400)
        
        # Validate and get hospitals
        for hosp_id in hospital_ids or []:
            try:
                hospital = Hospital.objects.get(id=hosp_id)
                hospitals.append(hospital)
            except Hospital.DoesNotExist:
                return JsonResponse({'error': f'Hospital with ID {hosp_id} not found'}, status=400)
        
        # Validate and get skillathons
        for skill_id in skillathon_ids or []:
            try:
                skillathon = SkillathonEvent.objects.get(id=skill_id)
                skillathons.append(skillathon)
            except SkillathonEvent.DoesNotExist:
                return JsonResponse({'error': f'Skillathon with ID {skill_id} not found'}, status=400)
        
        # Validate and get permissions
        for perm_id in permission_ids:
            try:
                permission = Permission.objects.get(id=perm_id)
                permissions.append(permission)
            except Permission.DoesNotExist:
                return JsonResponse({'error': f'Permission with ID {perm_id} not found'}, status=400)
        
        # Update many-to-many relationships
        if access_all_institutes:
            user.assigned_institutions.set(Institution.objects.all())
        else:
            user.assigned_institutions.set(institutions)
        if access_all_hospitals:
            user.assigned_hospitals.set(Hospital.objects.all())
        else:
            user.assigned_hospitals.set(hospitals)
        if access_all_skillathons:
            user.assigned_skillathons.set(SkillathonEvent.objects.all())
        else:
            user.assigned_skillathons.set(skillathons)
        user.user_permissions_custom.set(permissions)
        
        # Update custom roles
        if role_id:
            try:
                custom_role = CustomRole.objects.get(id=role_id)
                user.custom_roles = custom_role
            except CustomRole.DoesNotExist:
                return JsonResponse({'error': 'Selected role not found'}, status=400)
        else:
            user.custom_roles = None
        
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'User "{user.full_name}" updated successfully',
            'user_id': user.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
def toggle_user_active(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
        is_active = payload.get('is_active')
        if is_active is None:
            return JsonResponse({'error': 'Missing is_active flag'}, status=400)

        try:
            user = EbekUser.objects.get(id=user_id)
        except EbekUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

        user.is_active = bool(is_active)
        user.save(update_fields=['is_active'])

        return JsonResponse({
            'success': True,
            'message': f'User "{user.full_name or user.email}" is now {"active" if user.is_active else "inactive"}',
            'is_active': user.is_active,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

def update_test_status(request, test_id, status):
    try:
        print(test_id, status)
        test_ref = db.collection('Test').document(test_id)
        print(test_ref)
        test_doc = test_ref.get()
        if not test_doc.exists:
            return JsonResponse({'error': 'Test not found'}, status=404)
        test_ref.update({'status': status})
        procedure_assignments = test_doc.to_dict().get('procedureAssignments', [])
        for procedure_assignment_ref in procedure_assignments:
            procedure_assignment_doc = procedure_assignment_ref.get()
            if not procedure_assignment_doc.exists:
                return JsonResponse({'error': 'Procedure assignment not found'}, status=404)
            procedure_assignment_ref.update({'status': status})
        return JsonResponse({'success': True})
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

        if not status:
            return JsonResponse({'error': 'Status is required'}, status=400)




@csrf_exempt
def fetch_assessments(request):
    """API endpoint to fetch all assessments (procedures) with pagination, search, status, and category filters."""
    try:
        # --- Query Parameters ---
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 10))
        search = request.GET.get('search', '').strip().lower()
        status_filters = request.GET.getlist('status')
        status_filters = [s.lower() for s in status_filters if s]
        category_filters = request.GET.getlist('category')  # <-- Add this line
        category_filters = [c.lower() for c in category_filters if c]

        # --- Fetch Data from Firestore ---
        procedures_ref = db.collection('ProcedureTable')
        all_docs = list(procedures_ref.stream())

        filtered_docs = []

        for doc in all_docs:
            data = doc.to_dict()
            name = data.get('procedureName', 'N/A')
            examMetaData = data.get("examMetaData", [])
            active = data.get("active", True)
            status = 'active' if active else 'inactive'

            # Extract Category
            category = 'N/A'
            if examMetaData:
                section = examMetaData[0]
                section_questions = section.get("section_questions", [])
                if section_questions:
                    category = section_questions[0].get("category", "N/A")

            # --- Apply Filters ---
            if search and search not in name.lower():
                continue
            if status_filters and status not in status_filters:
                continue
            if category_filters and category.lower() not in category_filters:
                continue

            # --- Count Questions ---
            question_count = sum(len(section.get("section_questions", []))
                                 for section in examMetaData if isinstance(section, dict))

            filtered_docs.append({
                'id': doc.id,
                'name': name,
                'questions': question_count,
                'active': active,
                'category': category,
                'status': status
            })

        # --- Pagination ---
        total_items = len(filtered_docs)
        paginated = filtered_docs[offset:offset + limit]
        all_loaded = offset + limit >= total_items

        return JsonResponse({
            'assessments': paginated,
            'all_loaded': all_loaded,
            'total_count': total_items
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def upload_preview(request):
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded'})

    try:
        # Read Excel, header assumed at row 1 (0-indexed)
        df = pd.read_excel(file, header=0)

        # Clean column names (strip spaces)
        df.columns = df.columns.str.strip()

        # Replace NaN with empty string for preview
        preview_data = df.head(10).fillna('').to_dict(orient='records')

        # Required headers
        required_columns = [
            'Section', 'Parameters', 'Indicators',
            'Category (i.e C for Communication, K for Knowledge and D for Documentation)',
            'Marks', 'Critical'
        ]
        missing_cols = [col for col in required_columns if col not in df.columns]

        errors = []
        if missing_cols:
            errors.append({'row': '-', 'message': f'Missing columns: {", ".join(missing_cols)}'})

        parameters_seen = set()

        for idx, row in df.iterrows():
            row_number = idx + 2  # Excel row number

            # Section required
            if str(row.get('Section')).strip() == '':
                errors.append({'row': row_number, 'message': 'Section is required'})

            # Parameters required + uniqueness
            param = str(row.get('Parameters')).strip()
            if param == '':
                errors.append({'row': row_number, 'message': 'Parameters is required'})
            elif param in parameters_seen:
                errors.append({'row': row_number, 'message': f'Duplicate Parameters: {param}'})
            else:
                parameters_seen.add(param)

            # Marks must be int
            marks = row.get('Marks')
            if marks == '' or pd.isna(marks):
                errors.append({'row': row_number, 'message': 'Marks is required'})
            else:
                try:
                    int(marks)
                except ValueError:
                    errors.append({'row': row_number, 'message': 'Marks must be an integer'})

            # Critical must be boolean
            critical = str(row.get('Critical')).strip().lower()
            if critical not in ['true', 'false', '1', '0']:
                errors.append({'row': row_number, 'message': 'Critical must be boolean (True/False)'})

        return JsonResponse({
            'status': 'success',
            'preview': preview_data,
            'validation': errors,
            'total_rows': len(df)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
@login_required
def get_procedure_for_edit(request, procedure_id):
    """API endpoint to fetch procedure data for editing"""
    try:
        procedure_ref = db.collection('ProcedureTable').document(procedure_id)
        procedure_doc = procedure_ref.get()
        
        if not procedure_doc.exists:
            return JsonResponse({'status': 'error', 'message': 'Procedure not found'}, status=404)
        
        procedure_data = procedure_doc.to_dict()
        
        return JsonResponse({
            'status': 'success',
            'procedure': {
                'id': procedure_id,
                'procedureName': procedure_data.get('procedureName', ''),
                'category': procedure_data.get('category', ''),
                'examMetaData': procedure_data.get('examMetaData', []),
                'notes': procedure_data.get('notes', ''),
                'active': procedure_data.get('active', True)
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@login_required
@require_POST
def update_procedure(request):
    """API endpoint to update procedure data"""
    try:
        import json
        data = json.loads(request.body)
        
        procedure_id = data.get('procedure_id')
        procedure_name = data.get('procedure_name', '').strip()
        category = data.get('category', '').strip()
        exam_meta_data = data.get('exam_meta_data', [])
        
        if not procedure_id:
            return JsonResponse({'status': 'error', 'message': 'Procedure ID is required'}, status=400)
        
        if not procedure_name:
            return JsonResponse({'status': 'error', 'message': 'Procedure name is required'}, status=400)
        
        if not category:
            return JsonResponse({'status': 'error', 'message': 'Category is required'}, status=400)
        
        # Get existing procedure
        procedure_ref = db.collection('ProcedureTable').document(procedure_id)
        procedure_doc = procedure_ref.get()

        if not procedure_doc.exists:
            return JsonResponse({'status': 'error', 'message': 'Procedure not found'}, status=404)

        # Check if another procedure with the same name exists (excluding current procedure)
        existing_procedure_data = procedure_doc.to_dict()
        current_name = existing_procedure_data.get('procedureName', '')

        # Only check for duplicates if the name is being changed
        if procedure_name != current_name:
            duplicate_procedures = db.collection('ProcedureTable').where('procedureName', '==', procedure_name).limit(1).stream()
            duplicate_list = list(duplicate_procedures)

            if duplicate_list:
                return JsonResponse({
                    'status': 'error',
                    'message': f'A procedure with the name "{procedure_name}" already exists. Please use a different name.'
                }, status=400)

        print(exam_meta_data)
        # Check for duplicate steps in exam_meta_data
        if exam_meta_data:
            step_texts = []
            for step in exam_meta_data[0]["section_questions"]:
                step_text = step.get('question', '').strip().lower()
                print(step_text)
                if step_text:
                    if step_text in step_texts:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Duplicate step found: "{step.get("question", "").strip()}". Each step must have unique wording.'
                        }, status=400)
                    step_texts.append(step_text)

        # Update procedure
        update_data = {
            'procedureName': procedure_name,
            'category': category,
            'examMetaData': exam_meta_data
        }

        procedure_ref.update(update_data)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Procedure updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error updating procedure: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def upload_excel(request):
    file = request.FILES.get('file')
    procedure_name = request.POST.get('procedure_name')
    category = request.POST.get('category')

    if not file:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded'})

    try:
        # Save the file to MEDIA_ROOT/uploaded_excels/
        file_name = f"{uuid.uuid4()}_{file.name}".replace(" ", "_")
        file_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_excels', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

        # Now read it via pandas
        df = pd.read_excel(file_path)

        # --- Your existing processing logic ---
        df.columns = df.columns.str.strip()
        required_columns = [
            'Section', 'Parameters',
            'Marks', 'Critical'
        ]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return JsonResponse({'status': 'error', 'message': f'Missing columns: {", ".join(missing_cols)}'})

        # Convert Marks and Critical
        df['Marks'] = pd.to_numeric(df['Marks'], errors='coerce').fillna(0).astype(int)
        df['Critical'] = df['Critical'].astype(str).str.lower().map({'true': True, 'false': False, '1': True, '0': False}).fillna(False)

        # Fill missing strings
        df[['Section', 'Parameters', 'Indicators', 'Category (i.e C for Communication, K for Knowledge and D for Documentation)']] = \
            df[['Section', 'Parameters', 'Indicators', 'Category (i.e C for Communication, K for Knowledge and D for Documentation)']].fillna('')


        # Validate unique Parameters
        if df['Parameters'].duplicated().any():
            duplicates = df[df['Parameters'].duplicated(keep=False)]['Parameters'].tolist()
            return JsonResponse({'status': 'error', 'message': f'Duplicate Parameters found: {", ".join(duplicates)}'})

        success = len(df)
        updated = 0
        errors = 0

        # Note add code to add it to the firebase database

        df_data = pd.read_excel(file_path)
        parsed_json = parse_excel_to_json(df_data, procedure_name,category)

        # Check if procedure with same name already exists
        existing_procedures = db.collection('ProcedureTable').where('procedureName', '==', parsed_json['procedure_name']).limit(1).stream()
        existing_procedure_list = list(existing_procedures)

        if existing_procedure_list:
            # Ask user if they want to update existing procedure
            return JsonResponse({
                'status': 'error',
                'message': f'A procedure with the name "{parsed_json["procedure_name"]}" already exists. Please use a different name or delete the existing procedure first.'
            })

        # Upload to Firebase
        procedure_ref = db.collection('ProcedureTable').document()
        procedure_ref.set({
            "procedureName": parsed_json['procedure_name'],
            "category": category,  # Store category at procedure level
            "examMetaData": parsed_json['exammetadata'],
            "notes": parsed_json['notes'],
            "active": True
        })
        print(f"File uploaded successfully - {procedure_ref.id}")

        # logger.info(f"File uploaded successfully - {procedure_ref.id}")

        return JsonResponse({
            'status': 'success',
            'file_path': file_path,  
            'total_rows': len(df),
            'success': success,
            'updated': updated,
            'errors': errors
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ==================== ADMIN REPORT PORTAL ====================

@login_required
def render_admin_report_portal(request):
    """Render the admin report portal page"""
    if not request.user.check_icon_navigation_permissions('reports'):
        return HttpResponse('You are not authorized to access this page')
    return render(request, 'assessments/admin_report_portal.html')


@csrf_exempt
@login_required
def fetch_admin_report_filter_options(request):
    """Fetch filter options for admin report portal"""
    try:
        # Get academic years from batches
        batches = db.collection('Batches').stream()
        academic_years = set()
        for batch in batches:
            batch_data = batch.to_dict()
            year = batch_data.get('yearOfBatch', '')
            if year:
                academic_years.add(str(year))
        
        # Get institutions
        institutions = []
        if request.user.has_all_permissions():
            inst_queryset = Institution.objects.all()
        else:
            inst_queryset = request.user.assigned_institutions.all()
        
        for inst in inst_queryset:
            institutions.append({
                'id': inst.id,
                'name': inst.name,
                'state': inst.state or ''
            })
        
        # Get states
        states = set()
        for inst in Institution.objects.all():
            if inst.state:
                states.add(inst.state)
        
        # Get skills/procedures
        procedures = db.collection('Procedures').stream()
        skills = []
        for proc in procedures:
            proc_data = proc.to_dict()
            proc_name = proc_data.get('procedureName', '')
            if proc_name:
                skills.append(proc_name)
        
        return JsonResponse({
            'success': True,
            'academic_years': sorted(list(academic_years), reverse=True),
            'institutions': institutions,
            'states': sorted(list(states)),
            'skills': sorted(list(set(skills)))
        })
        
    except Exception as e:
        print(f"Error fetching filter options: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def fetch_admin_report_kpis(request):
    """Fetch KPI metrics for admin report portal with filters"""
    try:
        # Get filter parameters
        academic_year = request.GET.get('academic_year', '').strip()
        region = request.GET.get('region', '').strip()
        state = request.GET.get('state', '').strip()
        institution = request.GET.get('institution', '').strip()
        semester = request.GET.get('semester', '').strip()
        osce_level = request.GET.get('osce_level', '').strip()  # All/Classroom/Mock/Final
        category = request.GET.get('category', '').strip()
        skill = request.GET.get('skill', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        # Build query for ExamAssignment
        query = db.collection('ExamAssignment').where('status', '==', 'Completed')
        
        # Apply filters
        if osce_level and osce_level != 'All':
            query = query.where('examType', '==', osce_level)
        
        if skill:
            query = query.where('procedure_name', '==', skill)
        
        if date_from:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.where('completed_date', '>=', from_date)
        
        if date_to:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.where('completed_date', '<=', to_date)
        
        # Get all exam assignments
        exam_assignments = query.stream()
        
        # Get batch data for academic year and semester filtering
        batch_refs = {}
        batch_data_cache = {}
        
        # Collect batchassignment references
        batchassignment_refs = set()
        exam_data_list = []
        
        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            
            # Get batchassignment reference
            batchassignment_ref = exam_doc.get('batchassignment')
            if batchassignment_ref:
                batchassignment_refs.add(batchassignment_ref)
            
            exam_data_list.append({
                'exam_doc': exam_doc,
                'exam_id': exam.id
            })
        
        # Fetch batchassignment data
        for batchassignment_ref in batchassignment_refs:
            try:
                batchassignment_doc = batchassignment_ref.get()
                if batchassignment_doc.exists:
                    batchassignment_data = batchassignment_doc.to_dict()
                    batch_ref = batchassignment_data.get('batch')
                    if batch_ref:
                        batch_doc = batch_ref.get()
                        if batch_doc.exists:
                            batch_data = batch_doc.to_dict()
                            batch_year = batch_data.get('yearOfBatch', '')
                            batch_semester = batch_data.get('semester', '')
                            
                            # Filter by academic year and semester
                            if academic_year and batch_year != academic_year:
                                continue
                            if semester and semester != 'All' and batch_semester != semester:
                                continue
                            
                            batch_data_cache[str(batchassignment_ref.id)] = {
                                'year': batch_year,
                                'semester': batch_semester,
                                'batch_data': batch_data
                            }
            except Exception as e:
                print(f"Error fetching batch data: {str(e)}")
                continue
        
        # Filter exams by batch filters
        filtered_exams = []
        institutions_set = set()
        students_set = set()
        assessors_set = set()
        total_score = 0
        total_max_marks = 0
        passed_count = 0
        total_exams = 0
        
        for exam_item in exam_data_list:
            exam_doc = exam_item['exam_doc']
            batchassignment_ref = exam_doc.get('batchassignment')
            
            # Check if batch matches filters (only if academic year or semester is specified)
            if academic_year or (semester and semester != 'All'):
                if batchassignment_ref:
                    batch_key = str(batchassignment_ref.id)
                    if batch_key not in batch_data_cache:
                        continue  # Skip if batch doesn't match filters
                else:
                    continue  # Skip exams without batch if filters require batch data
            
            # Filter by institution
            if institution and institution != 'All':
                unit_ref = exam_doc.get('unit')
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_data = unit_doc.to_dict()
                            unit_name = unit_data.get('instituteName') or unit_data.get('hospitalName', '')
                            if unit_name != institution:
                                continue
                    except:
                        continue
            
            # Filter by state/region
            if state or region:
                unit_ref = exam_doc.get('unit')
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_data = unit_doc.to_dict()
                            unit_state = unit_data.get('state', '')
                            if state and unit_state != state:
                                continue
                    except:
                        continue
            
            # Filter by category
            if category:
                exam_metadata = exam_doc.get('examMetaData', [])
                found_category = False
                for section in exam_metadata:
                    for question in section.get('section_questions', []):
                        if question.get('category', '').lower() == category.lower():
                            found_category = True
                            break
                        for sub_q in question.get('sub_section_questions', []):
                            if sub_q.get('category', '').lower() == category.lower():
                                found_category = True
                                break
                    if found_category:
                        break
                if not found_category:
                    continue
            
            # Collect data for KPIs
            filtered_exams.append(exam_item)
            total_exams += 1
            
            # Get institution
            unit_ref = exam_doc.get('unit')
            if unit_ref:
                try:
                    unit_doc = unit_ref.get()
                    if unit_doc.exists:
                        unit_name = unit_doc.to_dict().get('instituteName') or unit_doc.to_dict().get('hospitalName', '')
                        if unit_name:
                            institutions_set.add(unit_name)
                except:
                    pass
            
            # Get student
            user_ref = exam_doc.get('user')
            if user_ref:
                try:
                    user_doc = user_ref.get()
                    if user_doc.exists:
                        user_email = user_doc.to_dict().get('emailID', '')
                        if user_email:
                            students_set.add(user_email)
                except:
                    pass
            
            # Get assessor (from supervisor)
            supervisor_ref = exam_doc.get('supervisor')
            if supervisor_ref:
                try:
                    supervisor_doc = supervisor_ref.get()
                    if supervisor_doc.exists:
                        supervisor_email = supervisor_doc.to_dict().get('emailID', '')
                        if supervisor_email:
                            assessors_set.add(supervisor_email)
                except:
                    pass
            
            # Calculate scores
            marks = exam_doc.get('marks', 0)
            max_marks = sum(
                question.get('right_marks_for_question', 0)
                for section in exam_doc.get('examMetaData', [])
                for question in section.get('section_questions', [])
            )
            
            total_score += marks
            total_max_marks += max_marks
            
            # Calculate pass rate (≥80%)
            if max_marks > 0:
                percentage = (marks / max_marks) * 100
                if percentage >= 80:
                    passed_count += 1
        
        # Calculate KPIs
        institutions_active = len(institutions_set)
        students_assessed = len(students_set)
        active_assessors = len(assessors_set)
        osces_conducted = total_exams
        avg_osce_score = round((total_score / total_max_marks) * 100, 2) if total_max_marks > 0 else 0
        pass_rate = round((passed_count / total_exams) * 100, 2) if total_exams > 0 else 0
        
        # Calculate inactive institutions (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        inactive_institutions = 0
        # This would need to check last activity from exam assignments
        
        return JsonResponse({
            'success': True,
            'kpis': {
                'institutions_active': institutions_active,
                'students_assessed': students_assessed,
                'active_assessors': active_assessors,
                'osces_conducted': osces_conducted,
                'avg_osce_score': avg_osce_score,
                'avg_osce_grade': get_grade_letter(avg_osce_score),
                'pass_rate': pass_rate,
                'inactive_institutions': inactive_institutions
            }
        })
        
    except Exception as e:
        print(f"Error fetching admin report KPIs: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def fetch_admin_report_skills_metrics(request):
    """Fetch skills metrics table for admin report portal"""
    try:
        # Get filter parameters (same as KPIs)
        academic_year = request.GET.get('academic_year', '').strip()
        semester = request.GET.get('semester', '').strip()
        osce_level = request.GET.get('osce_level', '').strip()
        category = request.GET.get('category', '').strip()
        skill = request.GET.get('skill', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        # Categories to track
        categories = ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Critical Thinking', 'Pre-Procedure']
        
        # Build query
        query = db.collection('ExamAssignment').where('status', '==', 'Completed')
        
        if osce_level and osce_level != 'All':
            query = query.where('examType', '==', osce_level)
        
        if skill:
            query = query.where('procedure_name', '==', skill)
        
        if date_from:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.where('completed_date', '>=', from_date)
        
        if date_to:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.where('completed_date', '<=', to_date)
        
        exam_assignments = query.stream()
        
        # Aggregate by category
        category_stats = {cat: {'total_questions': 0, 'total_marks': 0, 'total_max': 0, 'count': 0, 'students': set()} for cat in categories}
        
        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            
            # Get batch data for filtering (only if filters require batch data)
            if academic_year or (semester and semester != 'All'):
                batchassignment_ref = exam_doc.get('batchassignment')
                if batchassignment_ref:
                    try:
                        batchassignment_doc = batchassignment_ref.get()
                        if batchassignment_doc.exists:
                            batch_ref = batchassignment_doc.to_dict().get('batch')
                            if batch_ref:
                                batch_doc = batch_ref.get()
                                if batch_doc.exists:
                                    batch_data = batch_doc.to_dict()
                                    if academic_year and batch_data.get('yearOfBatch', '') != academic_year:
                                        continue
                                    if semester and semester != 'All' and batch_data.get('semester', '') != semester:
                                        continue
                                else:
                                    continue  # Skip if batch doesn't exist but filter requires it
                            else:
                                continue  # Skip if batch ref doesn't exist but filter requires it
                        else:
                            continue  # Skip if batchassignment doesn't exist but filter requires it
                    except:
                        continue  # Skip on error if filter requires batch data
                else:
                    continue  # Skip exams without batchassignment if filter requires batch data
            
            # Filter by category if specified
            if category and category not in categories:
                continue
            
            # Get student
            user_ref = exam_doc.get('user')
            student_email = None
            if user_ref:
                try:
                    user_doc = user_ref.get()
                    if user_doc.exists:
                        student_email = user_doc.to_dict().get('emailID', '')
                except:
                    pass
            
            # Process exam metadata
            exam_metadata = exam_doc.get('examMetaData', [])
            for section in exam_metadata:
                for question in section.get('section_questions', []):
                    q_category = question.get('category', '')
                    if q_category in categories:
                        if not category or category == q_category:
                            category_stats[q_category]['count'] += 1
                            category_stats[q_category]['total_marks'] += question.get('answer_scored', 0)
                            category_stats[q_category]['total_max'] += question.get('right_marks_for_question', 0)
                            category_stats[q_category]['total_questions'] += 1
                            if student_email:
                                category_stats[q_category]['students'].add(student_email)
                    
                    # Check sub-questions
                    for sub_q in question.get('sub_section_questions', []):
                        sub_category = sub_q.get('category', '')
                        if sub_category in categories:
                            if not category or category == sub_category:
                                category_stats[sub_category]['count'] += 1
                                category_stats[sub_category]['total_marks'] += sub_q.get('answer_scored', 0)
                                category_stats[sub_category]['total_max'] += sub_q.get('right_marks_for_question', 0)
                                category_stats[sub_category]['total_questions'] += 1
                                if student_email:
                                    category_stats[sub_category]['students'].add(student_email)
        
        # Format results
        skills_metrics = []
        for cat in categories:
            stats = category_stats[cat]
            if stats['count'] > 0:
                avg_score = round((stats['total_marks'] / stats['total_max']) * 100, 2) if stats['total_max'] > 0 else 0
                skills_metrics.append({
                    'skill_name': cat,
                    'questions_count': stats['total_questions'],
                    'avg_score_percentage': avg_score,
                    'total_students': len(stats['students']),
                    'avg_score': round(stats['total_marks'] / stats['count'], 2) if stats['count'] > 0 else 0,
                    'max_score': round(stats['total_max'] / stats['count'], 2) if stats['count'] > 0 else 0
                })
        
        return JsonResponse({
            'success': True,
            'skills_metrics': skills_metrics
        })
        
    except Exception as e:
        print(f"Error fetching skills metrics: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def fetch_admin_report_assessors_performance(request):
    """Fetch assessors performance table for admin report portal"""
    try:
        # Get filter parameters
        academic_year = request.GET.get('academic_year', '').strip()
        semester = request.GET.get('semester', '').strip()
        institution = request.GET.get('institution', '').strip()
        
        # Build query
        query = db.collection('ExamAssignment').where('status', '==', 'Completed')
        
        exam_assignments = query.stream()
        
        # Aggregate by assessor
        assessor_stats = {}
        
        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            
            # Get batch data for filtering (only if filters require batch data)
            if academic_year or (semester and semester != 'All'):
                batchassignment_ref = exam_doc.get('batchassignment')
                if batchassignment_ref:
                    try:
                        batchassignment_doc = batchassignment_ref.get()
                        if batchassignment_doc.exists:
                            batch_ref = batchassignment_doc.to_dict().get('batch')
                            if batch_ref:
                                batch_doc = batch_ref.get()
                                if batch_doc.exists:
                                    batch_data = batch_doc.to_dict()
                                    if academic_year and batch_data.get('yearOfBatch', '') != academic_year:
                                        continue
                                    if semester and semester != 'All' and batch_data.get('semester', '') != semester:
                                        continue
                                else:
                                    continue  # Skip if batch doesn't exist but filter requires it
                            else:
                                continue  # Skip if batch ref doesn't exist but filter requires it
                        else:
                            continue  # Skip if batchassignment doesn't exist but filter requires it
                    except:
                        continue  # Skip on error if filter requires batch data
                else:
                    continue  # Skip exams without batchassignment if filter requires batch data
            
            # Filter by institution
            if institution and institution != 'All':
                unit_ref = exam_doc.get('unit')
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_name = unit_doc.to_dict().get('instituteName') or unit_doc.to_dict().get('hospitalName', '')
                            if unit_name != institution:
                                continue
                    except:
                        continue
            
            # Get assessor
            supervisor_ref = exam_doc.get('supervisor')
            if not supervisor_ref:
                continue
            
            try:
                supervisor_doc = supervisor_ref.get()
                if not supervisor_doc.exists:
                    continue
                
                supervisor_data = supervisor_doc.to_dict()
                assessor_email = supervisor_data.get('emailID', '')
                assessor_name = supervisor_data.get('username', '') or supervisor_data.get('fullName', '') or assessor_email
                
                if not assessor_email:
                    continue
                
                # Get institution name
                unit_ref = exam_doc.get('unit')
                inst_name = 'Unknown'
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_data = unit_doc.to_dict()
                            inst_name = unit_data.get('instituteName') or unit_data.get('hospitalName', 'Unknown')
                    except:
                        pass
                
                # Initialize assessor stats
                if assessor_email not in assessor_stats:
                    assessor_stats[assessor_email] = {
                        'name': assessor_name,
                        'institution': inst_name,
                        'osces_rated': 0,
                        'students_rated': set(),
                        'scores': [],
                        'institution_scores': []
                    }
                
                # Update stats
                assessor_stats[assessor_email]['osces_rated'] += 1
                
                # Get student
                user_ref = exam_doc.get('user')
                if user_ref:
                    try:
                        user_doc = user_ref.get()
                        if user_doc.exists:
                            student_email = user_doc.to_dict().get('emailID', '')
                            if student_email:
                                assessor_stats[assessor_email]['students_rated'].add(student_email)
                    except:
                        pass
                
                # Calculate score
                marks = exam_doc.get('marks', 0)
                max_marks = sum(
                    question.get('right_marks_for_question', 0)
                    for section in exam_doc.get('examMetaData', [])
                    for question in section.get('section_questions', [])
                )
                
                if max_marks > 0:
                    percentage = (marks / max_marks) * 100
                    assessor_stats[assessor_email]['scores'].append(percentage)
                    assessor_stats[assessor_email]['institution_scores'].append((inst_name, percentage))
                
            except Exception as e:
                print(f"Error processing assessor: {str(e)}")
                continue
        
        # Calculate institution means
        institution_means = {}
        for assessor_email, stats in assessor_stats.items():
            for inst_name, score in stats['institution_scores']:
                if inst_name not in institution_means:
                    institution_means[inst_name] = []
                institution_means[inst_name].append(score)
        
        for inst_name in institution_means:
            institution_means[inst_name] = sum(institution_means[inst_name]) / len(institution_means[inst_name]) if institution_means[inst_name] else 0
        
        # Format results
        assessors_performance = []
        for assessor_email, stats in assessor_stats.items():
            if len(stats['scores']) > 0:
                mean_score = sum(stats['scores']) / len(stats['scores'])
                inst_mean = institution_means.get(stats['institution'], 0)
                delta = mean_score - inst_mean
                
                # Calculate standard deviation
                if len(stats['scores']) > 1:
                    variance = sum((x - mean_score) ** 2 for x in stats['scores']) / len(stats['scores'])
                    score_sd = round(variance ** 0.5, 2)
                else:
                    score_sd = 0
                
                assessors_performance.append({
                    'assessor': stats['name'],
                    'institution': stats['institution'],
                    'osces_rated': stats['osces_rated'],
                    'students_rated': len(stats['students_rated']),
                    'mean_score': round(mean_score, 2),
                    'delta_vs_inst_mean': round(delta, 2),
                    'score_sd': score_sd,
                    'irr': 'N/A',  # Would need multiple assessors rating same exam
                    'last_calibration': 'N/A'  # Would need tracking
                })
        
        # Sort by assessor name
        assessors_performance.sort(key=lambda x: x['assessor'])
        
        return JsonResponse({
            'success': True,
            'assessors_performance': assessors_performance
        })
        
    except Exception as e:
        print(f"Error fetching assessors performance: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def fetch_admin_report_usage_engagement(request):
    """Fetch usage & engagement data for admin report portal"""
    try:
        # Institution Last Access Date
        institutions_access = []
        
        # Get all institutions
        institutions = Institution.objects.all()
        for inst in institutions:
            # Get unit head's last login
            last_login = None
            if inst.unit_head:
                last_login = inst.unit_head.last_login
            
            if last_login:
                if isinstance(last_login, datetime):
                    days_since_login = (datetime.now(datetime.timezone.utc).replace(tzinfo=None) - last_login.replace(tzinfo=datetime.timezone.utc).replace(tzinfo=None)).days
                else:
                    days_since_login = 999
                status = 'Active' if days_since_login < 30 else 'In-Active'
            else:
                status = 'In-Active'
            
            institutions_access.append({
                'institution': inst.name,
                'last_login': last_login.strftime('%Y-%m-%d %H:%M:%S') if last_login else 'Never',
                'status': status
            })
        
        # OSCE Upload Timeliness
        upload_timeliness = []
        exam_assignments = db.collection('ExamAssignment').where('status', '==', 'Completed').stream()
        
        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            created_at = exam_doc.get('createdAt')
            completed_date = exam_doc.get('completed_date')
            
            if created_at and completed_date:
                # Calculate delay
                if isinstance(created_at, datetime):
                    created_dt = created_at
                else:
                    created_dt = created_at
                
                if isinstance(completed_date, datetime):
                    completed_dt = completed_date
                else:
                    completed_dt = completed_date
                
                delay_days = (completed_dt - created_dt).days
                
                # Get unit name
                unit_ref = exam_doc.get('unit')
                unit_name = 'Unknown'
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_data = unit_doc.to_dict()
                            unit_name = unit_data.get('instituteName') or unit_data.get('hospitalName', 'Unknown')
                    except:
                        pass
                
                upload_timeliness.append({
                    'osce_date': completed_dt.strftime('%Y-%m-%d') if completed_dt else 'N/A',
                    'upload_date': completed_dt.strftime('%Y-%m-%d') if completed_dt else 'N/A',
                    'delay_days': delay_days,
                    'institution': unit_name
                })
        
        # Checklist Versions Used (would need version tracking)
        checklist_versions = []
        procedures = db.collection('Procedures').stream()
        for proc in procedures:
            proc_doc = proc.to_dict()
            proc_name = proc_doc.get('procedureName', 'Unknown')
            version_id = proc_doc.get('version', '1.0')  # Default if not tracked
            
            # Get institutions using this procedure
            exam_assignments = db.collection('ExamAssignment').where('procedure_name', '==', proc_name).stream()
            institutions_using = set()
            for exam in exam_assignments:
                exam_doc = exam.to_dict()
                unit_ref = exam_doc.get('unit')
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_data = unit_doc.to_dict()
                            unit_name = unit_data.get('instituteName') or unit_data.get('hospitalName', '')
                            if unit_name:
                                institutions_using.add(unit_name)
                    except:
                        pass
            
            if institutions_using:
                checklist_versions.append({
                    'skill': proc_name,
                    'version_id': str(version_id),
                    'institutions': list(institutions_using)
                })
        
        return JsonResponse({
            'success': True,
            'institution_access': institutions_access,
            'upload_timeliness': upload_timeliness[:100],  # Limit to 100 for performance
            'checklist_versions': checklist_versions
        })
        
    except Exception as e:
        print(f"Error fetching usage & engagement: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def export_admin_report_excel(request):
    """Export admin report data to Excel"""
    try:
        # Get filter parameters
        academic_year = request.GET.get('academic_year', '').strip()
        semester = request.GET.get('semester', '').strip()
        institution = request.GET.get('institution', '').strip()
        osce_level = request.GET.get('osce_level', '').strip()
        category = request.GET.get('category', '').strip()
        skill = request.GET.get('skill', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        # Create Excel file
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        
        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Cell format
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Get KPIs
        kpis_response = fetch_admin_report_kpis(request)
        kpis_data = json.loads(kpis_response.content)
        
        # Worksheet 1: KPIs
        worksheet1 = workbook.add_worksheet('KPIs')
        worksheet1.write(0, 0, 'KPI', header_format)
        worksheet1.write(0, 1, 'Value', header_format)
        
        if kpis_data.get('success'):
            kpis = kpis_data.get('kpis', {})
            row = 1
            worksheet1.write(row, 0, 'Institutions Active', cell_format)
            worksheet1.write(row, 1, kpis.get('institutions_active', 0), cell_format)
            row += 1
            worksheet1.write(row, 0, 'Students Assessed', cell_format)
            worksheet1.write(row, 1, kpis.get('students_assessed', 0), cell_format)
            row += 1
            worksheet1.write(row, 0, 'Active Assessors', cell_format)
            worksheet1.write(row, 1, kpis.get('active_assessors', 0), cell_format)
            row += 1
            worksheet1.write(row, 0, 'OSCEs Conducted', cell_format)
            worksheet1.write(row, 1, kpis.get('osces_conducted', 0), cell_format)
            row += 1
            worksheet1.write(row, 0, 'Avg OSCE Score', cell_format)
            worksheet1.write(row, 1, f"{kpis.get('avg_osce_score', 0)}% ({kpis.get('avg_osce_grade', 'N/A')})", cell_format)
            row += 1
            worksheet1.write(row, 0, 'Pass Rate (≥80%)', cell_format)
            worksheet1.write(row, 1, f"{kpis.get('pass_rate', 0)}%", cell_format)
        
        # Worksheet 2: Skills Metrics
        worksheet2 = workbook.add_worksheet('Skills Metrics')
        worksheet2.write(0, 0, 'Skill Name', header_format)
        worksheet2.write(0, 1, 'Questions Count', header_format)
        worksheet2.write(0, 2, 'Avg Score %', header_format)
        worksheet2.write(0, 3, 'Total Students', header_format)
        worksheet2.write(0, 4, 'Avg Score', header_format)
        worksheet2.write(0, 5, 'Max Score', header_format)
        
        # Fetch skills metrics
        skills_response = fetch_admin_report_skills_metrics(request)
        skills_data = json.loads(skills_response.content)
        
        if skills_data.get('success'):
            row = 1
            for skill in skills_data.get('skills_metrics', []):
                worksheet2.write(row, 0, skill.get('skill_name', ''), cell_format)
                worksheet2.write(row, 1, skill.get('questions_count', 0), cell_format)
                worksheet2.write(row, 2, f"{skill.get('avg_score_percentage', 0)}%", cell_format)
                worksheet2.write(row, 3, skill.get('total_students', 0), cell_format)
                worksheet2.write(row, 4, skill.get('avg_score', 0), cell_format)
                worksheet2.write(row, 5, skill.get('max_score', 0), cell_format)
                row += 1
        
        # Worksheet 3: Assessors Performance
        worksheet3 = workbook.add_worksheet('Assessors Performance')
        worksheet3.write(0, 0, 'Assessor', header_format)
        worksheet3.write(0, 1, 'Institution', header_format)
        worksheet3.write(0, 2, 'OSCEs Rated', header_format)
        worksheet3.write(0, 3, 'Students Rated', header_format)
        worksheet3.write(0, 4, 'Mean Score', header_format)
        worksheet3.write(0, 5, 'Δ vs Inst. Mean', header_format)
        worksheet3.write(0, 6, 'Score SD', header_format)
        worksheet3.write(0, 7, 'IRR', header_format)
        worksheet3.write(0, 8, 'Last Calibration', header_format)
        
        # Fetch assessors performance
        assessors_response = fetch_admin_report_assessors_performance(request)
        assessors_data = json.loads(assessors_response.content)
        
        if assessors_data.get('success'):
            row = 1
            for assessor in assessors_data.get('assessors_performance', []):
                worksheet3.write(row, 0, assessor.get('assessor', ''), cell_format)
                worksheet3.write(row, 1, assessor.get('institution', ''), cell_format)
                worksheet3.write(row, 2, assessor.get('osces_rated', 0), cell_format)
                worksheet3.write(row, 3, assessor.get('students_rated', 0), cell_format)
                worksheet3.write(row, 4, assessor.get('mean_score', 0), cell_format)
                worksheet3.write(row, 5, assessor.get('delta_vs_inst_mean', 0), cell_format)
                worksheet3.write(row, 6, assessor.get('score_sd', 0), cell_format)
                worksheet3.write(row, 7, assessor.get('irr', 'N/A'), cell_format)
                worksheet3.write(row, 8, assessor.get('last_calibration', 'N/A'), cell_format)
                row += 1
        
        workbook.close()
        buffer.seek(0)
        
        # Create response
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="admin_report.xlsx"'
        
        return response
        
    except Exception as e:
        print(f"Error exporting admin report: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def fetch_institutions_hospitals_for_report(request):
    """Fetch institutions and hospitals based on user permissions for OSCE report"""
    try:
        from assessments.models import Institution, Hospital
        
        institutions = []
        hospitals = []
        
        # Check if user has all permissions
        if request.user.has_all_permissions() or request.user.access_all_institutions:
            django_institutions = Institution.objects.filter(is_active=True, onboarding_type="b2b")
        else:
            django_institutions = request.user.assigned_institutions.filter(is_active=True)
        
        if request.user.has_all_permissions() or request.user.access_all_hospitals:
            django_hospitals = Hospital.objects.filter(is_active=True, onboarding_type="b2b")
        else:
            django_hospitals = request.user.assigned_hospitals.filter(is_active=True)
        
        # Add institutions
        for inst in django_institutions:
            institutions.append({
                'id': inst.id,
                'name': inst.name,
                'type': 'institution'
            })
        
        # Add hospitals
        for hosp in django_hospitals:
            hospitals.append({
                'id': hosp.id,
                'name': hosp.name,
                'type': 'hospital'
            })
        
        # Also fetch from Firebase InstituteNames for backward compatibility
        try:
            institutes_ref = db.collection('InstituteNames')
            for doc in institutes_ref.stream():
                institute_data = doc.to_dict()
                institute_name = institute_data.get('instituteName', 'Unnamed Institute')
                
                # Check if already in Django list or if user has all permissions
                if request.user.has_all_permissions() or request.user.access_all_institutions:
                    if not any(inst['name'] == institute_name for inst in institutions):
                        institutions.append({
                            'id': doc.id,
                            'name': institute_name,
                            'type': 'institution'
                        })
                else:
                    # Check if user has access to this institution
                    assigned_names = list(request.user.assigned_institutions.values_list('name', flat=True))
                    if institute_name in assigned_names:
                        if not any(inst['name'] == institute_name for inst in institutions):
                            institutions.append({
                                'id': doc.id,
                                'name': institute_name,
                                'type': 'institution'
                            })
        except Exception as e:
            print(f"Error fetching from Firebase: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'institutions': institutions,
            'hospitals': hospitals
        })
    except Exception as e:
        print(f"Error fetching institutions/hospitals: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@login_required
def fetch_osce_report(request):
    """
    ⚠️ DEPRECATED - This function has been replaced by fetch_osce_report_optimized
    
    This old implementation computed everything on-demand (5-10 seconds).
    The new system pre-computes all analytics (0.5 seconds response time).
    
    Kept for reference only - NOT USED IN PRODUCTION
    """
    try:
        # Get filter parameters
        academic_year = request.GET.get('academic_year', '').strip()
        institution_id = request.GET.get('institution_id', '').strip()
        institution_type = request.GET.get('institution_type', '').strip()  # 'institution' or 'hospital'
        semester = request.GET.get('semester', '').strip()
        osce_level = request.GET.get('osce_level', '').strip()  # All/Classroom/Mock/Final
        skill = request.GET.get('skill', '').strip()
        student_search = request.GET.get('student_search', '').strip()
        
        # Validate mandatory fields
        if not academic_year:
            return JsonResponse({'success': False, 'error': 'Academic year is required'}, status=400)
        if not institution_id or not institution_type:
            return JsonResponse({'success': False, 'error': 'Institution/Hospital selection is required'}, status=400)
        
        # Get institution/hospital name from Django models
        institution_name = None
        if institution_type == 'institution':
            from assessments.models import Institution
            try:
                inst = Institution.objects.get(id=institution_id)
                institution_name = inst.name
            except Institution.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Institution not found'}, status=404)
        elif institution_type == 'hospital':
            from assessments.models import Hospital
            try:
                hosp = Hospital.objects.get(id=institution_id)
                institution_name = hosp.name
            except Hospital.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Hospital not found'}, status=404)
        
        # Query BatchAssignment with yearOfBatch filter
        batch_assignments_query = db.collection('BatchAssignment').where('yearOfBatch', '==', academic_year).where('unit_name', '==', institution_name)
        batch_assignments = batch_assignments_query.stream()
        print(f"Batch Assignments: {batch_assignments}")

        #print all batch assignnment ids

        # Collections to track data
        all_user_ids = set()  # All unique user IDs from examassignments (for enrolled)
        completed_user_ids = set()  # Unique user IDs from completed examassignments (for assessed)
        unique_procedures = set()  # Unique procedure IDs
        filtered_batch_assignments_count = 0
        
        # For calculating average score and pass rate
        completed_exam_scores = []  # List of percentages for completed exams
        
        # For semester-wise performance
        semester_data = {}  # {semester: {students: set(), osces: [], scores: [], dates: [], types: []}}
        
        # For category-wise performance - track by procedure category
        category_scores = {
            'Core Skills': [],
            'Infection Control': [],
            'Communication': [],
            'Documentation': [],
            'Pre-Procedure': [],
            'Critical Thinking': []
        }
        
        # For semester dashboard (only when semester filter is applied)
        semester_filter_applied = semester and semester != 'All'
        assessors_set = set()  # Unique assessors for the semester
        osce_activity_timeline = []  # List of OSCE activities with details
        student_performance_data = {}  # {user_id: {name, overall_avg, classroom: score, mock: score, final: score}}
        
        # Process each BatchAssignment
        for ba_doc in batch_assignments:
            ba_data = ba_doc.to_dict()
            print(f"Batch Assignment: {ba_data}")
            
            # Filter by semester
            if semester and semester != 'All':
                ba_semester = ba_data.get('semester', '')
                if ba_semester != semester:
                    continue
            
            # Filter by OSCE level (examType)
            if osce_level and osce_level != 'All':
                print(f"OSCE Level: {osce_level}")
                exam_type = ba_data.get('examType', '')
                if exam_type != osce_level:
                    continue
            
            # Filter by skill/procedure if applied (procedure ID)
            if skill:
                procedure_ref = ba_data.get('procedure')
                if procedure_ref:
                    # Compare procedure reference ID with selected procedure ID
                    if procedure_ref.id != skill:
                        continue
                else:
                    continue  # Skip if no procedure reference
            
            # Count this BatchAssignment
            filtered_batch_assignments_count += 1
            
            # Collect procedure ID and get procedure category
            procedure_ref = ba_data.get('procedure')
            procedure_category = None
            if procedure_ref:
                unique_procedures.add(procedure_ref.id)
                # Get category from procedure document
                try:
                    procedure_doc = procedure_ref.get()
                    if procedure_doc.exists:
                        procedure_data = procedure_doc.to_dict()
                        procedure_category = procedure_data.get('category', '')
                except Exception as e:
                    print(f"Error fetching procedure category: {str(e)}")
            
            # Get semester and exam type for semester-wise tracking
            ba_semester = ba_data.get('semester', '')
            exam_type = ba_data.get('examType', '')
            test_date = ba_data.get('testDate')
            created_at = ba_data.get('createdAt')
            
            # Track assessors for semester dashboard (only when semester filter is applied)
            # Get unique assessors from BatchAssignment.assessorlist field
            if semester_filter_applied:
                assessors = ba_data.get('assessorlist', [])
                if assessors:
                    for assessor_ref in assessors:
                        if assessor_ref:
                            # Add assessor ID to set (handles both reference objects and IDs)
                            if hasattr(assessor_ref, 'id'):
                                assessors_set.add(assessor_ref.id)
                            elif isinstance(assessor_ref, str):
                                assessors_set.add(assessor_ref)
            
            # Initialize semester data if not exists
            if ba_semester and ba_semester not in semester_data:
                semester_data[ba_semester] = {
                    'students': set(),
                    'osces': [],
                    'scores': [],
                    'dates': [],
                    'types': []
                }
            
            # Track OSCE activity for timeline - MOVED to BatchAssignmentSummary section below
            # No longer tracking per BatchAssignment, will use BatchAssignmentSummary instead
            
            # Get examassignments from batchassignment
            exam_assignments = ba_data.get('examassignment', [])
            for exam_ref in exam_assignments:
                if exam_ref:
                    try:
                        exam_doc = exam_ref.get()
                        if exam_doc.exists:
                            exam_data = exam_doc.to_dict()
                            user_ref = exam_data.get('user')
                            if user_ref:
                                user_id = user_ref.id
                                # Add to all user IDs (for enrolled)
                                all_user_ids.add(user_id)
                                
                                # Track semester data (for all students, not just completed)
                                if ba_semester:
                                    semester_data[ba_semester]['students'].add(user_id)
                                    # Track OSCE for semester (only once per BatchAssignment)
                                    ba_id = ba_doc.id
                                    if ba_id not in semester_data[ba_semester]['osces']:
                                        semester_data[ba_semester]['osces'].append(ba_id)
                                        if test_date:
                                            semester_data[ba_semester]['dates'].append(test_date)
                                        if exam_type:
                                            semester_data[ba_semester]['types'].append(exam_type)
                                
                                # Process completed exams for score calculation
                                if str(exam_data.get('status', '')).lower() == 'completed':
                                    completed_user_ids.add(user_id)
                                    
                                    # Calculate percentage for completed exams
                                    total_score = exam_data.get("marks", 0)
                                    exam_metadata = exam_data.get('examMetaData', [])
                                    max_marks = sum(
                                        question.get('right_marks_for_question', 0)
                                        for section in exam_metadata
                                        for question in section.get("section_questions", [])
                                    )
                                    if max_marks > 0:
                                        percentage = round((total_score / max_marks) * 100, 2)
                                        completed_exam_scores.append(percentage)
                                        
                                        # Track semester scores
                                        if ba_semester:
                                            semester_data[ba_semester]['scores'].append(percentage)
                                        
                                        # Track category-wise scores based on procedure category
                                        if procedure_category and procedure_category in category_scores:
                                            category_scores[procedure_category].append(percentage)
                                        
                                        # Track student performance data (only when semester filter is applied)
                                        if semester_filter_applied:
                                            if user_id not in student_performance_data:
                                                # Get user name from Firestore
                                                user_name = 'Unknown'
                                                try:
                                                    user_doc = user_ref.get()
                                                    if user_doc.exists:
                                                        user_data = user_doc.to_dict()
                                                        user_name = user_data.get('name', user_data.get('firstName', 'Unknown'))
                                                except:
                                                    pass
                                                
                                                student_performance_data[user_id] = {
                                                    'name': user_name,
                                                    'scores': [],
                                                    'classroom': None,
                                                    'mock': None,
                                                    'final': None
                                                }
                                            
                                            # Store score by OSCE level
                                            if exam_type == 'Classroom':
                                                student_performance_data[user_id]['classroom'] = percentage
                                            elif exam_type == 'Mock':
                                                student_performance_data[user_id]['mock'] = percentage
                                            elif exam_type == 'Final':
                                                student_performance_data[user_id]['final'] = percentage
                                            
                                            # Track all scores for overall average
                                            student_performance_data[user_id]['scores'].append(percentage)
                    except Exception as e:
                        print(f"Error processing exam assignment: {str(e)}")
                        continue
        
        # Calculate total_students_enrolled from Batches
        # Get institution/hospital reference from Firestore using the name
        institution_ref = None
        if institution_type == 'institution':
            print(f"Institution Name: {institution_name}")
            # Query InstituteNames collection by name to get the reference
            inst_docs = db.collection('InstituteNames').where('instituteName', '==', institution_name).limit(1).stream()
            for doc in inst_docs:
                institution_ref = doc.reference
                break
        elif institution_type == 'hospital':
            # Query Hospitals collection by name (adjust collection name if different)
            hosp_docs = db.collection('Hospitals').where('hospitalName', '==', institution_name).limit(1).stream()
            for doc in hosp_docs:
                institution_ref = doc.reference
                break
        
        # Collect all enrolled students from batches
        enrolled_user_ids = set()
        if institution_ref:
            print(f"Institution Reference: {institution_ref}")
            # Query batches by unit reference and year
            batches_query = db.collection('Batches').where('unit', '==', institution_ref).where('yearOfBatch', '==', academic_year)
            print(f"Batches Query: {batches_query}")
            # If semester filter is applied, also filter by semester
            if semester and semester != 'All':
                batches_query = batches_query.where('semester', '==', semester)
            
            batches = batches_query.stream()
            
            # Collect all learners from matching batches
            for batch_doc in batches:
                batch_data = batch_doc.to_dict()
                learners = batch_data.get('learners', [])
                for learner_ref in learners:
                    if learner_ref:
                        # Extract user ID from reference
                        if hasattr(learner_ref, 'id'):
                            enrolled_user_ids.add(learner_ref.id)
                        elif isinstance(learner_ref, str):
                            # Handle string path like "/Users/2219"
                            if '/Users/' in learner_ref:
                                user_id = learner_ref.split('/Users/')[-1]
                                enrolled_user_ids.add(user_id)
                            else:
                                enrolled_user_ids.add(learner_ref)
        
        total_students_enrolled = len(enrolled_user_ids)
        students_assessed = len(completed_user_ids)
        print(f"Students Assessed: {students_assessed}")
        print(f"Total Students Enrolled: {total_students_enrolled}")
        
        # Calculate total_osce_conducted from BatchAssignmentSummary
        # Each BatchAssignmentSummary document represents one OSCE
        bas_query = db.collection('BatchAssignmentSummary').where('yearOfBatch', '==', academic_year).where('unit_name', '==', institution_name)
        
        # Filter by semester if applied
        if semester and semester != 'All':
            bas_query = bas_query.where('semester', '==', semester)
        
        # Filter by exam_type (OSCE level) if applied
        if osce_level and osce_level != 'All':
            bas_query = bas_query.where('exam_type', '==', osce_level)
        
        # Convert stream to list so we can iterate multiple times if needed
        batch_assignment_summaries = list(bas_query.stream())
        total_osce_conducted = 0
        
        # If skill/procedure filter is applied, check if procedure exists in procedure_assessor_mappings
        if skill:
            for bas_doc in batch_assignment_summaries:
                bas_data = bas_doc.to_dict()
                procedure_mappings = bas_data.get('procedure_assessor_mappings', [])
                
                # Check if the selected procedure exists in any mapping
                procedure_found = False
                for mapping in procedure_mappings:
                    if isinstance(mapping, dict):
                        procedure_id = mapping.get('procedure_id', '')
                        if procedure_id == skill:
                            procedure_found = True
                            break
                
                if procedure_found:
                    total_osce_conducted += 1
        else:
            # No skill filter, count all matching BatchAssignmentSummary documents
            total_osce_conducted = len(batch_assignment_summaries)
        
        assessment_rate = round((students_assessed / total_students_enrolled * 100) if total_students_enrolled > 0 else 0, 2)
        skills_evaluated = len(unique_procedures)
        
        # Calculate Average Institution Score
        average_institution_score = 0
        if completed_exam_scores:
            average_institution_score = round(sum(completed_exam_scores) / len(completed_exam_scores), 2)
        
        # Calculate Pass Rate (≥80%)
        pass_count = sum(1 for score in completed_exam_scores if score >= 80)
        pass_rate = round((pass_count / len(completed_exam_scores) * 100) if completed_exam_scores else 0, 2)
        
        # Get grade letter for average score
        def get_grade_letter(percentage):
            if percentage >= 90:
                return 'A'
            elif percentage >= 80:
                return 'B'
            elif percentage >= 70:
                return 'C'
            elif percentage >= 60:
                return 'D'
            else:
                return 'E'
        
        grade_letter = get_grade_letter(average_institution_score) if average_institution_score > 0 else '-'
        
        # Process semester-wise data (always process - data is already filtered by applied filters)
        semester_wise_performance = []
        for sem in sorted(semester_data.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            sem_data = semester_data[sem]
            num_students = len(sem_data['students'])
            
            # Calculate num_osces from BatchAssignmentSummary for this semester
            # Each BatchAssignmentSummary document represents one OSCE
            bas_query_sem = db.collection('BatchAssignmentSummary').where('yearOfBatch', '==', academic_year).where('unit_name', '==', institution_name).where('semester', '==', sem)
            
            # Filter by exam_type (OSCE level) if applied
            if osce_level and osce_level != 'All':
                bas_query_sem = bas_query_sem.where('exam_type', '==', osce_level)
            
            batch_assignment_summaries_sem = list(bas_query_sem.stream())
            
            # If skill/procedure filter is applied, check if procedure exists in procedure_assessor_mappings
            if skill:
                num_osces = 0
                for bas_doc in batch_assignment_summaries_sem:
                    bas_data = bas_doc.to_dict()
                    procedure_mappings = bas_data.get('procedure_assessor_mappings', [])
                    
                    # Check if the selected procedure exists in any mapping
                    procedure_found = False
                    for mapping in procedure_mappings:
                        if isinstance(mapping, dict):
                            procedure_id = mapping.get('procedure_id', '')
                            if procedure_id == skill:
                                procedure_found = True
                                break
                    
                    if procedure_found:
                        num_osces += 1
            else:
                # No skill filter, count all matching BatchAssignmentSummary documents for this semester
                num_osces = len(batch_assignment_summaries_sem)
            
            avg_score = round(sum(sem_data['scores']) / len(sem_data['scores']), 2) if sem_data['scores'] else 0
            pass_count_sem = sum(1 for s in sem_data['scores'] if s >= 80)
            pass_pct = round((pass_count_sem / len(sem_data['scores']) * 100) if sem_data['scores'] else 0, 2)
            
            # Get most recent date and corresponding OSCE type
            most_recent_date = None
            osce_type = '-------'
            
            if sem_data['dates']:
                try:
                    # Convert Firestore timestamps to datetime and track indices
                    date_type_pairs = []
                    for i, d in enumerate(sem_data['dates']):
                        if d:
                            parsed_date = None
                            if hasattr(d, 'timestamp'):
                                # Firestore Timestamp
                                parsed_date = datetime.fromtimestamp(d.timestamp())
                            elif hasattr(d, 'seconds'):
                                # Firestore Timestamp with seconds attribute
                                parsed_date = datetime.fromtimestamp(d.seconds)
                            elif isinstance(d, datetime):
                                parsed_date = d
                            elif isinstance(d, str):
                                # Try parsing string date
                                try:
                                    parsed_date = datetime.strptime(d, '%Y-%m-%d')
                                except:
                                    pass
                            
                            if parsed_date and i < len(sem_data['types']):
                                date_type_pairs.append((parsed_date, sem_data['types'][i]))
                    
                    if date_type_pairs:
                        # Sort by exam type priority (Final, Mock, Classroom) and then by date
                        exam_type_priority = {'Final': 2, 'Mock': 1, 'Classroom': 0}
                        date_type_pairs.sort(
                            key=lambda x: (
                                exam_type_priority.get(x[1], -1),  # Sort by exam type first
                                x[0]  # Then by date
                            ),
                            reverse=True
                        )
                        most_recent_date = date_type_pairs[0][0].strftime('%Y-%m-%d')
                        osce_type = date_type_pairs[0][1]  # Get the type of the most recent/highest priority exam
                    else:
                        most_recent_date = 'N/A'
                except Exception as e:
                    print(f"Error processing dates: {str(e)}")
                    most_recent_date = 'N/A'
            
            semester_wise_performance.append({
                'semester': sem,
                'num_students': num_students,
                'num_osces': num_osces,
                'average_score': avg_score,
                'pass_percentage': pass_pct,
                'most_recent_date': most_recent_date or 'N/A',
                'osce_type': osce_type
            })
        
        # Update overall pass rate and average score based on semester_wise_performance
        print(f"DEBUG: semester value = '{semester}', type = {type(semester)}")
        print(f"DEBUG: semester_wise_performance = {semester_wise_performance}")
        print(f"DEBUG: Current pass_rate before override = {pass_rate}")
        
        if semester_wise_performance:
            if semester and semester != 'All':
                # If specific semester is selected, use that semester's values
                print(f"DEBUG: Looking for semester '{semester}' in semester_wise_performance")
                for sem_perf in semester_wise_performance:
                    print(f"DEBUG: Checking sem_perf['semester'] = '{sem_perf['semester']}', type = {type(sem_perf['semester'])}")
                    if sem_perf['semester'] == semester:
                        print(f"DEBUG: MATCH FOUND! Updating pass_rate from {pass_rate} to {sem_perf['pass_percentage']}")
                        pass_rate = sem_perf['pass_percentage']
                        average_institution_score = sem_perf['average_score']
                        grade_letter = get_grade_letter(average_institution_score) if average_institution_score > 0 else '-'
                        break
                else:
                    print(f"DEBUG: NO MATCH FOUND for semester '{semester}'")
            else:
                # If no semester filter (All semesters), calculate average pass rate across all semesters
                semester_pass_rates = [sem_perf['pass_percentage'] for sem_perf in semester_wise_performance if sem_perf['pass_percentage'] is not None]
                semester_avg_scores = [sem_perf['average_score'] for sem_perf in semester_wise_performance if sem_perf['average_score'] is not None]
                
                if semester_pass_rates:
                    pass_rate = round(sum(semester_pass_rates) / len(semester_pass_rates), 2)
                if semester_avg_scores:
                    average_institution_score = round(sum(semester_avg_scores) / len(semester_avg_scores), 2)
                    grade_letter = get_grade_letter(average_institution_score) if average_institution_score > 0 else '-'
        
        # Process category-wise performance (always process - data is already filtered by applied filters)
        category_wise_performance = []
        for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
            scores = category_scores.get(category, [])
            avg_percentage = round(sum(scores) / len(scores), 2) if scores else None
            category_wise_performance.append({
                'category': category,
                'percentage': avg_percentage
            })
        
        # Process semester dashboard data (only when semester filter is applied)
        semester_dashboard_data = None
        if semester_filter_applied:
            # Populate OSCE Activity Timeline from BatchAssignmentSummary
            # Each BatchAssignmentSummary represents one complete OSCE
            bas_query_timeline = db.collection('BatchAssignmentSummary').where('yearOfBatch', '==', academic_year).where('unit_name', '==', institution_name).where('semester', '==', semester)
            
            # Filter by exam_type (OSCE level) if applied
            if osce_level and osce_level != 'All':
                bas_query_timeline = bas_query_timeline.where('exam_type', '==', osce_level)
            
            batch_assignment_summaries_timeline = list(bas_query_timeline.stream())
            
            # Process each BatchAssignmentSummary to create timeline entries
            for bas_doc in batch_assignment_summaries_timeline:
                bas_data = bas_doc.to_dict()
                
                # If skill/procedure filter is applied, check if procedure exists in procedure_assessor_mappings
                if skill:
                    procedure_mappings = bas_data.get('procedure_assessor_mappings', [])
                    procedure_found = False
                    for mapping in procedure_mappings:
                        if isinstance(mapping, dict):
                            procedure_id = mapping.get('procedure_id', '')
                            if procedure_id == skill:
                                procedure_found = True
                                break
                    
                    # Skip this OSCE if the filtered procedure is not found
                    if not procedure_found:
                        continue
                
                # Get OSCE details
                osce_level_value = bas_data.get('exam_type', 'N/A')
                test_date = bas_data.get('test_date')
                
                # Format date
                date_str = 'N/A'
                if test_date:
                    try:
                        if hasattr(test_date, 'timestamp'):
                            date_str = datetime.fromtimestamp(test_date.timestamp()).strftime('%d %b %Y')
                        elif hasattr(test_date, 'seconds'):
                            date_str = datetime.fromtimestamp(test_date.seconds).strftime('%d %b %Y')
                        elif isinstance(test_date, datetime):
                            date_str = test_date.strftime('%d %b %Y')
                        elif isinstance(test_date, str):
                            try:
                                date_obj = datetime.strptime(test_date, '%Y-%m-%d')
                                date_str = date_obj.strftime('%d %b %Y')
                            except:
                                date_str = test_date
                    except:
                        date_str = 'N/A'
                
                # Get all batch assignments for this summary to calculate stats
                procedure_mappings = bas_data.get('procedure_assessor_mappings', [])
                osce_students = set()
                osce_scores = []
                osce_pass_count = 0
                
                # Iterate through each procedure mapping to get batch assignments
                for mapping in procedure_mappings:
                    if isinstance(mapping, dict):
                        batchassignment_id = mapping.get('batchassignment_id', '')
                        if batchassignment_id:
                            try:
                                # Get the batch assignment
                                ba_ref = db.collection('BatchAssignment').document(batchassignment_id)
                                ba_doc_timeline = ba_ref.get()
                                if ba_doc_timeline.exists:
                                    ba_data_timeline = ba_doc_timeline.to_dict()
                                    
                                    # Get exam assignments
                                    exam_assignments_timeline = ba_data_timeline.get('examassignment', [])
                                    for exam_ref in exam_assignments_timeline:
                                        if exam_ref:
                                            try:
                                                exam_doc_timeline = exam_ref.get()
                                                if exam_doc_timeline.exists:
                                                    exam_data_timeline = exam_doc_timeline.to_dict()
                                                    user_ref = exam_data_timeline.get('user')
                                                    
                                                    if user_ref:
                                                        user_id = user_ref.id
                                                        osce_students.add(user_id)
                                                        
                                                        # Process completed exams for score calculation
                                                        if str(exam_data_timeline.get('status', '')).lower() == 'completed':
                                                            total_score = exam_data_timeline.get("marks", 0)
                                                            exam_metadata = exam_data_timeline.get('examMetaData', [])
                                                            max_marks = sum(
                                                                question.get('right_marks_for_question', 0)
                                                                for section in exam_metadata
                                                                for question in section.get("section_questions", [])
                                                            )
                                                            if max_marks > 0:
                                                                percentage = round((total_score / max_marks) * 100, 2)
                                                                osce_scores.append(percentage)
                                                                if percentage >= 80:
                                                                    osce_pass_count += 1
                                            except Exception as e:
                                                print(f"Error processing exam assignment in timeline: {str(e)}")
                                                continue
                            except Exception as e:
                                print(f"Error getting batch assignment for timeline: {str(e)}")
                                continue
                
                # Calculate average score and pass rate for this timeline entry
                avg_score = round(sum(osce_scores) / len(osce_scores), 2) if osce_scores else 0
                timeline_pass_rate = round((osce_pass_count / len(osce_scores) * 100) if osce_scores else 0, 2)
                
                # Add to timeline
                osce_activity_timeline.append({
                    'osce_level': osce_level_value,
                    'date_conducted': date_str,
                    'num_students': len(osce_students),
                    'avg_score': avg_score,
                    'pass_percentage': timeline_pass_rate
                })
            
            # Sort OSCE activity timeline by exam type priority (Final, Mock, Classroom) and then by date
            # Higher priority numbers come first with reverse=True, so Final=2, Mock=1, Classroom=0
            exam_type_priority = {'Final': 2, 'Mock': 1, 'Classroom': 0}
            osce_activity_timeline.sort(
                key=lambda x: (
                    exam_type_priority.get(x.get('osce_level', ''), -1),  # Sort by exam type first (Final, Mock, Classroom)
                    x.get('date_conducted', '') if x.get('date_conducted') != 'N/A' else '0000-00-00'  # Then by date (most recent first)
                ),
                reverse=True
            )
            
            # Get latest OSCE
            latest_osce = 'N/A'
            if osce_activity_timeline:
                latest = osce_activity_timeline[0]
                latest_osce = f"{latest['osce_level']} OSCE - {latest['date_conducted']}"
            
            # Use the exact same values from semester_wise_performance table
            # This ensures the dashboard shows identical metrics as the semester-wise table
            semester_avg_score = 0
            semester_pass_rate = 0
            
            # Find the matching semester in semester_wise_performance
            for sem_perf in semester_wise_performance:
                if sem_perf['semester'] == semester:
                    semester_avg_score = sem_perf['average_score']
                    semester_pass_rate = sem_perf['pass_percentage']
                    break
            
            # Get grade letter for semester average
            semester_grade_letter = get_grade_letter(semester_avg_score) if semester_avg_score > 0 else '-'
            
            # Process student performance data
            student_batch_report = []
            for user_id, student_data in student_performance_data.items():
                # Calculate overall average
                overall_avg = round(sum(student_data['scores']) / len(student_data['scores']), 2) if student_data['scores'] else 0
                overall_grade = get_grade_letter(overall_avg)
                
                # Convert scores to grade letters
                def score_to_grade(score):
                    if score is None:
                        return '-'
                    return get_grade_letter(score)
                
                student_batch_report.append({
                    'user_id': user_id,
                    'name': student_data['name'],
                    'overall_avg': overall_avg,
                    'overall_grade': overall_grade,
                    'classroom': score_to_grade(student_data['classroom']),
                    'mock': score_to_grade(student_data['mock']),
                    'final': score_to_grade(student_data['final'])
                })
            
            # Sort students by name
            student_batch_report.sort(key=lambda x: x['name'])
            
            semester_dashboard_data = {
                'total_students': total_students_enrolled,
                'num_assessors': len(assessors_set),
                'osces_conducted': total_osce_conducted,
                'latest_osce': latest_osce,
                'average_score': semester_avg_score,
                'grade_letter': semester_grade_letter,
                'pass_rate': semester_pass_rate,
                'semester_name': f"Semester {semester}",
                'academic_year': academic_year,
                'osce_activity_timeline': osce_activity_timeline,
                'student_batch_report': student_batch_report
            }
        
        # Build response - always include semester, category, and grade distribution data
        # Data is automatically filtered by applied filters (semester, osce_level, skill)
        # If no filters are applied, shows overall/institutional data
        print(f"DEBUG: Final pass_rate being sent in response = {pass_rate}")
        print(f"DEBUG: Final average_institution_score being sent in response = {average_institution_score}")
        
        response_data = {
            'success': True,
            'total_students_enrolled': total_students_enrolled,
            'students_assessed': students_assessed,
            'total_osce_conducted': total_osce_conducted,
            'assessment_rate': assessment_rate,
            'skills_evaluated': skills_evaluated,
            'average_institution_score': average_institution_score,
            'grade_letter': grade_letter,
            'pass_rate': pass_rate,
            'filter_year': academic_year,
            'semester_wise_performance': semester_wise_performance,
            'category_wise_performance': category_wise_performance,
            'completed_exam_scores': completed_exam_scores  # For grade distribution chart
        }
        
        # Add semester dashboard data when semester filter is applied
        if semester_filter_applied and semester_dashboard_data:
            response_data['semester_dashboard'] = semester_dashboard_data
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error fetching OSCE report: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def fetch_skills_for_category(request):
    """Fetch skills data for a selected category"""
    try:
        # Get filter parameters
        category = request.GET.get('category', '').strip()
        academic_year = request.GET.get('academic_year', '').strip()
        institution_id = request.GET.get('institution_id', '').strip()
        institution_type = request.GET.get('institution_type', '').strip()
        semester = request.GET.get('semester', '').strip()
        osce_level = request.GET.get('osce_level', '').strip()
        
        # Validate mandatory fields
        if not category:
            return JsonResponse({'success': False, 'error': 'Category is required'}, status=400)
        if not academic_year:
            return JsonResponse({'success': False, 'error': 'Academic year is required'}, status=400)
        if not institution_id or not institution_type:
            return JsonResponse({'success': False, 'error': 'Institution/Hospital selection is required'}, status=400)
        
        # Get institution/hospital name from Django models
        institution_name = None
        if institution_type == 'institution':
            from assessments.models import Institution
            try:
                inst = Institution.objects.get(id=institution_id)
                institution_name = inst.name
            except Institution.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Institution not found'}, status=404)
        elif institution_type == 'hospital':
            from assessments.models import Hospital
            try:
                hosp = Hospital.objects.get(id=institution_id)
                institution_name = hosp.name
            except Hospital.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Hospital not found'}, status=404)
        
        # Query BatchAssignment with filters
        batch_assignments_query = db.collection('BatchAssignment').where('yearOfBatch', '==', academic_year).where('unit_name', '==', institution_name)
        batch_assignments = batch_assignments_query.stream()
        
        # Track skills data: {procedure_id: {name, category, osce_levels: set(), students: set(), scores: []}}
        skills_data = {}
        
        # Process each BatchAssignment
        for ba_doc in batch_assignments:
            ba_data = ba_doc.to_dict()
            
            # Filter by semester
            if semester and semester != 'All':
                ba_semester = ba_data.get('semester', '')
                if ba_semester != semester:
                    continue
            
            # Filter by OSCE level
            if osce_level and osce_level != 'All':
                exam_type = ba_data.get('examType', '')
                if exam_type != osce_level:
                    continue
            
            # Get procedure reference
            procedure_ref = ba_data.get('procedure')
            if not procedure_ref:
                continue
            
            # Get procedure data
            try:
                procedure_doc = procedure_ref.get()
                if not procedure_doc.exists:
                    continue
                
                procedure_data = procedure_doc.to_dict()
                procedure_category = procedure_data.get('category', '')
                
                # Only process if category matches
                if procedure_category != category:
                    continue
                
                procedure_id = procedure_ref.id
                procedure_name = procedure_data.get('procedureName', 'Unknown Skill')
                exam_type = ba_data.get('examType', '')
                
                # Initialize skill data if not exists
                if procedure_id not in skills_data:
                    skills_data[procedure_id] = {
                        'name': procedure_name,
                        'category': procedure_category,
                        'osce_levels': set(),
                        'students': set(),
                        'scores': []
                    }
                
                # Add OSCE level
                if exam_type:
                    skills_data[procedure_id]['osce_levels'].add(exam_type)
                
                # Process exam assignments
                exam_assignments = ba_data.get('examassignment', [])
                for exam_ref in exam_assignments:
                    if exam_ref:
                        try:
                            exam_doc = exam_ref.get()
                            if exam_doc.exists:
                                exam_data = exam_doc.to_dict()
                                user_ref = exam_data.get('user')
                                
                                if user_ref:
                                    user_id = user_ref.id
                                    skills_data[procedure_id]['students'].add(user_id)
                                    
                                    # Process completed exams
                                    if str(exam_data.get('status', '')).lower() == 'completed':
                                        total_score = exam_data.get("marks", 0)
                                        exam_metadata = exam_data.get('examMetaData', [])
                                        max_marks = sum(
                                            question.get('right_marks_for_question', 0)
                                            for section in exam_metadata
                                            for question in section.get("section_questions", [])
                                        )
                                        if max_marks > 0:
                                            percentage = round((total_score / max_marks) * 100, 2)
                                            skills_data[procedure_id]['scores'].append(percentage)
                        except Exception as e:
                            print(f"Error processing exam assignment: {str(e)}")
                            continue
            except Exception as e:
                print(f"Error fetching procedure data: {str(e)}")
                continue
        
        # Process skills data for response
        skills_list = []
        for procedure_id, skill_data in skills_data.items():
            avg_score = round(sum(skill_data['scores']) / len(skill_data['scores']), 2) if skill_data['scores'] else 0
            
            # Get grade letter
            def get_grade_letter(percentage):
                if percentage >= 90:
                    return 'A'
                elif percentage >= 80:
                    return 'B'
                elif percentage >= 70:
                    return 'C'
                elif percentage >= 60:
                    return 'D'
                else:
                    return 'E'
            
            grade = get_grade_letter(avg_score) if avg_score > 0 else '-'
            
            # Sort OSCE levels
            osce_levels_list = sorted(list(skill_data['osce_levels']))
            osce_levels_str = ', '.join(osce_levels_list) if osce_levels_list else 'N/A'
            
            skills_list.append({
                'procedure_id': procedure_id,
                'name': skill_data['name'],
                'category': skill_data['category'],
                'osce_levels': osce_levels_str,
                'students_attempted': len(skill_data['students']),
                'average_score': avg_score,
                'grade': grade
            })
        
        # Calculate summary KPIs
        total_skills = len(skills_list)
        highest_skill = None
        lowest_skill = None
        
        if skills_list:
            # Sort by average score to find highest and lowest
            sorted_by_score = sorted(skills_list, key=lambda x: x['average_score'], reverse=True)
            highest_skill = sorted_by_score[0]
            lowest_skill = sorted_by_score[-1]
        
        # Calculate skills distribution for pie chart
        distribution = {
            'above_90': 0,
            'between_80_90': 0,
            'between_70_80': 0,
            'between_60_70': 0,
            'below_60': 0
        }
        
        for skill in skills_list:
            score = skill['average_score']
            if score >= 90:
                distribution['above_90'] += 1
            elif score >= 80:
                distribution['between_80_90'] += 1
            elif score >= 70:
                distribution['between_70_80'] += 1
            elif score >= 60:
                distribution['between_60_70'] += 1
            else:
                distribution['below_60'] += 1
        
        return JsonResponse({
            'success': True,
            'total_skills': total_skills,
            'highest_skill': highest_skill,
            'lowest_skill': lowest_skill,
            'skills': skills_list,
            'distribution': distribution
        })
        
    except Exception as e:
        print(f"Error fetching skills for category: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def fetch_osce_report_optimized(request):
    """
    OPTIMIZED OSCE Report - Reads from pre-computed metrics
    
    Works for BOTH institutions and hospitals
    
    This endpoint is 20x faster because it reads from pre-computed
    SemesterMetrics and UnitMetrics collections instead of computing
    everything on-demand.
    
    Usage:
        GET /api/osce-report/?unit_name=DJ%20Sanghvi%20College&academic_year=2025&semester=1
        GET /api/osce-report/?unit_name=City%20Hospital&academic_year=2025&semester=1
    
    Pre-requisites:
        - Run: python manage.py process_metric_queue every 5 minutes via cron
        - Frontend must queue updates via MetricUpdateQueue collection
    """
    try:
        # Get filter parameters
        # Support multiple parameter formats:
        # 1. unit_name (direct) - preferred
        # 2. institution_name (backward compatibility)
        # 3. institution_id + institution_type (from frontend) - convert to unit_name
        unit_name = request.GET.get('unit_name') or request.GET.get('institution_name')
        institution_id = request.GET.get('institution_id')
        institution_type = request.GET.get('institution_type')
        academic_year = request.GET.get('academic_year')
        semester = request.GET.get('semester', 'All')
        osce_level = request.GET.get('osce_level', 'All')
        skill = request.GET.get('skill', '')
        
        # Convert institution_id + institution_type to unit_name if needed
        if not unit_name and institution_id and institution_type:
            if institution_type == 'institution':
                from assessments.models import Institution
                try:
                    inst = Institution.objects.get(id=institution_id)
                    unit_name = inst.name
                except Institution.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Institution not found'
                    }, status=404)
            elif institution_type == 'hospital':
                from assessments.models import Hospital
                try:
                    hosp = Hospital.objects.get(id=institution_id)
                    unit_name = hosp.name
                except Hospital.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Hospital not found'
                    }, status=404)
        
        if not unit_name or not academic_year:
            return JsonResponse({
                'success': False,
                'error': 'unit_name (or institution_name or institution_id+institution_type) and academic_year are required'
            }, status=400)
        
        # Check if metrics are available
        doc_id = f"{unit_name}_{academic_year}"
        unit_doc = db.collection('UnitMetrics').document(doc_id).get()
        
        if not unit_doc.exists:
            return JsonResponse({
                'success': False,
                'error': 'No pre-computed metrics found. Please wait for metrics to be computed.',
                'hint': 'Run: python manage.py process_metric_queue'
            }, status=404)
        
        unit_data = unit_doc.to_dict()
        
        # ==========================================
        # SCENARIO 1: ALL SEMESTERS (No filters)
        # ==========================================
        if semester == 'All' and osce_level == 'All' and not skill:
            semester_breakdown = unit_data.get('semester_breakdown', {})
            
            # Convert to semester_wise_performance format
            semester_wise_performance = []
            for sem_num, sem_data in sorted(semester_breakdown.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                semester_wise_performance.append({
                    'semester': str(sem_num),
                    'num_students': sem_data.get('total_students', 0),
                    'num_osces': sem_data.get('osces_conducted', 0),
                    'average_score': sem_data.get('avg_score', 0),
                    'pass_percentage': sem_data.get('pass_rate', 0),
                    'most_recent_date': 'N/A',  # TODO: Add to pre-computed data
                    'osce_type': 'Mixed'  # TODO: Add to pre-computed data
                })
            
            # Convert category_performance to category_wise_performance format
            category_wise_performance = []
            for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
                category_wise_performance.append({
                    'category': category,
                    'percentage': unit_data.get('category_performance', {}).get(category)
                })
            
            total_students = unit_data.get('total_students', 0)
            students_assessed = unit_data.get('students_assessed', 0)
            total_osces = unit_data.get('total_osces', 0)
            skills_evaluated = unit_data.get('skills_evaluated', 0)
            assessment_rate = round((students_assessed / total_students * 100), 2) if total_students else 0
            
            return JsonResponse({
                'success': True,
                'display_mode': 'overall',  # Indicates overall institutional view
                'total_students_enrolled': total_students,
                'students_assessed': students_assessed,
                'total_osce_conducted': total_osces,
                'assessment_rate': assessment_rate,
                'skills_evaluated': skills_evaluated,
                'average_institution_score': unit_data.get('avg_score', 0),
                'grade_letter': _get_grade_letter(unit_data.get('avg_score', 0)),
                'pass_rate': unit_data.get('pass_rate', 0),
                'filter_year': academic_year,
                'semester_wise_performance': semester_wise_performance,
                'category_wise_performance': category_wise_performance,
                'completed_exam_scores': [],  # Not needed for overall view
                'data_source': 'pre_computed',
                'unit_type': unit_data.get('unit_type', 'institute'),  # Include unit type
                'last_updated': unit_data.get('last_updated')
            })
        
        # ==========================================
        # SCENARIO 2: SPECIFIC SEMESTER (FULL ANALYTICS)
        # ==========================================
        if semester != 'All':
            sem_doc_id = f"{unit_name}_{academic_year}_{semester}"
            sem_doc = db.collection('SemesterMetrics').document(sem_doc_id).get()
            
            if not sem_doc.exists:
                return JsonResponse({
                    'success': False,
                    'error': f'No metrics found for semester {semester}'
                }, status=404)
            
            sem_data = sem_doc.to_dict()
            
            # Convert category_performance
            category_wise_performance = []
            for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
                category_wise_performance.append({
                    'category': category,
                    'percentage': sem_data.get('category_performance', {}).get(category)
                })
            
            # Get latest OSCE details
            latest_osce_data = sem_data.get('latest_osce', {})
            latest_osce_str = 'N/A'
            if latest_osce_data:
                latest_osce_str = f"{latest_osce_data.get('osce_level', 'N/A')} OSCE - {latest_osce_data.get('date_conducted', 'N/A')}"
            
            # Build semester_wise_performance
            osce_timeline = sem_data.get('osce_activity_timeline', [])
            most_recent_date = 'N/A'
            osce_type = 'Mixed'
            
            if osce_timeline:
                # Get the highest priority OSCE
                most_recent_date = osce_timeline[0].get('date_conducted', 'N/A')
                osce_type = osce_timeline[0].get('osce_level', 'Mixed')
            
            semester_wise_performance = [{
                'semester': semester,
                'num_students': sem_data.get('total_students', 0),
                'num_osces': sem_data.get('osces_conducted', 0),
                'average_score': sem_data.get('avg_score', 0),
                'pass_percentage': sem_data.get('pass_rate', 0),
                'most_recent_date': most_recent_date,
                'osce_type': osce_type
            }]
            
            # Build COMPLETE semester dashboard with ALL data
            semester_dashboard = {
                'total_students': sem_data.get('total_students', 0),
                'num_assessors': sem_data.get('num_assessors', 0),
                'osces_conducted': sem_data.get('osces_conducted', 0),
                'latest_osce': latest_osce_str,
                'average_score': sem_data.get('avg_score', 0),
                'grade_letter': sem_data.get('grade_letter', 'D'),
                'pass_rate': sem_data.get('pass_rate', 0),
                'semester_name': f"Semester {semester}",
                'academic_year': academic_year,
                'osce_activity_timeline': sem_data.get('osce_activity_timeline', []),
                'student_batch_report': sem_data.get('student_batch_report', [])
            }
            
            # Build skills list (for category-wise drill-down)
            skills_performance = sem_data.get('skills_performance', {})
            skills_by_category = defaultdict(list)
            
            for skill_id, skill_data in skills_performance.items():
                category = skill_data.get('category', 'Unknown')
                skills_by_category[category].append({
                    'skill_id': skill_id,
                    'skill_name': skill_data.get('skill_name', 'Unknown'),
                    'category': category,  # Include category in skill data
                    'attempts': skill_data.get('attempts', 0),
                    'students_attempted': skill_data.get('students_attempted', 0),
                    'avg_score': skill_data.get('avg_score', 0),
                    'pass_rate': skill_data.get('pass_rate', 0),
                    'highest_score': skill_data.get('highest_score', 0),
                    'lowest_score': skill_data.get('lowest_score', 0),
                    'osce_types': skill_data.get('osce_types', []),
                    'station_breakdown': skill_data.get('station_breakdown', {})
                })
            
            return JsonResponse({
                'success': True,
                'display_mode': 'semester',  # Indicates semester-specific view
                'total_students_enrolled': sem_data.get('total_students', 0),
                'students_assessed': sem_data.get('students_assessed', 0),
                'total_osce_conducted': sem_data.get('osces_conducted', 0),
                'assessment_rate': round((sem_data.get('students_assessed', 0) / sem_data.get('total_students', 1) * 100), 2),
                'skills_evaluated': sem_data.get('skills_evaluated', 0),
                'average_institution_score': sem_data.get('avg_score', 0),
                'grade_letter': sem_data.get('grade_letter', 'D'),
                'pass_rate': sem_data.get('pass_rate', 0),
                'filter_year': academic_year,
                'semester_wise_performance': semester_wise_performance,
                'category_wise_performance': category_wise_performance,
                'completed_exam_scores': sem_data.get('raw_scores', []),
                'grade_distribution': sem_data.get('grade_distribution', {}),
                'semester_dashboard': semester_dashboard,
                'skills_by_category': dict(skills_by_category),
                'data_source': 'pre_computed',
                'unit_type': sem_data.get('unit_type', 'institute'),  # Include unit type
                'last_updated': sem_data.get('last_updated')
            })
        
        # ==========================================
        # SCENARIO 3: WITH FILTERS (OSCE Level or Procedure)
        # ==========================================
        # Filter pre-computed semester data based on OSCE level or procedure
        
        if (osce_level and osce_level != 'All') or skill:
            # Must have semester selected for filtered views
            if semester == 'All':
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a specific semester to apply OSCE Level or Procedure filters'
                }, status=400)
            
            # Get semester metrics
            sem_doc_id = f"{unit_name}_{academic_year}_{semester}"
            sem_doc = db.collection('SemesterMetrics').document(sem_doc_id).get()
            
            if not sem_doc.exists:
                return JsonResponse({
                    'success': False,
                    'error': f'No metrics found for semester {semester}'
                }, status=404)
            
            sem_data = sem_doc.to_dict()
            
            # Filter data based on OSCE level or procedure
            filtered_skills = {}
            filtered_timeline = []
            filtered_students = {}
            filtered_scores = []
            
            # Filter skills_performance
            skills_performance = sem_data.get('skills_performance', {})
            for skill_id, skill_data in skills_performance.items():
                osce_types = skill_data.get('osce_types', [])
                
                # Apply OSCE level filter
                if osce_level and osce_level != 'All':
                    if osce_level not in osce_types:
                        continue
                
                # Apply procedure filter
                if skill:
                    if skill_id != skill:
                        continue
                
                filtered_skills[skill_id] = skill_data
            
            # Filter OSCE activity timeline
            osce_timeline = sem_data.get('osce_activity_timeline', [])
            for osce in osce_timeline:
                osce_type = osce.get('osce_level', '')
                
                # Apply OSCE level filter
                if osce_level and osce_level != 'All':
                    if osce_type != osce_level:
                        continue
                
                # Apply procedure filter (check if procedure is in this OSCE)
                if skill:
                    # This requires checking if the skill was assessed in this OSCE
                    # For now, we'll include all OSCEs (can be refined later)
                    pass
                
                filtered_timeline.append(osce)
            
            # Filter student batch report (recalculate based on filtered data)
            # This is complex, so for now we'll return full student list
            # but indicate that scores are filtered
            student_batch_report = sem_data.get('student_batch_report', [])
            
            # Recalculate aggregate metrics from filtered data
            if filtered_skills:
                all_skill_scores = []
                for skill_data in filtered_skills.values():
                    # We don't have individual scores, use avg_score * attempts as approximation
                    avg = skill_data.get('avg_score', 0)
                    attempts = skill_data.get('attempts', 0)
                    # This is approximate
                    all_skill_scores.extend([avg] * attempts)
                
                filtered_avg_score = round(sum(all_skill_scores) / len(all_skill_scores), 2) if all_skill_scores else 0
                filtered_pass_rate = round(sum(1 for s in all_skill_scores if s >= 80) / len(all_skill_scores) * 100, 2) if all_skill_scores else 0
            else:
                filtered_avg_score = 0
                filtered_pass_rate = 0
            
            # Calculate category performance from filtered skills
            category_scores = defaultdict(list)
            for skill_data in filtered_skills.values():
                category = skill_data.get('category', 'Unknown')
                avg_score = skill_data.get('avg_score', 0)
                if avg_score > 0:
                    category_scores[category].append(avg_score)
            
            category_wise_performance = []
            for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
                if category in category_scores:
                    avg = round(sum(category_scores[category]) / len(category_scores[category]), 2)
                    category_wise_performance.append({
                        'category': category,
                        'percentage': avg
                    })
                else:
                    category_wise_performance.append({
                        'category': category,
                        'percentage': None
                    })
            
            # Build skills_by_category for filtered skills
            skills_by_category = defaultdict(list)
            for skill_id, skill_data in filtered_skills.items():
                category = skill_data.get('category', 'Unknown')
                skills_by_category[category].append({
                    'skill_id': skill_id,
                    'skill_name': skill_data.get('skill_name', 'Unknown'),
                    'category': category,
                    'attempts': skill_data.get('attempts', 0),
                    'students_attempted': skill_data.get('students_attempted', 0),
                    'avg_score': skill_data.get('avg_score', 0),
                    'pass_rate': skill_data.get('pass_rate', 0),
                    'highest_score': skill_data.get('highest_score', 0),
                    'lowest_score': skill_data.get('lowest_score', 0),
                    'osce_types': skill_data.get('osce_types', []),
                    'station_breakdown': skill_data.get('station_breakdown', {})
                })
            
            # Build semester_wise_performance (single row for filtered data)
            semester_wise_performance = [{
                'semester': semester,
                'num_students': sem_data.get('total_students', 0),  # Keep total students
                'num_osces': len(filtered_timeline),  # Filtered OSCEs count
                'average_score': filtered_avg_score,
                'pass_percentage': filtered_pass_rate,
                'most_recent_date': filtered_timeline[0].get('date_conducted', 'N/A') if filtered_timeline else 'N/A',
                'osce_type': filtered_timeline[0].get('osce_level', 'N/A') if filtered_timeline else 'N/A'
            }]
            
            # Build semester dashboard
            semester_dashboard = {
                'total_students': sem_data.get('total_students', 0),
                'num_assessors': sem_data.get('num_assessors', 0),
                'osces_conducted': len(filtered_timeline),
                'latest_osce': f"{filtered_timeline[0].get('osce_level', 'N/A')} OSCE - {filtered_timeline[0].get('date_conducted', 'N/A')}" if filtered_timeline else 'N/A',
                'average_score': filtered_avg_score,
                'grade_letter': _get_grade_letter(filtered_avg_score),
                'pass_rate': filtered_pass_rate,
                'semester_name': f"Semester {semester}",
                'academic_year': academic_year,
                'osce_activity_timeline': filtered_timeline,
                'student_batch_report': student_batch_report  # Full list for now
            }
            
            return JsonResponse({
                'success': True,
                'display_mode': 'filtered',  # Indicates filtered view (OSCE level or procedure)
                'total_students_enrolled': sem_data.get('total_students', 0),
                'students_assessed': sem_data.get('students_assessed', 0),
                'total_osce_conducted': len(filtered_timeline),
                'assessment_rate': round((sem_data.get('students_assessed', 0) / sem_data.get('total_students', 1) * 100), 2),
                'skills_evaluated': len(filtered_skills),
                'average_institution_score': filtered_avg_score,
                'grade_letter': _get_grade_letter(filtered_avg_score),
                'pass_rate': filtered_pass_rate,
                'filter_year': academic_year,
                'semester_wise_performance': semester_wise_performance,
                'category_wise_performance': category_wise_performance,
                'completed_exam_scores': [],  # Not available in filtered view
                'grade_distribution': {},  # Not available in filtered view
                'semester_dashboard': semester_dashboard,
                'skills_by_category': dict(skills_by_category),
                'data_source': 'pre_computed_filtered',
                'unit_type': sem_data.get('unit_type', 'institute'),
                'last_updated': sem_data.get('last_updated'),
                'filter_applied': {
                    'osce_level': osce_level if osce_level != 'All' else None,
                    'procedure': skill if skill else None
                }
            })
        
        # If we reach here, no special filtering needed, return error
        return JsonResponse({
            'success': False,
            'error': 'Invalid filter combination'
        }, status=400)
        
    except Exception as e:
        print(f"Error in optimized report: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _get_grade_letter(percentage):
    """Helper function to convert percentage to grade letter"""
    if percentage >= 90:
        return 'A'
    elif percentage >= 80:
        return 'B'
    elif percentage >= 70:
        return 'C'
    elif percentage >= 60:
        return 'D'
    else:
        return 'E'


@csrf_exempt
def view_metrics_data(request):
    """
    Frontend page to view SemesterMetrics and UnitMetrics data
    """
    return render(request, 'assessments/metrics_viewer.html')


@csrf_exempt
def fetch_semester_metrics(request):
    """
    API endpoint to fetch all SemesterMetrics documents

    Query Parameters:
        - unit_name: Filter by unit name (optional)
        - year: Filter by year (optional)
        - semester: Filter by semester (optional)
    """
    try:
        import os
        from dotenv import load_dotenv
        from firebase_admin import firestore

        load_dotenv()
        firebase_database = os.getenv('FIREBASE_DATABASE')
        db = firestore.client(database_id=firebase_database) if firebase_database else firestore.client()

        # Build query
        query = db.collection('SemesterMetrics')

        # Apply filters
        unit_name = request.GET.get('unit_name')
        year = request.GET.get('year')
        semester = request.GET.get('semester')

        if unit_name:
            query = query.where('unit_name', '==', unit_name)
        if year:
            query = query.where('year', '==', year)
        if semester:
            query = query.where('semester', '==', semester)

        # Fetch documents
        docs = list(query.stream())

        # Convert to JSON-serializable format
        results = []
        for doc in docs:
            data = doc.to_dict()

            # Convert Firestore timestamps to ISO strings
            if 'last_updated' in data and data['last_updated']:
                try:
                    data['last_updated'] = data['last_updated'].isoformat()
                except:
                    data['last_updated'] = str(data['last_updated'])

            # Convert sets to lists for JSON serialization
            if 'assessed_student_ids' in data and isinstance(data['assessed_student_ids'], set):
                data['assessed_student_ids'] = list(data['assessed_student_ids'])

            results.append({
                'doc_id': doc.id,
                'data': data
            })

        return JsonResponse({
            'success': True,
            'count': len(results),
            'documents': results
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def fetch_unit_metrics(request):
    """
    API endpoint to fetch all UnitMetrics documents

    Query Parameters:
        - unit_name: Filter by unit name (optional)
        - year: Filter by year (optional)
    """
    try:
        import os
        from dotenv import load_dotenv
        from firebase_admin import firestore

        load_dotenv()
        firebase_database = os.getenv('FIREBASE_DATABASE')
        db = firestore.client(database_id=firebase_database) if firebase_database else firestore.client()

        # Build query
        query = db.collection('UnitMetrics')

        # Apply filters
        unit_name = request.GET.get('unit_name')
        year = request.GET.get('year')

        if unit_name:
            query = query.where('unit_name', '==', unit_name)
        if year:
            query = query.where('year', '==', year)

        # Fetch documents
        docs = list(query.stream())

        # Convert to JSON-serializable format
        results = []
        for doc in docs:
            data = doc.to_dict()

            # Convert Firestore timestamps to ISO strings
            if 'last_updated' in data and data['last_updated']:
                try:
                    data['last_updated'] = data['last_updated'].isoformat()
                except:
                    data['last_updated'] = str(data['last_updated'])

            results.append({
                'doc_id': doc.id,
                'data': data
            })

        return JsonResponse({
            'success': True,
            'count': len(results),
            'documents': results
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
