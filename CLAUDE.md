# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EBEK** is a Django-based OSCE (Objective Structured Clinical Examination) management platform for healthcare education assessment. It manages learners (students and nurses), assessors, institutions, hospitals, and skillathon events, with deep integration to Firebase/Firestore for real-time data synchronization.

**Tech Stack:**
- Django 5.2.3 with PostgreSQL (dev) / SQLite (prod - reversed in DEBUG flag)
- Firebase Admin SDK for authentication and Firestore database
- Django REST Framework for API endpoints
- Redis for caching
- Custom user model (`EbekUser`) with permission-based role system

## Development Setup

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Environment variables required in .env
DEBUG=True                    # True for PostgreSQL, False for SQLite
DB_NAME=<database_name>
DB_USER=<database_user>
DB_PASSWORD=<database_password>
DB_HOST=<database_host>
DB_PORT=<database_port>
FIREBASE_DATABASE=<firebase_database_id>

# Firebase credentials required
# Place firebase_key.json in project root

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Database Configuration

**IMPORTANT:** The DEBUG flag controls database selection (reversed logic):
- `DEBUG=True` → Uses **PostgreSQL** (development)
- `DEBUG=False` → Uses **SQLite** (production)

### Static Files

```bash
# Collect static files
python manage.py collectstatic
```

## Core Architecture

### Authentication & Permissions

**Custom User Model:** `assessments.EbekUser` extends `AbstractBaseUser` with:
- Email-based authentication (USERNAME_FIELD = 'email')
- Role-based access via `user_role` field and `CustomRole` model
- Fine-grained permissions via `Permission` model and `user_permissions_custom` M2M
- Access control for institutions/hospitals/skillathons via M2M relationships

**Roles:**
- `super_admin`, `ebek_admin` - Full access
- `group_admin` - Manages groups
- `institute_admin` - Manages institutions
- `hospital_admin` - Manages hospitals
- `supervisor` - External assessor
- `student`, `nurse` - Learners

**Permission Check Methods:**
- `user.has_all_permissions()` - Admin role check
- `user.get_all_permissions()` - Returns list of permission codes
- `user.check_icon_navigation_permissions(tab_name)` - UI tab access control

### Firebase Integration

**Dual-Database Architecture:**
- Django PostgreSQL/SQLite for core data models
- Firebase Firestore for real-time OSCE data, metrics, and synchronization

**Signal-Based Sync:** All model changes (create/update/delete) automatically sync to Firestore via Django signals in `assessments/firebase_sync.py`

**Key Firestore Collections:**
- `Users` - Synced from EbekUser
- `Institutions`, `Hospitals` - Synced from Django models
- `Test`, `ProcedureAssignment`, `ExamAssignment` - OSCE exam data
- `MetricUpdateQueue` - Queue for pre-computing analytics
- `SemesterMetrics`, `UnitMetrics` - Pre-computed analytics (see below)

**Disable Signals When Needed:**
```python
from assessments.firebase_sync import DisableSignals
from django.db.models.signals import post_save

with DisableSignals((post_save, EbekUser)):
    # Bulk operations without triggering Firebase sync
    user.save()
```

### Pre-Computed Analytics System

**Performance Optimization:** OSCE reports are pre-computed every 5 minutes instead of on-demand, reducing response time from 5-10s to 0.2-0.5s.

**How It Works:**
1. Frontend adds entries to `MetricUpdateQueue` Firestore collection on exam submit
2. `process_metric_queue` management command runs every 5 minutes (cron/systemd)
3. Pre-computes analytics into `SemesterMetrics` and `UnitMetrics` collections
4. API reads pre-computed data instead of calculating on-the-fly

**Run Analytics Pre-Computation:**
```bash
# Manual execution
python manage.py process_metric_queue

# Initial backfill (first time setup - takes 2-5 minutes)
python manage.py process_metric_queue
```

**Setup Automated Processing:**

Option A - Crontab (Mac/Linux):
```bash
crontab -e
# Add: */5 * * * * cd /path/to/Ebek && /usr/bin/python3 manage.py process_metric_queue >> /tmp/osce_metrics.log 2>&1
```

Option B - Systemd (Linux servers):
```bash
# Files already exist: metric-queue-processor.service, metric-queue-processor.timer
sudo cp metric-queue-processor.service /etc/systemd/system/
sudo cp metric-queue-processor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now metric-queue-processor.timer
```

**Optimized API Endpoint:**
- `GET /api/osce-report/` - Pre-computed analytics (fast)
- Returns data from `SemesterMetrics` or `UnitMetrics` collections
- Supports institution/hospital, academic year, semester filters

### Entity Relationships

**Onboarding Entities:**
- `Group` → Contains multiple `Institution` or `Hospital`
- `Institution` (colleges) → Contains `Learner` (students)
- `Hospital` → Contains `Learner` (nurses)
- `SkillathonEvent` → Associated with learners for events

**OSCE Flow:**
- `Course` → Contains procedures
- `Batch` → Group of learners
- `ExamAssignment` → Links learner to procedure with OSCE type (Mock/Final/Classroom)

**Key Foreign Keys:**
- `Institution.group` → `Group`
- `Institution.unit_head` → `EbekUser` (auto-sets user_role to 'institute_admin')
- `Learner.college` → `Institution` (for students)
- `Learner.hospital` → `Hospital` (for nurses)
- `Learner.learner_user` → `EbekUser`

**Important:** Model saves auto-update related user roles (see models.py `save()` methods)

## Management Commands

### Available Commands

```bash
# Pre-compute OSCE analytics (run every 5 minutes)
python manage.py process_metric_queue

# Populate initial permissions data
python manage.py populate_permissions

# Run exam scheduler (systemd service: exam-scheduler.service)
python manage.py run_exam_scheduler
```

## API Endpoints

### OSCE Reports (Optimized)

```bash
# Get pre-computed OSCE report
GET /api/osce-report/?institution_name=DJ%20Sanghvi%20College&academic_year=2025&semester=1

# Get semester metrics (debugging)
GET /api/semester-metrics/?unit_name=DJ%20Sanghvi%20College&year=2025&semester=1

# Get unit-level metrics (debugging)
GET /api/unit-metrics/?unit_name=DJ%20Sanghvi%20College&year=2025
```

### Admin Reports

```bash
# Admin report portal
GET /admin-report-portal/ - Admin report dashboard UI

# Admin report APIs
GET /api/admin-report/filter-options/ - Get filter options (institutions, academic years, etc.)
GET /api/admin-report/kpis/ - Get key performance indicators
GET /api/admin-report/skills-metrics/ - Get skills-wise metrics
GET /api/admin-report/assessors-performance/ - Get assessor performance data
GET /api/admin-report/usage-engagement/ - Get usage and engagement metrics
POST /api/admin-report/export-excel/ - Export report to Excel
```

### Skillathon Reports (Optimized)

```bash
# Skillathon metrics (pre-computed for performance)
GET /fetch-exam-metrics/?skillathon_name=X&institution_name=Y - Pre-computed skillathon analytics
GET /api/osce-report/?institution_name=X&academic_year=Y&semester=Z - OSCE report (pre-computed)

# Helper endpoints
GET /fetch-skillathons/ - Get list of skillathons
POST /api/institute-based-skillathon/ - Get institutes for skillathon
GET /exam-reports/ - Exam reports UI
GET /metrics-viewer/ - Metrics viewer UI
```

### Exam Management

```bash
GET /api/tests/<test_id>/ - Get exam details
POST /api/tests/<test_id>/update/ - Update exam
DELETE /api/tests/<test_id>/delete/ - Delete exam
DELETE /api/batch-assignments/<ba_id>/delete/ - Delete batch assignment
POST /update-test-status/<test_id>/<status>/ - Update exam status

# Course & batch management
GET /courses/ - List courses
POST /courses/create/ - Create course
POST /courses/<course_id>/toggle-status/ - Toggle course active/inactive
POST /api/batches/<batch_id>/toggle-status/ - Toggle batch active/inactive
```

### Onboarding

Most onboarding entities follow CRUD pattern with NEW status toggles:
- List: `/onboarding/<entity>/`
- Create: `/onboarding/<entity>/create/`
- Edit: `/onboarding/<entity>/<pk>/edit/`
- Delete: `/onboarding/<entity>/<pk>/delete/`
- **NEW** Toggle Status: `/onboarding/<entity>/<pk>/toggle-status/`

Entities: `groups`, `institutions`, `hospitals`, `learners`, `assessors`, `skillathon`

**Bulk Operations (NEW):**
```bash
POST /onboarding/learners/bulk-upload/ - Upload learners in bulk
POST /onboarding/learners/bulk-delete/ - Delete multiple learners
GET /onboarding/learners/active-uploads/ - Get active upload sessions
GET /onboarding/learners/upload-details/<session_key>/ - Get upload session details
POST /onboarding/sync-strength-counts/ - Sync strength counts to Firestore

# Helper endpoints
GET /onboarding/learners/get-institutions-by-skillathon/ - Get institutions for skillathon
GET /onboarding/learners/get-hospitals-by-skillathon/ - Get hospitals for skillathon
```

## Recent Changes (November 2024 - Present)

### Admin Report Portal
**Commit:** dd02696 (Nov 27 2025)
- NEW FEATURE: Comprehensive admin reporting dashboard
- Location: `/admin-report-portal/` endpoint
- Includes: KPIs, skills metrics, assessor performance tracking, usage engagement
- Export functionality to Excel reports
- Template: `assessments/templates/assessments/admin_report_portal.html` (2596 lines)

### Gender Metrics Fix (Critical)
**Commit:** 24b99a9 (Nov 28 2025)
- FIXED: `fetch_exam_metrics()` now uses **student-level gender calculations** (not exam-level)
- Uses **Total Marks Method**: Aggregates all exam marks per student first, then calculates grade
- Gender metrics now count each student **once** (not once per exam attempt)
- Location: `assessments/views.py:2224-2260`
- Ensures gender distribution reflects unique students, not exam volume

### Status Management Features
**Batch/Course Active/Inactive Toggles** (Nov 25-26 2025)
- NEW ENDPOINTS:
  - `courses/<course_id>/toggle-status/` - Toggle course active/inactive
  - `batches/<batch_id>/toggle-status/` - Toggle batch active/inactive
- When course marked inactive, automatically removed from all batches
- When batch marked inactive, checks parent institution/hospital status
- Prevents activating batch if parent unit is inactive

**Institution/Hospital/Learner Status Toggles** (Nov 26 2025)
- NEW ENDPOINTS:
  - `/onboarding/institutions/<pk>/toggle-status/` - Toggle institution status
  - `/onboarding/hospitals/<pk>/toggle-status/` - Toggle hospital status
  - `/onboarding/learners/<pk>/toggle-status/` - Toggle learner status
- Cascading effects: Inactive parent units affect child batches

### Bulk Learner Upload Enhancements (Nov 2024)
- Improved bulk upload UI with upload session tracking
- NEW ENDPOINTS:
  - `/onboarding/learners/bulk-upload/` - Upload learners
  - `/onboarding/learners/active-uploads/` - Track active sessions
  - `/onboarding/learners/upload-details/<session_key>/` - Get upload details
  - `/onboarding/learners/bulk-delete/` - Delete multiple learners
- Better error handling and progress tracking

### Process Metric Queue Optimizations (Nov 27-28 2025)
- **Assessor Name Lookup Caching**: Reduced Firestore queries via caching
- **Exam-to-OSCE Mapping**: Phase 1.5 pre-computes exam assignment to OSCE context
- **Queue Filter Bug Fix**: Changed from `processed == True` to `processed == False`
  - Was incorrectly processing already-processed items
  - Now correctly processes unprocessed items only

### New Helper Endpoints
- `onboarding/learners/get-institutions-by-skillathon/` - Get institutions for skillathon
- `onboarding/learners/get-hospitals-by-skillathon/` - Get hospitals for skillathon
- `onboarding/sync-strength-counts/` - Sync strength counts to Firestore

---

## Middleware

### CheckInactiveUserMiddleware
**File:** `assessments/middleware.py` (lines 6-62)
**Purpose:** Automatically logs out inactive users on every request
**Behavior:**
- Checks if authenticated user's `is_active` status is still True
- Refreshes user object from database on each request to detect status changes
- Logs out user if marked inactive
- Prevents inactive users from accessing the system
- Excluded pages: login/logout routes
**Configuration:** Registered in `INSTALLED_APPS` as middleware

---

## Testing Infrastructure

**Current State:** NO automated test coverage
- Empty `assessments/tests.py` (boilerplate only)
- No test files, fixtures, or test infrastructure
- All testing is currently manual

**Future Testing Setup:**
```bash
# Install testing dependencies
pip install pytest pytest-django pytest-cov factory-boy faker

# Create test structure
mkdir -p assessments/tests
touch assessments/tests/__init__.py
touch assessments/tests/conftest.py

# Run tests
pytest assessments/
```

**Test Coverage Priority:**
1. Authentication & Permissions (critical - 240 test cases planned)
2. OSCE Exam Flow (high - 40-50 test cases)
3. Analytics & Reports (high - 30-40 test cases)
4. Onboarding (medium - 25-35 test cases)
5. Firebase Sync (medium - 15-20 test cases)
6. API Endpoints (medium - 20-30 test cases)

---

## Important Notes

### Database Quirk
The `DEBUG` setting has **reversed** database logic:
- `DEBUG=True` uses PostgreSQL (for development with real data)
- `DEBUG=False` uses SQLite (lightweight for production)

### Session Configuration
- `SESSION_COOKIE_AGE = 360000` (100 hours)
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = False`

### Logging
Logs are written to:
- Console (INFO level)
- `logs/info.log` (INFO level)
- `logs/error.log` (ERROR level)

Logger name: `assessments`

### Testing the Metrics System

```bash
# Verify pre-computed data exists
python manage.py shell
>>> from firebase_admin import firestore
>>> db = firestore.client()
>>> doc = db.collection('SemesterMetrics').document('DJ Sanghvi College_2025_1').get()
>>> doc.exists
True
>>> doc.to_dict().keys()  # Should show pre-computed metrics
```

### UUID Fields
These models auto-generate UUID-based IDs on save:
- `Institution.institute_id`
- `Hospital.hospital_id`
- `Learner.learner_id`
- `Assessor.assessor_id`
- `Group.group_id`

### File Uploads
- Media files: `MEDIA_ROOT = <project_root>/media`
- Bulk learner upload supported via `/onboarding/learners/bulk-upload/`

## Development Workflow

### Making Model Changes

1. Modify model in `assessments/models.py`
2. Create migration: `python manage.py makemigrations`
3. Apply migration: `python manage.py migrate`
4. Update corresponding Firestore sync logic in `assessments/firebase_sync.py` if needed
5. Test signal-based sync works correctly

### Adding New Permissions

1. Add permission to `assessments/management/commands/populate_permissions.py`
2. Run: `python manage.py populate_permissions`
3. Assign to roles via admin interface or programmatically
4. Use in view permission checks: `user.get_all_permissions()`

### Troubleshooting Analytics

If pre-computed metrics are missing or stale:

```bash
# Check queue has unprocessed items
python manage.py shell
>>> db.collection('MetricUpdateQueue').where('processed', '==', False).stream()

# Check cron/systemd is running
crontab -l  # or: systemctl status metric-queue-processor.timer

# Force re-computation
python manage.py process_metric_queue

# View logs
tail -f /tmp/osce_metrics.log  # or: journalctl -u metric-queue-processor.service -f
```

## Key Files

- `ebek_django_app/settings.py` - Django settings, Firebase init, caching, logging
- `assessments/models.py` - All data models (User, Institution, Hospital, Learner, etc.)
- `assessments/views.py` - Main views (very large file ~370KB)
- `assessments/onboarding_views.py` - Onboarding CRUD operations
- `assessments/firebase_sync.py` - Signal handlers for Firestore sync
- `assessments/urls.py` - URL routing
- `assessments/management/commands/process_metric_queue.py` - Analytics pre-computation

## Deployment Files

- `DEPLOYMENT_GUIDE.md` - Complete analytics system deployment
- `METRICS_SETUP.md` - Metrics pre-computation setup
- `SYSTEMD_SETUP.md` - Systemd timer configuration
- `exam-scheduler.service`, `metric-queue-processor.service`, `metric-queue-processor.timer` - Systemd units

## References

See existing documentation:
- `DEPLOYMENT_GUIDE.md` - Analytics system architecture and deployment
- `METRICS_SETUP.md` - Metrics pre-computation technical details
- `SYSTEMD_SETUP.md` - Production systemd timer setup
