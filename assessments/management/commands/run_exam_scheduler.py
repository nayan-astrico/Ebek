import json
import traceback
import time
import os
import fcntl
import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from assessments.models import ExamAssignment, SchedularObject, Learner
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Runs the exam scheduler every 30 seconds with proper locking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (continuous loop)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Interval in seconds between runs (default: 30)',
        )

    def handle(self, *args, **options):
        if options['daemon']:
            self.run_daemon(options['interval'])
        else:
            self.run_once()

    def run_daemon(self, interval):
        """Run the scheduler as a daemon with proper locking"""
        lock_file = '/tmp/exam_scheduler.lock'
        
        try:
            # Try to acquire lock
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            self.stdout.write(
                self.style.SUCCESS(f'Starting exam scheduler daemon (interval: {interval}s)')
            )
            
            while True:
                try:
                    self.run_once()
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.stdout.write(self.style.WARNING('Stopping exam scheduler...'))
                    break
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error in scheduler loop: {e}')
                    )
                    time.sleep(interval)  # Continue running despite errors
                    
        except IOError:
            self.stdout.write(
                self.style.ERROR('Another instance of exam scheduler is already running')
            )
            sys.exit(1)
        finally:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                os.unlink(lock_file)
            except:
                pass

    def run_once(self):
        """Run the scheduler once"""
        from django.conf import settings
        import os
        from dotenv import load_dotenv

        load_dotenv()
        firebase_database = os.getenv('FIREBASE_DATABASE')

        db = firestore.client(database_id=firebase_database)
        
        schedular_object = SchedularObject.objects.filter(is_completed=False).first()
        
        if not schedular_object:
            self.stdout.write('No pending scheduler objects found')
            return
            
        try:
            start_time = time.time()
            data = json.loads(schedular_object.data)
            learner_ids = data["learner_ids"]
            skillathon_name = data["skillathon_name"]
            
            self.stdout.write(f'Processing {len(learner_ids)} learners for skillathon: {skillathon_name}')
            
            test_refs = db.collection('Test').where('skillathon', '==', skillathon_name).get()
            if not test_refs:
                self.stdout.write(self.style.ERROR('NO TEST FOUND'))
                return
                
            self.stdout.write(f'Found {len(test_refs)} tests for skillathon: {skillathon_name}')
            
            # Process all tests with the same skillathon name
            all_procedure_assignments_data = []
            all_procedure_assignment_refs = []
            
            for test_doc in test_refs:
                test_data = test_doc.to_dict()
                procedure_assignments = test_data.get('procedureAssignments', []) or []

                # Skip if procedure_assignments doesn't exist or is empty
                if not procedure_assignments:
                    self.stdout.write(self.style.WARNING(f'Skipping test {test_doc.id} - no procedure assignments found'))
                    continue

                self.stdout.write(f'Processing test {test_doc.id} with {len(procedure_assignments)} procedure assignments')

                for proc_assignment_ref in procedure_assignments:
                    proc_assignment = proc_assignment_ref.get()
                    proc_data = proc_assignment.to_dict()
                    procedure_ref = proc_data.get('procedure')
                    if procedure_ref:
                        procedure_data = procedure_ref.get().to_dict()
                        all_procedure_assignments_data.append(procedure_data)
                        all_procedure_assignment_refs.append(proc_assignment_ref)  # Store the ref

            logger.info(f'Total procedure assignments to process: {len(all_procedure_assignments_data)}')
            processed_count = 0
            for learner_id in learner_ids:
                # Directly get learner by ID from Firebase
                learner_user_doc = db.collection('Users').document(str(learner_id)).get()
                if not learner_user_doc.exists:
                    self.stdout.write(
                        self.style.WARNING(f'Learner with ID {learner_id} not found in Firebase')
                    )
                    continue
                    
                emailID = learner_user_doc.get('emailID')
                try:
                    learner = Learner.objects.get(learner_user__email=emailID)
                except Learner.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Learner with email {emailID} not found in Django')
                    )
                    continue

                for i, procedure in enumerate(all_procedure_assignments_data):
                    # Check if exam assignment already exists
                    if ExamAssignment.objects.filter(
                        learner=learner, 
                        procedure_name=procedure.get('procedureName', ''), 
                        type_of_event="skillathon", 
                        skillathon_name=skillathon_name
                    ).exists():
                        continue
                        
                    exam_assignment_data = {
                        'user': learner_user_doc.reference,
                        'examMetaData': procedure.get('examMetaData', {}),
                        'status': 'Pending',
                        'notes': procedure.get('notes', ''),
                        'procedure_name': procedure.get('procedureName', ''),
                        'institute': learner_user_doc.get("institute") if learner_user_doc.get("institute") else None,
                        'institution': learner_user_doc.get("institute") if learner_user_doc.get("institute") else None,
                        'hospital': learner_user_doc.get("hospital") if learner_user_doc.get("hospital") else None,
                        'skillathon': skillathon_name,  # Add skillathon field for report queries
                    }
                    
                    exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
                    
                    # Update the correct procedure assignment with new exam assignment reference
                    all_procedure_assignment_refs[i].update({
                        'examAssignmentArray': firestore.ArrayUnion([exam_assignment_ref])
                    })
                    
                    exam_assignment = ExamAssignment.objects.create(
                        learner=learner,
                        procedure_name=procedure.get('procedureName', ''),
                        exam_assignment_id=exam_assignment_ref.id,
                        type_of_event="skillathon",
                        skillathon_name=skillathon_name
                    )
                    processed_count += 1
                    
            with transaction.atomic():
                schedular_object.is_completed = True
                schedular_object.status = 'passed'
                schedular_object.save()

            end_time = time.time()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processed {processed_count} exam assignments in {end_time - start_time:.2f} seconds'
                )
            )

        except Exception as e:
            error_msg = f'{str(e)}\n{traceback.format_exc()}'

            # Mark scheduler object as failed
            with transaction.atomic():
                schedular_object.is_completed = True
                schedular_object.status = 'failed'
                schedular_object.error_message = error_msg
                schedular_object.save()

            self.stdout.write(
                self.style.ERROR(f'Error processing scheduler object: {e}')
            )
            self.stdout.write(traceback.format_exc()) 