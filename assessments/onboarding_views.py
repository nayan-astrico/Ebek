import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Group, Institution, Hospital, Learner, Assessor, SkillathonEvent, EbekUser
from .onboarding_forms import (
    GroupForm, InstitutionForm, HospitalForm, LearnerForm,
    AssessorForm, SkillathonEventForm, BulkLearnerUploadForm
)
import csv
from django.http import HttpResponse, StreamingHttpResponse
from datetime import datetime
from django.contrib.auth import get_user_model
from assessments.utils_ses import send_email
import random
import string
from django.urls import reverse
import openpyxl
from django.shortcuts import render, redirect
from django.contrib import messages
from .onboarding_forms import LearnerForm
from .models import Learner, Institution, Hospital, SkillathonEvent
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from .firebase_sync import sync_user_to_firestore, sync_user_to_firebase_auth, batch_sync_users_to_firestore, batch_sync_users_to_firebase_auth, create_test_and_exam_assignments, DisableSignals, enable_all_signals
from django.db.models.signals import post_save, post_delete
from django.dispatch import Signal
from firebase_admin import firestore
import traceback
import json
import os
import uuid
from django.core.cache import cache
from .firebase_sync import (
    on_user_save, on_user_delete,
    on_institute_save, on_institution_delete,
    on_hospital_save, on_hospital_delete,
    on_learner_save, on_learner_delete,
    on_assessor_save, on_assessor_delete,
    on_skillathon_save, on_skillathon_delete,
    on_group_save, on_group_delete, batch_sync_users_to_firestore_with_progress
)


# Group Views
@login_required
def group_list(request):
    groups = Group.objects.all().order_by('-created_at')
    
    # Get filter values as lists
    selected_groups = request.GET.getlist('group')
    selected_types = request.GET.getlist('type')
    selected_statuses = request.GET.getlist('status')
    
    # Apply filters
    if selected_groups:
        groups = groups.filter(id__in=selected_groups)
    if selected_types:
        groups = groups.filter(type__in=selected_types)
    if selected_statuses:
        active_status = [status.lower() == 'active' for status in selected_statuses]
        groups = groups.filter(is_active__in=active_status)
    
    # Convert selected IDs to integers for template comparison
    selected_groups = [int(x) for x in selected_groups] if selected_groups else []
    
    paginator = Paginator(groups, 10)
    page = request.GET.get('page')
    groups = paginator.get_page(page)
    
    return render(request, 'assessments/onboarding/group_list.html', {
        'groups': groups,
        'all_groups': Group.objects.all(),
        'selected_groups': selected_groups,
        'selected_types': selected_types,
        'selected_statuses': selected_statuses,
    })

@login_required
def group_create(request):
    User = get_user_model()
    print("group_create")
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            print("form is valid")
            # Extract group head info
            head_name = form.cleaned_data['group_head_name']
            head_email = form.cleaned_data['group_head_email']
            head_phone = form.cleaned_data['group_head_phone']
            group_name = form.cleaned_data['name']
            print(form.cleaned_data)
            user = None
            # Check if user exists
            if head_name == '' or head_email == '' or head_phone == '':
                pass
            else:
                try:
                    user = User.objects.get(email=head_email)
                    # Update name and phone if changed
                    updated = False
                    if user.full_name != head_name:
                        user.full_name = head_name
                        updated = True
                    if user.phone_number != head_phone:
                        user.phone_number = head_phone
                        updated = True
                    if updated:
                        user.save()
                    created = False
                except User.DoesNotExist:
                    print("User does not exist")
                    user = User.objects.create(
                        email=head_email,
                        full_name=head_name,
                        phone_number=head_phone,
                        is_active=True
                    )
                    # Set default password
                    default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    user.set_password(default_password)
                    user.save()
                    # Send email with credentials
                    reset_link = request.build_absolute_uri(
                        reverse('login')
                    )
                    print(reset_link)
                    subject = 'Your Group Admin Account Created'
                    body = f"""Dear {head_name},\n\nYour group admin account has been created for the group {group_name}.\n\nUsername: {head_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                    send_email(subject, body, [head_email])
                    created = True
            # Create group and assign group_head
            group = form.save(commit=False)
            if user is not None:
                group.group_head = user
            
            group.is_active = request.POST.get('is_active') == 'on'
            group.save()
            messages.success(request, 'Group created successfully.')
            return HttpResponse('OK')
    else:
        form = GroupForm()
    return render(request, 'assessments/onboarding/group_form.html', {'form': form, 'action': 'Create'})

@login_required
def group_edit(request, pk):
    User = get_user_model()
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            head_name = form.cleaned_data['group_head_name']
            head_email = form.cleaned_data['group_head_email']
            head_phone = form.cleaned_data['group_head_phone']
            group_name = form.cleaned_data['name']
            current_head = group.group_head
            if head_name != "" and head_email != "" and head_phone != "":
                if not current_head or current_head.email != head_email:
                    user, created = User.objects.get_or_create(
                        email=head_email,
                        defaults={
                            'is_active': True,
                        }
                    )
                    if created:
                        user.full_name = head_name
                        user.phone_number = head_phone
                        default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        user.set_password(default_password)
                        user.save()
                        reset_link = request.build_absolute_uri(reverse('login'))
                        subject = 'Your Group Admin Account Created'
                        body = f"""Dear {head_name},\n\nYour group admin account has been created for the group {group_name}.\n\nUsername: {head_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                        send_email(subject, body, [head_email])
                    else:
                        updated = False
                        if user.full_name != head_name:
                            user.full_name = head_name
                            updated = True
                        if user.phone_number != head_phone:
                            user.phone_number = head_phone
                            updated = True
                        if updated:
                            user.save()
                    group.group_head = user
                else:
                    updated = False
                    if current_head.full_name != head_name:
                        current_head.full_name = head_name
                        updated = True
                    if current_head.phone_number != head_phone:
                        current_head.phone_number = head_phone
                        updated = True
                    if updated:
                        current_head.save()
            group = form.save(commit=False)
            group.save()
            messages.success(request, 'Group updated successfully.')
            return HttpResponse('OK')
    else:
        form = GroupForm(instance=group, initial={
            'group_head_name': group.group_head.full_name if group.group_head else '',
            'group_head_email': group.group_head.email if group.group_head else '',
            'group_head_phone': group.group_head.phone_number if group.group_head else '',
        })
    return render(request, 'assessments/onboarding/group_form.html', {'form': form, 'action': 'Edit'})

@login_required
def group_delete(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Group deleted successfully.')
        return redirect('group_list')
    return redirect('group_list')

# Institution Views
@login_required
def institution_list(request):
    institutions = Institution.objects.all().order_by('-created_at')
    
    # Get filter values as lists
    selected_groups = request.GET.getlist('group')
    selected_institutions = request.GET.getlist('institution')
    selected_states = request.GET.getlist('state')
    selected_statuses = request.GET.getlist('status')
    
    # Apply filters
    if selected_groups:
        institutions = institutions.filter(group_id__in=selected_groups)
    if selected_institutions:
        institutions = institutions.filter(id__in=selected_institutions)
    if selected_states:
        institutions = institutions.filter(state__in=selected_states)
    if selected_statuses:
        active_status = [status.lower() == 'active' for status in selected_statuses]
        institutions = institutions.filter(is_active__in=active_status)
    
    # Convert selected IDs to integers for template comparison
    selected_groups = [int(x) for x in selected_groups] if selected_groups else []
    selected_institutions = [int(x) for x in selected_institutions] if selected_institutions else []
    
    paginator = Paginator(institutions, 10)
    page = request.GET.get('page')
    institutions = paginator.get_page(page)
    
    # Get unique states for filter
    all_states = Institution.objects.values_list('state', flat=True).distinct()
    
    return render(request, 'assessments/onboarding/institution_list.html', {
        'institutions': institutions,
        'groups': Group.objects.all(),
        'all_institutions': Institution.objects.all(),
        'all_states': all_states,
        'selected_groups': selected_groups,
        'selected_institutions': selected_institutions,
        'selected_states': selected_states,
        'selected_statuses': selected_statuses,
    })

@login_required
def institution_create(request):
    print("institution_create")
    print("heree")
    User = get_user_model()
    print(request.method)
    if request.method == 'POST':

        form = InstitutionForm(request.POST)
        if form.is_valid():
            print("form is valid")
            head_name = form.cleaned_data['unit_head_name']
            head_email = form.cleaned_data['unit_head_email']
            head_phone = form.cleaned_data['unit_head_phone']
            institution_name = form.cleaned_data['name']
            user = None
            if head_name == '' or head_email == '' or head_phone == '':
                pass
            else:
                user, created = User.objects.get_or_create(
                    email=head_email,
                    defaults={
                        'is_active': True,
                    }
                )
                if created:
                    user.full_name = head_name
                    user.phone_number = head_phone
                    default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    user.set_password(default_password)
                    user.save()
                    reset_link = request.build_absolute_uri(reverse('login'))
                    subject = 'Your Unit Head Account Created'
                    body = f"""Dear {head_name},\n\nYour unit head account has been created for the institution {institution_name}.\n\nUsername: {head_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                    send_email(subject, body, [head_email])
                else:
                    # Update name/phone if changed
                    updated = False
                    if user.full_name != head_name:
                        user.full_name = head_name
                        updated = True
                    if user.phone_number != head_phone:
                        user.phone_number = head_phone
                        updated = True
                    if updated:
                        user.save()
            institution = form.save(commit=False)
            if user is not None:
                institution.unit_head = user
            institution.is_active = request.POST.get('is_active') == 'on'
            institution.save()
            messages.success(request, 'Institution created successfully.')
            return HttpResponse('OK')
    else:
        form = InstitutionForm()
    return render(request, 'assessments/onboarding/institution_form.html', {'form': form, 'action': 'Create'})

@login_required
def institution_edit(request, pk):
    User = get_user_model()
    institution = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        form = InstitutionForm(request.POST, instance=institution)
        if form.is_valid():
            head_name = form.cleaned_data['unit_head_name']
            head_email = form.cleaned_data['unit_head_email']
            head_phone = form.cleaned_data['unit_head_phone']
            institution_name = form.cleaned_data['name']
            current_head = institution.unit_head
            if head_name != "" and head_email != "" and head_phone != "":
                if not current_head or current_head.email != head_email:
                    user, created = User.objects.get_or_create(
                        email=head_email,
                        defaults={
                            'is_active': True,
                        }
                    )
                    if created:
                        user.full_name = head_name
                        user.phone_number = head_phone
                        default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        user.set_password(default_password)
                        user.save()
                        reset_link = request.build_absolute_uri(reverse('login'))
                        subject = 'Your Unit Head Account Created'
                        body = f"""Dear {head_name},\n\nYour unit head account has been created for the institution {institution_name}.\n\nUsername: {head_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                        send_email(subject, body, [head_email])
                    else:
                        updated = False
                        if user.full_name != head_name:
                            user.full_name = head_name
                            updated = True
                        if user.phone_number != head_phone:
                            user.phone_number = head_phone
                            updated = True
                        if updated:
                            user.save()
                    institution.unit_head = user
                else:
                    updated = False
                    if current_head.full_name != head_name:
                        current_head.full_name = head_name
                        updated = True
                    if current_head.phone_number != head_phone:
                        current_head.phone_number = head_phone
                        updated = True
                    if updated:
                        current_head.save()
            institution = form.save(commit=False)
            institution.save()
            messages.success(request, 'Institution updated successfully.')
            return HttpResponse('OK')
    else:
        form = InstitutionForm(instance=institution, initial={
            'unit_head_name': institution.unit_head.full_name if institution.unit_head else '',
            'unit_head_email': institution.unit_head.email if institution.unit_head else '',
            'unit_head_phone': institution.unit_head.phone_number if institution.unit_head else '',
        })
    return render(request, 'assessments/onboarding/institution_form.html', {'form': form, 'action': 'Edit'})

@login_required
def institution_delete(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        institution.delete()
        messages.success(request, 'Institution deleted successfully.')
        return redirect('institution_list')
    return redirect('institution_list')

# Hospital Views
@login_required
def hospital_list(request):
    hospitals = Hospital.objects.all().order_by('-created_at')
    
    # Get filter values as lists
    selected_groups = request.GET.getlist('group')
    selected_hospitals = request.GET.getlist('hospital')
    selected_states = request.GET.getlist('state')
    selected_statuses = request.GET.getlist('status')
    
    # Apply filters
    if selected_groups:
        hospitals = hospitals.filter(group_id__in=selected_groups)
    if selected_hospitals:
        hospitals = hospitals.filter(id__in=selected_hospitals)
    if selected_states:
        hospitals = hospitals.filter(state__in=selected_states)
    if selected_statuses:
        active_status = [status.lower() == 'active' for status in selected_statuses]
        hospitals = hospitals.filter(is_active__in=active_status)
    
    # Convert selected IDs to integers for template comparison
    selected_groups = [int(x) for x in selected_groups] if selected_groups else []
    selected_hospitals = [int(x) for x in selected_hospitals] if selected_hospitals else []
    
    paginator = Paginator(hospitals, 10)
    page = request.GET.get('page')
    hospitals = paginator.get_page(page)
    
    # Get unique states for filter
    all_states = Hospital.objects.values_list('state', flat=True).distinct()
    
    return render(request, 'assessments/onboarding/hospital_list.html', {
        'hospitals': hospitals,
        'groups': Group.objects.all(),
        'all_hospitals': Hospital.objects.all(),
        'all_states': all_states,
        'selected_groups': selected_groups,
        'selected_hospitals': selected_hospitals,
        'selected_states': selected_states,
        'selected_statuses': selected_statuses,
    })

@login_required
def hospital_create(request):
    User = get_user_model()
    if request.method == 'POST':
        form = HospitalForm(request.POST)
        if form.is_valid():
            head_name = form.cleaned_data['unit_head_name']
            head_email = form.cleaned_data['unit_head_email']
            head_phone = form.cleaned_data['unit_head_phone']
            hospital_name = form.cleaned_data['name']
            user = None
            if head_name == '' or head_email == '' or head_phone == '':
                pass
            else:
                user, created = User.objects.get_or_create(
                    email=head_email,
                    defaults={
                        'is_active': True,
                    }
                )
                if created:
                    user.full_name = head_name
                    user.phone_number = head_phone
                    default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    user.set_password(default_password)
                    user.save()
                    reset_link = request.build_absolute_uri(reverse('login'))
                    subject = 'Your Unit Head Account Created'
                    body = f"""Dear {head_name},\n\nYour unit head account has been created for the hospital {hospital_name}.\n\nUsername: {head_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                    send_email(subject, body, [head_email])
                else:
                    # Update name/phone if changed
                    updated = False
                    if user.full_name != head_name:
                        user.full_name = head_name
                        updated = True
                    if user.phone_number != head_phone:
                        user.phone_number = head_phone
                        updated = True
                    if updated:
                        user.save()
            hospital = form.save(commit=False)
            if user is not None:
                hospital.unit_head = user
            hospital.is_active = request.POST.get('is_active') == 'on'
            hospital.save()
            messages.success(request, 'Hospital created successfully.')
            return HttpResponse('OK')
    else:
        form = HospitalForm()
    return render(request, 'assessments/onboarding/hospital_form.html', {'form': form, 'action': 'Create'})

@login_required
def hospital_edit(request, pk):
    User = get_user_model()
    hospital = get_object_or_404(Hospital, pk=pk)
    if request.method == 'POST':
        form = HospitalForm(request.POST, instance=hospital)
        if form.is_valid():
            head_name = form.cleaned_data['unit_head_name']
            head_email = form.cleaned_data['unit_head_email']
            head_phone = form.cleaned_data['unit_head_phone']
            hospital_name = form.cleaned_data['name']
            current_head = hospital.unit_head
            if head_name != "" and head_email != "" and head_phone != "":
                if not current_head or current_head.email != head_email:
                    user, created = User.objects.get_or_create(
                        email=head_email,
                        defaults={
                            'is_active': True,
                        }
                    )
                    if created:
                        user.full_name = head_name
                        user.phone_number = head_phone
                        default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        user.set_password(default_password)
                        user.save()
                        reset_link = request.build_absolute_uri(reverse('login'))
                        subject = 'Your Unit Head Account Created'
                        body = f"""Dear {head_name},\n\nYour unit head account has been created for the hospital {hospital_name}.\n\nUsername: {head_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                        send_email(subject, body, [head_email])
                    else:
                        updated = False
                        if user.full_name != head_name:
                            user.full_name = head_name
                            updated = True
                        if user.phone_number != head_phone:
                            user.phone_number = head_phone
                            updated = True
                        if updated:
                            user.save()
                    hospital.unit_head = user
                else:
                    updated = False
                    if current_head.full_name != head_name:
                        current_head.full_name = head_name
                        updated = True
                    if current_head.phone_number != head_phone:
                        current_head.phone_number = head_phone
                        updated = True
                    if updated:
                        current_head.save()
            hospital = form.save(commit=False)
            hospital.save()
            messages.success(request, 'Hospital updated successfully.')
            return HttpResponse('OK')
    else:
        form = HospitalForm(instance=hospital, initial={
            'unit_head_name': hospital.unit_head.full_name if hospital.unit_head else '',
            'unit_head_email': hospital.unit_head.email if hospital.unit_head else '',
            'unit_head_phone': hospital.unit_head.phone_number if hospital.unit_head else '',
        })
    return render(request, 'assessments/onboarding/hospital_form.html', {'form': form, 'action': 'Edit'})

@login_required
def hospital_delete(request, pk):
    hospital = get_object_or_404(Hospital, pk=pk)
    if request.method == 'POST':
        hospital.delete()
        messages.success(request, 'Hospital deleted successfully.')
        return redirect('hospital_list')
    return redirect('hospital_list')

# Learner Views
@login_required
def learner_list(request):
    learners = Learner.objects.all().order_by('-created_at')
    
    # Get filter values as lists
    selected_institutions = request.GET.getlist('institution')
    selected_hospitals = request.GET.getlist('hospital')
    selected_learner_types = request.GET.getlist('learner_type')
    
    # Apply filters
    if selected_institutions:
        learners = learners.filter(college_id__in=selected_institutions)
    if selected_hospitals:
        learners = learners.filter(hospital_id__in=selected_hospitals)
    if selected_learner_types:
        learners = learners.filter(learner_type__in=selected_learner_types)
    
    # Convert selected IDs to integers for template comparison
    selected_institutions = [int(x) for x in selected_institutions] if selected_institutions else []
    selected_hospitals = [int(x) for x in selected_hospitals] if selected_hospitals else []
    
    paginator = Paginator(learners, 10)
    page = request.GET.get('page')
    learners = paginator.get_page(page)
    
    return render(request, 'assessments/onboarding/learner_list.html', {
        'learners': learners,
        'institutions': Institution.objects.all(),
        'hospitals': Hospital.objects.all(),
        'selected_institutions': selected_institutions,
        'selected_hospitals': selected_hospitals,
        'selected_learner_types': selected_learner_types,
    })

@login_required
def learner_create(request):
    User = get_user_model()
    if request.method == 'POST':
        form = LearnerForm(request.POST)
        if form.is_valid():
            learner_name = form.cleaned_data['learner_name']
            learner_email = form.cleaned_data['learner_email']
            learner_phone = form.cleaned_data['learner_phone']

            if learner_name == '' or learner_email == '' or learner_phone == '':
                pass
            else:
                user, created = User.objects.get_or_create(
                    email=learner_email,
                    defaults={
                        'is_active': True,
                    }
                )
                if created:
                    user.full_name = learner_name
                    user.phone_number = learner_phone
                    default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    user.set_password(default_password)
                    user.save()
                    # reset_link = request.build_absolute_uri(reverse('login'))
                    # subject = 'Your Learner Account Created'
                    # body = f"""Dear {learner_name},\n\nYour learner account has been created.\n\nUsername: {learner_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                    # send_email(subject, body, [learner_email])
                else:
                    # Update name/phone if changed
                    updated = False
                    if user.full_name != learner_name:
                        user.full_name = learner_name
                        updated = True
                    if user.phone_number != learner_phone:
                        user.phone_number = learner_phone
                        updated = True
                    if updated:
                        user.save()
            
            learner = form.save(commit=False)
            if user is not None:
                learner.learner_user = user
            learner.save()
            
            # Create test and exam assignments if skillathon is assigned
            create_test_and_exam_assignments(learner, learner.skillathon_event)
            
            messages.success(request, 'Learner created successfully.')
            return HttpResponse('OK')
    else:
        form = LearnerForm()
    return render(request, 'assessments/onboarding/learner_form.html', {'form': form, 'action': 'Create'})

@login_required
def learner_edit(request, pk):
    User = get_user_model()
    learner = get_object_or_404(Learner, pk=pk)
    if request.method == 'POST':
        form = LearnerForm(request.POST, instance=learner)
        if form.is_valid():
            learner_name = form.cleaned_data['learner_name']
            learner_email = form.cleaned_data['learner_email']
            learner_phone = form.cleaned_data['learner_phone']
            current_user = learner.learner_user
            
            if not current_user or current_user.email != learner_email:
                user, created = User.objects.get_or_create(
                    email=learner_email,
                    defaults={
                        'is_active': True,
                    }
                )
                if created:
                    user.full_name = learner_name
                    user.phone_number = learner_phone
                    default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    user.set_password(default_password)
                    user.save()
                    # reset_link = request.build_absolute_uri(reverse('login'))
                    # subject = 'Your Learner Account Created'
                    # body = f"""Dear {learner_name},\n\nYour learner account has been created.\n\nUsername: {learner_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                    # send_email(subject, body, [learner_email])
                else:
                    updated = False
                    if user.full_name != learner_name:
                        user.full_name = learner_name
                        updated = True
                    if user.phone_number != learner_phone:
                        user.phone_number = learner_phone
                        updated = True
                    if updated:
                        user.save()
            else:
                updated = False
                if current_user.full_name != learner_name:
                    current_user.full_name = learner_name
                    updated = True
                if current_user.phone_number != learner_phone:
                    current_user.phone_number = learner_phone
                    updated = True
                if updated:
                    current_user.save()
            
            learner = form.save(commit=False)
            learner.save()
            
            # Create test and exam assignments if skillathon is assigned
            create_test_and_exam_assignments(learner, learner.skillathon_event)
            
            messages.success(request, 'Learner updated successfully.')
            return HttpResponse('OK')
    else:
        form = LearnerForm(instance=learner, initial={
            'learner_name': learner.learner_user.full_name,
            'learner_email': learner.learner_user.email,
            'learner_phone': learner.learner_user.phone_number,
        })
    return render(request, 'assessments/onboarding/learner_form.html', {'form': form, 'action': 'Edit'})

@login_required
def learner_bulk_upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({
                'success': False,
                'error': 'No file uploaded'
            })
            
        if not file.name.endswith('.xlsx'):
            return JsonResponse({
                'success': False,
                'error': 'Please upload a valid Excel (.xlsx) file'
            })

        try:
            # Generate unique session key for this upload
            session_key = str(uuid.uuid4())
            
            # Save file temporarily
            file_name = f"{uuid.uuid4()}_{file.name}".replace(" ", "_")
            file_path = os.path.join('media', 'uploaded_excels', file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # Initialize progress
            progress_data = {
                'status': 'starting',
                'message': 'Reading Excel file...',
                'progress': 0,
                'total_rows': 0,
                'processed_rows': 0,
                'success_count': 0,
                'update_count': 0,
                'error_count': 0,
                'errors': []
            }
            cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
            
            # Start background processing in a separate thread
            print(f"[DEBUG] Starting background thread for session: {session_key}")
            background_thread = threading.Thread(
                target=process_bulk_upload_with_progress,
                args=(file_path, session_key),
                daemon=True
            )
            background_thread.start()
            print(f"[DEBUG] Background thread started for session: {session_key}")
            
            return JsonResponse({
                'success': True,
                'session_key': session_key,
                'message': 'Upload started. You can track progress in real-time.'
            })

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': f'Error processing file: {str(e)}'
            })

    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

def process_bulk_upload_with_progress(file_path, session_key):
    """
    Process bulk upload with real-time progress tracking
    """
    print(f"[DEBUG] Starting bulk upload process for session: {session_key}")
    print(f"[DEBUG] File path: {file_path}")
    print(f"[DEBUG] Thread ID: {threading.current_thread().ident}")
    print(f"[DEBUG] Thread name: {threading.current_thread().name}")
    
    try:
        # Update progress - Reading file
        progress_data = {
            'status': 'reading',
            'message': 'Reading Excel file...',
            'progress': 5,
            'total_rows': 0,
            'processed_rows': 0,
            'success_count': 0,
            'update_count': 0,
            'error_count': 0,
            'errors': []
        }
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        print(f"[DEBUG] Initial progress set: {progress_data}")
        
        # Load Excel file
        print(f"[DEBUG] Loading Excel file...")
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        print(f"[DEBUG] Excel file loaded successfully")

        # Define header mapping
        header_map = {
            'Onboarding Type': 'onboarding_type',
            'Learner Type': 'learner_type',
            'Learner Name': 'learner_name',
            'Learner Email': 'learner_email',
            'Learner Phone': 'learner_phone',
            'College': 'college',
            'Course': 'course',
            'Stream': 'stream',
            'Year of Study': 'year_of_study',
            'Hospital': 'hospital',
            'Designation': 'designation',
            'Years of Experience': 'years_of_experience',
            'Educational Qualification': 'educational_qualification',
            'Educational Institution': 'educational_institution',
            'Speciality': 'speciality',
            'State': 'state',
            'District': 'district',
            'Pincode': 'pincode',
            'Address': 'address',
            'Date of Birth': 'date_of_birth',
            'Certifications': 'certifications',
            'Learner Gender': 'learner_gender',
            'Skillathon Event': 'skillathon_event',
        }

        # Read headers
        headers = [cell.value for cell in ws[1]]
        
        # Validate headers
        missing_headers = []
        for excel_col, form_field in header_map.items():
            if excel_col not in headers:
                missing_headers.append(excel_col)
        
        if missing_headers:
            progress_data.update({
                'status': 'error',
                'message': f'Missing required columns: {", ".join(missing_headers)}',
                'progress': 100
            })
            cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
            return
        
        # Get all rows and filter out empty ones
        print(f"[DEBUG] Reading rows from Excel...")
        all_rows = list(ws.iter_rows(min_row=2, values_only=True))
        print(f"[DEBUG] Total rows in Excel: {len(all_rows)}")
        
        non_empty_rows = [
            (idx, row) for idx, row in enumerate(all_rows, start=2)
            if any(cell is not None and str(cell).strip() for cell in row)
        ]
        
        total_rows = len(non_empty_rows)
        print(f"[DEBUG] Non-empty rows: {total_rows}")
        
        # Update progress - Validating data
        progress_data.update({
            'status': 'validating',
            'message': 'Validating data...',
            'progress': 10,
            'total_rows': total_rows
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        print(f"[DEBUG] Progress updated to 10%: {progress_data}")
        
        success_count = 0
        update_count = 0
        error_rows = []
        User = get_user_model()
        users_to_sync = []
        
        # Disable signals during bulk creation
        print(f"[DEBUG] Starting Django processing loop...")
        with DisableSignals((post_save, Learner), (post_save, EbekUser)):
            for idx, (row_idx, row) in enumerate(non_empty_rows):
                try:
                    # Update progress for Django processing (10% to 30%)
                    progress = 10 + int((idx / total_rows) * 20)
                    progress_data.update({
                        'status': 'processing_django',
                        'message': f'Processing row {idx + 1} of {total_rows}...',
                        'progress': progress,
                        'processed_rows': idx + 1
                    })
                    cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
                    
                    # Debug print every 5 rows
                    if (idx + 1) % 5 == 0 or idx == 0:
                        print(f"[DEBUG] Processing row {idx + 1}/{total_rows}, Progress: {progress}%")
                    
                    row_data = dict(zip(headers, row))
                    
                    # Prepare form data
                    form_data = {}
                    for excel_col, form_field in header_map.items():
                        value = row_data.get(excel_col)
                        
                        if value is not None:
                            value = str(value).strip()
                            if value:
                                # Handle ForeignKeys by name
                                if form_field == 'college' and value:
                                    try:
                                        form_data['college'] = Institution.objects.get(name=value).id
                                    except Institution.DoesNotExist:
                                        form_data['college'] = None
                                elif form_field == 'hospital' and value:
                                    try:
                                        form_data['hospital'] = Hospital.objects.get(name=value).id
                                    except Hospital.DoesNotExist:
                                        form_data['hospital'] = None
                                else:
                                    form_data[form_field] = value
                                
                                if form_field == 'onboarding_type' and value:
                                    form_data['onboarding_type'] = value.lower()
                                
                                if form_field == 'learner_gender' and value:
                                    form_data['learner_gender'] = value.lower()
                                
                                if form_field == 'skillathon_event' and value:
                                    try:
                                        form_data['skillathon_event'] = SkillathonEvent.objects.get(name=value.strip()).id
                                    except SkillathonEvent.DoesNotExist:
                                        form_data['skillathon_event'] = None
                    
                    # Add required user fields
                    form_data['learner_name'] = row_data.get('Learner Name', '').strip()
                    form_data['learner_email'] = row_data.get('Learner Email', '').strip()
                    form_data['learner_phone'] = str(row_data.get('Learner Phone', '')).strip()[:10]
                    
                    # Skip if required fields are empty
                    if not all([form_data['learner_name'], form_data['learner_email'], form_data['learner_phone']]):
                        error_rows.append({
                            'row': row_idx,
                            'errors': {'__all__': ['Name, email and phone are required']}
                        })
                        continue
                    
                    form = LearnerForm(form_data)
                    if form.is_valid():
                        # Check if learner already exists
                        existing_learner = Learner.objects.filter(
                            learner_user__email=form.cleaned_data['learner_email'],
                            learner_user__full_name=form.cleaned_data['learner_name'],
                            learner_user__phone_number=form.cleaned_data['learner_phone']
                        ).first()
                        
                        if existing_learner:
                            # Update existing learner
                            for field, value in form.cleaned_data.items():
                                if field != 'learner_user':
                                    setattr(existing_learner, field, value)
                            existing_learner.save()
                            update_count += 1
                            users_to_sync.append(existing_learner.learner_user)
                        else:
                            # Create new learner
                            email = form.cleaned_data['learner_email']
                            full_name = form.cleaned_data['learner_name']
                            phone = form.cleaned_data['learner_phone']
                            user, created = User.objects.get_or_create(
                                email=email,
                                defaults={'full_name': full_name, 'phone_number': phone, 'is_active': True}
                            )
                            if not created:
                                # Update name/phone if changed
                                updated = False
                                if user.full_name != full_name:
                                    user.full_name = full_name
                                    updated = True
                                if user.phone_number != phone:
                                    user.phone_number = phone
                                    updated = True
                                if updated:
                                    user.save()
                                    users_to_sync.append(user)
                            else:
                                # Set default password for new users
                                default_password = 'Success@123$'
                                user.set_password(default_password)
                                user.save()
                                users_to_sync.append(user)
                            
                            learner = form.save(commit=False)
                            learner.learner_user = user
                            learner.save()
                            success_count += 1
                            
                    else:
                        error_rows.append({
                            'row': row_idx,
                            'errors': form.errors
                        })
                        
                except Exception as e:
                    error_rows.append({
                        'row': row_idx,
                        'errors': {'__all__': [f'Processing error: {str(e)}']}
                    })
        
        # Reconnect signals
        reconnect_all_signals()
        print(f"[DEBUG] Django processing completed. Success: {success_count}, Updates: {update_count}, Errors: {len(error_rows)}")
        
        # Update progress for Firebase sync (30% to 90%)
        progress_data.update({
            'status': 'syncing_firebase',
            'message': 'Syncing with Firebase...',
            'progress': 30,
            'success_count': success_count,
            'update_count': update_count,
            'error_count': len(error_rows)
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        print(f"[DEBUG] Progress updated to 30% for Firebase sync: {progress_data}")
        
        # Batch sync all users to Firebase with progress tracking
        if users_to_sync:
            print(f"[DEBUG] Starting Firebase sync for {len(users_to_sync)} users...")
            batch_sync_users_to_firestore_with_progress(users_to_sync, session_key, total_rows)
        else:
            print(f"[DEBUG] No users to sync to Firebase")
        
        # Final progress update
        progress_data.update({
            'status': 'completed',
            'message': f'Successfully imported {success_count} new learners and updated {update_count} existing learners.',
            'progress': 100,
            'success_count': success_count,
            'update_count': update_count,
            'error_count': len(error_rows),
            'errors': error_rows if error_rows else None
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        print(f"[DEBUG] Final progress set to 100%: {progress_data}")
        print(f"[DEBUG] Bulk upload process completed for session: {session_key}")
        
    except Exception as e:
        # Handle any unexpected errors
        progress_data.update({
            'status': 'error',
            'message': f'Error processing file: {str(e)}',
            'progress': 100
        })
        cache.set(f"upload_progress:{session_key}", progress_data, timeout=3600)
        print(f"Bulk upload error: {e}")
        print(traceback.format_exc())
        print(f"[DEBUG] Bulk upload process failed for session: {session_key}")

@login_required
def upload_progress_stream(request, session_key):
    """
    SSE endpoint for real-time upload progress
    """
    print(f"[DEBUG] SSE connection started for session: {session_key}")
    print(f"[DEBUG] Request method: {request.method}")
    print(f"[DEBUG] Request user: {request.user}")
    
    def event_stream():
        print(f"[DEBUG] Event stream function started")
        while True:
            # Get progress from cache
            progress_data = cache.get(f"upload_progress:{session_key}")
            print(f"[DEBUG] Retrieved progress data: {progress_data}")
            
            if not progress_data:
                # No progress data found
                print(f"[DEBUG] No progress data found for session: {session_key}")
                yield f"data: {json.dumps({'error': 'No progress data found'})}\n\n"
                break
            
            # Send progress data
            yield f"data: {json.dumps(progress_data)}\n\n"
            print(f"[DEBUG] Sent progress data: {progress_data.get('progress', 'N/A')}%")
            
            # If completed or error, stop streaming
            if progress_data.get('status') in ['completed', 'error']:
                print(f"[DEBUG] Upload {progress_data.get('status')}, stopping SSE stream")
                break
                        
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

@login_required
def learner_delete(request, pk):
    learner = get_object_or_404(Learner, pk=pk)
    if request.method == 'POST':
        learner.delete()
        messages.success(request, 'Learner deleted successfully.')
        return redirect('learner_list')
    return redirect('learner_list')

# Assessor Views
@login_required
def assessor_list(request):
    assessors = Assessor.objects.all().order_by('-created_at')
    
    # Get filter values as lists
    selected_specialities = request.GET.getlist('speciality')
    selected_statuses = request.GET.getlist('status')
    
    # Apply filters
    if selected_specialities:
        assessors = assessors.filter(specialization__in=selected_specialities)
    if selected_statuses:
        active_status = [status.lower() == 'active' for status in selected_statuses]
        assessors = assessors.filter(is_active__in=active_status)
    
    paginator = Paginator(assessors, 10)
    page = request.GET.get('page')
    assessors = paginator.get_page(page)
    
    # Get unique specialities for filter
    all_specialities = Assessor.objects.values_list('specialization', flat=True).distinct()
    
    return render(request, 'assessments/onboarding/assessor_list.html', {
        'assessors': assessors,
        'all_specialities': all_specialities,
        'selected_specialities': selected_specialities,
        'selected_statuses': selected_statuses,
    })

@login_required
def assessor_create(request):
    User = get_user_model()
    if request.method == 'POST':
        form = AssessorForm(request.POST)
        if form.is_valid():
            assessor_name = form.cleaned_data['assessor_name']
            assessor_email = form.cleaned_data['assessor_email']
            assessor_phone = form.cleaned_data['assessor_phone']
            
            user, created = User.objects.get_or_create(
                email=assessor_email,
                defaults={
                    'is_active': True,
                }
            )
            if created:
                user.full_name = assessor_name
                user.phone_number = assessor_phone
                default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                user.set_password(default_password)
                user.save()
                reset_link = request.build_absolute_uri(reverse('login'))
                subject = 'Your Assessor Account Created'
                body = f"""Dear {assessor_name},\n\nYour assessor account has been created.\n\nUsername: {assessor_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                send_email(subject, body, [assessor_email])
            else:
                # Update name/phone if changed
                updated = False
                if user.full_name != assessor_name:
                    user.full_name = assessor_name
                    updated = True
                if user.phone_number != assessor_phone:
                    user.phone_number = assessor_phone
                    updated = True
                if updated:
                    user.save()
            
            assessor = form.save(commit=False)
            assessor.assessor_user = user
            assessor.save()
            messages.success(request, 'Assessor created successfully.')
            return HttpResponse('OK')
    else:
        form = AssessorForm()
    return render(request, 'assessments/onboarding/assessor_form.html', {'form': form, 'action': 'Create'})

@login_required
def assessor_edit(request, pk):
    User = get_user_model()
    assessor = get_object_or_404(Assessor, pk=pk)
    if request.method == 'POST':
        form = AssessorForm(request.POST, instance=assessor)
        user = None
        if form.is_valid():
            assessor_name = form.cleaned_data['assessor_name']
            assessor_email = form.cleaned_data['assessor_email']
            assessor_phone = form.cleaned_data['assessor_phone']
            current_user = assessor.assessor_user

            if assessor_name != "" and assessor_email != "" and assessor_phone != "":
            
                if not current_user or current_user.email != assessor_email:
                    user, created = User.objects.get_or_create(
                        email=assessor_email,
                        defaults={
                            'is_active': True,
                        }
                    )
                    if created:
                        user.full_name = assessor_name
                        user.phone_number = assessor_phone
                        default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        user.set_password(default_password)
                        user.save()
                        reset_link = request.build_absolute_uri(reverse('login'))
                        subject = 'Your Assessor Account Created'
                        body = f"""Dear {assessor_name},\n\nYour assessor account has been created.\n\nUsername: {assessor_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                        send_email(subject, body, [assessor_email])
                    else:
                        updated = False
                        if user.full_name != assessor_name:
                            user.full_name = assessor_name
                            updated = True
                        if user.phone_number != assessor_phone:
                            user.phone_number = assessor_phone
                            updated = True
                        if updated:
                            user.save()
                    assessor.assessor_user = user
                else:
                    updated = False
                    if current_user.full_name != assessor_name:
                        current_user.full_name = assessor_name
                        updated = True
                    if current_user.phone_number != assessor_phone:
                        current_user.phone_number = assessor_phone
                        updated = True
                    if updated:
                        current_user.save()
            
            assessor = form.save(commit=False)
            assessor.save()
            messages.success(request, 'Assessor updated successfully.')
            return HttpResponse('OK')
    else:
        form = AssessorForm(instance=assessor, initial={
            'assessor_name': assessor.assessor_user.full_name,
            'assessor_email': assessor.assessor_user.email,
            'assessor_phone': assessor.assessor_user.phone_number,
        })
    return render(request, 'assessments/onboarding/assessor_form.html', {'form': form, 'action': 'Edit'})

@login_required
def assessor_delete(request, pk):
    assessor = get_object_or_404(Assessor, pk=pk)
    if request.method == 'POST':
        assessor.delete()
        messages.success(request, 'Assessor deleted successfully.')
        return redirect('assessor_list')
    return redirect('assessor_list')

# Skillathon Event Views
@login_required
def skillathon_list(request):
    events = SkillathonEvent.objects.all().order_by('-date')
    
    # Filtering
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    location = request.GET.get('location')
    
    if status:
        events = events.filter(status=status)
    if date_from:
        events = events.filter(date__gte=date_from)
    if date_to:
        events = events.filter(date__lte=date_to)
    if location:
        events = events.filter(Q(state__icontains=location) | Q(city__icontains=location))
    
    paginator = Paginator(events, 10)
    page = request.GET.get('page')
    events = paginator.get_page(page)
    
    return render(request, 'assessments/onboarding/skillathon_list.html', {'events': events})

@login_required
def skillathon_create(request):
    if request.method == 'POST':
        form = SkillathonEventForm(request.POST)
        if form.is_valid():
            event = form.save()
            messages.success(request, 'Skillathon event created successfully.')
            return HttpResponse('OK')
    else:
        form = SkillathonEventForm()
    return render(request, 'assessments/onboarding/skillathon_form.html', {'form': form, 'action': 'Create'})

@login_required
def skillathon_edit(request, pk):
    event = get_object_or_404(SkillathonEvent, pk=pk)
    if request.method == 'POST':
        form = SkillathonEventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skillathon event updated successfully.')
            return HttpResponse('OK')
    else:
        form = SkillathonEventForm(instance=event)
    return render(request, 'assessments/onboarding/skillathon_form.html', {'form': form, 'action': 'Edit'}) 

@login_required
def skillathon_delete(request, pk):
    event = get_object_or_404(SkillathonEvent, pk=pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Skillathon event deleted successfully.')
        return redirect('skillathon_list')
    return redirect('skillathon_list')

def reconnect_all_signals():
    post_save.connect(on_user_save, sender=EbekUser)
    post_delete.connect(on_user_delete, sender=EbekUser)
    post_save.connect(on_institute_save, sender=Institution)
    post_delete.connect(on_institution_delete, sender=Institution)
    post_save.connect(on_hospital_save, sender=Hospital)
    post_delete.connect(on_hospital_delete, sender=Hospital)
    post_save.connect(on_learner_save, sender=Learner)
    post_delete.connect(on_learner_delete, sender=Learner)
    post_save.connect(on_assessor_save, sender=Assessor)
    post_delete.connect(on_assessor_delete, sender=Assessor)
    post_save.connect(on_skillathon_save, sender=SkillathonEvent)
    post_delete.connect(on_skillathon_delete, sender=SkillathonEvent)
    post_save.connect(on_group_save, sender=Group)
    post_delete.connect(on_group_delete, sender=Group)
    print("All signals have been reconnected.")