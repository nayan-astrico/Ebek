import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import time
from django.conf import settings

def delete_all_data():
    # Initialize Firebase Admin with your service account key
    cred = credentials.Certificate(settings.FIREBASE_KEY_PATH)

    # Get Firestore client
    db = firestore.client()

    # Get all collections
    collections = db.collections()

    deleted_docs = 0
    
    try:
        for collection in collections:
            # Get all documents in the collection
            docs = collection.stream()
            
            # Delete each document
            for doc in docs:
                print(f'Deleting document {doc.id} from collection {collection.id}')
                doc.reference.delete()
                deleted_docs += 1
                
                # Optional: Add a small delay to prevent hitting quota limits
                time.sleep(0.1)
        
        print(f'Successfully deleted {deleted_docs} documents')
        
    except Exception as e:
        print(f'Error occurred: {str(e)}')

# confirm = input("WARNING: This will delete ALL data from your Firestore database. Type 'YES' to confirm: ")

# if confirm == 'YES':
#     delete_all_data()
# else:
#     print('Operation cancelled')
# delete_all_data()