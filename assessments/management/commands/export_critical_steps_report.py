"""
Management command to export Skillathon Candidate Scores Report

⚠️  IMPORTANT: This script is COMPLETELY ISOLATED from development environment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Uses ONLY production Firebase credentials
- Does NOT use development Firebase from settings.py
- Requires --service-account parameter (MANDATORY)
- Cannot run without production credentials

Data Source:
- Fetches completed exams from ExamAssignment collection
- Gets institute-to-skillathon mapping from InstituteNames collection
- Performs client-side filtering and joining of data

This script generates a comprehensive report with the following structure:
    Skillathon → Institution → Candidate → Skills with Scores and Critical Steps

CSV Format:
    For each skill/procedure, there are 2 columns:
    - Procedure Name: Candidate's percentage score (e.g., "90%")
    - Procedure Name - Critical Steps Missed: Number of critical steps missed

Example Output:
    | Skillathon | Institution | Candidate Name | Intubation | Intubation - Critical Steps Missed | Central Line | Central Line - Critical Steps Missed |
    | Test Event | College A   | John Doe       | 90%        | 2                                  | 85%          | 1                                   |
    | Test Event | College A   | Jane Smith     | 78%        | 3                                  | 88%          | 0                                   |
    | Test Event | College B   | Alice Brown    | 95%        | 0                                  | 90%          | 2                                   |

Usage:
    python manage.py export_critical_steps_report --service-account "path/to/prod-creds.json" [OPTIONS]

Required Arguments:
    --service-account "path/to/prod-firebase-credentials.json"  Path to production Firebase service account JSON

Optional Arguments:
    --skillathon "Name"              Filter by skillathon name
    --institution "Name"             Filter by institution name
    --output "file.csv"              Output CSV file path (default: critical_steps_report.csv)

Examples:
    # Export all data from Production
    python manage.py export_critical_steps_report --service-account "/path/to/prod-firebase-credentials.json" --output report.csv

    # Export for specific skillathon
    python manage.py export_critical_steps_report --service-account "/path/to/prod-firebase-credentials.json" --skillathon "OSCE 2025" --output report.csv

    # Export for specific skillathon and institution
    python manage.py export_critical_steps_report --service-account "/path/to/prod-firebase-credentials.json" --skillathon "OSCE 2025" --institution "XYZ College" --output report.csv
"""

import csv
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import firebase_admin
from firebase_admin import credentials, firestore
import os


class Command(BaseCommand):
    help = "Export Skillathon Critical Steps Report (Skillathon → Institution → Candidate → Skills with Critical Steps Missed)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--skillathon',
            type=str,
            help='Filter by skillathon name',
        )
        parser.add_argument(
            '--institution',
            type=str,
            help='Filter by institution name',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='critical_steps_report.csv',
            help='Output CSV file path (default: critical_steps_report.csv)',
        )
        parser.add_argument(
            '--service-account',
            type=str,
            help='Path to Firebase service account JSON file (for production database). If not provided, uses default Firebase credentials.',
        )

    def handle(self, *args, **options):
        skillathon_filter = options.get('skillathon')
        institution_filter = options.get('institution')
        output_file = options.get('output')
        service_account_path = options.get('service_account')

        self.stdout.write(self.style.SUCCESS('🚀 Starting Critical Steps Report Export...'))

        # IMPORTANT: This script MUST use a separate Firebase instance
        # It should NEVER use the development Firebase from settings.py
        if not service_account_path:
            raise CommandError(
                "❌ ERROR: --service-account parameter is REQUIRED for this script.\n"
                "This script is isolated from development and only works with production Firebase credentials.\n"
                "\nUsage:\n"
                "  python manage.py export_critical_steps_report --service-account \"/path/to/prod-firebase-credentials.json\" --output report.csv\n"
            )

        # Validate service account file exists
        if not os.path.exists(service_account_path):
            raise CommandError(f"❌ Service account file not found: {service_account_path}")

        try:
            self.stdout.write(f"📁 Reading service account file: {service_account_path}")
            cred = credentials.Certificate(service_account_path)

            # Create a completely isolated Firebase app instance
            # This is NOT connected to development Firebase in any way
            app_name = 'production-export-report-app'

            # Check if this specific app already exists
            if firebase_admin._apps.get(app_name):
                self.stdout.write(f"♻️  Reusing existing Firebase app instance: {app_name}")
                app = firebase_admin.get_app(app_name)
            else:
                self.stdout.write(f"🔧 Initializing new Firebase app instance: {app_name}")
                app = firebase_admin.initialize_app(cred, name=app_name)

            # Get Firestore client from this isolated app instance
            db = firestore.client(app=app)
            self.stdout.write(self.style.SUCCESS('✅ Successfully connected to Production Firebase (ISOLATED)'))
            self.stdout.write(f"ℹ️  This script is completely independent from development environment")

        except Exception as e:
            raise CommandError(f"❌ Failed to initialize Production Firebase: {str(e)}")

        try:
            # Step 1: Build mapping of institute -> skillathon from InstituteNames collection
            self.stdout.write("📚 Building institute-to-skillathon mapping from InstituteNames collection...")
            institute_to_skillathon = {}
            institute_names = db.collection('InstituteNames').stream()

            for doc in institute_names:
                data = doc.to_dict()
                institute_name = data.get('instituteName')
                skillathon_event = data.get('skillathon_event')
                if institute_name and skillathon_event:
                    institute_to_skillathon[institute_name] = skillathon_event

            self.stdout.write(f"✅ Mapped {len(institute_to_skillathon)} institutes to skillathons")

            # Step 2: Fetch exam assignments with status='Completed'
            self.stdout.write("📋 Fetching completed exam assignments from ExamAssignment collection...")
            query = db.collection('ExamAssignment').where('status', '==', 'Completed')
            exam_assignments = list(query.stream())
            self.stdout.write(f"Found {len(exam_assignments)} total completed exam assignments")

            # Step 3: Filter by skillathon and institution using the mapping
            if skillathon_filter or institution_filter:
                self.stdout.write("🔍 Applying filters...")
                if skillathon_filter:
                    self.stdout.write(f"  Filtering by skillathon: {skillathon_filter}")
                if institution_filter:
                    self.stdout.write(f"  Filtering by institution: {institution_filter}")

                filtered_exams = []
                for exam in exam_assignments:
                    exam_data = exam.to_dict()
                    institute = exam_data.get('institute')

                    # Get skillathon from mapping
                    skillathon = institute_to_skillathon.get(institute)

                    # Apply filters
                    if skillathon_filter and skillathon != skillathon_filter:
                        continue
                    if institution_filter and institute != institution_filter:
                        continue

                    filtered_exams.append(exam)

                exam_assignments = filtered_exams
                self.stdout.write(f"✅ After filtering: {len(exam_assignments)} exam assignments match criteria")
            else:
                self.stdout.write(f"✅ No filters applied: processing all {len(exam_assignments)} assignments")

            if not exam_assignments:
                self.stdout.write(self.style.WARNING('No exam assignments found matching the criteria'))
                return

            # Organize data: Skillathon → Institution → Student → Procedures
            data_structure = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
            all_procedures = defaultdict(set)  # skillathon -> set of procedures

            for exam in exam_assignments:
                exam_doc = exam.to_dict()

                # Get institute from exam document
                institute = exam_doc.get('institute', 'Unknown')
                # Get skillathon from the mapping we built
                skillathon = institute_to_skillathon.get(institute, 'Unknown')

                student_email = exam_doc.get('emailID')
                student_name = exam_doc.get('name') or exam_doc.get('username') or student_email
                procedure_name = exam_doc.get('procedureName') or exam_doc.get('procedure_name', 'Unknown')

                if not student_email:
                    continue

                # Calculate score/percentage
                total_score = exam_doc.get('marks', 0)
                max_marks = sum(
                    question.get('right_marks_for_question', 0)
                    for section in exam_doc.get('examMetaData', [])
                    for question in section.get('section_questions', [])
                )
                percentage = round((total_score / max_marks) * 100, 2) if max_marks else 0

                # Count critical steps missed
                critical_missed = 0
                for section in exam_doc.get('examMetaData', []):
                    for question in section.get('section_questions', []):
                        if question.get('critical', False) and question.get('answer_scored', 0) == 0:
                            critical_missed += 1

                # Store student's procedure data
                student_data = {
                    'email': student_email,
                    'name': student_name,
                    'procedure': procedure_name,
                    'score': total_score,
                    'max_marks': max_marks,
                    'percentage': percentage,
                    'critical_missed': critical_missed
                }

                data_structure[skillathon][institute][student_email].append(student_data)
                all_procedures[skillathon].add(procedure_name)

            # Get unique students per institution (in case of multiple procedures)
            unique_students = defaultdict(lambda: defaultdict(dict))
            for skillathon, institutions in data_structure.items():
                for inst_name, students in institutions.items():
                    for student_email, procedures in students.items():
                        # Get student name from first procedure entry
                        student_name = procedures[0]['name']
                        unique_students[skillathon][inst_name][student_email] = student_name

            # Get all unique procedures for each skillathon
            all_procedures_by_skillathon = {
                skillathon: sorted(list(procedures))
                for skillathon, procedures in all_procedures.items()
            }

            # Get ALL UNIQUE procedures across ALL skillathons (for column headers)
            all_unique_procedures = sorted(set(
                proc for procedures in all_procedures_by_skillathon.values()
                for proc in procedures
            ))

            # Write CSV
            self.stdout.write(f"Writing report to {output_file}...")
            self.stdout.write(f"Total unique procedures across all skillathons: {len(all_unique_procedures)}")

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Prepare headers with ALL procedures from ALL skillathons
                headers = ['Skillathon', 'Institution', 'Candidate Name']

                # Add all unique procedures as columns
                for procedure in all_unique_procedures:
                    headers.append(f'{procedure}')
                    headers.append(f'{procedure} - Critical Steps Missed')

                writer = csv.writer(csvfile)
                writer.writerow(headers)

                # Write data rows
                for skillathon in sorted(data_structure.keys()):
                    institutions = data_structure[skillathon]

                    for inst_name in sorted(institutions.keys()):
                        students = unique_students[skillathon][inst_name]

                        for student_email in sorted(students.keys()):
                            student_name = students[student_email]
                            student_procedures = data_structure[skillathon][inst_name][student_email]

                            # Create a map of procedure -> score details
                            procedure_map = {
                                proc['procedure']: {
                                    'percentage': proc['percentage'],
                                    'critical_missed': proc['critical_missed']
                                }
                                for proc in student_procedures
                            }

                            row = [skillathon, inst_name, student_name]

                            # Add procedures in consistent order (ALL unique procedures across all skillathons)
                            for procedure in all_unique_procedures:
                                if procedure in procedure_map:
                                    score_info = procedure_map[procedure]
                                    row.append(f"{score_info['percentage']}%")  # Score %
                                    row.append(score_info['critical_missed'])  # Critical steps missed
                                else:
                                    row.append("-")  # Not Attempted - Score %
                                    row.append("-")  # Not Attempted - Critical steps missed

                            writer.writerow(row)

            self.stdout.write(self.style.SUCCESS(f'✅ Report exported successfully to {output_file}'))

            # Print summary
            total_skillathons = len(data_structure)
            total_institutions = sum(len(insts) for insts in data_structure.values())
            total_students = sum(
                len(unique_students[s][inst])
                for s in unique_students
                for inst in unique_students[s]
            )

            self.stdout.write(self.style.SUCCESS(f'\n📊 Summary:'))
            self.stdout.write(f'  Skillathons: {total_skillathons}')
            self.stdout.write(f'  Institutions: {total_institutions}')
            self.stdout.write(f'  Candidates: {total_students}')
            self.stdout.write(f'  Total Procedures: {sum(len(p) for p in all_procedures.values())}')

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            raise CommandError(f'Error generating report: {str(e)}\n\nFull traceback:\n{error_trace}')
