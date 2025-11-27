"""
Django Management Command: Complete OSCE Analytics Pre-Computation
Matches ALL analytics shown in the design screenshots

Usage:
    python manage.py process_metric_queue

Setup cron (runs every 5 minutes):
    */5 * * * * cd /path/to/ebek_django_app && python manage.py process_metric_queue >> /var/log/metrics.log 2>&1
"""

from django.core.management.base import BaseCommand
from firebase_admin import firestore
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import time
import os
from dotenv import load_dotenv
load_dotenv()

firebase_database = os.getenv('FIREBASE_DATABASE')
db = firestore.client(database_id=firebase_database) if firebase_database else firestore.client()



class Command(BaseCommand):
    help = 'Process metric queue and pre-compute ALL OSCE analytics'

    def handle(self, *args, **options):
        start_time = time.time()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"[{timestamp}] Starting Complete Analytics Pre-Computation")
        self.stdout.write(f"{'='*80}\n")
        
        try:
            # Step 1: Process queue
            unprocessed_count = self._process_queue()
            
        
            
            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Complete analytics computed successfully!"
            ))
            self.stdout.write(f"   - Processed: {unprocessed_count} items")
            self.stdout.write(f"   - Time elapsed: {elapsed:.2f} seconds\n")
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\n❌ Error: {str(e)}\n"))
            import traceback
            traceback.print_exc()
            raise

    def _process_queue(self):
        """Fetch and process unprocessed queue items"""
        
        cutoff_time = datetime.now() - timedelta(minutes=300)
        
        queue_ref = db.collection('MetricUpdateQueue')\
            .where('processed', '==', True)\
            .limit(1000)
        
        queue_items = list(queue_ref.stream())
        
        if not queue_items:
            self.stdout.write("   No items in queue. All up to date! ✓")
            return 0
        
        self.stdout.write(f"   Found {len(queue_items)} unprocessed items")
        
        # Group by context
        contexts = defaultdict(list)
        
        for item_doc in queue_items:
            item_data = item_doc.to_dict()
            
            if item_data.get('retry_count', 0) > 3:
                self._mark_failed(item_doc.id, "Max retries exceeded")
                continue
            
            context_key = (
                item_data.get('unit_name'),  # Works for both institution and hospital
                item_data.get('unit_type', 'institute'),  # 'institute' or 'hospital'
                item_data.get('year'),
                item_data.get('semester')
            )
            
            contexts[context_key].append({
                'doc_id': item_doc.id,
                'data': item_data
            })
        
        # Process each context
        processed_count = 0
        for context_key, items in contexts.items():
            unit_name, unit_type, year, semester = context_key
            
            try:
                self.stdout.write(f"   Processing: {unit_name} ({unit_type}) - {year} - Semester {semester}")
                
                # FULL ANALYTICS COMPUTATION
                self._compute_complete_analytics(unit_name, unit_type, year, semester)
                
                # Mark processed
                for item in items:
                    self._mark_processed(item['doc_id'])
                    processed_count += 1
                
                self.stdout.write(f"      ✓ Computed all analytics for {len(items)} items")
                
            except Exception as e:
                self.stderr.write(f"      ✗ Error: {str(e)}")
                for item in items:
                    self._increment_retry(item['doc_id'])
        
        return processed_count

    def _compute_complete_analytics(self, unit_name, unit_type, year, semester):
        """
        Compute COMPLETE analytics matching the design screenshots
        This includes everything needed for the full report

        Args:
            unit_name: Institution or Hospital name (e.g., "DJ Sanghvi College")
            unit_type: "institute" or "hospital"
            year: Academic year (e.g., "2025")
            semester: Semester number (e.g., "1")
        """

        # ============================================
        # PHASE 0: FETCH UNIT STATE FROM FIRESTORE
        # ============================================

        # Get state from Institution or Hospital in Firestore
        unit_state = 'Unknown'
        try:
            if unit_type == 'institution':
                # Query Firestore InstituteNames collection by instituteName field
                self.stdout.write(f"      Searching for institution '{unit_name}' in InstituteNames...")
                institutions_query = db.collection('InstituteNames').where('instituteName', '==', unit_name).stream()
                found = False
                for inst_doc in institutions_query:
                    found = True
                    inst_data = inst_doc.to_dict()
                    state_value = inst_data.get('state')
                    self.stdout.write(f"        Found institution document: {inst_doc.id}")
                    self.stdout.write(f"        State value: {state_value}")
                    if state_value:
                        unit_state = state_value
                        self.stdout.write(f"      ✓ Found state '{unit_state}' for institution '{unit_name}'")
                        break
                if not found:
                    self.stdout.write(f"      ✗ No institution document found for '{unit_name}' in InstituteNames")
            elif unit_type == 'hospital':
                # Query Firestore HospitalNames collection by hospitalName field
                self.stdout.write(f"      Searching for hospital '{unit_name}' in HospitalNames...")
                hospitals_query = db.collection('HospitalNames').where('hospitalName', '==', unit_name).stream()
                found = False
                for hosp_doc in hospitals_query:
                    found = True
                    hosp_data = hosp_doc.to_dict()
                    state_value = hosp_data.get('state')
                    self.stdout.write(f"        Found hospital document: {hosp_doc.id}")
                    self.stdout.write(f"        State value: {state_value}")
                    if state_value:
                        unit_state = state_value
                        self.stdout.write(f"      ✓ Found state '{unit_state}' for hospital '{unit_name}'")
                        break
                if not found:
                    self.stdout.write(f"      ✗ No hospital document found for '{unit_name}' in HospitalNames")
        except Exception as e:
            self.stdout.write(f"      ✗ Error fetching state for {unit_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            unit_state = 'Unknown'

        # ============================================
        # PHASE 1: COLLECT ALL RAW DATA
        # ============================================

        # First, get all enrolled students from Batches collection
        # This will be our base for total_students_enrolled
        enrolled_student_ids = set()
        
        # Query batches for this unit/year/semester
        batches_query = db.collection('Batches')\
            .where('yearOfBatch', '==', year)\
            .where('semester', '==', semester)
        
        batches = list(batches_query.stream())
        self.stdout.write(f"    Found {len(batches)} batches for year={year}, semester={semester}")
        
        for batch_doc in batches:
            batch_data = batch_doc.to_dict()
            # Check if batch belongs to this unit
            batch_unit_name = batch_data.get('unit_name')
            
            if not batch_unit_name:
                # Fall back to extracting from unit reference
                unit_ref = batch_data.get('unit')
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_doc_data = unit_doc.to_dict()
                            # Try multiple possible field names
                            # InstituteNames uses 'instituteName', Hospitals uses 'hospitalName'
                            batch_unit_name = (
                                unit_doc_data.get('instituteName') or   # For institutions (correct field)
                                unit_doc_data.get('hospitalName') or    # For hospitals
                                unit_doc_data.get('name') or 
                                unit_doc_data.get('institutionName') or  # Fallback
                                unit_doc_data.get('institution_name') or
                                unit_doc_data.get('hospital_name') or
                                ''
                            )
                            self.stdout.write(f"      Batch {batch_doc.id}: Extracted unit_name = '{batch_unit_name}' from reference")
                    except Exception as e:
                        self.stdout.write(f"      Error fetching unit reference: {e}")
                        pass
            
            self.stdout.write(f"      Batch {batch_doc.id}: unit_name='{batch_unit_name}', target='{unit_name}', match={batch_unit_name == unit_name}")
            
            if batch_unit_name == unit_name:
                # Add all learners from this batch
                learner_count = len(batch_data.get('learners', []))
                for learner_ref in batch_data.get('learners', []):
                    if learner_ref:
                        learner_id = learner_ref.id if hasattr(learner_ref, 'id') else str(learner_ref).split('/')[-1]
                        enrolled_student_ids.add(learner_id)
                self.stdout.write(f"      Added {learner_count} learners from batch {batch_doc.id}")
        
        self.stdout.write(f"    Total enrolled students: {len(enrolled_student_ids)}")
        if enrolled_student_ids:
            self.stdout.write(f"    Enrolled student IDs: {sorted(list(enrolled_student_ids)[:10])}...")  # Show first 10
        
        # Query all BatchAssignments for this semester
        # Use unit_name field which works for both institutions and hospitals
        ba_query = db.collection('BatchAssignment')\
            .where('unit_name', '==', unit_name)\
            .where('yearOfBatch', '==', year)\
            .where('semester', '==', semester)
        
        batch_assignments = list(ba_query.stream())
        self.stdout.write(f"    Found {len(batch_assignments)} batch assignments")
        
        # Query BatchAssignmentSummary for OSCE-level data
        bas_query = db.collection('BatchAssignmentSummary')\
            .where('unit_name', '==', unit_name)\
            .where('yearOfBatch', '==', year)\
            .where('semester', '==', semester)
        
        osce_summaries = list(bas_query.stream())

        # Initialize comprehensive tracking
        students_data = {}  # {user_id: {name, scores by type, overall, etc}}
        skills_data = defaultdict(lambda: {
            'attempts': 0,
            'scores': [],
            'students': set(),
            'skill_name': '',
            'category': '',
            'osce_types': set(),
            'station_scores': defaultdict(list),
            'student_marks': {}  # NEW: {user_id: {'obtained': int, 'max': int}}
        })
        category_scores = defaultdict(list)
        osce_timeline = []
        assessors_set = set()
        all_scores = []
        grade_distribution = Counter()
        evaluated_procedures = set()  # Track unique procedures that were evaluated
        completed_student_ids = set()
        
        # ============================================
        # PHASE 2: PROCESS BATCH ASSIGNMENTS
        # ============================================
        
        for ba_doc in batch_assignments:
            ba_data = ba_doc.to_dict()
            ba_id = ba_doc.id
            
            # Get procedure details
            procedure_ref = ba_data.get('procedure')
            procedure_id = None
            procedure_name = None
            procedure_category = None
            
            if procedure_ref:
                procedure_id = procedure_ref.id if hasattr(procedure_ref, 'id') else str(procedure_ref).split('/')[-1]
                # Track this procedure as evaluated (an OSCE was created for it)
                if procedure_id:
                    evaluated_procedures.add(procedure_id)
                try:
                    procedure_doc = procedure_ref.get()
                    if procedure_doc.exists:
                        proc_data = procedure_doc.to_dict()
                        procedure_name = proc_data.get('procedureName', 'Unknown')
                        procedure_category = proc_data.get('category', '')
                except:
                    pass
            
            exam_type = ba_data.get('examType', '')
            test_date = ba_data.get('testDate')
            
            # Track assessors
            for assessor_ref in ba_data.get('assessorlist', []):
                if assessor_ref:
                    if hasattr(assessor_ref, 'id'):
                        assessors_set.add(assessor_ref.id)
                    elif isinstance(assessor_ref, str):
                        assessors_set.add(assessor_ref)
            
            # Process each exam assignment
            for exam_ref in ba_data.get('examassignment', []):
                try:
                    exam_doc = exam_ref.get()
                    if not exam_doc.exists:
                        continue
                    
                    exam_data = exam_doc.to_dict()
                    user_ref = exam_data.get('user')
                    
                    if not user_ref:
                        continue
                    
                    user_id = user_ref.id if hasattr(user_ref, 'id') else str(user_ref).split('/')[-1]
                    
                    # Initialize student data
                    if user_id not in students_data:
                        # Fetch user name
                        user_name = 'Unknown'
                        try:
                            user_doc = user_ref.get()
                            if user_doc.exists:
                                user_data_dict = user_doc.to_dict()
                                user_name = user_data_dict.get('name', user_data_dict.get('firstName', 'Unknown'))
                        except:
                            pass
                        
                        students_data[user_id] = {
                            'name': user_name,
                            'scores_by_type': {'Classroom': [], 'Mock': [], 'Final': []},
                            'marks_by_type': {
                                'Classroom': {'obtained': 0, 'max': 0},
                                'Mock': {'obtained': 0, 'max': 0},
                                'Final': {'obtained': 0, 'max': 0}
                            },
                            'all_scores': [],
                            'category_scores': defaultdict(list),
                            'category_marks': defaultdict(lambda: {'obtained': 0, 'max': 0}),
                            'exam_attempts': [],
                            'skills_attempted': set(),
                            'skills_passed': set(),
                            'total_osces': 0,
                            'total_marks_obtained': 0,
                            'total_max_marks': 0
                        }
                    
                    students_data[user_id]['total_osces'] += 1
                    
                    # Process completed exams
                    if str(exam_data.get('status', '')).lower() == 'completed':
                        total_score = exam_data.get('marks', 0)
                        exam_metadata = exam_data.get('examMetaData', [])
                        
                        # Calculate max marks and station scores
                        max_marks = 0
                        station_scores = {}
                        
                        for section_idx, section in enumerate(exam_metadata):
                            section_name = section.get('section_title', f'Station {section_idx + 1}')
                            section_score = 0
                            section_max = 0
                            
                            for question in section.get('section_questions', []):
                                q_max = question.get('right_marks_for_question', 0)
                                q_score = question.get('marks_obtained', 0)
                                section_max += q_max
                                section_score += q_score
                            
                            max_marks += section_max
                            
                            if section_max > 0:
                                station_pct = round((section_score / section_max) * 100, 2)
                                station_scores[section_name] = station_pct
                        
                        if max_marks > 0:
                            percentage = round((total_score / max_marks) * 100, 2)

                            # Track overall
                            all_scores.append(percentage)
                            students_data[user_id]['all_scores'].append(percentage)

                            # Track marks obtained and max marks
                            students_data[user_id]['total_marks_obtained'] += total_score
                            students_data[user_id]['total_max_marks'] += max_marks
                            
                            # Track by exam type (both percentage and marks)
                            if exam_type in students_data[user_id]['scores_by_type']:
                                students_data[user_id]['scores_by_type'][exam_type].append(percentage)
                                # Track marks by type
                                students_data[user_id]['marks_by_type'][exam_type]['obtained'] += total_score
                                students_data[user_id]['marks_by_type'][exam_type]['max'] += max_marks

                            # NOTE: Grade distribution is now calculated at student-level (not exam-level)
                            # See after student_batch_report creation for proper calculation

                            # Track student completion
                            completed_student_ids.add(user_id)
                            
                            # Track by category
                            if procedure_category:
                                category_scores[procedure_category].append(percentage)
                                students_data[user_id]['category_scores'][procedure_category].append(percentage)
                                # Track category marks for student-level calculation
                                students_data[user_id]['category_marks'][procedure_category]['obtained'] += total_score
                                students_data[user_id]['category_marks'][procedure_category]['max'] += max_marks
                            
                            # Parse checklist summary from examMetaData
                            checklist_summary = self._parse_checklist_summary(exam_metadata)

                            # Get notes/comments from exam assignment
                            notes = exam_data.get('notes', '')

                            # Get assessor names from batchassignment assessorlist
                            assessor_names = []
                            for assessor_ref in ba_data.get('assessorlist', []):
                                try:
                                    assessor_doc = assessor_ref.get()
                                    if assessor_doc.exists:
                                        assessor_data = assessor_doc.to_dict()
                                        assessor_name = assessor_data.get('name', 'Unknown')
                                        assessor_names.append(assessor_name)
                                except:
                                    pass

                            # Track per-exam breakdown for the student
                            students_data[user_id]['exam_attempts'].append({
                                'procedure_id': procedure_id,
                                'procedure_name': procedure_name,
                                'category': procedure_category,
                                'exam_type': exam_type,
                                'score': percentage,
                                'marks_obtained': total_score,
                                'max_marks': max_marks,
                                'test_date': test_date.isoformat() if test_date else None,
                                'pass': percentage >= 80,
                                'station_scores': station_scores,  # Station-by-station breakdown
                                'checklist_summary': checklist_summary,  # Detailed checklist statistics
                                'notes': notes,  # Examiner notes/comments
                                'assessor_names': assessor_names,  # List of assessor names
                                'exam_assignment_id': exam_doc.id  # Reference to exam assignment
                            })
                            
                            # Track by skill
                            if procedure_id:
                                skills_data[procedure_id]['attempts'] += 1
                                skills_data[procedure_id]['scores'].append(percentage)
                                skills_data[procedure_id]['students'].add(user_id)
                                skills_data[procedure_id]['skill_name'] = procedure_name
                                skills_data[procedure_id]['category'] = procedure_category
                                skills_data[procedure_id]['osce_types'].add(exam_type)

                                # NEW: Track student-level marks for this skill
                                if user_id not in skills_data[procedure_id]['student_marks']:
                                    skills_data[procedure_id]['student_marks'][user_id] = {'obtained': 0, 'max': 0}
                                skills_data[procedure_id]['student_marks'][user_id]['obtained'] += total_score
                                skills_data[procedure_id]['student_marks'][user_id]['max'] += max_marks

                                # Track station scores for this skill
                                for station, score in station_scores.items():
                                    skills_data[procedure_id]['station_scores'][station].append(score)

                                students_data[user_id]['skills_attempted'].add(procedure_id)
                                if percentage >= 80:
                                    students_data[user_id]['skills_passed'].add(procedure_id)
                
                except Exception as e:
                    self.stderr.write(f"      Error processing exam: {str(e)}")
                    continue
        
        # ============================================
        # PHASE 3: PROCESS OSCE SUMMARIES (Timeline)
        # ============================================
        
        for bas_doc in osce_summaries:
            bas_data = bas_doc.to_dict()
            
            osce_level = bas_data.get('exam_type', 'N/A')
            test_date = bas_data.get('test_date')
            
            # Format date
            date_str = 'N/A'
            if test_date:
                try:
                    if hasattr(test_date, 'timestamp'):
                        date_str = datetime.fromtimestamp(test_date.timestamp()).strftime('%d %b %Y')
                    elif hasattr(test_date, 'seconds'):
                        date_str = datetime.fromtimestamp(test_date.seconds).strftime('%d %b %Y')
                except:
                    date_str = str(test_date)
            
            # Fetch batch name and total students from Batches collection
            batch_name = 'N/A'
            total_batch_students = 0
            batch_id = bas_data.get('batch_id', '')
            if batch_id:
                try:
                    batch_doc = db.collection('Batches').document(batch_id).get()
                    if batch_doc.exists:
                        batch_data = batch_doc.to_dict()
                        batch_name = batch_data.get('batchName', batch_id)
                        # Count total learners in this batch
                        total_batch_students = len(batch_data.get('learners', []))
                except Exception as e:
                    print(f"Error fetching batch name for {batch_id}: {str(e)}")
                    batch_name = batch_id
            
            # Get stats from batch assignments for this OSCE
            # Track marks per student (Total Marks Method - consistent with category performance)
            procedure_mappings = bas_data.get('procedure_assessor_mappings', [])
            osce_students = set()
            student_osce_marks = {}  # {user_id: {'obtained': X, 'max': Y}}
            
            for mapping in procedure_mappings:
                if isinstance(mapping, dict):
                    ba_id = mapping.get('batchassignment_id', '')
                    if ba_id:
                        try:
                            ba_ref = db.collection('BatchAssignment').document(ba_id)
                            ba_doc_ref = ba_ref.get()
                            if ba_doc_ref.exists:
                                ba_data_ref = ba_doc_ref.to_dict()
                                
                                for exam_ref in ba_data_ref.get('examassignment', []):
                                    exam_doc = exam_ref.get()
                                    if exam_doc.exists:
                                        exam_data = exam_doc.to_dict()
                                        user_ref = exam_data.get('user')
                                        
                                        if user_ref:
                                            user_id = user_ref.id
                                            osce_students.add(user_id)
                                            
                                            if str(exam_data.get('status', '')).lower() == 'completed':
                                                marks = exam_data.get('marks', 0)
                                                metadata = exam_data.get('examMetaData', [])
                                                max_m = sum(
                                                    q.get('right_marks_for_question', 0)
                                                    for sec in metadata
                                                    for q in sec.get('section_questions', [])
                                                )
                                                
                                                if max_m > 0:
                                                    # Track total marks per student
                                                    if user_id not in student_osce_marks:
                                                        student_osce_marks[user_id] = {'obtained': 0, 'max': 0}
                                                    
                                                    student_osce_marks[user_id]['obtained'] += marks
                                                    student_osce_marks[user_id]['max'] += max_m
                        except:
                            pass
            
            # Calculate student-level percentages using Total Marks Method
            student_percentages = []
            students_passing = 0
            
            for user_id, marks_data in student_osce_marks.items():
                if marks_data['max'] > 0:
                    student_pct = round((marks_data['obtained'] / marks_data['max']) * 100, 2)
                    student_percentages.append(student_pct)
                    if student_pct >= 80:
                        students_passing += 1
            
            # Calculate OSCE-level metrics (student-centric with total marks)
            avg_score = round(sum(student_percentages) / len(student_percentages), 2) if student_percentages else 0
            pass_rate = round((students_passing / len(student_percentages) * 100), 2) if student_percentages else 0

            osce_timeline.append({
                'osce_level': osce_level,
                'batch_name': batch_name,
                'date_conducted': date_str,
                'students_attempted': len(student_osce_marks),  # Students who completed at least one exam
                'total_students': total_batch_students,  # Total enrolled in batch
                'num_students': len(osce_students),  # Keep for backward compatibility
                'avg_score': avg_score,
                'pass_percentage': pass_rate
            })
        
        # Sort timeline by priority (Final, Mock, Classroom) and date
        exam_type_priority = {'Final': 2, 'Mock': 1, 'Classroom': 0}
        osce_timeline.sort(
            key=lambda x: (
                exam_type_priority.get(x['osce_level'], -1),
                x['date_conducted']
            ),
            reverse=True
        )
        
        # ============================================
        # PHASE 4: COMPUTE AGGREGATIONS
        # ============================================

        # Overall metrics - Calculate from STUDENT overall grades (not exam-wise)
        # This ensures consistency with grade_distribution and category_performance
        student_overall_percentages = []
        for user_id, student_data in students_data.items():
            if student_data['total_max_marks'] > 0:
                # Calculate this student's overall percentage from total marks
                student_overall_pct = round((student_data['total_marks_obtained'] / student_data['total_max_marks']) * 100, 2)
                student_overall_percentages.append(student_overall_pct)

        # Average all student overall percentages
        avg_score = round(sum(student_overall_percentages) / len(student_overall_percentages), 2) if student_overall_percentages else 0

        # Calculate pass rate from student overall percentages (students with >= 80% overall)
        pass_count = sum(1 for s in student_overall_percentages if s >= 80)
        pass_rate = round((pass_count / len(student_overall_percentages) * 100), 2) if student_overall_percentages else 0
        
        # Category performance (Student-Average Method with Total Marks)
        # Calculate using total marks per student (consistent with overall_grade calculation)
        category_performance = {}
        for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
            student_category_averages = []
            
            # Calculate each student's category percentage using total marks
            for user_id, student_data in students_data.items():
                if category in student_data['category_marks']:
                    obtained = student_data['category_marks'][category]['obtained']
                    max_marks = student_data['category_marks'][category]['max']
                    if max_marks > 0:
                        student_category_percentage = (obtained / max_marks) * 100
                        student_category_averages.append(student_category_percentage)
            
            # Average all student category percentages
            if student_category_averages:
                category_performance[category] = round(sum(student_category_averages) / len(student_category_averages), 2)
            else:
                category_performance[category] = None
        
        # Skills performance (detailed)
        skills_performance = {}
        for skill_id, skill_data in skills_data.items():
            if skill_data['scores']:
                avg_skill_score = round(sum(skill_data['scores']) / len(skill_data['scores']), 2)
                skill_pass_rate = round((sum(1 for s in skill_data['scores'] if s >= 80) / len(skill_data['scores']) * 100), 2)

                # NEW: Calculate avg_score using Student-Average Method (for category drill-down)
                # This ensures alignment with category_performance calculation
                student_skill_averages = []
                for student_id, marks in skill_data['student_marks'].items():
                    if marks['max'] > 0:
                        student_skill_pct = (marks['obtained'] / marks['max']) * 100
                        student_skill_averages.append(student_skill_pct)

                avg_skill_score_student_method = round(sum(student_skill_averages) / len(student_skill_averages), 2) if student_skill_averages else avg_skill_score

                # Station breakdown
                station_breakdown = {}
                for station, scores in skill_data['station_scores'].items():
                    if scores:
                        station_breakdown[station] = {
                            'avg_score': round(sum(scores) / len(scores), 2),
                            'attempts': len(scores)
                        }

                skills_performance[skill_id] = {
                    'skill_name': skill_data['skill_name'],
                    'category': skill_data['category'],
                    'attempts': skill_data['attempts'],
                    'students_attempted': len(skill_data['students']),
                    'avg_score': avg_skill_score,  # Exam-average (for skills table)
                    'avg_score_student_method': avg_skill_score_student_method,  # NEW: Student-average (for category drill-down)
                    'pass_rate': skill_pass_rate,
                    'highest_score': max(skill_data['scores']),
                    'lowest_score': min(skill_data['scores']),
                    'osce_types': list(skill_data['osce_types']),
                    'station_breakdown': station_breakdown
                }

        # PRE-COMPUTE: Category drill-down details
        # Eliminates frontend filtering and calculation on every category click (~200 iterations per click)
        category_details = {}
        for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
            skills_in_category = [
                skill for skill_id, skill in skills_performance.items()
                if skill['category'] == category
            ]

            if skills_in_category:
                # Find highest and lowest scoring skills using student-average method
                highest_skill = max(skills_in_category, key=lambda s: s['avg_score_student_method'])
                lowest_skill = min(skills_in_category, key=lambda s: s['avg_score_student_method'])

                # Calculate skill grade distribution (grade each skill, not each exam)
                skill_grade_dist = Counter()
                for skill in skills_in_category:
                    grade = self._get_grade(skill['avg_score_student_method'])
                    skill_grade_dist[grade] += 1

                category_details[category] = {
                    'total_skills': len(skills_in_category),
                    'highest_scoring_skill': {
                        'name': highest_skill['skill_name'],
                        'score': highest_skill['avg_score_student_method']
                    },
                    'lowest_scoring_skill': {
                        'name': lowest_skill['skill_name'],
                        'score': lowest_skill['avg_score_student_method']
                    },
                    'skill_grade_distribution': dict(skill_grade_dist)
                }
            else:
                category_details[category] = None

        # Student batch report
        student_batch_report = []
        for user_id, student_data in students_data.items():
            if not student_data['all_scores']:
                # Skip students with no completed exams
                continue
            
            # Calculate overall average from total marks (not averaging percentages)
            overall_avg = round((student_data['total_marks_obtained'] / student_data['total_max_marks']) * 100, 2) if student_data['total_max_marks'] > 0 else 0
            overall_grade = self._get_grade(overall_avg)
            
            # Get type averages from total marks (not averaging percentages)
            classroom_marks = student_data['marks_by_type']['Classroom']
            classroom_avg = round((classroom_marks['obtained'] / classroom_marks['max']) * 100, 2) if classroom_marks['max'] > 0 else None

            mock_marks = student_data['marks_by_type']['Mock']
            mock_avg = round((mock_marks['obtained'] / mock_marks['max']) * 100, 2) if mock_marks['max'] > 0 else None

            final_marks = student_data['marks_by_type']['Final']
            final_avg = round((final_marks['obtained'] / final_marks['max']) * 100, 2) if final_marks['max'] > 0 else None
            
            # Determine best performing OSCE
            osce_avgs = {}
            if classroom_avg: osce_avgs['Classroom'] = classroom_avg
            if mock_avg: osce_avgs['Mock'] = mock_avg
            if final_avg: osce_avgs['Final'] = final_avg
            
            best_osce = max(osce_avgs, key=osce_avgs.get) if osce_avgs else 'N/A'
            worst_osce = min(osce_avgs, key=osce_avgs.get) if osce_avgs else 'N/A'
            
            # Skills needing improvement
            skills_below_80 = len(student_data['skills_attempted']) - len(student_data['skills_passed'])
            
            category_breakdown = {}
            for category, scores in student_data['category_scores'].items():
                if scores:
                    category_breakdown[category] = {
                        'attempts': len(scores),
                        'avg_score': round(sum(scores) / len(scores), 2)
                    }

            # PRE-COMPUTE: Procedure scores by OSCE type
            # This eliminates 500-1000+ frontend calculations in getStudentProcedureScores()
            # Groups exam attempts by OSCE type, then by procedure name, and calculates
            # aggregated percentage using Total Marks Method (METRICS_CALCULATION_GUIDE.md)
            procedure_scores_by_type = {}
            for osce_type in ['Classroom', 'Mock', 'Final']:
                procedure_scores_by_type[osce_type] = {}

                # Get all exam attempts for this OSCE type
                type_attempts = [e for e in student_data['exam_attempts'] if e.get('exam_type') == osce_type]

                # Group by procedure name and aggregate marks
                procedure_marks = {}  # {proc_name: {obtained: X, max: Y}}
                for attempt in type_attempts:
                    proc_name = attempt.get('procedure_name')
                    if proc_name:
                        if proc_name not in procedure_marks:
                            procedure_marks[proc_name] = {'obtained': 0, 'max': 0}

                        # Aggregate marks using Total Marks Method
                        procedure_marks[proc_name]['obtained'] += attempt.get('marks_obtained', 0)
                        procedure_marks[proc_name]['max'] += attempt.get('max_marks', 0)

                # Calculate percentage for each procedure
                for proc_name, marks in procedure_marks.items():
                    if marks['max'] > 0:
                        procedure_scores_by_type[osce_type][proc_name] = round((marks['obtained'] / marks['max']) * 100, 2)
                    else:
                        procedure_scores_by_type[osce_type][proc_name] = 0

            # Calculate unique OSCEs participated by grouping exam_type + test_date
            # Multiple procedures on same day with same type = 1 OSCE session
            unique_osce_sessions = set()
            for attempt in student_data['exam_attempts']:
                exam_type = attempt.get('exam_type', '')
                test_date = attempt.get('test_date', '')
                if test_date:
                    # Extract date part only (YYYY-MM-DD)
                    test_date = test_date.split('T')[0] if 'T' in test_date else test_date
                # Create unique key: exam_type + test_date
                session_key = f"{exam_type}_{test_date}"
                unique_osce_sessions.add(session_key)
            unique_osces_participated = len(unique_osce_sessions)

            student_batch_report.append({
                'user_id': user_id,
                'name': student_data['name'],
                'overall_avg': overall_avg,
                'overall_grade': overall_grade,
                'classroom_score': classroom_avg,
                'classroom_grade': self._get_grade(classroom_avg) if classroom_avg else '-',
                'mock_score': mock_avg,
                'mock_grade': self._get_grade(mock_avg) if mock_avg else '-',
                'final_score': final_avg,
                'final_grade': self._get_grade(final_avg) if final_avg else '-',
                'total_osces': student_data['total_osces'],
                'unique_osces_participated': unique_osces_participated,  # Count of unique BatchAssignmentSummary documents
                'skills_attempted': len(student_data['skills_attempted']),
                'skills_passed': len(student_data['skills_passed']),
                'skills_needing_improvement': skills_below_80,
                'best_performing_osce': best_osce,
                'worst_performing_osce': worst_osce,
                'category_breakdown': category_breakdown,
                'category_marks': dict(student_data['category_marks']),  # Total Marks Method data
                'exam_attempts': student_data['exam_attempts'],
                'total_marks_obtained': student_data['total_marks_obtained'],
                'total_max_marks': student_data['total_max_marks'],
                'procedure_scores_by_type': procedure_scores_by_type  # NEW: Pre-computed procedure scores
            })
        
        # Sort student report by overall average (descending)
        student_batch_report.sort(key=lambda x: x['overall_avg'], reverse=True)

        # Calculate STUDENT-LEVEL grade distribution (not exam-level)
        # This follows METRICS_CALCULATION_GUIDE.md methodology
        student_grade_distribution = Counter()
        for student in student_batch_report:
            student_grade_distribution[student['overall_grade']] += 1

        # Replace the exam-level grade_distribution with student-level
        grade_distribution = student_grade_distribution

        # ============================================
        # PHASE 4B: PRE-COMPUTE OSCE TYPE BREAKDOWN
        # ============================================
        # Calculate separate metrics for each OSCE type (Classroom, Mock, Final)
        # This allows the API to return filtered metrics without recalculating

        osce_type_breakdown = {}
        for osce_type in ['Classroom', 'Mock', 'Final']:
            type_student_overall_percentages = []
            type_completed_students = set()
            type_grade_dist = Counter()
            type_skills_perf = {}
            type_osce_timeline = []
            type_student_batch_report = []

            # Collect data for this OSCE type only
            for user_id, student_data in students_data.items():
                # Check if student has this exam type
                type_marks = student_data['marks_by_type'].get(osce_type, {})
                if type_marks and type_marks.get('max', 0) > 0:
                    type_completed_students.add(user_id)
                    # Calculate this student's percentage for this OSCE type
                    type_student_pct = round((type_marks['obtained'] / type_marks['max']) * 100, 2)
                    type_student_overall_percentages.append(type_student_pct)
                    type_grade_dist[self._get_grade(type_student_pct)] += 1

            # Calculate category performance for this OSCE type using Student-Average Method with Total Marks
            # This ensures consistency with main category_performance calculation
            self.stdout.write(f"\n🔍 DEBUG: Calculating category_performance for OSCE Type: {osce_type}")

            # DEBUG: Count total exams by type
            exam_type_counts = {}
            for user_id, student_data in students_data.items():
                for exam in student_data['exam_attempts']:
                    exam_type = exam.get('exam_type', 'Unknown')
                    exam_type_counts[exam_type] = exam_type_counts.get(exam_type, 0) + 1
            self.stdout.write(f"  Total exams by type: {exam_type_counts}")

            type_category_performance = {}
            for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
                student_category_averages = []
                exams_found_for_category = 0
                all_exam_scores_for_category = []  # DEBUG: Track all exam scores

                # For each student, calculate their category percentage for this OSCE type
                for user_id, student_data in students_data.items():
                    type_marks = student_data['marks_by_type'].get(osce_type, {})
                    if type_marks and type_marks.get('max', 0) > 0:
                        # Aggregate marks for this category from exams of this type
                        category_obtained = 0
                        category_max = 0

                        for exam in student_data['exam_attempts']:
                            if exam.get('exam_type') == osce_type and exam.get('category') == category:
                                exams_found_for_category += 1
                                exam_obtained = exam.get('marks_obtained', 0)
                                exam_max = exam.get('max_marks', 0)
                                category_obtained += exam_obtained
                                category_max += exam_max

                                # DEBUG: Track exam score
                                if exam_max > 0:
                                    exam_score = round((exam_obtained / exam_max) * 100, 2)
                                    all_exam_scores_for_category.append(exam_score)

                        # Calculate this student's category percentage using Total Marks Method
                        if category_max > 0:
                            student_category_pct = (category_obtained / category_max) * 100
                            student_category_averages.append(student_category_pct)

                # Average all student category percentages
                if student_category_averages:
                    type_category_performance[category] = round(sum(student_category_averages) / len(student_category_averages), 2)

                    # DEBUG: Show all exam scores and student averages
                    exam_avg = round(sum(all_exam_scores_for_category) / len(all_exam_scores_for_category), 2) if all_exam_scores_for_category else 0
                    self.stdout.write(f"  📊 {category}:")
                    self.stdout.write(f"     Exam scores ({len(all_exam_scores_for_category)}): {all_exam_scores_for_category}")
                    self.stdout.write(f"     Exam-level avg: {exam_avg}%")
                    self.stdout.write(f"     Student percentages ({len(student_category_averages)}): {[round(p, 2) for p in student_category_averages]}")
                    self.stdout.write(f"     Student-level avg: {type_category_performance[category]}%")
                else:
                    type_category_performance[category] = None
                    self.stdout.write(f"  {category}: {exams_found_for_category} exams, No student data")

            # Calculate skills performance for this OSCE type
            # Must recalculate from student exam_attempts to get type-specific data
            for user_id, student_data in students_data.items():
                type_marks = student_data['marks_by_type'].get(osce_type, {})
                if type_marks and type_marks.get('max', 0) > 0:
                    # Process exams of this type
                    for exam in student_data['exam_attempts']:
                        if exam.get('exam_type') == osce_type:
                            procedure_id = exam.get('procedure_id')
                            procedure_name = exam.get('procedure_name')
                            if procedure_id and procedure_name:
                                # Initialize skill if not exists
                                if procedure_id not in type_skills_perf:
                                    type_skills_perf[procedure_id] = {
                                        'skill_name': procedure_name,
                                        'category': exam.get('category', 'N/A'),
                                        'attempts': 0,
                                        'students': set(),
                                        'scores': [],
                                        'student_marks': {}
                                    }

                                # Track exam-level data
                                type_skills_perf[procedure_id]['attempts'] += 1
                                type_skills_perf[procedure_id]['students'].add(user_id)

                                # Calculate exam percentage
                                exam_obtained = exam.get('marks_obtained', 0)
                                exam_max = exam.get('max_marks', 0)
                                if exam_max > 0:
                                    exam_pct = round((exam_obtained / exam_max) * 100, 2)
                                    type_skills_perf[procedure_id]['scores'].append(exam_pct)

                                # Track student-level marks
                                if user_id not in type_skills_perf[procedure_id]['student_marks']:
                                    type_skills_perf[procedure_id]['student_marks'][user_id] = {'obtained': 0, 'max': 0}
                                type_skills_perf[procedure_id]['student_marks'][user_id]['obtained'] += exam_obtained
                                type_skills_perf[procedure_id]['student_marks'][user_id]['max'] += exam_max

            # Calculate aggregated metrics for each skill
            type_skills_perf_final = {}
            for skill_id, skill_data in type_skills_perf.items():
                if skill_data['scores']:
                    # Exam-level average
                    skill_avg_score = round(sum(skill_data['scores']) / len(skill_data['scores']), 2)
                    skill_pass_rate = round((sum(1 for s in skill_data['scores'] if s >= 80) / len(skill_data['scores']) * 100), 2)

                    # Student-level average
                    student_skill_averages = []
                    for student_id, marks in skill_data['student_marks'].items():
                        if marks['max'] > 0:
                            student_skill_pct = (marks['obtained'] / marks['max']) * 100
                            student_skill_averages.append(student_skill_pct)

                    avg_skill_score_student_method = round(sum(student_skill_averages) / len(student_skill_averages), 2) if student_skill_averages else skill_avg_score

                    type_skills_perf_final[skill_id] = {
                        'skill_name': skill_data['skill_name'],
                        'category': skill_data['category'],
                        'attempts': skill_data['attempts'],
                        'students_attempted': len(skill_data['students']),
                        'avg_score': skill_avg_score,  # Exam-level average
                        'avg_score_student_method': avg_skill_score_student_method,  # Student-level average
                        'pass_rate': skill_pass_rate,
                        'highest_score': max(skill_data['scores']),
                        'lowest_score': min(skill_data['scores']),
                        'osce_types': [osce_type]
                    }

            type_skills_perf = type_skills_perf_final

            # Filter OSCE timeline for this type
            for osce in osce_timeline:
                if osce.get('osce_level') == osce_type:
                    type_osce_timeline.append(osce)

            # PRE-COMPUTE: Category drill-down details for this OSCE type
            type_category_details = {}
            for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
                type_skills_in_category = [
                    skill for skill_id, skill in type_skills_perf.items()
                    if skill['category'] == category
                ]

                if type_skills_in_category:
                    # Find highest and lowest scoring skills
                    type_highest_skill = max(type_skills_in_category, key=lambda s: s['avg_score'])
                    type_lowest_skill = min(type_skills_in_category, key=lambda s: s['avg_score'])

                    # Calculate skill grade distribution
                    type_skill_grade_dist = Counter()
                    for skill in type_skills_in_category:
                        grade = self._get_grade(skill['avg_score'])
                        type_skill_grade_dist[grade] += 1

                    type_category_details[category] = {
                        'total_skills': len(type_skills_in_category),
                        'highest_scoring_skill': {
                            'name': type_highest_skill['skill_name'],
                            'score': type_highest_skill['avg_score']
                        },
                        'lowest_scoring_skill': {
                            'name': type_lowest_skill['skill_name'],
                            'score': type_lowest_skill['avg_score']
                        },
                        'skill_grade_distribution': dict(type_skill_grade_dist)
                    }
                else:
                    type_category_details[category] = None

            # Build student batch report for this OSCE type
            for user_id, student_data in students_data.items():
                type_marks = student_data['marks_by_type'].get(osce_type, {})
                if type_marks and type_marks.get('max', 0) > 0:
                    type_overall_avg = round((type_marks['obtained'] / type_marks['max']) * 100, 2)
                    type_overall_grade = self._get_grade(type_overall_avg)

                    # Get category breakdown for this type
                    type_cat_breakdown = {}
                    for exam in student_data['exam_attempts']:
                        if exam.get('exam_type') == osce_type:
                            category = exam.get('category')
                            if category not in type_cat_breakdown:
                                type_cat_breakdown[category] = []
                            type_cat_breakdown[category].append(exam.get('score', 0))

                    type_category_breakdown = {}
                    for category, scores in type_cat_breakdown.items():
                        if scores:
                            type_category_breakdown[category] = {
                                'attempts': len(scores),
                                'avg_score': round(sum(scores) / len(scores), 2)
                            }

                    # PRE-COMPUTE: Procedure scores for this specific OSCE type
                    type_procedure_scores = {}
                    type_attempts = [e for e in student_data['exam_attempts'] if e.get('exam_type') == osce_type]

                    procedure_marks = {}
                    for attempt in type_attempts:
                        proc_name = attempt.get('procedure_name')
                        if proc_name:
                            if proc_name not in procedure_marks:
                                procedure_marks[proc_name] = {'obtained': 0, 'max': 0}
                            procedure_marks[proc_name]['obtained'] += attempt.get('marks_obtained', 0)
                            procedure_marks[proc_name]['max'] += attempt.get('max_marks', 0)

                    for proc_name, marks in procedure_marks.items():
                        if marks['max'] > 0:
                            type_procedure_scores[proc_name] = round((marks['obtained'] / marks['max']) * 100, 2)
                        else:
                            type_procedure_scores[proc_name] = 0

                    type_student_batch_report.append({
                        'user_id': user_id,
                        'name': student_data['name'],
                        'overall_avg': type_overall_avg,
                        'overall_grade': type_overall_grade,
                        'total_marks_obtained': type_marks['obtained'],
                        'total_max_marks': type_marks['max'],
                        'category_breakdown': type_category_breakdown,
                        'exam_attempts': type_attempts,
                        'procedure_scores_by_type': {osce_type: type_procedure_scores}  # NEW: Pre-computed for this type
                    })

            # Calculate metrics for this OSCE type
            type_avg_score = round(sum(type_student_overall_percentages) / len(type_student_overall_percentages), 2) if type_student_overall_percentages else 0
            type_pass_count = sum(1 for s in type_student_overall_percentages if s >= 80)
            type_pass_rate = round((type_pass_count / len(type_student_overall_percentages) * 100), 2) if type_student_overall_percentages else 0

            # Calculate STUDENT-LEVEL grade distribution for this OSCE type
            type_grade_dist = Counter()
            for student in type_student_batch_report:
                type_grade_dist[student['overall_grade']] += 1

            # Store OSCE type breakdown
            osce_type_breakdown[osce_type] = {
                'total_students': len(type_student_overall_percentages),
                'students_assessed': len(type_completed_students),
                'osces_conducted': len(type_osce_timeline),  # Count of OSCEs for this type
                'avg_score': type_avg_score,
                'pass_rate': type_pass_rate,
                'grade_letter': self._get_grade(type_avg_score),
                'grade_distribution': dict(type_grade_dist),
                'category_performance': type_category_performance,
                'category_details': type_category_details,  # NEW: Pre-computed category drill-down metrics
                'skills_performance': type_skills_perf,
                'osce_activity_timeline': type_osce_timeline,
                'student_batch_report': type_student_batch_report,
                'raw_scores': type_student_overall_percentages
            }

        # ============================================
        # PHASE 5: STORE IN FIRESTORE
        # ============================================

        # Store semester metrics
        semester_metrics = {
            'unit_name': unit_name,
            'unit_type': unit_type,  # 'institute' or 'hospital'
            'state': unit_state,  # State from Institution or Hospital model
            'year': year,
            'semester': semester,
            'total_students': len(enrolled_student_ids),  # Total enrolled from Batches
            'students_assessed': len(completed_student_ids),  # Students who completed at least one exam
            'osces_conducted': len(osce_summaries),
            'avg_score': avg_score,
            'pass_rate': pass_rate,
            'grade_letter': self._get_grade(avg_score),
            'num_assessors': len(assessors_set),
            'skills_evaluated': len(evaluated_procedures),  # Count unique procedures evaluated
            'category_performance': category_performance,
            'category_details': category_details,  # NEW: Pre-computed category drill-down metrics
            'skills_performance': skills_performance,
            'grade_distribution': dict(grade_distribution),
            'osce_type_breakdown': osce_type_breakdown,  # NEW: Pre-computed breakdown by OSCE type
            'osce_activity_timeline': osce_timeline,
            'student_batch_report': student_batch_report,
            'latest_osce': osce_timeline[0] if osce_timeline else None,
            'raw_scores': all_scores,
            'assessed_student_ids': list(completed_student_ids),
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        
        doc_id = f"{unit_name}_{year}_{semester}"
        db.collection('SemesterMetrics').document(doc_id).set(semester_metrics)

        self.stdout.write(f"    ✅ FINAL METRICS:")
        self.stdout.write(f"       Total Students (from Batches): {len(enrolled_student_ids)}")
        self.stdout.write(f"       Students Assessed (took exams): {len(students_data)}")
        self.stdout.write(f"       OSCEs Conducted: {len(osce_summaries)}")
        self.stdout.write(f"       Skills Evaluated: {len(evaluated_procedures)}")
        self.stdout.write(f"       Avg Score: {avg_score}%")
        self.stdout.write(f"       Pass Rate: {pass_rate}%")

        # Update unit metrics (works for both institution and hospital)
        self._update_unit_metrics(unit_name, unit_type, year)

    def _update_unit_metrics(self, unit_name, unit_type, year):
        """
        Aggregate all semester metrics into unit-level metrics
        Works for both institutions and hospitals

        IMPORTANT: enrolled students count uses same logic as SemesterMetrics:
        - Query Batches for unit/year (no semester filter)
        - Count unique learner IDs
        """

        # ============================================
        # FETCH UNIT STATE FROM FIRESTORE
        # ============================================

        # Get state from Institution or Hospital in Firestore
        unit_state = 'Unknown'
        try:
            if unit_type == 'institution':
                # Query Firestore InstituteNames collection by instituteName field
                self.stdout.write(f"      Searching for institution '{unit_name}' in InstituteNames...")
                institutions_query = db.collection('InstituteNames').where('instituteName', '==', unit_name).stream()
                found = False
                for inst_doc in institutions_query:
                    found = True
                    inst_data = inst_doc.to_dict()
                    state_value = inst_data.get('state')
                    self.stdout.write(f"        Found institution document: {inst_doc.id}")
                    self.stdout.write(f"        State value: {state_value}")
                    if state_value:
                        unit_state = state_value
                        self.stdout.write(f"      ✓ Found state '{unit_state}' for institution '{unit_name}'")
                        break
                if not found:
                    self.stdout.write(f"      ✗ No institution document found for '{unit_name}' in InstituteNames")
            elif unit_type == 'hospital':
                # Query Firestore HospitalNames collection by hospitalName field
                self.stdout.write(f"      Searching for hospital '{unit_name}' in HospitalNames...")
                hospitals_query = db.collection('HospitalNames').where('hospitalName', '==', unit_name).stream()
                found = False
                for hosp_doc in hospitals_query:
                    found = True
                    hosp_data = hosp_doc.to_dict()
                    state_value = hosp_data.get('state')
                    self.stdout.write(f"        Found hospital document: {hosp_doc.id}")
                    self.stdout.write(f"        State value: {state_value}")
                    if state_value:
                        unit_state = state_value
                        self.stdout.write(f"      ✓ Found state '{unit_state}' for hospital '{unit_name}'")
                        break
                if not found:
                    self.stdout.write(f"      ✗ No hospital document found for '{unit_name}' in HospitalNames")
        except Exception as e:
            self.stdout.write(f"      ✗ Error fetching state for {unit_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            unit_state = 'Unknown'

        # Get all enrolled students for this unit/year (same logic as SemesterMetrics, but without semester filter)
        enrolled_student_ids = set()
        batches_query = db.collection('Batches')\
            .where('yearOfBatch', '==', year)

        for batch_doc in batches_query.stream():
            batch_data = batch_doc.to_dict()
            batch_unit_name = batch_data.get('unit_name')

            # Fall back to extracting from unit reference if unit_name not present
            if not batch_unit_name:
                unit_ref = batch_data.get('unit')
                if unit_ref:
                    try:
                        unit_doc = unit_ref.get()
                        if unit_doc.exists:
                            unit_doc_data = unit_doc.to_dict()
                            batch_unit_name = (
                                unit_doc_data.get('instituteName') or
                                unit_doc_data.get('hospitalName') or
                                unit_doc_data.get('name') or
                                ''
                            )
                    except:
                        pass

            # Only count learners from batches belonging to this unit
            if batch_unit_name == unit_name:
                for learner_ref in batch_data.get('learners', []):
                    if learner_ref:
                        learner_id = learner_ref.id if hasattr(learner_ref, 'id') else str(learner_ref).split('/')[-1]
                        enrolled_student_ids.add(learner_id)

        semester_docs = db.collection('SemesterMetrics')\
            .where('unit_name', '==', unit_name)\
            .where('year', '==', year)\
            .stream()

        # Student-level aggregation (same as METRICS_CALCULATION_GUIDE.md)
        # Collect each STUDENT's overall percentage from student_batch_report across all semesters
        # If a student appears in multiple semesters, they contribute multiple data points
        student_overall_percentages = []
        total_osces = 0
        assessed_student_ids = set()
        all_skills_evaluated = set()
        all_category_scores = defaultdict(list)
        semester_breakdown = {}
        total_grade_dist = Counter()

        for sem_doc in semester_docs:
            sem_data = sem_doc.to_dict()
            semester_num = sem_data.get('semester')

            # Collect student-level percentages from student_batch_report
            # This ensures we use STUDENT averages (not exam-level raw_scores)
            for student in sem_data.get('student_batch_report', []):
                student_overall_percentages.append(student.get('overall_avg', 0))

            total_osces += sem_data.get('osces_conducted', 0)

            # Track students assessed and skills evaluated from each semester
            # Note: We track unique skills across all semesters
            all_skills_evaluated.update(sem_data.get('skills_performance', {}).keys())
            assessed_student_ids.update(sem_data.get('assessed_student_ids', []))

            # Aggregate categories - collect scores and average later
            for category, score in sem_data.get('category_performance', {}).items():
                if score is not None:
                    all_category_scores[category].append(score)

            # Aggregate grade distribution
            for grade, count in sem_data.get('grade_distribution', {}).items():
                total_grade_dist[grade] += count

            # Store semester breakdown
            semester_breakdown[semester_num] = {
                'total_students': sem_data.get('total_students', 0),
                'students_assessed': sem_data.get('students_assessed', 0),
                'avg_score': sem_data.get('avg_score', 0),
                'pass_rate': sem_data.get('pass_rate', 0),
                'osces_conducted': sem_data.get('osces_conducted', 0),
                'skills_evaluated': sem_data.get('skills_evaluated', 0)
            }

        # Compute unit-level aggregations using STUDENT-LEVEL AVERAGING
        # Average category scores across all students in all semesters
        category_performance = {}
        for category, scores in all_category_scores.items():
            category_performance[category] = round(sum(scores) / len(scores), 2) if scores else None

        # Calculate average score from student percentages (TOTAL MARKS METHOD per METRICS_CALCULATION_GUIDE.md)
        avg_score = round(sum(student_overall_percentages) / len(student_overall_percentages), 2) if student_overall_percentages else 0
        pass_count = sum(1 for s in student_overall_percentages if s >= 80)
        pass_rate = round((pass_count / len(student_overall_percentages) * 100), 2) if student_overall_percentages else 0

        # Aggregate students_assessed: count unique student IDs who attempted at least one OSCE
        total_students_assessed = len(assessed_student_ids) if assessed_student_ids else sum(
            s.get('students_assessed', 0) for s in semester_breakdown.values()
        )

        unit_metrics = {
            'unit_name': unit_name,
            'unit_type': unit_type,  # 'institute' or 'hospital'
            'state': unit_state,  # State from Institution or Hospital model
            'year': year,
            'total_students': len(enrolled_student_ids),  # Unique learners from Batches (same logic as SemesterMetrics)
            'students_assessed': total_students_assessed,  # Total students who took at least 1 OSCE
            'skills_evaluated': len(all_skills_evaluated),  # Unique skills across all semesters
            'total_osces': total_osces,
            'avg_score': avg_score,  # Student-level average of overall percentages
            'pass_rate': pass_rate,  # Pass rate from student percentages
            'grade_letter': self._get_grade(avg_score),  # Grade based on avg_score
            'category_performance': category_performance,
            'semester_breakdown': semester_breakdown,
            'grade_distribution': dict(total_grade_dist),
            'raw_scores': student_overall_percentages,  # Student-level percentages from all semesters (student can appear multiple times if in multiple semesters)
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        
        doc_id = f"{unit_name}_{year}"
        # Store in unified collection (works for both institutions and hospitals)
        db.collection('UnitMetrics').document(doc_id).set(unit_metrics)


    def _parse_checklist_summary(self, exam_metadata):
        """
        Parse examMetaData to compute checklist summary statistics
        Returns dict with total_steps, steps_completed, critical_steps, etc.
        """
        total_steps = 0
        steps_completed = 0
        critical_steps_total = 0
        critical_steps_missed = 0
        missed_critical_steps_list = []

        for section in exam_metadata:
            for question in section.get('section_questions', []):
                total_steps += 1

                # Check if step was completed (has marks_obtained > 0 or answer_scored > 0)
                marks_obtained = question.get('marks_obtained') or question.get('answer_scored', 0)
                if marks_obtained > 0:
                    steps_completed += 1

                # Check if critical step
                if question.get('critical', False):
                    critical_steps_total += 1
                    if marks_obtained == 0:
                        critical_steps_missed += 1
                        missed_critical_steps_list.append(question.get('question', 'Unknown step'))

                # Process sub-section questions if present
                if question.get('sub_section_questions_present', False):
                    for sub_q in question.get('sub_section_questions', []):
                        total_steps += 1
                        sub_marks = sub_q.get('marks_obtained') or sub_q.get('answer_scored', 0)
                        if sub_marks > 0:
                            steps_completed += 1

                        if sub_q.get('critical', False):
                            critical_steps_total += 1
                            if sub_marks == 0:
                                critical_steps_missed += 1
                                missed_critical_steps_list.append(sub_q.get('question', 'Unknown step'))

        return {
            'total_steps': total_steps,
            'steps_completed': steps_completed,
            'steps_missed': total_steps - steps_completed,
            'critical_steps_total': critical_steps_total,
            'critical_steps_missed': critical_steps_missed,
            'missed_critical_steps_list': missed_critical_steps_list
        }

    def _get_grade(self, percentage):
        """Convert percentage to grade letter"""
        if percentage is None:
            return '-'
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

    def _mark_processed(self, doc_id):
        db.collection('MetricUpdateQueue').document(doc_id).update({
            'processed': True,
            'processed_at': firestore.SERVER_TIMESTAMP
        })

    def _mark_failed(self, doc_id, reason):
        db.collection('MetricUpdateQueue').document(doc_id).update({
            'processed': False,
            'failed': True,
            'failure_reason': reason,
            'failed_at': firestore.SERVER_TIMESTAMP
        })

    def _increment_retry(self, doc_id):
        db.collection('MetricUpdateQueue').document(doc_id).update({
            'retry_count': firestore.Increment(1),
            'last_retry_at': firestore.SERVER_TIMESTAMP
        })
