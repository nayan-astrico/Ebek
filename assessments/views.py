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
from django.views.decorators.csrf import csrf_exempt



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
        cohort_ref = db.collection('Cohort').where('cohortName', '==', 'SupervisorCohort').limit(1)
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

                    # Create ProcedureAssignment for each assessor
                    for assessor_id in assessor_ids:
                        procedure_assignment_data = {
                            'assignmentToBeDoneDate': test_date_obj,
                            'cohort': cohort_ref,
                            'cohortStudentExamTaken': 0,
                            'creationDate': datetime.datetime.now(),
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
                        for user_ref in users:
                            exam_meta_data = procedure_data.get('examMetaData', {})
                            notes = procedure_data.get('notes', '')
                            procedure_name = procedure_data.get('procedureName', '')

                            exam_assignment_data = {
                                'user': user_ref,
                                'examMetaData': exam_meta_data,
                                'status': 'Pending',
                                'notes': notes,
                                'procedure_name': procedure_name
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

def render_exam_reports_page(request):
    return render(request, 'assessments/exam_reports.html')


@csrf_exempt
def fetch_exam_reports(request):
    try:
        exam_reports = []

        # Handle pagination
        offset = int(request.GET.get("offset", 0))
        limit = int(request.GET.get("limit", 10))

        # Handle auto-fetch for new data
        auto_fetch = request.GET.get("auto_fetch", "false").lower() == "true"

        if auto_fetch:
            one_minute_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
            exam_assignments_ref = db.collection('ExamAssignment').where("completed_data", ">=", one_minute_ago)
            exam_assignments_ref = exam_assignments_ref.order_by("completed_data", direction=firestore.Query.DESCENDING)
            exam_assignments = exam_assignments_ref.stream()
        else:
            exam_assignments_ref = db.collection('ExamAssignment').where("status", "==", "Completed")
            exam_assignments_ref = exam_assignments_ref.order_by("completed_data", direction=firestore.Query.DESCENDING)
            exam_assignments = exam_assignments_ref.offset(offset).limit(limit).stream()

        for exam in exam_assignments:
            exam_doc = exam.to_dict()
            student_ref = exam_doc.get('user')

            if not student_ref:
                continue

            student_id = student_ref.id
            student_data = student_ref.get().to_dict()
            student_name = student_data.get('username', 'Unknown')

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
            .order_by("completed_data", direction=firestore.Query.DESCENDING)
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
        print(institutes_ref)
        print(institutes)
        
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
        users_ref = db.collection('Users')
        users = []

        query = request.GET.get("query", "")

        # Fetch all users
        for doc in users_ref.stream():
            user_data = doc.to_dict()
            institute_ref = user_data.get('institute')
            
            institute_name = "Unknown"
            if institute_ref:
                institute_doc = institute_ref.get()
                if institute_doc.exists:
                    institute_name = institute_doc.to_dict().get('instituteName', 'Unknown')

            user = {
                'id': doc.id,
                'username': user_data.get('username', 'N/A'),
                'emailID': user_data.get('emailID', 'N/A'),
                'institute': institute_name,
                'role': user_data.get('role', 'student'),
                'createdAt': user_data.get('createdAt')  # Get creation date
            }
            
            if query:
                if query.lower() in user['username'].lower() or query.lower() in institute_name.lower():
                    users.append(user)
            else:
                users.append(user)

        # Sort users by creation date (newest first)
        users.sort(key=lambda x: x.get('createdAt', datetime.datetime.min), reverse=True)

        # Pagination
        paginator = Paginator(users, 10)  # Show 10 users per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(request, 'assessments/users_management.html', {
            "page_obj": page_obj,
            "query": query,
        })

    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return render(request, 'assessments/users_management.html', {
            "error": "Failed to fetch users",
            "page_obj": [],
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