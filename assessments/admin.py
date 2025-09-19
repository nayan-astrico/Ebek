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


admin.site.register(EbekUser)

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

class ExamAssignmentAdmin(admin.ModelAdmin):
    list_display = ('learner', 'procedure_name', 'exam_assignment_id', 'created_at')
    search_fields = ('learner', 'procedure_name', 'exam_assignment_id')
    readonly_fields = ('exam_assignment_id', 'created_at')

admin.site.register(ExamAssignment, ExamAssignmentAdmin)

admin.site.register(SchedularObject)

class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('code', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('category', 'name')

admin.site.register(Permission, PermissionAdmin)

class CustomRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'permissions_count', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('permissions',)
    
    def permissions_count(self, obj):
        return obj.permissions.count()
    permissions_count.short_description = 'Permissions Count'

admin.site.register(CustomRole, CustomRoleAdmin)