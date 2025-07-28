#!/usr/bin/env python
"""
Script to sync existing groups to Firebase with updated structure including is_active field.
This ensures all existing groups are properly synced with the new Firebase structure.
"""

import os
import django
import sys

# Add the project directory to the Python path
sys.path.append('/Users/nayanjain/Documents/ebek_django_app')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ebek_django_app.settings')
django.setup()

from assessments.models import Group
from firebase_admin import firestore
from django.contrib.auth import get_user_model

db = firestore.client()
User = get_user_model()

def sync_existing_groups():
    """
    Sync all existing groups to Firebase with the updated structure.
    """
    print("Starting to sync existing groups to Firebase...")
    
    groups = Group.objects.all()
    print(f"Found {groups.count()} groups to sync")
    
    for group in groups:
        try:
            # Prepare the data with the updated structure
            data = {
                "name": group.name,
                "type": group.type,
                "is_active": group.is_active,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None,
                "group_head_name": group.group_head.full_name if group.group_head else None,
                "group_head_email": group.group_head.email if group.group_head else None,
                "group_head_phone": group.group_head.phone_number if group.group_head else None,
            }
            
            # Update the group document in Firebase
            db.collection("Groups").document(str(group.id)).set(data)
            
            # Update group head's user record with group name and active status
            if group.group_head:
                # Find user document by email
                users_ref = db.collection("Users")
                query = users_ref.where("emailID", "==", group.group_head.email).limit(1)
                docs = query.get()
                
                if docs:
                    # Update the first matching document
                    user_data = {
                        "group": group.name,
                        "group_active": group.is_active,
                    }
                    docs[0].reference.update(user_data)
                    print(f"Updated user record for group head: {group.group_head.email}")
            
            print(f"✓ Synced group: {group.name} (ID: {group.id})")
            
        except Exception as e:
            print(f"✗ Error syncing group {group.name} (ID: {group.id}): {str(e)}")
    
    print("Group sync completed!")

if __name__ == "__main__":
    sync_existing_groups() 