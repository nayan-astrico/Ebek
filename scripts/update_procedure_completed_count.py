from firebase_admin import firestore


db = firestore.client()

def update_procedure_completed_counts():
    try:
        # Get all ProcedureAssignments
        procedure_assignments = db.collection('ProcedureAssignment').stream()
        procedure_count = 0
        
        for procedure_doc in procedure_assignments:
            procedure_data = procedure_doc.to_dict()
            exam_assignment_refs = procedure_data.get('examAssignmentArray', [])
            
            # Skip if no exam assignments
            if not exam_assignment_refs:
                print(f"Skipping procedure {procedure_doc.id} - no exam assignments")
                continue
            
            # Get exam assignment IDs
            exam_assignment_ids = []
            for ref in exam_assignment_refs:
                if isinstance(ref, str):
                    exam_assignment_ids.append(ref.split('/')[-1])
                else:
                    exam_assignment_ids.append(ref.id)
            
            # Count completed exams
            completed_count = 0
            batch_size = 10
            
            for i in range(0, len(exam_assignment_ids), batch_size):
                batch_ids = exam_assignment_ids[i:i + batch_size]
                completed_query = (
                    db.collection('ExamAssignment')
                    .where('__name__', 'in', batch_ids)
                    .where('status', '==', 'Completed')
                )
                completed_snapshot = completed_query.get()
                completed_count += len(completed_snapshot)
            
            # Update the procedure assignment
            procedure_doc.reference.update({
                'completedExamsCount': completed_count
            })
            
            procedure_count += 1
            print(f"Updated procedure {procedure_doc.id} with completedExamsCount: {completed_count}")
        
        print(f"Successfully updated {procedure_count} procedure assignments")
        
    except Exception as e:
        print(f"Error updating procedure assignments: {str(e)}")

uupdate_procedure_completed_counts() 