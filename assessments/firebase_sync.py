import firebase_admin
from firebase_admin import auth, firestore
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import EbekUser, Institution, Hospital, Learner, Assessor, SkillathonEvent, Group

# Use the default app initialized in settings.py
db = firestore.client()

def sync_user_to_firestore(user):
    user_data = {
        "emailID": user.email,
        "name": user.full_name,
        "role": user.user_role,
        "is_active": user.is_active,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "phone_number": user.phone_number,
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
        # Add other fields as needed
    }
    db.collection("InstituteNames").document(str(instance.id)).set(data)

@receiver(post_delete, sender=Institution)
def on_institute_delete(sender, instance, **kwargs):
    db.collection("InstituteNames").document(str(instance.id)).delete()

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

@receiver(post_delete, sender=Hospital)
def on_hospital_delete(sender, instance, **kwargs):
    db.collection("HospitalNames").document(str(instance.id)).delete()

# --- Group Sync ---
@receiver(post_save, sender=Group)
def on_group_save(sender, instance, created, **kwargs):
    data = {
        "name": instance.name,
        "type": instance.type
    }
    db.collection("Groups").document(str(instance.id)).set(data)

@receiver(post_delete, sender=Group)
def on_group_delete(sender, instance, **kwargs):
    db.collection("Groups").document(str(instance.id)).delete()