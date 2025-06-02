from django.contrib import admin
from .models import *
# Register your models here
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import EbekUser
from .forms import EbekUserCreationForm, EbekUserChangeForm

# assessments/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import EbekUser
from .forms import EbekUserCreationForm, EbekUserChangeForm

class EbekUserAdmin(BaseUserAdmin):
    form = EbekUserChangeForm
    add_form = EbekUserCreationForm

    list_display = ('email', 'is_staff', 'is_active', 'user_role')
    list_filter = ('is_staff', 'is_active', 'user_role')
    fieldsets = (
        (None, {'fields': ('email', 'password', 'full_name', 'phone_number')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Personal info', {'fields': ('user_role', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'user_role', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)

admin.site.register(EbekUser, EbekUserAdmin)

admin.site.register(PasswordResetToken)

class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'group_id', 'is_active', 'created_at')
    list_filter = ('type', 'is_active')
    search_fields = ('name', 'group_id')
    readonly_fields = ('group_id', 'created_at', 'updated_at')

admin.site.register(Group, GroupAdmin)

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'institute_id', 'is_active', 'created_at')
    list_filter = ('group', 'is_active')
    search_fields = ('name', 'institute_id')
    readonly_fields = ('institute_id', 'created_at', 'updated_at')

admin.site.register(Institution, InstitutionAdmin)

class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'hospital_id', 'is_active', 'created_at')
    list_filter = ('group', 'is_active')
    search_fields = ('name', 'hospital_id')
    readonly_fields = ('hospital_id', 'created_at', 'updated_at')

admin.site.register(Hospital, HospitalAdmin)

class LearnerAdmin(admin.ModelAdmin):
    list_display = ('learner_user', 'learner_id', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('learner_user', 'learner_id')
    readonly_fields = ('learner_id', 'created_at', 'updated_at')

admin.site.register(Learner, LearnerAdmin)

class AssessorAdmin(admin.ModelAdmin):
    list_display = ('assessor_user', 'assessor_id', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('assessor_user', 'assessor_id')
    readonly_fields = ('assessor_id', 'created_at', 'updated_at')

admin.site.register(Assessor, AssessorAdmin)

class SkillathonEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'state', 'city', 'created_at')
    search_fields = ('name', 'date', 'state', 'city')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(SkillathonEvent, SkillathonEventAdmin)