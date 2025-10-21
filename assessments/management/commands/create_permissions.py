from django.core.management.base import BaseCommand
from assessments.models import Permission, CustomRole
from assessments.constants import PERMISSIONS

class Command(BaseCommand):
    help = 'Populate all initial data (permissions and default roles)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n Starting data population...\n'))
        
        # Step 1: Create Permissions
        self.create_permissions()
        
        # Step 2: Create Default Roles with Permissions
        self.create_default_roles()
        
        self.stdout.write(self.style.SUCCESS('\n All data populated successfully!\n'))

    def create_permissions(self):
        """Create all permissions from constants.py"""
        self.stdout.write(self.style.WARNING(' Creating Permissions...'))
        
        def get_category(code):
            if 'report' in code:
                return 'Reports'
            elif 'course' in code:
                return 'Courses'
            elif 'batch' in code:
                return 'Batches'
            elif 'institute' in code:
                return 'Institutes'
            elif 'hospital' in code:
                return 'Hospitals'
            elif 'group' in code:
                return 'Groups'
            elif 'learner' in code:
                return 'Learners'
            elif 'assessor' in code:
                return 'Assessors'
            elif 'skillathon' in code:
                return 'Skillathons'
            elif 'assignment' in code:
                return 'Assignments'
            else:
                return 'General'
        
        created_count = 0
        existing_count = 0
        
        for code, name in PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'category': get_category(code),
                    'is_active': True,
                    'description': f'Permission to {name.lower()}'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Created: {name}')
            else:
                existing_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n Permissions: {created_count} created, {existing_count} already existed\n'
            )
        )

    def create_default_roles(self):
        """Create default roles based on constants.py role types"""
        self.stdout.write(self.style.WARNING(' Creating Default Roles...'))
        
        roles_config = [
            {
                'name': 'Super Admin',
                'description': 'Full system access - all permissions',
                'permissions': [perm[0] for perm in PERMISSIONS]  # All permissions
            },
            {
                'name': 'EBEK Admin',
                'description': 'EBEK administrative access',
                'permissions': [
                    'view_overall_report', 'view_candidate_report', 'download_candidate_report',
                    'view_courses', 'create_course', 'edit_course', 'delete_course', 'update_course_status',
                    'view_batches', 'create_batch', 'edit_batch', 'delete_batch',
                    'view_institutes', 'create_institute', 'edit_institute',
                    'view_hospitals', 'create_hospital', 'edit_hospital',
                    'view_groups', 'create_group', 'edit_group',
                    'view_learners', 'add_learner', 'edit_learner', 'bulk_upload_learners',
                    'view_assessors', 'add_assessor', 'edit_assessor',
                    'view_skillathons', 'add_skillathon', 'edit_skillathon',
                    'view_assignment', 'assign_assignment', 'edit_assignment'
                ]
            },
            {
                'name': 'Group Admin',
                'description': 'Manage group-level institutions and hospitals',
                'permissions': [
                    'view_institutes', 'create_institute', 'edit_institute',
                    'view_hospitals', 'create_hospital', 'edit_hospital',
                    'view_learners', 'add_learner', 'edit_learner', 'bulk_upload_learners',
                    'view_assessors', 'add_assessor', 'edit_assessor',
                    'view_batches', 'create_batch', 'edit_batch',
                    'view_courses'
                ]
            },
            {
                'name': 'Institute Admin',
                'description': 'Manage institute students and batches',
                'permissions': [
                    'view_institutes', 'edit_institute',
                    'view_learners', 'add_learner', 'edit_learner', 'bulk_upload_learners',
                    'view_batches', 'create_batch', 'edit_batch',
                    'add_learner_in_batch', 'remove_learner_from_batch',
                    'view_courses',
                    'view_candidate_report', 'download_candidate_report'
                ]
            },
            {
                'name': 'Hospital Admin',
                'description': 'Manage hospital staff and assessments',
                'permissions': [
                    'view_hospitals', 'edit_hospital',
                    'view_learners', 'add_learner', 'edit_learner',
                    'view_assessors', 'add_assessor', 'edit_assessor',
                    'view_batches', 'create_batch', 'edit_batch',
                    'view_courses',
                    'view_candidate_report', 'download_candidate_report'
                ]
            },
            {
                'name': 'Supervisor',
                'description': 'Assess learners and view reports',
                'permissions': [
                    'view_candidate_report',
                    'view_assignment',
                    'view_learners',
                    'view_courses'
                ]
            },
            {
                'name': 'Skillathon Admin',
                'description': 'Manage skillathon events and participants',
                'permissions': [
                    'view_skillathons', 'add_skillathon', 'edit_skillathon', 'delete_skillathon',
                    'view_learners', 'add_learner', 'edit_learner',
                    'view_assessors', 'add_assessor', 'edit_assessor',
                    'view_institutes', 'view_hospitals',
                    'view_assignment', 'assign_assignment',
                    'view_overall_report', 'view_candidate_report', 'download_candidate_report'
                ]
            },
            {
                'name': 'Report Viewer',
                'description': 'View and download reports only',
                'permissions': [
                    'view_overall_report',
                    'view_candidate_report',
                    'download_candidate_report'
                ]
            },
            {
                'name': 'Course Manager',
                'description': 'Manage courses and procedures',
                'permissions': [
                    'view_courses', 'create_course', 'edit_course', 'delete_course',
                    'update_course_status',
                    'view_batches',
                    'add_course_in_batch', 'remove_course_from_batch'
                ]
            },
            {
                'name': 'Batch Coordinator',
                'description': 'Manage batches and learner assignments',
                'permissions': [
                    'view_batches', 'create_batch', 'edit_batch', 'delete_batch',
                    'add_learner_in_batch', 'remove_learner_from_batch',
                    'add_course_in_batch', 'remove_course_from_batch',
                    'view_learners',
                    'view_courses'
                ]
            }
        ]
        
        created_count = 0
        existing_count = 0
        
        for role_config in roles_config:
            role, created = CustomRole.objects.get_or_create(
                name=role_config['name'],
                defaults={'description': role_config['description']}
            )
            
            if created or role.permissions.count() == 0:
                # Get permission objects
                perms = Permission.objects.filter(
                    code__in=role_config['permissions'],
                    is_active=True
                )
                role.permissions.set(perms)
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        f'  ✓ Created: {role_config["name"]} '
                        f'({perms.count()} permissions)'
                    )
                else:
                    self.stdout.write(
                        f'  ↻ Updated: {role_config["name"]} '
                        f'({perms.count()} permissions)'
                    )
            else:
                existing_count += 1
                self.stdout.write(
                    f'  ○ Exists: {role_config["name"]} '
                    f'({role.permissions.count()} permissions)'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n Roles: {created_count} created, {existing_count} already existed\n'
            )
        )