from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Add your protected URLs here
        self.protected_urls = [
            '/create_assessment/',  # Example URL
            '/upload_excel/',    # Example URL
            '/procedures/',
            '/assign_assessment/',
            '/fetch-institutes/',
            '/fetch-cohorts/',
            '/fetch-assessors/',
            '/fetch-procedures/',
            '/exam-reports/',
            '/fetch-exam-reports/',
            '/fetch-exam-metrics/',
            '/fetch-student-metrics/',
            '/fetch-particular-student/',
            '/institutes/',
            '/institutes/create/',
            '/users/upload-excel/',
            '/users/create/',
            '/users/',
            '/users/edit/',
            '/cohorts/',
            '/cohorts/create/',
            '/cohorts/fetch-institute-students/',
            '/cohorts/<str:cohort_id>/add-student/',
            '/cohorts/<str:cohort_id>/view-students/',
            '/cohorts/<str:cohort_id>/get-students/',
            '/onboarding/groups/',
            '/onboarding/groups/create/',
            '/onboarding/groups/<int:pk>/edit/',
            '/onboarding/groups/<int:pk>/delete/',
            '/onboarding/',
            # Add more URLs that require authentication
        ]

    def __call__(self, request):
        # Check if the current path is in protected URLs
        if request.path in self.protected_urls:
            # Check if user is not authenticated
            if not request.user.is_authenticated:
                # Redirect to login page
                return redirect('login_page')  # Make sure 'login' is the name of your login URL pattern
        
        response = self.get_response(request)
        return response 