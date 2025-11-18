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
            'station_scores': defaultdict(list)
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
                            'all_scores': [],
                            'category_scores': defaultdict(list),
                            'exam_attempts': [],
                            'skills_attempted': set(),
                            'skills_passed': set(),
                            'total_osces': 0
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
                            
                            # Track by exam type
                            if exam_type in students_data[user_id]['scores_by_type']:
                                students_data[user_id]['scores_by_type'][exam_type].append(percentage)
                            
                            # Track grade distribution
                            grade = self._get_grade(percentage)
                            grade_distribution[grade] += 1
                            
                            # Track student completion
                            completed_student_ids.add(user_id)
                            
                            # Track by category
                            if procedure_category:
                                category_scores[procedure_category].append(percentage)
                                students_data[user_id]['category_scores'][procedure_category].append(percentage)
                            
                            # Track per-exam breakdown for the student
                            students_data[user_id]['exam_attempts'].append({
                                'procedure_id': procedure_id,
                                'procedure_name': procedure_name,
                                'category': procedure_category,
                                'exam_type': exam_type,
                                'score': percentage,
                                'test_date': test_date.isoformat() if test_date else None,
                                'pass': percentage >= 80
                            })
                            
                            # Track by skill
                            if procedure_id:
                                skills_data[procedure_id]['attempts'] += 1
                                skills_data[procedure_id]['scores'].append(percentage)
                                skills_data[procedure_id]['students'].add(user_id)
                                skills_data[procedure_id]['skill_name'] = procedure_name
                                skills_data[procedure_id]['category'] = procedure_category
                                skills_data[procedure_id]['osce_types'].add(exam_type)
                                
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
            
            # Get stats from batch assignments for this OSCE
            procedure_mappings = bas_data.get('procedure_assessor_mappings', [])
            osce_students = set()
            osce_scores_list = []
            
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
                                        if exam_data.get('user'):
                                            osce_students.add(exam_data['user'].id)
                                        
                                        if str(exam_data.get('status', '')).lower() == 'completed':
                                            marks = exam_data.get('marks', 0)
                                            metadata = exam_data.get('examMetaData', [])
                                            max_m = sum(
                                                q.get('right_marks_for_question', 0)
                                                for sec in metadata
                                                for q in sec.get('section_questions', [])
                                            )
                                            if max_m > 0:
                                                osce_scores_list.append(round((marks / max_m) * 100, 2))
                        except:
                            pass
            
            avg_score = round(sum(osce_scores_list) / len(osce_scores_list), 2) if osce_scores_list else 0
            pass_rate = round((sum(1 for s in osce_scores_list if s >= 80) / len(osce_scores_list) * 100), 2) if osce_scores_list else 0
            
            osce_timeline.append({
                'osce_level': osce_level,
                'date_conducted': date_str,
                'num_students': len(osce_students),
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
        
        # Overall metrics
        pass_count = sum(1 for s in all_scores if s >= 80)
        avg_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0
        pass_rate = round((pass_count / len(all_scores) * 100), 2) if all_scores else 0
        
        # Category performance
        category_performance = {}
        for category in ['Core Skills', 'Infection Control', 'Communication', 'Documentation', 'Pre-Procedure', 'Critical Thinking']:
            if category in category_scores and category_scores[category]:
                category_performance[category] = round(sum(category_scores[category]) / len(category_scores[category]), 2)
            else:
                category_performance[category] = None
        
        # Skills performance (detailed)
        skills_performance = {}
        for skill_id, skill_data in skills_data.items():
            if skill_data['scores']:
                avg_skill_score = round(sum(skill_data['scores']) / len(skill_data['scores']), 2)
                skill_pass_rate = round((sum(1 for s in skill_data['scores'] if s >= 80) / len(skill_data['scores']) * 100), 2)
                
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
                    'avg_score': avg_skill_score,
                    'pass_rate': skill_pass_rate,
                    'highest_score': max(skill_data['scores']),
                    'lowest_score': min(skill_data['scores']),
                    'osce_types': list(skill_data['osce_types']),
                    'station_breakdown': station_breakdown
                }
        
        # Student batch report
        student_batch_report = []
        for user_id, student_data in students_data.items():
            if not student_data['all_scores']:
                # Skip students with no completed exams
                continue
            
            overall_avg = round(sum(student_data['all_scores']) / len(student_data['all_scores']), 2) if student_data['all_scores'] else 0
            overall_grade = self._get_grade(overall_avg)
            
            # Get best and worst OSCE
            classroom_avg = round(sum(student_data['scores_by_type']['Classroom']) / len(student_data['scores_by_type']['Classroom']), 2) if student_data['scores_by_type']['Classroom'] else None
            mock_avg = round(sum(student_data['scores_by_type']['Mock']) / len(student_data['scores_by_type']['Mock']), 2) if student_data['scores_by_type']['Mock'] else None
            final_avg = round(sum(student_data['scores_by_type']['Final']) / len(student_data['scores_by_type']['Final']), 2) if student_data['scores_by_type']['Final'] else None
            
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
                'skills_attempted': len(student_data['skills_attempted']),
                'skills_passed': len(student_data['skills_passed']),
                'skills_needing_improvement': skills_below_80,
                'best_performing_osce': best_osce,
                'worst_performing_osce': worst_osce,
                'category_breakdown': category_breakdown,
                'exam_attempts': student_data['exam_attempts']
            })
        
        # Sort student report by overall average (descending)
        student_batch_report.sort(key=lambda x: x['overall_avg'], reverse=True)
        
        # ============================================
        # PHASE 5: STORE IN FIRESTORE
        # ============================================
        
        # Store semester metrics
        semester_metrics = {
            'unit_name': unit_name,
            'unit_type': unit_type,  # 'institute' or 'hospital'
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
            'skills_performance': skills_performance,
            'grade_distribution': dict(grade_distribution),
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
        """
        
        semester_docs = db.collection('SemesterMetrics')\
            .where('unit_name', '==', unit_name)\
            .where('year', '==', year)\
            .stream()
        
        all_scores = []
        total_osces = 0
        all_students_enrolled = set()
        all_students_assessed = set()
        all_skills_evaluated = set()
        assessed_student_ids = set()
        all_category_scores = defaultdict(list)
        semester_breakdown = {}
        total_grade_dist = Counter()
        
        for sem_doc in semester_docs:
            sem_data = sem_doc.to_dict()
            semester_num = sem_data.get('semester')
            
            all_scores.extend(sem_data.get('raw_scores', []))
            total_osces += sem_data.get('osces_conducted', 0)
            
            # Track students assessed and skills evaluated from each semester
            # Note: We track unique skills across all semesters
            all_skills_evaluated.update(sem_data.get('skills_performance', {}).keys())
            assessed_student_ids.update(sem_data.get('assessed_student_ids', []))
            
            # Aggregate categories
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
        
        # Compute unit-level aggregations
        category_performance = {}
        for category, scores in all_category_scores.items():
            category_performance[category] = round(sum(scores) / len(scores), 2) if scores else None
        
        pass_count = sum(1 for s in all_scores if s >= 80)
        
        # Aggregate students_assessed: count unique student IDs who attempted at least one OSCE
        total_students_assessed = len(assessed_student_ids) if assessed_student_ids else sum(
            s.get('students_assessed', 0) for s in semester_breakdown.values()
        )
        
        unit_metrics = {
            'unit_name': unit_name,
            'unit_type': unit_type,  # 'institute' or 'hospital'
            'year': year,
            'total_students': sum(s.get('total_students', 0) for s in semester_breakdown.values()),
            'students_assessed': total_students_assessed,  # Total students who took at least 1 OSCE
            'skills_evaluated': len(all_skills_evaluated),  # Unique skills across all semesters
            'total_osces': total_osces,
            'avg_score': round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
            'pass_rate': round((pass_count / len(all_scores) * 100), 2) if all_scores else 0,
            'category_performance': category_performance,
            'semester_breakdown': semester_breakdown,
            'grade_distribution': dict(total_grade_dist),
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        
        doc_id = f"{unit_name}_{year}"
        # Store in unified collection (works for both institutions and hospitals)
        db.collection('UnitMetrics').document(doc_id).set(unit_metrics)

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
