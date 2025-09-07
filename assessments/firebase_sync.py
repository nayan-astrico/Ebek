import firebase_admin
from firebase_admin import auth, firestore
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
from django.conf import settings
from .models import EbekUser, Institution, Hospital, Learner, Assessor, SkillathonEvent, Group, SchedularObject
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
import traceback
import json

from django.conf import settings
import os
from dotenv import load_dotenv

load_dotenv()
firebase_database = os.getenv('FIREBASE_DATABASE')

db = firestore.client(database_id=firebase_database)

def enable_all_signals():
    """
    Function to enable all Django signals by reloading the signal handlers.
    This is more reliable than trying to restore the receivers directly.
    """
    import importlib
    import sys
    
    # Get the current module
    current_module = sys.modules[__name__]
    
    # Reload the module to re-register all signal handlers
    importlib.reload(current_module)
    
    print("All signals have been re-enabled")

class DisableSignals:

    def __init__(self, *signal_sender_pairs):
        self.signal_sender_pairs = signal_sender_pairs
        self.receivers = {}

    def __enter__(self):
        for signal, sender in self.signal_sender_pairs:
            key = (signal, sender)
            self.receivers[key] = list(signal.receivers)  # Store a copy of the receivers
            signal.receivers = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("EXITING DISABLE SIGNALS")
        print(self.receivers)
        for signal, sender in self.signal_sender_pairs:
            key = (signal, sender)
            if key in self.receivers:
                signal.receivers = self.receivers[key]  # Restore the original receivers

def create_test_and_exam_assignments(learner, skillathon_event, test_ref=None, proc_assignment_ref_array=None):
    try:
        """Helper function to create test and exam assignments for a learner with a skillathon event"""
        print("INSIDE CREATE TEST AND EXAM ASSIGNMENTS")
        print(learner)
        print(skillathon_event)
        if not skillathon_event:
            return
        
        # Check if test already exists for this skillathon
        skillathon_name = skillathon_event.name
        test_ref = db.collection('Test').where('skillathon', '==', skillathon_name).limit(1).get()
        if not test_ref:
            print("NO TEST FOUND")
            return
        test_doc = test_ref[0]
        test_data = test_doc.to_dict()
        procedure_assignments = test_data.get('procedureAssignments', []) or []
        
        # Get the learner's user document reference
        learner_user_ref = db.collection('Users').where('emailID', '==', learner.learner_user.email).limit(1).get()
        if not learner_user_ref:
            print("NO LEARNER USER FOUND")
            return
        
        learner_user_ref = learner_user_ref[0].reference
        
        # For each procedure assignment, create an exam assignment for this learner
        for proc_assignment_ref in procedure_assignments:
            proc_assignment = proc_assignment_ref.get()
            if not proc_assignment.exists:
                print("NO PROC ASSIGNMENT FOUND")
                continue
                
            proc_data = proc_assignment.to_dict()
            procedure_ref = proc_data.get('procedure')
            
            if not procedure_ref:
                print("NO PROCEDURE REF FOUND")
                continue
                
            procedure = procedure_ref.get()
            if not procedure.exists:
                print("NO PROCEDURE FOUND")
                continue
                
            procedure_data = procedure.to_dict()
            
            # Check if exam assignment already exists for this user and procedure
            existing_exam_assignments = proc_data.get('examAssignmentArray', [])
            for existing_ref in existing_exam_assignments:
                existing_exam = existing_ref.get()
                if existing_exam.exists:
                    existing_data = existing_exam.to_dict()
                    if existing_data.get('user') == learner_user_ref:
                        # Skip creating new exam assignment if one already exists
                        continue
            
            # Create exam assignment
            exam_assignment_data = {
                'user': learner_user_ref,
                'examMetaData': procedure_data.get('examMetaData', {}),
                'status': 'Pending',
                'notes': procedure_data.get('notes', ''),
                'procedure_name': procedure_data.get('procedureName', ''),
                'institute': learner.college.name if learner.college else None,
                'hospital': learner.hospital.name if learner.hospital else None,
            }
            
            # Add exam assignment to Firestore and get its reference
            exam_assignment_ref = db.collection('ExamAssignment').add(exam_assignment_data)[1]
            
            # Update procedure assignment with new exam assignment reference
            proc_assignment_ref.update({
                'examAssignmentArray': firestore.ArrayUnion([exam_assignment_ref])
            })
    except Exception as e:
        print(e)
        print(traceback.format_exc())

def sync_user_to_firestore(user):
    user_data = {
        "emailID": user.email,
        "name": user.full_name,
        "role": user.user_role,
        "is_active": user.is_active,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "phone_number": user.phone_number,
        "username":user.email
    }
    db.collection("Users").document(str(user.id)).set(user_data)

def delete_user_from_firestore(user):
    db.collection("Users").document(str(user.id)).delete()

def sync_user_to_firebase_auth(user, password=None):
    try:
        fb_user = auth.get_user_by_email(user.email)
        # Update user
        auth.update_user(
            fb_user.uid,
            email=user.email,
            display_name=user.full_name,
            disabled=not user.is_active,
            password=password if password else None,
        )
    except auth.UserNotFoundError:
        # Create user
        auth.create_user(
            email=user.email,
            display_name=user.full_name,
            password=password or "DefaultPassword123!",  # You may want to handle this securely
            disabled=not user.is_active,
        )

def delete_user_from_firebase_auth(user):
    try:
        fb_user = auth.get_user_by_email(user.email)
        auth.delete_user(fb_user.uid)
    except auth.UserNotFoundError:
        pass

@receiver(post_save, sender=EbekUser)
def on_user_save(sender, instance, created, **kwargs):
    print("INSIDE ON USER SAVE")
    # If password is being set, pass it to Firebase Auth
    password = None
    if hasattr(instance, "_raw_password"):
        password = instance._raw_password
    sync_user_to_firestore(instance)
    if instance.user_role != 'student' or instance.user_role != 'nurse':
        sync_user_to_firebase_auth(instance, password=password)

@receiver(post_delete, sender=EbekUser)
def on_user_delete(sender, instance, **kwargs):
    delete_user_from_firestore(instance)
    delete_user_from_firebase_auth(instance)

# --- InstituteNames Sync ---
@receiver(post_save, sender=Institution)
def on_institute_save(sender, instance, created, **kwargs):
    data = {
        "instituteName": instance.name,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "onboarding_type": instance.onboarding_type,
        "is_active": instance.is_active,  # Add is_active field
        "state": instance.state,
        "district": instance.district,
        "address": instance.address,
        "pin_code": instance.pin_code,
        "total_strength": instance.total_strength,
        "group_id": str(instance.group.id) if instance.group else None,
        "group_name": instance.group.name if instance.group else None,
        "unit_head_name": instance.unit_head.full_name if instance.unit_head else None,
        "unit_head_email": instance.unit_head.email if instance.unit_head else None,
        "unit_head_phone": instance.unit_head.phone_number if instance.unit_head else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        "skillathon_event": instance.skillathon.name if instance.skillathon else None
    }

    db.collection("InstituteNames").document(str(instance.id)).set(data)
    
    # Update unit head's user record with institute name
    if instance.unit_head:
        # Find user document by email
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.unit_head.email).limit(1)
        docs = query.get()
        
        if docs:
            # Update the first matching document
            user_data = {
                "institute": instance.name,
                "institute_id": str(instance.id),
                "institute_active": instance.is_active,  # Add institute active status
            }
            docs[0].reference.update(user_data)

@receiver(post_delete, sender=Institution)
def on_institution_delete(sender, instance, **kwargs):
    # Delete from Firestore
    db.collection("InstituteNames").document(str(instance.id)).delete()
    
    # Delete unit head user if exists
    if instance.unit_head:
        # Delete from Firebase Auth
        try:
            fb_user = auth.get_user_by_email(instance.unit_head.email)
            auth.delete_user(fb_user.uid)
        except auth.UserNotFoundError:
            pass
        
        # Delete from Firestore
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.unit_head.email).limit(1)
        docs = query.get()
        if docs:
            docs[0].reference.delete()
        
        # Delete from Django admin
        User = get_user_model()
        try:
            user = User.objects.get(email=instance.unit_head.email)
            user.delete()
        except User.DoesNotExist:
            pass

# --- Skillathon Sync ---
@receiver(post_save, sender=SkillathonEvent)
def on_skillathon_save(sender, instance, created, **kwargs):
    data = {
        "skillathonName": instance.name,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
    }
    db.collection("Skillathon").document(str(instance.id)).set(data)

@receiver(post_delete, sender=SkillathonEvent)
def on_skillathon_delete(sender, instance, **kwargs):
    db.collection("Skillathon").document(str(instance.id)).delete()

@receiver(post_save, sender=Hospital)
def on_hospital_save(sender, instance, created, **kwargs):
    data = {
        "hospitalName": instance.name,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "onboarding_type": instance.onboarding_type,
        "is_active": instance.is_active,  # Add is_active field
        "state": instance.state,
        "district": instance.district,
        "address": instance.address,
        "pin_code": instance.pin_code,
        "nurse_strength": instance.nurse_strength,
        "number_of_beds": instance.number_of_beds,
        "group_id": str(instance.group.id) if instance.group else None,
        "group_name": instance.group.name if instance.group else None,
        "unit_head_name": instance.unit_head.full_name if instance.unit_head else None,
        "unit_head_email": instance.unit_head.email if instance.unit_head else None,
        "unit_head_phone": instance.unit_head.phone_number if instance.unit_head else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        "skillathon_event": instance.skillathon.name if instance.skillathon else None
    }
    db.collection("HospitalNames").document(str(instance.id)).set(data)
    
    # Update unit head's user record with hospital name
    if instance.unit_head:
        # Find user document by email
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.unit_head.email).limit(1)
        docs = query.get()
        
        if docs:
            # Update the first matching document
            user_data = {
                "hospital": instance.name,
                "hospital_id": str(instance.id),
                "hospital_active": instance.is_active,  # Add hospital active status
            }
            docs[0].reference.update(user_data)

@receiver(post_delete, sender=Hospital)
def on_hospital_delete(sender, instance, **kwargs):
    # Delete from Firestore
    db.collection("HospitalNames").document(str(instance.id)).delete()
    
    # Delete unit head user if exists
    if instance.unit_head:
        # Delete from Firebase Auth
        try:
            fb_user = auth.get_user_by_email(instance.unit_head.email)
            auth.delete_user(fb_user.uid)
        except auth.UserNotFoundError:
            pass
        
        # Delete from Firestore
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.unit_head.email).limit(1)
        docs = query.get()
        if docs:
            docs[0].reference.delete()
        
        # Delete from Django admin
        User = get_user_model()
        try:
            user = User.objects.get(email=instance.unit_head.email)
            user.delete()
        except User.DoesNotExist:
            pass

# --- Group Sync ---
@receiver(post_save, sender=Group)
def on_group_save(sender, instance, created, **kwargs):
    try:
        data = {
            "name": instance.name,
            "type": instance.type,
            "is_active": instance.is_active,  # Add is_active field
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
            "group_head_name": instance.group_head.full_name if instance.group_head else None,
            "group_head_email": instance.group_head.email if instance.group_head else None,
            "group_head_phone": instance.group_head.phone_number if instance.group_head else None,
        }
        
        db.collection("Groups").document(str(instance.id)).set(data)
        print(f"✓ Group synced to Firebase: {instance.name} (ID: {instance.id})")
        
        # Update group head's user record with group name and active status
        if instance.group_head:
            try:
                # Find user document by email
                users_ref = db.collection("Users")
                query = users_ref.where("emailID", "==", instance.group_head.email).limit(1)
                docs = query.get()
                
                if docs:
                    # Update the first matching document
                    user_data = {
                        "group": instance.name,
                        "group_active": instance.is_active,  # Add group active status
                    }
                    docs[0].reference.update(user_data)
                    print(f"✓ Updated user record for group head: {instance.group_head.email}")
                else:
                    print(f"⚠ User document not found for group head: {instance.group_head.email}")
            except Exception as e:
                print(f"✗ Error updating user record for group head {instance.group_head.email}: {str(e)}")
                
    except Exception as e:
        print(f"✗ Error syncing group {instance.name} (ID: {instance.id}) to Firebase: {str(e)}")
        import traceback
        traceback.print_exc()

@receiver(post_delete, sender=Group)
def on_group_delete(sender, instance, **kwargs):
    try:
        # Delete from Firestore
        db.collection("Groups").document(str(instance.id)).delete()
        print(f"✓ Group deleted from Firebase: {instance.name} (ID: {instance.id})")
        
        # Delete group head user if exists
        if instance.group_head:
            try:
                # Delete from Firebase Auth
                fb_user = auth.get_user_by_email(instance.group_head.email)
                auth.delete_user(fb_user.uid)
                print(f"✓ Deleted group head from Firebase Auth: {instance.group_head.email}")
            except auth.UserNotFoundError:
                print(f"⚠ Group head not found in Firebase Auth: {instance.group_head.email}")
            except Exception as e:
                print(f"✗ Error deleting group head from Firebase Auth {instance.group_head.email}: {str(e)}")
            
            try:
                # Delete from Firestore
                users_ref = db.collection("Users")
                query = users_ref.where("emailID", "==", instance.group_head.email).limit(1)
                docs = query.get()
                if docs:
                    docs[0].reference.delete()
                    print(f"✓ Deleted group head from Firestore: {instance.group_head.email}")
                else:
                    print(f"⚠ Group head not found in Firestore: {instance.group_head.email}")
            except Exception as e:
                print(f"✗ Error deleting group head from Firestore {instance.group_head.email}: {str(e)}")
            
            try:
                # Delete from Django admin
                User = get_user_model()
                user = User.objects.get(email=instance.group_head.email)
                user.delete()
                print(f"✓ Deleted group head from Django: {instance.group_head.email}")
            except User.DoesNotExist:
                print(f"⚠ Group head not found in Django: {instance.group_head.email}")
            except Exception as e:
                print(f"✗ Error deleting group head from Django {instance.group_head.email}: {str(e)}")
                
    except Exception as e:
        print(f"✗ Error deleting group {instance.name} (ID: {instance.id}) from Firebase: {str(e)}")
        import traceback
        traceback.print_exc()

# --- Learner Sync ---
@receiver(post_save, sender=Learner)
def on_learner_save(sender, instance, created, **kwargs):
    print("INSIDE ON LEARNER SAVE")
    print(instance)
    print(instance.learner_user)
    print(instance.skillathon_event)
    if instance.learner_user:
        # Find user document by email
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.learner_user.email).limit(1)
        docs = query.get()
        
        if docs:
            print(instance.date_of_birth)
            # Update the first matching document with all learner data
            user_data = {
                "learner_type": instance.learner_type if instance.learner_type else None,
                "speciality": instance.speciality if instance.speciality else None,
                "state": instance.state if instance.state else None,
                "district": instance.district if instance.district else None,
                "date_of_birth": instance.date_of_birth.isoformat() if instance.date_of_birth else None,
                "certifications": instance.certifications if instance.certifications else None,
                "learner_gender": instance.learner_gender if instance.learner_gender else None,
                "skillathon_event": instance.skillathon_event.name if instance.skillathon_event else None,
                "institute": instance.college.name if instance.college else None,
                "hospital": instance.hospital.name if instance.hospital else None,
                "course": instance.course if instance.course else None,
                "stream": instance.stream if instance.stream else None,
                "year_of_study": instance.year_of_study if instance.year_of_study else None,
                "designation": instance.designation if instance.designation else None,
                "years_of_experience": instance.years_of_experience if instance.years_of_experience else None,
                "educational_qualification": instance.educational_qualification if instance.educational_qualification else None,
            }
            
            docs[0].reference.update(user_data)

@receiver(post_delete, sender=Learner)
def on_learner_delete(sender, instance, **kwargs):
    if instance.learner_user:
        # Delete from Firebase Auth
        try:
            fb_user = auth.get_user_by_email(instance.learner_user.email)
            auth.delete_user(fb_user.uid)
        except auth.UserNotFoundError:
            pass
        
        # Delete from Firestore
        users_ref = db.collection("Users")
        print(instance.learner_user.email)
        query = users_ref.where("emailID", "==", instance.learner_user.email).limit(1)
        instance.learner_user.delete()
        docs = query.get()
        if docs:
            docs[0].reference.delete()

# --- Assessor Sync ---
@receiver(post_save, sender=Assessor)
def on_assessor_save(sender, instance, created, **kwargs):
    try:
        print(f"Syncing assessor to Firebase: {instance.assessor_user.email if instance.assessor_user else 'No user'}")
        
        if instance.assessor_user:
            # Find user document by email
            users_ref = db.collection("Users")
            query = users_ref.where("emailID", "==", instance.assessor_user.email).limit(1)
            docs = query.get()
            
            if docs:
                # Update the first matching document with all assessor data
                user_data = {
                    "assessor_type": instance.assessor_type,
                    "qualification": instance.qualification,
                    "designation": instance.designation,
                    "specialization": instance.specialization,
                    "is_verifier": instance.is_verifier,
                    "assessor_active": instance.is_active,
                    "created_at": instance.created_at.isoformat() if instance.created_at else None,
                    "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
                }
                
                # Add institution/hospital specific data
                if instance.institution:
                    user_data["institution"] = instance.institution.name
                if instance.hospital:
                    user_data["hospital"] = instance.hospital.name
                
                # Add internal/external specific data
                if instance.assessor_type == 'internal':
                    user_data["staff_id"] = instance.staff_id
                    user_data["branch"] = instance.branch
                else:  # external
                    user_data["location"] = instance.location
                
                docs[0].reference.update(user_data)
                print(f"✓ Successfully synced assessor: {instance.assessor_user.email}")
            else:
                print(f"⚠ Warning: No user document found for assessor: {instance.assessor_user.email}")
        else:
            print(f"⚠ Warning: Assessor has no associated user")
            
    except Exception as e:
        print(f"✗ Error syncing assessor to Firebase: {str(e)}")
        import traceback
        traceback.print_exc()

@receiver(post_delete, sender=Assessor)
def on_assessor_delete(sender, instance, **kwargs):
    try:
        print(f"Deleting assessor from Firebase: {instance.assessor_user.email if instance.assessor_user else 'No user'}")
        
        if instance.assessor_user:
            # Delete from Firebase Auth
            try:
                fb_user = auth.get_user_by_email(instance.assessor_user.email)
                auth.delete_user(fb_user.uid)
                print(f"✓ Successfully deleted assessor from Firebase Auth: {instance.assessor_user.email}")
            except auth.UserNotFoundError:
                print(f"⚠ Warning: User not found in Firebase Auth: {instance.assessor_user.email}")
            except Exception as e:
                print(f"✗ Error deleting from Firebase Auth: {str(e)}")
            
            # Delete from Firestore
            try:
                users_ref = db.collection("Users")
                query = users_ref.where("emailID", "==", instance.assessor_user.email).limit(1)
                docs = query.get()
                if docs:
                    docs[0].reference.delete()
                    print(f"✓ Successfully deleted assessor from Firestore: {instance.assessor_user.email}")
                else:
                    print(f"⚠ Warning: No user document found in Firestore: {instance.assessor_user.email}")
            except Exception as e:
                print(f"✗ Error deleting from Firestore: {str(e)}")
        else:
            print(f"⚠ Warning: Assessor has no associated user")
            
    except Exception as e:
        print(f"✗ Error deleting assessor from Firebase: {str(e)}")
        import traceback
        traceback.print_exc()


def batch_sync_users_to_firebase_auth(users):
    # Firebase Auth doesn't support true batch operations, but we can optimize
    # by using a single connection and handling errors gracefully
    for user in users:
        try:
            fb_user = auth.get_user_by_email(user.email)
            # Update user
            auth.update_user(
                fb_user.uid,
                email=user.email,
                display_name=user.full_name,
                disabled=not user.is_active
            )
        except auth.UserNotFoundError:
            # Create user with a default password
            auth.create_user(
                email=user.email,
                display_name=user.full_name,
                password="DefaultPassword123!",  # You may want to handle this securely
                disabled=not user.is_active
            )

def batch_sync_users_to_firestore_with_progress(users, session_key, total_rows, skillathon_name=""):
    """
    Batch sync users to Firestore with real-time progress tracking
    """
    print(f"[DEBUG] Starting Firebase sync for {len(users)} users")
    try:
        from django.core.cache import cache
        
        # Update progress - Starting Firebase sync
        progress_data = cache.get(f"upload_progress:{session_key}")
        print(f"[DEBUG] Retrieved initial progress data from cache: {progress_data}")
        
        progress_data.update({
            'status': 'syncing_firebase',
            'message': 'Starting Firebase sync...',
            'progress': 30
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        print(f"[DEBUG] Updated progress to 30% for Firebase sync start")
        
        # Step 1: Batch write user documents (30% to 50%)
        print(f"[DEBUG] Starting batch write to Firestore...")
        learners_ids = []
        batch = db.batch()
        for i, user in enumerate(users):
            user_data = {
                "emailID": user.email,
                "name": user.full_name,
                "role": user.user_role,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
                "phone_number": user.phone_number,
                "username": user.email
            }
            
            doc_ref = db.collection("Users").document(str(user.id))
            batch.set(doc_ref, user_data)
            learners_ids.append(user.id)
            
            # Update progress every 10 users
            if (i + 1) % 10 == 0:
                progress = 30 + int((i + 1) / len(users) * 20)
                progress_data.update({
                    'message': f'Syncing user {i + 1} of {len(users)} to Firestore...',
                    'progress': progress
                })
                cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        
        # Commit the batch
        batch.commit()
        
        # Update progress - Batch commit completed
        progress_data.update({
            'message': 'Firestore batch commit completed. Updating learner data...',
            'progress': 50
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        
        # Step 2: Update learner data and create assignments (50% to 90%)
        for i, user in enumerate(users):
            try:
                learner = Learner.objects.get(learner_user=user)
                
                # Update progress for learner data sync
                progress = 50 + int((i + 1) / len(users) * 35)
                progress_data.update({
                    'message': f'Updating learner data for {learner.learner_user.full_name}...',
                    'progress': progress
                })
                cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
                
                # Debug print every 5 users
                if (i + 1) % 5 == 0 or i == 0:
                    print(f"[DEBUG] Processing learner {i + 1}/{len(users)}: {learner.learner_user.full_name}, Progress: {progress}%")
                
                # Find user document in Firestore
                users_ref = db.collection("Users")
                query = users_ref.where("emailID", "==", learner.learner_user.email).limit(1)
                docs = query.get()
                
                if docs:
                    # Update the first matching document with all learner data
                    user_data = {
                        "learner_type": learner.learner_type,
                        "speciality": learner.speciality,
                        "state": learner.state,
                        "district": learner.district,
                        "date_of_birth": learner.date_of_birth.isoformat() if learner.date_of_birth else None,
                        "certifications": learner.certifications,
                        "learner_gender": learner.learner_gender,
                        "skillathon_event": learner.skillathon_event.name if learner.skillathon_event else None,
                        "onboarding_type": learner.onboarding_type,
                        "institute": learner.college.name if learner.college else None,
                        "hospital": learner.hospital.name if learner.hospital else None,
                        "course": learner.course if learner.course else None,
                        "stream": learner.stream if learner.stream else None,
                        "year_of_study": learner.year_of_study if learner.year_of_study else None,
                        "designation": learner.designation if learner.designation else None,
                        "years_of_experience": learner.years_of_experience if learner.years_of_experience else None,
                        "educational_qualification": learner.educational_qualification if learner.educational_qualification else None,
                    }
                    
                    docs[0].reference.update(user_data)
                    
                    # Update progress for test/exam assignments
                    progress = 85 + int((i + 1) / len(users) * 5)
                    progress_data.update({
                        'message': f'Creating assignments for {learner.learner_user.full_name}...',
                        'progress': progress
                    })
                    cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
                    
                    # Create test and exam assignments
                    # create_test_and_exam_assignments(learner, learner.skillathon_event)
            
            except Learner.DoesNotExist:
                # User exists but no learner record - this is normal for some users
                continue
            except Exception as e:
                print(f"Error processing learner {user.email}: {e}")
                continue
        
        if skillathon_name:
            SchedularObject.objects.create(
                data=json.dumps({
                    "learner_ids": learners_ids,
                    "skillathon_name": skillathon_name
                })
            )
                
        # Update progress - Firebase sync completed
        progress_data.update({
            'message': 'Firebase sync completed successfully!',
            'progress': 90
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        
    except Exception as e:
        print(f"Firebase sync error: {e}")
        print(traceback.format_exc())
        
        # Update progress with error
        progress_data = cache.get(f"upload_progress:{session_key}")
        progress_data.update({
            'status': 'error',
            'message': f'Firebase sync error: {str(e)}',
            'progress': 100
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)