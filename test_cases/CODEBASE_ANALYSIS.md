# EBEK OSCE Platform - Codebase Analysis

**Document Version:** 1.0
**Date Created:** November 29, 2025
**Purpose:** Comprehensive reference guide for understanding the EBEK codebase structure, models, endpoints, and test coverage

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Architecture](#project-architecture)
3. [Database Models](#database-models)
4. [API Endpoints](#api-endpoints)
5. [Views & Controllers](#views--controllers)
6. [Authentication & Authorization](#authentication--authorization)
7. [Firebase Integration](#firebase-integration)
8. [URL Routing](#url-routing)
9. [Management Commands](#management-commands)
10. [Test Coverage by Feature](#test-coverage-by-feature)

---

## Project Overview

**Project Name:** EBEK OSCE Platform
**Framework:** Django 5.2.3
**Database:** PostgreSQL (dev) / SQLite (prod)
**Real-time Database:** Firebase Firestore
**API Framework:** Django REST Framework
**Caching:** Redis
**Authentication:** Email-based custom user model

**Purpose:** EBEK is a comprehensive Objective Structured Clinical Examination (OSCE) management platform for healthcare education, managing learners (students and nurses), assessors, institutions, hospitals, and skillathon events with deep Firebase/Firestore integration.

**Key Features:**
- User authentication and role-based access control
- Multi-tenant architecture (institutions and hospitals)
- OSCE exam management (creation, assignment, evaluation)
- Real-time data synchronization with Firebase
- Pre-computed analytics and reporting
- Bulk learner import and management
- Assessment workflow and scoring
- Performance metrics and analytics

---

## Project Architecture

### 1. Application Structure

```
Ebek/
├── ebek_django_app/          # Main project settings
│   ├── settings.py           # Django configuration, Firebase init
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py
├── assessments/              # Main app (single-app architecture)
│   ├── models.py            # 14+ Django models
│   ├── views.py             # 160+ view functions (8,748 lines)
│   ├── onboarding_views.py  # Onboarding CRUD operations (2,888 lines)
│   ├── forms.py             # Django forms
│   ├── onboarding_forms.py  # Forms for onboarding entities
│   ├── middleware.py         # CheckInactiveUserMiddleware
│   ├── firebase_sync.py      # Firestore synchronization
│   ├── urls.py              # URL patterns (160+ routes)
│   ├── constants.py         # Roles and permissions definitions
│   ├── management/commands/ # Management commands
│   │   └── process_metric_queue.py  # Analytics pre-computation
│   ├── templates/           # HTML templates
│   └── static/             # CSS, JavaScript, images
├── test_cases/              # Test case documentation
│   ├── functional_test_cases.py     # Test case definitions
│   ├── generate_excel.py            # Excel generation script
│   ├── EBEK_Functional_Test_Cases.xlsx  # Test case spreadsheet
│   ├── EXECUTION_GUIDE.md           # Testing instructions
│   └── CODEBASE_ANALYSIS.md         # This file
├── media/                   # User uploads
├── logs/                    # Application logs
├── CLAUDE.md               # Development guide
├── DEPLOYMENT_GUIDE.md     # Deployment documentation
├── requirements.txt        # Python dependencies
└── manage.py              # Django management script
```

### 2. Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | Django | 5.2.3 |
| API Framework | Django REST Framework | 3.14.0 |
| Database | PostgreSQL / SQLite | Latest |
| Real-time DB | Firebase Firestore | Latest |
| Authentication | Firebase Admin SDK | Latest |
| Caching | Redis | Latest |
| Python Version | Python | 3.8+ |
| Task Queue | Celery (optional) | Latest |
| Email | AWS SES | Via utils_ses.py |

### 3. Key Design Patterns

**Dual-Database Architecture:**
- Django models for CRUD operations and complex queries
- Firebase Firestore for real-time data and analytics
- Signal-based synchronization: model changes → auto-sync to Firestore

**Role-Based Access Control (RBAC):**
- 9 built-in roles + custom role support
- 45+ granular permissions
- User-level and group-level access control

**Pre-Computed Analytics:**
- MetricUpdateQueue in Firestore
- Async processing via process_metric_queue.py
- Results cached in SemesterMetrics and UnitMetrics

**Multi-Tenant Design:**
- Institutions and Hospitals as primary tenants
- Data filtering by user's associated institutions/hospitals
- Group management for organizing multiple institutions

---

## Database Models

### Core Models (14+ total)

#### 1. **EbekUser** (assessments/models.py)
Custom user model extending AbstractBaseUser
- **Fields:**
  - `email` (unique, USERNAME_FIELD)
  - `username` (optional)
  - `first_name`, `last_name`
  - `is_active`, `is_staff`, `is_superuser`
  - `user_role` (ForeignKey → CustomRole)
  - `phone_number`, `address`
  - `date_joined`, `last_login`
- **Relationships:**
  - M2M: `groups` (Django groups)
  - M2M: `user_permissions_custom` (CustomPermission)
  - M2M: `institutions` (Institution)
  - M2M: `hospitals` (Hospital)
  - M2M: `skillathon_events` (SkillathonEvent)
  - M2M: `additional_access` (for shared access)
- **Methods:**
  - `has_all_permissions()` - Check if admin
  - `get_all_permissions()` - Get permission list
  - `check_icon_navigation_permissions(tab_name)` - Check UI tab access
- **Signals:** Firestore sync on create/update/delete

#### 2. **PasswordResetToken** (assessments/models.py)
Handles password reset functionality
- **Fields:**
  - `user` (ForeignKey → EbekUser)
  - `token` (unique)
  - `created_at`, `expires_at`
  - `is_used` (boolean)
- **Purpose:** Secure password reset via email tokens

#### 3. **Group** (assessments/models.py)
Organizational grouping of institutions/hospitals
- **Fields:**
  - `group_id` (UUID, auto-generated)
  - `group_name` (unique)
  - `description`
  - `group_head` (ForeignKey → EbekUser, optional)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - 1-M: `institutions` (Institution)
  - 1-M: `hospitals` (Hospital)
  - M2M: `members` (EbekUser, optional)
- **Signals:** Auto-assign group_head to `group_admin` role on save

#### 4. **Institution** (assessments/models.py)
College/educational institution
- **Fields:**
  - `institute_id` (UUID, auto-generated)
  - `institute_name` (unique)
  - `institute_type` (choices: college, university)
  - `group` (ForeignKey → Group)
  - `unit_head` (ForeignKey → EbekUser, optional)
  - `email`, `phone_number`
  - `address`, `city`, `state`, `country`
  - `postal_code`, `website`
  - `strength` (integer)
  - `active` (boolean)
  - `created_at`, `updated_at`
  - `state_code`, `district_code`
  - `academic_year`, `semester`
- **Relationships:**
  - FK: `group` (Group)
  - 1-M: `learners` (Learner with college=this)
  - 1-M: `courses` (Course)
  - 1-M: `batches` (Batch)
  - M2M: `members` (EbekUser)
- **Signals:** Auto-assign unit_head to `institute_admin` role on save

#### 5. **Hospital** (assessments/models.py)
Hospital organization
- **Fields:**
  - `hospital_id` (UUID, auto-generated)
  - `hospital_name` (unique)
  - `group` (ForeignKey → Group)
  - `hospital_head` (ForeignKey → EbekUser, optional)
  - `email`, `phone_number`
  - `address`, `city`, `state`, `country`
  - `postal_code`, `website`
  - `strength` (integer)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `group` (Group)
  - 1-M: `learners` (Learner with hospital=this)
- **Signals:** Auto-assign hospital_head to `hospital_admin` role

#### 6. **Learner** (assessments/models.py)
Student or nurse learner
- **Fields:**
  - `learner_id` (UUID, auto-generated)
  - `enrollment_number` (unique per institution/hospital)
  - `learner_user` (ForeignKey → EbekUser)
  - `college` (ForeignKey → Institution, optional)
  - `hospital` (ForeignKey → Hospital, optional)
  - `learner_type` (choices: student, nurse)
  - `learner_gender` (choices: male, female, other)
  - `phone_number`, `email`
  - `semester`, `batch_name`
  - `skillathon_event` (ForeignKey → SkillathonEvent, optional)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `learner_user` (EbekUser)
  - FK: `college` (Institution)
  - FK: `hospital` (Hospital)
  - 1-M: `exam_assignments` (ExamAssignment)
- **Signals:** Create associated EbekUser on creation

#### 7. **Assessor** (assessments/models.py)
Healthcare professional evaluating learners
- **Fields:**
  - `assessor_id` (UUID, auto-generated)
  - `assessor_user` (ForeignKey → EbekUser)
  - `assessor_name` (auto-filled)
  - `institution` (ForeignKey → Institution, optional)
  - `hospital` (ForeignKey → Hospital, optional)
  - `phone_number`, `email`
  - `specialty`, `experience_years`
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `assessor_user` (EbekUser)
  - FK: `institution` (Institution)
  - FK: `hospital` (Hospital)
  - 1-M: `exam_assignments` (ExamAssignment)
- **Signals:** Create associated EbekUser on creation

#### 8. **SkillathonEvent** (assessments/models.py)
Special assessment event
- **Fields:**
  - `event_id` (UUID)
  - `event_name` (unique)
  - `institution` (ForeignKey → Institution)
  - `description`, `date`, `location`
  - `max_participants` (integer)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `institution` (Institution)
  - M2M: `learners` (Learner)
  - 1-M: `exam_assignments` (with type=skillathon)

#### 9. **Course** (assessments/models.py)
Educational course containing procedures
- **Fields:**
  - `course_id` (UUID)
  - `course_name` (unique)
  - `institution` (ForeignKey → Institution)
  - `semester`, `academic_year`
  - `description`, `course_code`
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `institution` (Institution)
  - 1-M: `procedures` (Procedure via course field)
  - 1-M: `batches` (Batch)
- **Signals:** Cascade delete procedures on course delete

#### 10. **Batch** (assessments/models.py)
Group of learners for a course
- **Fields:**
  - `batch_id` (UUID)
  - `batch_name` (unique per course)
  - `course` (ForeignKey → Course)
  - `institution` (ForeignKey → Institution)
  - `start_date`, `end_date`
  - `description`
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `course` (Course)
  - FK: `institution` (Institution)
  - M2M: `learners` (Learner)
  - 1-M: `exam_assignments` (ExamAssignment)

#### 11. **Procedure** (assessments/models.py)
Clinical procedure being assessed
- **Fields:**
  - `procedure_id` (UUID)
  - `procedure_name` (unique per course)
  - `course` (ForeignKey → Course)
  - `description`, `steps`
  - `duration_minutes` (integer)
  - `marks_total` (decimal)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `course` (Course)
  - 1-M: `exam_assignments` (ExamAssignment)

#### 12. **ExamAssignment** (assessments/models.py)
Assignment of exam/procedure to learner with assessor
- **Fields:**
  - `id` (UUID)
  - `learner` (ForeignKey → Learner)
  - `procedure` (ForeignKey → Procedure)
  - `assessor` (ForeignKey → Assessor)
  - `batch` (ForeignKey → Batch, optional)
  - `type_of_event` (choices: mock, final, classroom, skillathon)
  - `skillathon_name` (CharField, optional)
  - `exam_date`, `exam_time`
  - `status` (choices: scheduled, in_progress, completed, cancelled)
  - `marks_obtained` (decimal)
  - `feedback` (text)
  - `created_at`, `updated_at`
- **Relationships:**
  - FK: `learner` (Learner)
  - FK: `procedure` (Procedure)
  - FK: `assessor` (Assessor)
  - FK: `batch` (Batch)

#### 13. **Permission** (assessments/models.py)
Granular permission definitions
- **Fields:**
  - `permission_id` (UUID)
  - `permission_code` (unique)
  - `permission_name` (description)
  - `category` (choices: view, create, edit, delete, export, etc.)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Count:** 45+ permissions defined in constants.py

#### 14. **CustomRole** (assessments/models.py)
User role definition
- **Fields:**
  - `role_id` (UUID)
  - `role_name` (unique)
  - `description`
  - `permissions` (M2M → Permission)
  - `active` (boolean)
  - `created_at`, `updated_at`
- **Built-in Roles (9):**
  - `super_admin` - Full system access
  - `ebek_admin` - EBEK platform admin
  - `group_admin` - Manages groups
  - `institute_admin` - Manages institutions
  - `hospital_admin` - Manages hospitals
  - `supervisor` - External assessor
  - `student` - Learner (student)
  - `nurse` - Learner (nurse)
  - `visitor` - Limited guest access

#### 15. **SchedularObject** (assessments/models.py)
Scheduled task/event
- **Fields:**
  - `id` (UUID)
  - `task_type`, `task_data` (JSON)
  - `scheduled_at`, `executed_at`
  - `status` (choices: pending, running, completed, failed)

---

## API Endpoints

### 1. Authentication Endpoints (assessments/views.py)

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/login/` | GET, POST | `login_view()` | User login with email/password |
| `/logout/` | GET | `logout_view()` | User logout, session cleanup |
| `/forgot-password/` | GET, POST | `forgot_password()` | Request password reset email |
| `/reset-password/<token>/` | GET, POST | `reset_password()` | Reset password via token |
| `/api/check-auth/` | GET | `check_auth()` | Verify current session |

### 2. Onboarding Endpoints (assessments/onboarding_views.py)

**Group Management:**
- GET `/onboarding/groups/` - List groups
- POST `/onboarding/groups/create/` - Create group
- GET `/onboarding/groups/<pk>/edit/` - Edit group
- POST `/onboarding/groups/<pk>/update/` - Save group
- DELETE `/onboarding/groups/<pk>/delete/` - Delete group

**Institution Management:**
- GET `/onboarding/institutions/` - List institutions
- POST `/onboarding/institutions/create/` - Create institution
- GET `/onboarding/institutions/<pk>/edit/` - Edit institution
- POST `/onboarding/institutions/<pk>/update/` - Save institution
- DELETE `/onboarding/institutions/<pk>/delete/` - Delete institution
- POST `/onboarding/institutions/<pk>/toggle-status/` - Toggle active/inactive

**Hospital Management:**
- GET `/onboarding/hospitals/` - List hospitals
- POST `/onboarding/hospitals/create/` - Create hospital
- GET `/onboarding/hospitals/<pk>/edit/` - Edit hospital
- POST `/onboarding/hospitals/<pk>/update/` - Save hospital
- DELETE `/onboarding/hospitals/<pk>/delete/` - Delete hospital
- POST `/onboarding/hospitals/<pk>/toggle-status/` - Toggle active/inactive

**Learner Management:**
- GET `/onboarding/learners/` - List learners
- POST `/onboarding/learners/create/` - Create learner
- GET `/onboarding/learners/<pk>/edit/` - Edit learner
- POST `/onboarding/learners/<pk>/update/` - Save learner
- DELETE `/onboarding/learners/<pk>/delete/` - Delete learner
- POST `/onboarding/learners/<pk>/toggle-status/` - Toggle learner active/inactive
- POST `/onboarding/learners/bulk-upload/` - Upload CSV with learners
- GET `/onboarding/learners/get-upload-sessions/` - Get bulk upload progress
- POST `/onboarding/learners/delete-multiple/` - Bulk delete learners

**Assessor Management:**
- GET `/onboarding/assessors/` - List assessors
- POST `/onboarding/assessors/create/` - Create assessor
- GET `/onboarding/assessors/<pk>/edit/` - Edit assessor
- POST `/onboarding/assessors/<pk>/update/` - Save assessor
- DELETE `/onboarding/assessors/<pk>/delete/` - Delete assessor

**Course Management:**
- GET `/course-management/` - List courses
- POST `/course-create/` - Create course
- GET `/course-edit/<pk>/` - Edit course
- POST `/course-update/<pk>/` - Save course
- DELETE `/course-delete/<pk>/` - Delete course
- POST `/course/<pk>/toggle-status/` - Toggle course active/inactive

**Batch Management:**
- GET `/batch-management/` - List batches
- POST `/batch-create/` - Create batch
- GET `/batch-edit/<pk>/` - Edit batch
- POST `/batch-update/<pk>/` - Save batch
- DELETE `/batch-delete/<pk>/` - Delete batch
- POST `/batch/<pk>/toggle-status/` - Toggle batch active/inactive

**Skillathon Management:**
- GET `/onboarding/skillathon/` - List skillathon events
- POST `/onboarding/skillathon/create/` - Create skillathon
- GET `/onboarding/skillathon/<pk>/edit/` - Edit skillathon
- POST `/onboarding/skillathon/<pk>/update/` - Save skillathon
- DELETE `/onboarding/skillathon/<pk>/delete/` - Delete skillathon

### 3. Exam Management Endpoints (assessments/views.py)

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/create-assessment/` | GET, POST | `create_assessment()` | Create exam assignment |
| `/assign-assessment/` | GET, POST | `assign_assessment()` | Assign exam to learner |
| `/tests/<test_id>/` | GET | `get_test()` | Get exam details |
| `/tests/<test_id>/update/` | POST | `update_test()` | Update exam |
| `/tests/<test_id>/delete/` | DELETE | `delete_test()` | Delete exam |
| `/update-test-status/<test_id>/<status>/` | POST | `update_test_status()` | Update exam status |
| `/batch-assignments/<ba_id>/delete/` | DELETE | `delete_batch_assignment()` | Delete batch assignment |

### 4. Reports & Analytics Endpoints (assessments/views.py)

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/render-exam-reports/` | GET | `render_exam_reports_page()` | Reports dashboard page |
| `/api/osce-report/` | GET | `fetch_osce_report_optimized()` | Pre-computed analytics (FAST) |
| `/api/semester-metrics/` | GET | `fetch_semester_metrics()` | Semester-level metrics |
| `/api/unit-metrics/` | GET | `fetch_unit_metrics()` | Unit-level metrics |
| `/api/download-student-report/` | GET | `download_student_report()` | Export individual report |

### 5. Data Fetch Endpoints (assessments/views.py)

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/fetch-institutes/` | GET | `fetch_institutes()` | Get institution dropdown |
| `/fetch-cohorts/` | GET | `fetch_cohorts()` | Get batch dropdown |
| `/fetch-assessors/` | GET | `fetch_assessors()` | Get assessor dropdown |
| `/fetch-procedures/` | GET | `fetch_procedures()` | Get procedure dropdown |
| `/fetch-course-procedures/<course_id>/` | GET | `fetch_course_procedures()` | Get procedures for course |
| `/fetch-active-courses/` | GET | `fetch_active_courses()` | Get active courses |
| `/fetch-active-batches/` | GET | `fetch_active_batches()` | Get active batches |

### 6. Admin Reports Endpoints (assessments/views.py)

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/api/admin-report/filter-options/` | GET | `admin_report_filter_options()` | Get available filters |
| `/api/admin-report/kpis/` | GET | `admin_report_kpis()` | Key performance indicators |
| `/api/admin-report/skills-metrics/` | GET | `admin_report_skills_metrics()` | Skills assessment data |
| `/api/admin-report/assessors-performance/` | GET | `admin_report_assessors_performance()` | Assessor performance metrics |
| `/api/admin-report/usage-engagement/` | GET | `admin_report_usage_engagement()` | Platform usage stats |
| `/api/admin-report/export-excel/` | POST | `admin_report_export_excel()` | Export to Excel |

### 7. Utility Endpoints (assessments/views.py)

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/base/` | GET | `base_view()` | Dashboard page |
| `/calculate-exam-score/` | POST | `calculate_exam_score()` | Calculate exam marks |
| `/sync-institutions-with-firebase/` | POST | `sync_institutions_with_firebase()` | Manual sync |
| `/api/check-socket-status/` | GET | `check_socket_status()` | WebSocket health check |

---

## Views & Controllers

### Key View Files

#### assessments/views.py (8,748 lines)
**Primary view layer with 160+ endpoints**

**Key Functions:**
- `login_view()` - Email/password authentication with session creation
- `logout_view()` - Session cleanup and redirect
- `forgot_password()` - Generate password reset token, send email
- `reset_password()` - Token validation and password update
- `base_view()` - Main dashboard page
- `create_assessment()` - Create exam assignment with procedure selection
- `assign_assessment()` - Bulk assign exam to learners in batch
- `update_test_status()` - Change exam status (scheduled→in_progress→completed)
- `fetch_osce_report_optimized()` - **CRITICAL:** Returns pre-computed analytics in < 1 second
- `fetch_osce_report()` - On-demand calculation (5-10 seconds, deprecated in favor of optimized)
- `calculate_exam_score()` - Calculate marks, gender metrics, performance
- `render_exam_reports_page()` - Reports UI page
- `download_student_report()` - Export individual learner report

**Filter Methods:**
- `filter_by_institution()` - Filter data by user's institutions
- `filter_by_hospital()` - Filter data by user's hospitals
- `check_user_institution_access()` - Verify data access permission

#### assessments/onboarding_views.py (2,888 lines)
**Onboarding CRUD operations**

**Key Functions:**
- `group_list()`, `group_create()`, `group_edit()`, `group_delete()` - Group management
- `institution_list()`, `institution_create()`, `institution_edit()`, `institution_delete()`, `institution_toggle_status()` - Institution CRUD
- `hospital_list()`, `hospital_create()`, `hospital_edit()`, `hospital_delete()`, `hospital_toggle_status()` - Hospital CRUD
- `learner_list()`, `learner_create()`, `learner_edit()`, `learner_delete()`, `learner_toggle_status()` - Learner CRUD
- `learner_bulk_upload()` - CSV upload handler
- `process_bulk_upload_with_progress()` - Background processing
- `get_active_upload_sessions()` - Track upload progress
- `learners_bulk_delete()` - Bulk delete with cascade
- `assessor_list()`, `assessor_create()`, `assessor_edit()`, `assessor_delete()` - Assessor CRUD
- `skillathon_list()`, `skillathon_create()`, `skillathon_edit()`, `skillathon_delete()` - Skillathon event management

**Validation & Processing:**
- `validate_csv_headers()` - Verify CSV format
- `process_learner_row()` - Parse single CSV row
- `sync_strength_counts()` - Update institution/hospital strength after bulk operations
- `cascade_delete_learner_data()` - Safely delete learner and related exams
- `reconnect_all_signals()` - Re-enable Firebase sync after bulk ops

---

## Authentication & Authorization

### 1. Authentication Flow

```
User Request
    ↓
login_view() receives email + password
    ↓
EbekUser.objects.get(email=email)
    ↓
check_password(password) validation
    ↓
Session created (SESSION_COOKIE_AGE = 360000 seconds = 100 hours)
    ↓
Redirect to /base/ (dashboard)
```

### 2. Authorization - Role-Based Access Control (RBAC)

**9 Built-in Roles:**
- `super_admin` - Full system access (all permissions)
- `ebek_admin` - EBEK platform admin (all permissions)
- `group_admin` - Manage groups and associated institutions/hospitals
- `institute_admin` - Manage institutions and learners
- `hospital_admin` - Manage hospitals and learners
- `supervisor` - Assessor role (evaluate exams)
- `student` - Student learner role (take exams)
- `nurse` - Nurse learner role (take exams)
- `visitor` - Guest/limited access

**45+ Granular Permissions** (in constants.py):
- View permissions: view_institution, view_learner, view_assessor, etc.
- Create permissions: create_institution, create_learner, create_course, etc.
- Edit permissions: edit_institution, edit_learner, edit_exam, etc.
- Delete permissions: delete_institution, delete_learner, delete_course, etc.
- Export permissions: export_report, export_excel, etc.

### 3. Permission Check Methods

```python
# Check if user is admin
user.has_all_permissions()  # Returns True/False

# Get list of all user permissions
user.get_all_permissions()  # Returns list of permission codes

# Check specific UI tab access
user.check_icon_navigation_permissions('reports')  # Returns True/False
```

### 4. Data-Level Access Control

**Institution/Hospital Filtering:**
```python
# User can only see their own institutions/hospitals
user_institutions = user.institutions.all()  # M2M relationship
user_hospitals = user.hospitals.all()        # M2M relationship

# All views filter data by user's access
institution = Institution.objects.get(pk=pk)
if institution not in user.institutions.all():
    raise PermissionDenied
```

**Learner Privacy:**
- Students can only view their own exam results
- Assessors can only evaluate assigned exams
- Institutional admins can view their institution's data

### 5. Middleware Authentication

**CheckInactiveUserMiddleware** (assessments/middleware.py):
- Checks on every request if user.is_active == True
- Auto-logs out inactive users (deleted/disabled accounts)
- Session security enhancement

---

## Firebase Integration

### 1. Dual-Database Architecture

```
Django ORM (PostgreSQL)    ←→    Firebase Firestore
    ↓                              ↓
CRUD operations              Real-time sync
Complex queries              Analytics
Sessions                     Metrics
Permissions
```

### 2. Signal-Based Synchronization

**Automatic Sync on Model Changes:**
```python
# assessments/firebase_sync.py
@receiver(post_save, sender=EbekUser)
def sync_user_to_firebase(sender, instance, created, **kwargs):
    # Automatically sync to Firestore 'Users' collection

@receiver(post_save, sender=Institution)
def sync_institution_to_firebase(sender, instance, created, **kwargs):
    # Automatically sync to Firestore 'Institutions' collection
```

**Supported Models:**
- EbekUser → `Users` collection
- Institution → `Institutions` collection
- Hospital → `Hospitals` collection
- Learner → Synced via parent institution/hospital
- ExamAssignment → `Test` collection (exam data)

**Disable Signals for Bulk Operations:**
```python
from assessments.firebase_sync import DisableSignals

with DisableSignals((post_save, EbekUser)):
    # Bulk operations without triggering Firebase sync
    for user in users:
        user.email = "new_email@example.com"
        user.save()  # No Firestore sync
```

### 3. Firebase Collections

| Collection | Synced From | Purpose |
|-----------|-------------|---------|
| Users | EbekUser | User directory |
| Institutions | Institution | Institution directory |
| Hospitals | Hospital | Hospital directory |
| Test | ExamAssignment | OSCE exam data |
| ProcedureAssignment | ExamAssignment | Exam-procedure mapping |
| MetricUpdateQueue | Manual entry | Analytics queue |
| SemesterMetrics | process_metric_queue.py | Pre-computed semester metrics |
| UnitMetrics | process_metric_queue.py | Pre-computed unit metrics |

### 4. Pre-Computed Analytics System

**Problem Solved:**
- **Before:** OSCE reports generated on-demand = 5-10 seconds response time
- **After:** Pre-computed analytics = 0.2-0.5 seconds response time

**How It Works:**

1. **Frontend adds queue entry** (on exam submit):
   ```javascript
   db.collection('MetricUpdateQueue').add({
       exam_id: "...",
       institution_id: "...",
       processed: false,
       timestamp: Date.now()
   })
   ```

2. **Cron/systemd runs every 5 minutes:**
   ```bash
   python manage.py process_metric_queue
   ```

3. **process_metric_queue.py:**
   - Queries unprocessed entries in MetricUpdateQueue
   - Calculates analytics for each exam
   - Creates/updates SemesterMetrics document
   - Creates/updates UnitMetrics document
   - Marks entry as processed: processed=true

4. **API returns pre-computed data:**
   ```python
   # Fast lookup (< 1 second)
   GET /api/osce-report/?institution_name=DJ%20Sanghvi&year=2025&semester=1
   # Returns data from SemesterMetrics collection
   ```

**Metrics Computed:**
- Total exams, pass/fail counts
- Gender-wise performance breakdown
- Procedure-wise performance
- Average marks by category
- Learner performance trends
- Assessor performance

---

## URL Routing

### Main URL Configuration (assessments/urls.py)

**160+ URL patterns organized in sections:**

```python
urlpatterns = [
    # Authentication (5 routes)
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', reset_password, name='reset_password'),

    # Onboarding - Groups (4 routes)
    path('onboarding/groups/', group_list, name='group_list'),
    path('onboarding/groups/create/', group_create, name='group_create'),
    path('onboarding/groups/<uuid:pk>/edit/', group_edit, name='group_edit'),
    path('onboarding/groups/<uuid:pk>/delete/', group_delete, name='group_delete'),

    # Onboarding - Institutions (5 routes)
    path('onboarding/institutions/', institution_list, name='institution_list'),
    path('onboarding/institutions/create/', institution_create, name='institution_create'),
    path('onboarding/institutions/<uuid:pk>/edit/', institution_edit, name='institution_edit'),
    path('onboarding/institutions/<uuid:pk>/delete/', institution_delete, name='institution_delete'),
    path('onboarding/institutions/<uuid:pk>/toggle-status/', institution_toggle_status, name='institution_toggle'),

    # ... 150+ more routes
]
```

---

## Management Commands

### process_metric_queue.py (78 KB)

**Purpose:** Pre-compute OSCE analytics every 5 minutes

**Setup:**

Option A - Crontab (Mac/Linux):
```bash
crontab -e
# Add: */5 * * * * cd /path/to/Ebek && python manage.py process_metric_queue
```

Option B - Systemd (Linux servers):
```bash
sudo cp metric-queue-processor.service /etc/systemd/system/
sudo cp metric-queue-processor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now metric-queue-processor.timer
```

**Manual Execution:**
```bash
python manage.py process_metric_queue
```

**What It Does:**
1. Queries Firestore: `MetricUpdateQueue.where('processed', '==', false)`
2. For each exam:
   - Calculate marks, gender metrics, performance
   - Aggregate to semester level
   - Aggregate to unit level
3. Update SemesterMetrics and UnitMetrics collections
4. Mark as processed

**Output:**
```
Processing 45 queued exams...
✓ Processed exam_001 for DJ Sanghvi College
✓ Processed exam_002 for DJ Sanghvi College
...
✓ Updated SemesterMetrics for DJ Sanghvi College_2025_1
✓ Updated UnitMetrics for DJ Sanghvi College_2025
Complete in 23.5 seconds
```

---

## Test Coverage by Feature

### Feature Categories Tested (12 total)

| # | Category | Tests | Key Features |
|---|----------|-------|--------------|
| 1 | Authentication | 10 | Login, logout, password reset, inactive user detection |
| 2 | Group Management | 5 | Create, edit, delete groups; assign members |
| 3 | Institution Management | 10 | CRUD operations, toggle status, member assignment |
| 4 | Hospital Management | 5 | CRUD operations, toggle status |
| 5 | Learner Management | 15 | CRUD, bulk upload, toggle status, type validation |
| 6 | Assessor Management | 8 | CRUD operations, assignment validation |
| 7 | Course Management | 7 | CRUD operations, toggle status, procedure management |
| 8 | Batch Management | 13 | CRUD, learner assignment, status management |
| 9 | Exam Management | 15 | Create, assign, update status, delete, cascade |
| 10 | Reports & Analytics | 18 | Pre-computed metrics, semester/unit reports, exports |
| 11 | Skillathon Management | 6 | Event creation, learner assignment, exam management |
| 12 | Role & Permissions | 4 | Role assignment, permission checking, access control |
| **TOTAL** | **116 Test Cases** | **130+ Code Paths** | **Complete Coverage** |

### Test Execution Phases

**Phase 1: Critical Path (P0 - 16 tests)**
- Authentication (5 tests)
- Group & Institution Creation (5 tests)
- Learner Upload (3 tests)
- Exam Assignment (3 tests)
- Success Criteria: 95%+ pass rate (15/16)

**Phase 2: Feature Workflows (P1 - 86 tests)**
- All CRUD operations
- Status transitions
- Data filtering
- Report generation
- Success Criteria: 85%+ pass rate (73/86)

**Phase 3: Edge Cases (P2 - 14 tests)**
- Invalid inputs
- Concurrent operations
- Error handling
- Success Criteria: 70%+ pass rate (10/14)

---

## Summary

The EBEK OSCE Platform is a comprehensive healthcare education assessment system with:
- **14+ Django models** managing users, institutions, learners, exams, and assessors
- **160+ API endpoints** covering authentication, CRUD operations, reports, and analytics
- **Dual-database architecture** with Django ORM + Firebase Firestore synchronization
- **Role-based access control** with 9 built-in roles and 45+ granular permissions
- **Pre-computed analytics** reducing report generation from 5-10s to 0.2-0.5s
- **Multi-tenant design** isolating institutional data effectively
- **116 functional test cases** covering all major features and workflows

See `EBEK_Functional_Test_Cases.xlsx` for comprehensive test case documentation and `EXECUTION_GUIDE.md` for detailed testing instructions.

---

**Document Version:** 1.0
**Last Updated:** November 29, 2025
**Next Review:** After first module testing completion
