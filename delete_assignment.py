import os
import sys
import django
from dotenv import load_dotenv

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ebek_django_app.settings')
django.setup()

from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials

# Load environment variables
load_dotenv()

# Initialize Firebase
from ebek_django_app.settings import BASE_DIR
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "firebase_key.json")

if not os.path.exists(FIREBASE_KEY_PATH):
    print(f"Error: Firebase key file not found at {FIREBASE_KEY_PATH}")
    sys.exit(1)

# Initialize Firebase if not already initialized
try:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)
except ValueError:
    # Already initialized
    pass

firebase_database = os.getenv('FIREBASE_DATABASE')
db = firestore.client(database_id=firebase_database) if firebase_database else firestore.client()


def get_exam_assignments_with_batchassignment(limit=None):
    """
    Query ExamAssignment documents where batchassignment != null
    Note: Firestore doesn't support != null directly, so we need to query differently
    """
    print("Querying ExamAssignment collection for documents with batchassignment field...")
    
    # Get all ExamAssignment documents
    # Note: We'll filter in Python since Firestore doesn't support != null queries directly
    exam_assignments_ref = db.collection('ExamAssignment')
    
    all_docs = []
    count = 0
    
    # Stream all documents and filter in Python
    for doc in exam_assignments_ref.stream():
        doc_data = doc.to_dict()
        batchassignment = doc_data.get('batchassignment')
        
        # Check if batchassignment exists and is not None
        if batchassignment is not None:
            print(doc.id)
            all_docs.append({
                'id': doc.id,
                'data': doc_data
            })
            count += 1
            
            if limit and count >= limit:
                break
    
    return all_docs


def delete_exam_assignments(docs, dry_run=False):
    """Delete the ExamAssignment documents"""
    if not docs:
        print("No documents to delete.")
        return
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Found {len(docs)} ExamAssignment documents with batchassignment != null")
    
    if dry_run:
        print("\nDocuments that would be deleted:")
        for i, doc in enumerate(docs[:10], 1):  # Show first 10
            print(f"  {i}. ID: {doc['id']}")
            if 'user' in doc['data']:
                user_ref = doc['data'].get('user')
                if user_ref:
                    try:
                        user_doc = user_ref.get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            print(f"     User: {user_data.get('username', 'N/A')}")
                    except:
                        pass
        if len(docs) > 10:
            print(f"  ... and {len(docs) - 10} more")
        print("\n[DRY RUN] No documents were actually deleted.")
        return
    
    # Actual deletion
    deleted_count = 0
    failed_count = 0
    
    print(f"\nDeleting {len(docs)} documents...")
    
    # Delete in batches for better performance
    batch = db.batch()
    batch_size = 500  # Firestore batch limit is 500
    
    for i, doc in enumerate(docs):
        try:
            doc_ref = db.collection('ExamAssignment').document(doc['id'])
            batch.delete(doc_ref)
            
            # Commit batch when it reaches the limit
            if (i + 1) % batch_size == 0:
                batch.commit()
                deleted_count += batch_size
                print(f"  Deleted {deleted_count}/{len(docs)} documents...")
                batch = db.batch()
        except Exception as e:
            print(f"  Error deleting document {doc['id']}: {str(e)}")
            failed_count += 1
    
    # Commit remaining documents
    if len(docs) % batch_size != 0:
        try:
            batch.commit()
            deleted_count += len(docs) % batch_size
        except Exception as e:
            print(f"  Error committing final batch: {str(e)}")
            failed_count += len(docs) % batch_size
    
    print(f"\n✓ Successfully deleted {deleted_count} documents")
    if failed_count > 0:
        print(f"✗ Failed to delete {failed_count} documents")


def delete_entire_collection(collection_name, dry_run=False):
    """Delete all documents from a collection"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing collection: {collection_name}")

    collection_ref = db.collection(collection_name)
    docs = list(collection_ref.stream())

    if not docs:
        print(f"  No documents found in {collection_name}")
        return

    print(f"  Found {len(docs)} documents")

    if dry_run:
        print(f"  [DRY RUN] Would delete {len(docs)} documents from {collection_name}")
        return

    # Delete in batches
    deleted_count = 0
    failed_count = 0
    batch = db.batch()
    batch_size = 500

    for i, doc in enumerate(docs):
        try:
            batch.delete(doc.reference)

            # Commit batch when it reaches the limit
            if (i + 1) % batch_size == 0:
                batch.commit()
                deleted_count += batch_size
                print(f"  Deleted {deleted_count}/{len(docs)} documents from {collection_name}...")
                batch = db.batch()
        except Exception as e:
            print(f"  Error deleting document {doc.id}: {str(e)}")
            failed_count += 1

    # Commit remaining documents
    if len(docs) % batch_size != 0:
        try:
            batch.commit()
            deleted_count += len(docs) % batch_size
        except Exception as e:
            print(f"  Error committing final batch: {str(e)}")
            failed_count += len(docs) % batch_size

    print(f"  ✓ Successfully deleted {deleted_count} documents from {collection_name}")
    if failed_count > 0:
        print(f"  ✗ Failed to delete {failed_count} documents")


def main():
    dry_run = False  # Set to True to preview what would be deleted

    print("=" * 60)
    print("DELETION SCRIPT - Will delete from multiple collections")
    print("=" * 60)

    # Collections to completely delete
    collections_to_clear = [
        'BatchAssignment',
        'BatchAssignmentSummary',
        'MetricUpdateQueue',
        'SemesterMetrics',
        'UnitMetrics'
    ]

    # Get ExamAssignment documents with batchassignment
    print("\n1. Processing ExamAssignment (filtered by batchassignment != null)")
    docs = get_exam_assignments_with_batchassignment(limit=None)

    if not docs:
        print("  No ExamAssignment documents found with batchassignment != null")
    else:
        delete_exam_assignments(docs, dry_run=dry_run)

    # Delete all documents from the specified collections
    print(f"\n2. Deleting all documents from {len(collections_to_clear)} collections")
    for collection_name in collections_to_clear:
        delete_entire_collection(collection_name, dry_run=dry_run)

    print("\n" + "=" * 60)
    if dry_run:
        print("[DRY RUN] No documents were actually deleted.")
    else:
        print("✓ All deletion operations completed!")
    print("=" * 60)


main()
