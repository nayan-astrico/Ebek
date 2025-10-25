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

                                try:
                                    user_data = user_snapshot.to_dict()
                                    exam_assignment_data['institute'] = user_data.get('institution', '')
                                except (AttributeError, TypeError) as e:
                                    logger.warning(f"Failed to get institution for user {user_snapshot.id}: {str(e)}")
                                
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
                logger.info("Here in else")
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
                logger.info(test_data)
                
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

                        # Update Test document with all procedure assignments
                        test_ref.update({'procedureAssignments': firestore.ArrayUnion(procedure_assignment_refs)})
                    except Exception as e:
                        logger.error("ERROR IN ELSE", traceback.format_exc())
                        logger.error("ERROR IN ELSE", str(e))
                        pass
                
                    

            return JsonResponse({'success': True, 'created_tests': created_tests})

        except Exception as e:
            logger.error(str(e))
            logger.error(traceback.format_exc())
            logger.error("HEEEREEEEEE")
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

@csrf_exempt
def get_test(request, test_id):
    """Return consolidated details for a Test including procedures and assessors."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)
    try:
        test_ref = db.collection('Test').document(test_id)
        test_doc = test_ref.get()
        if not test_doc.exists:
            return JsonResponse({'error': 'Test not found'}, status=404)
        test_data = test_doc.to_dict()

        # Procedures
        procedures = []
        assessors_map = {}
        for proc_ref in test_data.get('procedureAssignments', []) or []:
            try:
                proc_doc = proc_ref.get()
                if not proc_doc.exists:
                    continue
                proc_data = proc_doc.to_dict()
                procedure_ref = proc_data.get('procedure')
                if procedure_ref:
                    pdoc = procedure_ref.get()
                    if pdoc.exists:
                        procedures.append({'id': procedure_ref.id, 'name': pdoc.to_dict().get('procedureName', 'Unknown')})
                # Supervisors can be single 'supervisor' or list 'supervisors'
                if 'supervisors' in proc_data and isinstance(proc_data['supervisors'], list):
                    sup_list = proc_data['supervisors']
                else:
                    sup = proc_data.get('supervisor')
                    sup_list = [sup] if sup else []
                for sref in sup_list:
                    try:
                        sdoc = sref.get()
                        if sdoc.exists:
                            sdata = sdoc.to_dict()
                            assessors_map[sref.id] = {'id': sref.id, 'name': sdata.get('name', sdata.get('username', 'Assessor'))}
                    except Exception:
                        continue
            except Exception:
                continue

        response = {
            'id': test_id,
            'assessment_name': test_data.get('batchname') or test_data.get('skillathon') or '',
            'status': test_data.get('status', 'Not Completed'),
            'testdate': (test_data.get('testdate').strftime('%Y-%m-%d') if test_data.get('testdate') else None),
            'procedures': procedures,
            'assessors': list(assessors_map.values()),
            'skillathon': test_data.get('skillathon')
        }
        return JsonResponse({'success': True, 'test': response})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
def update_test(request, test_id):
    """Update Test fields: testdate and status."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    try:
        body = json.loads(request.body or '{}')
        testdate_str = body.get('testdate')
        status_val = body.get('status')
        procedure_ids = body.get('procedure_ids') or []
        assessor_ids = body.get('assessor_ids') or []

        test_ref = db.collection('Test').document(test_id)
        test_doc = test_ref.get()
        if not test_doc.exists:
            return JsonResponse({'error': 'Test not found'}, status=404)

        update_payload = {}
        if testdate_str:
            try:
                # Accept YYYY-MM-DD
                new_date = datetime.datetime.strptime(testdate_str, '%Y-%m-%d')
                update_payload['testdate'] = new_date
            except Exception:
                return JsonResponse({'error': 'Invalid date format, expected YYYY-MM-DD'}, status=400)
        if status_val:
            update_payload['status'] = status_val

        if update_payload:
            test_ref.update(update_payload)

        # If procedures/assessors provided, rebuild procedureAssignments
        if procedure_ids or assessor_ids:
            test_data = test_doc.to_dict()
            # Delete existing children
            for proc_ref in test_data.get('procedureAssignments', []) or []:
                try:
                    proc_doc = proc_ref.get()
                    if proc_doc.exists:
                        proc_data = proc_doc.to_dict()
                        for exam_ref in proc_data.get('examAssignmentArray', []) or []:
                            try:
                                exam_ref.delete()
                            except Exception:
                                pass
                    proc_ref.delete()
                except Exception:
                    pass

            new_proc_refs = []
            for procedure_id in procedure_ids:
                procedure_ref = db.collection('ProcedureTable').document(procedure_id)
                proc_assignment_data = {
                    'creationDate': datetime.datetime.now(),
                    'procedure': procedure_ref,
                    'status': 'Pending',
                    'typeOfTest': 'Classroom',
                    'supervisors': [db.collection('Users').document(aid) for aid in assessor_ids],
                    'examAssignmentArray': [],
                    'cohortStudentExamStarted': 0,
                    'test': test_ref,
                }
                proc_assignment_ref = db.collection('ProcedureAssignment').add(proc_assignment_data)[1]
                new_proc_refs.append(proc_assignment_ref)

            if new_proc_refs:
                test_ref.update({'procedureAssignments': new_proc_refs})

        return JsonResponse({'success': True})
    except Exception as e:
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
    return render(request, 'assessments/course_management.html')

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
            'created_at': batch_data.get('createdAt')
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
            osce_types = data.get('osceTypes', [])
            verification_required = data.get('verificationRequired', False)
            
            if not course_name:
                return JsonResponse({'error': 'Course name is required'}, status=400)
            
            if not procedure_ids:
                return JsonResponse({'error': 'At least one procedure is required'}, status=400)
            
            if not osce_types:
                return JsonResponse({'error': 'At least one OSCE type is required'}, status=400)
            
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
                'osceTypes': osce_types,
                'verificationRequired': verification_required,
                'status': 'active',
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
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
            
            return JsonResponse({
                'success': True,
                'status': new_status,
                'message': 'Course status updated successfully'
            }, status=200)
            
        except Exception as e:
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
            osce_types = data.get('osceTypes', [])
            verification_required = data.get('verificationRequired', False)
            
            if not course_name:
                return JsonResponse({'error': 'Course name is required'}, status=400)
            
            if not procedure_ids:
                return JsonResponse({'error': 'At least one procedure is required'}, status=400)
            
            if not osce_types:
                return JsonResponse({'error': 'At least one OSCE type is required'}, status=400)
            
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
                'osceTypes': osce_types,
                'verificationRequired': verification_required,
                'updatedAt': firestore.SERVER_TIMESTAMP
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
        
        unit_types = [u.strip().lower() for u in unit_type_param.split(',') if u.strip()] if unit_type_param else []
        statuses = [s.strip().lower() for s in status_param.split(',') if s.strip()] if status_param else []


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


        # Transform and filter
        formatted_batches = []
        for doc_id, batch_data in batches:
            batch_data = doc.to_dict()

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
                'createdAt': batch_data.get('createdAt')
            })

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
            'createdAt': batch_data.get('createdAt')
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

            if data.get('updateOnlyBatchName', True):
                batch_ref = db.collection('Batches').document(batch_id)
                batch_ref.update({
                    'batchName': batch_name
                })
                return JsonResponse({
                    'success': True,
                    'message': 'Batch name updated successfully'
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
        return JsonResponse({'roles': roles})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
        print(exc_info())
        print(e)
        print(traceback.format_exc())
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

# @csrf_exempt
# def fetch_assessments(request):
#     """API endpoint to fetch all assessments (procedures), with optional offset/limit and search filter."""
#     try:
#         # Pagination and filter parameters
#         offset = int(request.GET.get('offset', 0))
#         limit = int(request.GET.get('limit', 10))
#         search = request.GET.get('search', '').strip().lower()

#         # Reference to Firestore collection
#         procedures_ref = db.collection('ProcedureTable')
#         all_docs = list(procedures_ref.stream())

#         filtered_docs = []

#         # Filter and format data
#         for doc in all_docs:
#             data = doc.to_dict()
#             name = data.get('procedureName', 'N/A')
#             examMetaData = data.get("examMetaData", [])

#             # Calculate question count safely
#             question_count = 0
#             if examMetaData and isinstance(examMetaData, list) and "section_questions" in examMetaData[0]:
#                 question_count = len(examMetaData[0]["section_questions"])

#             active = data.get("active", True)

#             # Search filter
#             if search and search not in name.lower():
#                 continue

#             filtered_docs.append({
#                 'id': doc.id,
#                 'name': name,
#                 'questions': question_count,
#                 'active': active
#             })

#         # Pagination (lazy loading)
#         total_items = len(filtered_docs)
#         paginated = filtered_docs[offset:offset + limit]
#         all_loaded = offset + limit >= total_items

#         return JsonResponse({
#             'assessments': paginated,
#             'all_loaded': all_loaded,
#             'total_count': total_items
#         }, status=200)

#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def fetch_assessments(request):
    """API endpoint to fetch all assessments (procedures), with optional offset/limit, search, and status filter."""
    try:
        # Pagination and filter parameters
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 10))
        search = request.GET.get('search', '').strip().lower()
        status_filters = request.GET.getlist('status')
        status_filters = [s.lower() for s in status_filters if s]

        # Reference to Firestore collection
        procedures_ref = db.collection('ProcedureTable')
        all_docs = list(procedures_ref.stream())

        filtered_docs = []

        # Filter and format data
        for doc in all_docs:
            data = doc.to_dict()
            name = data.get('procedureName', 'N/A')
            examMetaData = data.get("examMetaData", [])
            active = data.get("active", True)
            status = 'active' if active else 'inactive'

            # Search filter
            if search and search not in name.lower():
                continue

            # Status filter
            if status_filters and status not in status_filters:
                continue

            # Calculate question count safely
            question_count = 0
            if examMetaData and isinstance(examMetaData, list):
                question_count = sum(len(section.get("section_questions", [])) for section in examMetaData)

            filtered_docs.append({
                'id': doc.id,
                'name': name,
                'questions': question_count,
                'active': active,
                'status': status
            })

        # Pagination (lazy loading)
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

            # Indicators required
            if str(row.get('Indicators')).strip() == '':
                errors.append({'row': row_number, 'message': 'Indicators is required'})

            # Category must be C/K/D
            category = str(row.get('Category (i.e C for Communication, K for Knowledge and D for Documentation)')).strip()
            if category not in ['C', 'K', 'D']:
                errors.append({'row': row_number, 'message': 'Category must be one of C, K, D'})

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
@require_POST
def upload_excel(request):
    file = request.FILES.get('file')
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
            'Section', 'Parameters', 'Indicators',
            'Category (i.e C for Communication, K for Knowledge and D for Documentation)',
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