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
from django.shortcuts import render
from firebase_admin import firestore
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import datetime

# Logger setup
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
                    current_parameter["right_marks_for_question"] = len(current_parameter["sub_section_questions"])
                procedure_json["exammetadata"][0]["section_questions"].append(current_parameter)

            current_parameter = {
                "question": row["Parameters"],  # Parameters column
                "right_marks_for_question": 1,
                "answer_scored": 0,
                "sub_section_questions_present": False,
                "sub_section_questions": [],
                "category": row["Category"] if pd.isna(row["Indicators"]) and not pd.isna(row["Category"]) else ""  # Use Category if no Indicators
            }

        if not pd.isna(row["Indicators"]) and current_parameter:  # Check for Indicators
            current_parameter["sub_section_questions_present"] = True
            current_parameter["sub_section_questions"].append({
                "question": row["Indicators"],  # Indicators column
                "right_marks_for_question": 1,
                "answer_scored": 0,
                "category": row["Category"] if not pd.isna(row["Category"]) else ""  # Use Category
            })

    if current_parameter:
        if current_parameter["sub_section_questions_present"]:
            current_parameter["right_marks_for_question"] = len(current_parameter["sub_section_questions"])
        procedure_json["exammetadata"][0]["section_questions"].append(current_parameter)

    return procedure_json

def upload_excel_view(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        print(form)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']

            file_name = f"{uuid.uuid4()}_{uploaded_file.name}".replace(" ", "_")
            file_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_excels', file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            try:
                df = pd.read_excel(file_path, header=None)  # Read without header to validate row/column content

                # Validate specific cells in row 3
                if not (
                    df.iloc[2, 0] == "Section" and
                    df.iloc[2, 1] == "Parameters" and
                    df.iloc[2, 2] == "Indicators"
                ):
                    raise ValueError("Excel template is incorrect. Ensure row 3 contains 'Section', 'Parameters', 'Indicators'.")

                # Extract Procedure Name
                procedure_name = df.iloc[0, 1].strip()  # Procedure Name from row 1, column 2

                # Process data from row 4 onward
                df_data = pd.read_excel(file_path, skiprows=3, header=None, names=["Section", "Parameters", "Indicators", "Category"])
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
        cohort_ref = db.collection('Cohort').where('cohortName', '==', 'EbekCohort').limit(1)
        assessors = []
        for doc in cohort_ref.stream():
            cohort_data = doc.to_dict()
            user_refs = cohort_data.get('users', [])
            for user_ref in user_refs:
                user = db.document(user_ref.path).get()
                if user.exists:
                    user_data = user.to_dict()
                    assessors.append({
                        'id': user.id,
                        'name': user_data.get('username', 'Unknown Assessor')
                    })

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


def create_procedure_assignment_and_test(request):
    if request.method == 'POST':
        try:
            data = request.POST
            print(data)
            # Parse required inputs
            batch_ids = data.getlist('batch_ids')  # Assuming array sent as batch_ids[]
            procedure_ids = data.getlist('procedure_ids')  # Assuming array sent as procedure_ids[]
            test_date = data.get('test_date')  # Selected date
            assessor_ids = data.getlist('assessor_ids')  # List of selected assessors

            # Ensure all required fields are present
            if not batch_ids or not procedure_ids or not test_date:
                return JsonResponse({'error': 'All fields are required.'}, status=400)

            # Convert test_date to datetime object
            test_date_obj = datetime.datetime.strptime(test_date, '%Y-%m-%d')

            # Get current user (for now set to null as per your request)
            current_user = None  # Change this as needed based on your auth logic

            created_tests = []  # To store references for created tests

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
                    'creationDate': datetime.datetime.now(),
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

                    # Create ProcedureAssignment
                    # For Jaipur event
                    procedure_assignment_data = {
                        'assignmentToBeDoneDate': test_date_obj,  # Match selected test_date
                        'cohort': cohort_ref,
                        'cohortStudentExamTaken': 0,
                        'creationDate': datetime.datetime.now(),
                        'procedure': procedure_ref,
                        'status': 'Pending',
                        'typeOfTest': 'Classroom',  # Hardcoded to "Final"
                        'supervisor': db.collection('Users').document(assessor_ids[0]),  # Not needed for "Final"
                        'examAssignmentArray': [],
                        'cohortStudentExamStarted': 0,
                        'test': test_ref,
                    }

                    # For normal events
                    # procedure_assignment_data = {
                    #     'assignmentToBeDoneDate': test_date_obj,  # Match selected test_date
                    #     'cohort': cohort_ref,
                    #     'cohortStudentExamTaken': 0,
                    #     'creationDate': datetime.datetime.now(),
                    #     'procedure': procedure_ref,
                    #     'status': 'Pending',
                    #     'typeOfTest': 'Final',  # Hardcoded to "Final"
                    #     'supervisor': None,  # Not needed for "Final"
                    #     'examAssignmentArray': [],
                    #     'cohortStudentExamStarted': 0,
                    #     'test': test_ref,
                    # }
                    
                    procedure_assignment_ref = db.collection('ProcedureAssignment').add(procedure_assignment_data)[1]
                    procedure_assignment_refs.append(procedure_assignment_ref)

                    # Create ExamAssignments
                    exam_assignment_refs = []
                    for user_ref in users:
                        exam_meta_data = procedure_data.get('examMetaData', {})
                        notes = procedure_data.get('notes', '')

                        exam_assignment_data = {
                            'user': user_ref,
                            'examMetaData': exam_meta_data,
                            'status': 'Pending',
                            'notes': notes,
                        }
                        exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                        exam_assignment_refs.append(exam_assignment_ref)

                    # Update ProcedureAssignment with exam assignments
                    procedure_assignment_ref.update({'examAssignmentArray': firestore.ArrayUnion(exam_assignment_refs)})

                # Update Test document with procedure assignments
                test_ref.update({'procedureAssignments': firestore.ArrayUnion(procedure_assignment_refs)})

                # Create CohortProcedureAssignments
                for assessor_id in assessor_ids:
                    db.collection('CohortProcedureAssignments').add({
                        'test': test_ref,
                        'user': db.collection('Users').document(assessor_id),
                        'typeOfTest': 'Final',
                    })

            return JsonResponse({'success': True, 'created_tests': created_tests})

        except Exception as e:
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
        test_data.append({
            'id': test.id,
            'assessment_name': f"{test_doc.get('batchname', 'Unknown')} - {test_doc.get('testdate').strftime('%d %b')}",
            'institute': test_doc.get('cohort').get().to_dict().get('instituteName', 'Unknown') if test_doc.get('cohort') else 'Unknown',
            'status': test_doc.get('status', 'Not Available'),
        })

    query = request.GET.get("query", "")
    if query:
        test_data = [test for test in test_data if query.lower() in test["assessment_name"].lower()]
    
    # Pagination
    paginator = Paginator(test_data, 10)  # Show 10 procedures per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Render the template with test data and pagination object
    return render(request, 'assessments/assign_assessment.html', {
        "page_obj": page_obj,
        "query": query,
    })