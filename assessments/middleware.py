from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import reverse


class CheckInactiveUserMiddleware:
    """
    Middleware to check if user is authenticated and active.
    - Redirects unauthenticated users to logout page
    - Redirects inactive authenticated users to logout page
    - Excludes logout page from middleware checks to avoid redirect loops
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"[MIDDLEWARE] Called for path: {request.path}")
        print(f"[MIDDLEWARE] User authenticated: {request.user.is_authenticated}")

        # Get URLs to exclude from middleware checks
        login_page_url = reverse('login_page')
        login_url = reverse('login')
        logout_url = reverse('logout')

        # Skip middleware for login and logout pages to avoid redirect loops
        if request.path in [login_page_url, login_url, logout_url]:
            print(f"[MIDDLEWARE] Skipping middleware for {request.path}")
            response = self.get_response(request)
            return response

        # Check if user is authenticated
        if request.user.is_authenticated:
            print("[MIDDLEWARE] Inside authenticated block")

            # Refresh user from database to get latest is_active status
            # The session might have cached the old user object
            try:
                from assessments.models import EbekUser
                fresh_user = EbekUser.objects.get(pk=request.user.pk)
                print(f"[MIDDLEWARE] Fresh user is_active: {fresh_user.is_active}")

                # Check if user has been marked inactive
                if not fresh_user.is_active:
                    # Log out the inactive user and redirect to login page
                    print("User is inactive, logging out")
                    logout(request)
                    print("Redirecting to login page")
                    return redirect('login_page')
            except EbekUser.DoesNotExist:
                # User was deleted, log them out
                print("User not found, logging out")
                logout(request)
                return redirect('login_page')
        else:
            # User is not authenticated, redirect to login page
            print("[MIDDLEWARE] User not authenticated, redirecting to login page")
            return redirect('login_page')

        response = self.get_response(request)
        return response
