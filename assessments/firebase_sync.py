import firebase_admin
from firebase_admin import auth, firestore
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
from django.conf import settings
from .models import EbekUser, Institution, Hospital, Learner, Assessor, SkillathonEvent, Group
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

# Use the default app initialized in settings.py
db = firestore.client()

class DisableSignals:
    def __init__(self, signal):
        self.signal = signal
        self.receivers = []

    def __enter__(self):
        self.receivers = self.signal.receivers
        self.signal.receivers = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.signal.receivers = self.receivers

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