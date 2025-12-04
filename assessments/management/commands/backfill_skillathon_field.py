"""
Management command to backfill the 'skillathon' field in ExamAssignment documents
that are missing it. This fixes reports for skillathons created before the field was added.

Usage:
    python manage.py backfill_skillathon_field
    python manage.py backfill_skillathon_field --dry-run  # Preview changes without applying
"""
from django.core.management.base import BaseCommand
from firebase_admin import firestore
from django.conf import settings
import os
from dotenv import load_dotenv


class Command(BaseCommand):
    help = 'Backfill skillathon field in ExamAssignment documents that are missing it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )

    def handle(self, *args, **options):
        load_dotenv()
        firebase_database = os.getenv('FIREBASE_DATABASE')
        db = firestore.client(database_id=firebase_database)
        
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find all ExamAssignment documents
        exam_assignments = db.collection('ExamAssignment').stream()
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for exam_doc in exam_assignments:
            try:
                exam_data = exam_doc.to_dict()
                
                # Skip if skillathon field already exists
                if 'skillathon' in exam_data and exam_data['skillathon']:
                    skipped_count += 1
                    continue
                
                # Try to find skillathon from related Test document via ProcedureAssignment
                skillathon_name = None
                
                # Method 1: Search all ProcedureAssignments and check their examAssignmentArray
                # This is necessary because Firestore doesn't support array_contains with document references
                proc_assignments = db.collection('ProcedureAssignment').stream()
                
                for proc_assignment in proc_assignments:
                    try:
                        proc_data = proc_assignment.to_dict()
                        exam_assignment_array = proc_data.get('examAssignmentArray', [])
                        
                        # Check if this exam assignment is in the array
                        for exam_ref in exam_assignment_array:
                            if exam_ref.id == exam_doc.id:
                                # Found the procedure assignment containing this exam
                                test_ref = proc_data.get('test')
                                if test_ref:
                                    test_doc = test_ref.get()
                                    if test_doc.exists:
                                        test_data = test_doc.to_dict()
                                        skillathon_name = test_data.get('skillathon')
                                        break
                        
                        if skillathon_name:
                            break
                    except Exception:
                        continue
                
                # Method 2: If still not found, try to get from user's skillathon_event
                if not skillathon_name:
                    user_ref = exam_data.get('user')
                    if user_ref:
                        try:
                            user_doc = user_ref.get()
                            if user_doc.exists:
                                user_data = user_doc.to_dict()
                                skillathon_name = user_data.get('skillathon_event')
                        except Exception as e:
                            pass  # Silently continue to next method
                
                # Method 3: Check if exam has batchassignment (means it's OSCE, not skillathon)
                # Skip if it's an OSCE exam
                if exam_data.get('batchassignment'):
                    self.stdout.write(
                        self.style.WARNING(
                            f'Exam {exam_doc.id} is linked to batchassignment (OSCE), skipping'
                        )
                    )
                    skipped_count += 1
                    continue
                
                if skillathon_name:
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Would update exam {exam_doc.id} with skillathon: {skillathon_name}'
                            )
                        )
                    else:
                        exam_doc.reference.update({'skillathon': skillathon_name})
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated exam {exam_doc.id} with skillathon: {skillathon_name}'
                            )
                        )
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Could not determine skillathon for exam {exam_doc.id} - skipping'
                        )
                    )
                    skipped_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing exam {exam_doc.id}: {e}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Backfill Summary:'))
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Skipped (already has skillathon or cannot determine): {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were made'))
            self.stdout.write('Run without --dry-run to apply changes')

