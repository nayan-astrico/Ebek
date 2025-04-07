from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def update_exam_assignments_with_institute():
    # Initialize Firestore client
    db = firestore.client()
    
    try:
        # Get all exam assignments in batches
        batch_size = 500
        last_doc = None
        updated_count = 0
        error_count = 0
        
        while True:
            # Create query
            query = db.collection('ExamAssignment').limit(batch_size)
            if last_doc:
                query = query.start_after(last_doc)
            
            # Get batch of documents
            docs = query.get()
            docs_list = list(docs)
            
            if not docs_list:
                break  # No more documents to process
                
            # Process each exam assignment in the batch
            for exam in docs_list:
                try:
                    exam_data = exam.to_dict()
                    user_ref = exam_data.get('user')
                    
                    if user_ref:
                        # Get user document
                        user_doc = user_ref.get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            institute_ref = user_data.get('institute')
                            
                            if institute_ref:
                                # Update exam assignment with institute reference
                                exam.reference.update({
                                    'institute': institute_ref
                                })
                                updated_count += 1
                                print(f"Updated exam {exam.id}")
                            else:
                                print(f"No institute found for user: {user_doc.id}")
                                error_count += 1
                        else:
                            print(f"User document doesn't exist for exam: {exam.id}")
                            error_count += 1
                    else:
                        print(f"No user reference found for exam: {exam.id}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"Error processing exam {exam.id}: {str(e)}")
                    error_count += 1
            
            # Update last_doc for next batch
            last_doc = docs_list[-1]
            print(f"Processed batch. Current counts - Success: {updated_count}, Errors: {error_count}")
            
        print(f"Update completed. Total Success: {updated_count}, Total Errors: {error_count}")
        
    except Exception as e:
        print(f"Script failed: {str(e)}")


update_exam_assignments_with_institute()
