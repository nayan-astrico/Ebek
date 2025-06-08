import firebase_admin
from firebase_admin import auth, firestore
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
from django.conf import settings
from .models import EbekUser, Institution, Hospital, Learner, Assessor, SkillathonEvent, Group
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
import traceback
# Use the default app initialized in settings.py
db = firestore.client()

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

def create_test_and_exam_assignments(learner, skillathon_event):
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
                'institute': learner.college.name if learner.learner_type == 'student' else learner.hospital.name,
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
                "institute": instance.name
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
                "hospital": instance.name
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
    data = {
        "name": instance.name,
        "type": instance.type
    }
    
    db.collection("Groups").document(str(instance.id)).set(data)
    
    # Update group head's user record with group name
    if instance.group_head:
        # Find user document by email
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.group_head.email).limit(1)
        docs = query.get()
        
        if docs:
            # Update the first matching document
            user_data = {
                "group": instance.name
            }
            docs[0].reference.update(user_data)

@receiver(post_delete, sender=Group)
def on_group_delete(sender, instance, **kwargs):
    # Delete from Firestore
    db.collection("Groups").document(str(instance.id)).delete()
    
    # Delete group head user if exists
    if instance.group_head:
        # Delete from Firebase Auth
        try:
            fb_user = auth.get_user_by_email(instance.group_head.email)
            auth.delete_user(fb_user.uid)
        except auth.UserNotFoundError:
            pass
        
        # Delete from Firestore
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.group_head.email).limit(1)
        docs = query.get()
        if docs:
            docs[0].reference.delete()
        
        # Delete from Django admin
        User = get_user_model()
        try:
            user = User.objects.get(email=instance.group_head.email)
            user.delete()
        except User.DoesNotExist:
            pass

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
            # Update the first matching document with all learner data
            user_data = {
                "learner_type": instance.learner_type,
                "speciality": instance.speciality,
                "state": instance.state,
                "district": instance.district,
                "date_of_birth": instance.date_of_birth.isoformat() if instance.date_of_birth else None,
                "certifications": instance.certifications,
                "learner_gender": instance.learner_gender,
                "skillathon_event": instance.skillathon_event.name if instance.skillathon_event else None
            }
            
            # Add institution/hospital specific data
            if instance.learner_type == 'student' and instance.college:
                user_data["institution"] = instance.college.name
                user_data["course"] = instance.course
                user_data["stream"] = instance.stream
                user_data["year_of_study"] = instance.year_of_study
            elif instance.learner_type == 'nurse' and instance.hospital:
                user_data["hospital"] = instance.hospital.name
                user_data["designation"] = instance.designation
                user_data["years_of_experience"] = instance.years_of_experience
                user_data["educational_qualification"] = instance.educational_qualification
                user_data["educational_institution"] = instance.educational_institution
            
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
        query = users_ref.where("emailID", "==", instance.learner_user.email).limit(1)
        docs = query.get()
        if docs:
            docs[0].reference.delete()

# --- Assessor Sync ---
@receiver(post_save, sender=Assessor)
def on_assessor_save(sender, instance, created, **kwargs):
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
                "is_verifier": instance.is_verifier
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

@receiver(post_delete, sender=Assessor)
def on_assessor_delete(sender, instance, **kwargs):
    if instance.assessor_user:
        # Delete from Firebase Auth
        try:
            fb_user = auth.get_user_by_email(instance.assessor_user.email)
            auth.delete_user(fb_user.uid)
        except auth.UserNotFoundError:
            pass
        
        # Delete from Firestore
        users_ref = db.collection("Users")
        query = users_ref.where("emailID", "==", instance.assessor_user.email).limit(1)
        docs = query.get()
        if docs:
            docs[0].reference.delete()

def batch_sync_users_to_firestore(users):
    try:
        batch = db.batch()
        for user in users:
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
        batch.commit()
    
        for user in users:
            learner = Learner.objects.get(learner_user=user)
            print("INSIDE CREATE TEST AND EXAM ASSIGNMENTS")
            print(learner)
            print(learner.skillathon_event)

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
                    "skillathon_event": learner.skillathon_event.name if learner.skillathon_event else None
                }
                
                # Add institution/hospital specific data
                if learner.learner_type == 'student' and learner.college:
                    user_data["institution"] = learner.college.name
                    user_data["course"] = learner.course
                    user_data["stream"] = learner.stream
                    user_data["year_of_study"] = learner.year_of_study
                elif learner.learner_type == 'nurse' and learner.hospital:
                    user_data["hospital"] = learner.hospital.name
                    user_data["designation"] = learner.designation
                    user_data["years_of_experience"] = learner.years_of_experience
                    user_data["educational_qualification"] = learner.educational_qualification
                    user_data["educational_institution"] = learner.educational_institution
                
            docs[0].reference.update(user_data)
            create_test_and_exam_assignments(learner, learner.skillathon_event)
        
    except Exception as e:
        print(e)
        print(traceback.format_exc())

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