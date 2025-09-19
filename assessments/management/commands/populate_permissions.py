from django.core.management.base import BaseCommand
from assessments.models import Permission
from assessments.constants import PERMISSIONS

class Command(BaseCommand):
    help = 'Populate Permission model with data from constants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing permissions before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Permission.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Cleared all existing permissions')
            )

        created_count = 0
        updated_count = 0

        for permission_code, permission_name in PERMISSIONS:
            # Determine category based on permission code
            category = self.get_category_from_code(permission_code)
            
            permission, created = Permission.objects.get_or_create(
                code=permission_code,
                defaults={
                    'name': permission_name,
                    'category': category,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created permission: {permission_name}')
                )
            else:
                # Update existing permission if needed
                if permission.name != permission_name or permission.category != category:
                    permission.name = permission_name
                    permission.category = category
                    permission.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated permission: {permission_name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed permissions. Created: {created_count}, Updated: {updated_count}'
            )
        )

    def get_category_from_code(self, code):
        """Determine category based on permission code"""
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
        elif 'skillathon' in code:
            return 'Skillathons'
        elif 'learner' in code:
            return 'Learners'
        elif 'assessor' in code:
            return 'Assessors'
        elif 'assignment' in code:
            return 'Assignments'
        else:
            return 'General'
