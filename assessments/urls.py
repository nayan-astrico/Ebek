from django.urls import path
from . import views

urlpatterns = [
    path('create_assessment/', views.create_assessment, name='create_assessment'),
    path('upload_excel/', views.upload_excel_view, name='upload_excel'),
    path('procedures/<str:procedure_id>/<str:action>/', views.ProcedureAPIView.as_view(), name='procedure_api'),
    path('assign_assessment/', views.assign_assessment, name='assign_assessment'),
    path('fetch-institutes/', views.fetch_institutes, name='fetch-institutes'),
    path('fetch-cohorts/', views.fetch_cohorts, name='fetch-cohorts'),
    path('fetch-assessors/', views.fetch_assessors, name='fetch-assessors'),
    path('fetch-procedures/', views.fetch_procedures, name='fetch-procedures'),
    path('create-procedure-assignment-and-test/', views.create_procedure_assignment_and_test, name='create-procedure-assignment-and-test')
]
