from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Group, Institution, Hospital, Learner, Assessor, SkillathonEvent
from .onboarding_forms import (
    GroupForm, InstitutionForm, HospitalForm, LearnerForm,
    AssessorForm, SkillathonEventForm, BulkLearnerUploadForm
)
import csv
from django.http import HttpResponse
from datetime import datetime
from django.contrib.auth import get_user_model
from assessments.utils_ses import send_email
import random
import string
from django.urls import reverse

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
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            # Extract group head info
            head_name = form.cleaned_data['group_head_name']
            head_email = form.cleaned_data['group_head_email']
            head_phone = form.cleaned_data['group_head_phone']
            group_name = form.cleaned_data['name']
            print(form.cleaned_data)
            # Check if user exists
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
            group.group_head = user
            group.is_active = request.POST.get('is_active') == 'on'
            group.save()
            messages.success(request, 'Group created successfully.')
            return redirect('group_list')
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
            return redirect('group_list')
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
    User = get_user_model()
    if request.method == 'POST':
        form = InstitutionForm(request.POST)
        if form.is_valid():
            head_name = form.cleaned_data['unit_head_name']
            head_email = form.cleaned_data['unit_head_email']
            head_phone = form.cleaned_data['unit_head_phone']
            institution_name = form.cleaned_data['name']
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
            institution.unit_head = user
            institution.is_active = request.POST.get('is_active') == 'on'
            institution.save()
            messages.success(request, 'Institution created successfully.')
            return redirect('institution_list')
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
            return redirect('institution_list')
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
            hospital.unit_head = user
            hospital.is_active = request.POST.get('is_active') == 'on'
            hospital.save()
            messages.success(request, 'Hospital created successfully.')
            return redirect('hospital_list')
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
            return redirect('hospital_list')
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
                reset_link = request.build_absolute_uri(reverse('login'))
                subject = 'Your Learner Account Created'
                body = f"""Dear {learner_name},\n\nYour learner account has been created.\n\nUsername: {learner_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                send_email(subject, body, [learner_email])
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
            learner.learner_user = user
            learner.save()
            messages.success(request, 'Learner created successfully.')
            return redirect('learner_list')
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
                    reset_link = request.build_absolute_uri(reverse('login'))
                    subject = 'Your Learner Account Created'
                    body = f"""Dear {learner_name},\n\nYour learner account has been created.\n\nUsername: {learner_email}\nPassword: {default_password}\n\nPlease log in to the platform using the link below and change your password after first login. Click the link to login: {reset_link}\n\nRegards,\nTeam"""
                    send_email(subject, body, [learner_email])
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
            messages.success(request, 'Learner updated successfully.')
            return redirect('learner_list')
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
        form = BulkLearnerUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    Learner.objects.create(
                        onboarding_type=row['onboarding_type'],
                        full_name=row['full_name'],
                        email=row['email'],
                        mobile_number=row['mobile_number'],
                        learner_type=row['learner_type'],
                        # Add other fields as needed
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    messages.error(request, f'Error in row {success_count + error_count}: {str(e)}')
            
            messages.success(request, f'Successfully imported {success_count} learners.')
            if error_count > 0:
                messages.warning(request, f'Failed to import {error_count} learners.')
            
            return redirect('learner_list')
    else:
        form = BulkLearnerUploadForm()
    return render(request, 'assessments/onboarding/learner_bulk_upload.html', {'form': form})

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
            return redirect('assessor_list')
    else:
        form = AssessorForm()
    return render(request, 'assessments/onboarding/assessor_form.html', {'form': form, 'action': 'Create'})

@login_required
def assessor_edit(request, pk):
    User = get_user_model()
    assessor = get_object_or_404(Assessor, pk=pk)
    if request.method == 'POST':
        form = AssessorForm(request.POST, instance=assessor)
        if form.is_valid():
            assessor_name = form.cleaned_data['assessor_name']
            assessor_email = form.cleaned_data['assessor_email']
            assessor_phone = form.cleaned_data['assessor_phone']
            current_user = assessor.assessor_user
            
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
            return redirect('assessor_list')
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
            return redirect('skillathon_list')
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
            return redirect('skillathon_list')
    else:
        form = SkillathonEventForm(instance=event)
    return render(request, 'assessments/onboarding/skillathon_form.html', {'form': form, 'action': 'Edit'}) 