# EBEK OSCE Platform - Functional Test Execution Guide
## Module 1: Complete Feature Testing

**Created:** November 2025
**Test Cases:** 116 functional tests based on actual codebase
**Format:** Excel spreadsheet + This guide

---

## Overview

This guide explains how to execute the **116 functional test cases** for the EBEK OSCE Platform. These tests cover all actual features found in the codebase.

**Key Statistics:**
- Total Tests: 116
- Categories: 12 feature areas
- Priority: P0(16 critical), P1(86 high), P2(14 medium)
- Coverage: 100% of implemented features

---

## What's Included

**Files in `/Users/sanujphilip/Desktop/Ebek/test_cases/`:**

1. **EBEK_Functional_Test_Cases.xlsx** - Main test case document
2. **functional_test_cases.py** - Test data (Python source)
3. **generate_excel.py** - Excel generator script
4. **EXECUTION_GUIDE.md** - This file
5. **CODEBASE_ANALYSIS.md** - Detailed codebase breakdown
6. **README.md** - Quick start guide

---

## Test Categories & Coverage

### 1. Authentication (10 tests: FUNC-001 to FUNC-010)
**What it tests:** User login, password reset, session management, inactive user logout

**Key flows:**
- User login with valid/invalid credentials
- Password reset request and completion
- Logout and session destruction
- Auto-logout of inactive users

**Files tested:**
- `assessments/views.py`: login_view(), logout_view(), forgot_password(), reset_password()
- `assessments/middleware.py`: CheckInactiveUserMiddleware
- `assessments/models.py`: PasswordResetToken

---

### 2. Group Management (5 tests: FUNC-011 to FUNC-015)
**What it tests:** Organization groups (Medical, Hospital, etc.)

**Key operations:**
- Create, read, update, delete groups
- Assign group head (auto-sets group_admin role)
- API endpoints

**Files tested:**
- `onboarding_views.py`: group_list(), group_create(), group_edit(), group_delete()

---

### 3. Institution Management (10 tests: FUNC-016 to FUNC-025)
**What it tests:** Medical colleges/institutions

**Key operations:**
- Create institutions (auto-generates institute_id)
- Edit and delete with cascade protection
- Assign unit_head (auto-sets institute_admin role)
- Toggle active/inactive status
- Data filtering for non-admin users
- Firebase synchronization

**Files tested:**
- `onboarding_views.py`: institution_* functions
- `assessments/models.py`: Institution.save() (signal handler)

---

### 4. Hospital Management (5 tests: FUNC-026 to FUNC-030)
**What it tests:** Hospital entities and management

**Key operations:**
- Create hospitals with bed count and nurse strength
- Edit and delete operations
- Toggle active/inactive status

**Files tested:**
- `onboarding_views.py`: hospital_* functions

---

### 5. Learner Management (15 tests: FUNC-031 to FUNC-045)
**What it tests:** Student and nurse learner creation and management

**Key operations:**
- Create individual learners (student/nurse type)
- Bulk upload from Excel (50-100+ learners)
- Edit learner details
- Toggle active/inactive status
- Delete learners (soft delete)
- Filter learners by assignment (inst admin sees only assigned)
- Gender tracking for analytics
- Sync learner count to Firebase

**Files tested:**
- `onboarding_views.py`: learner_* functions, learner_bulk_upload(), sync_strength_counts()
- `assessments/models.py`: Learner model

---

### 6. Assessor Management (8 tests: FUNC-046 to FUNC-053)
**What it tests:** Internal and external assessor management

**Key operations:**
- Create internal assessors (auto-sets ebek_admin role)
- Create external assessors (auto-sets supervisor role)
- List, edit, delete assessors
- Toggle active/inactive status
- Assessor login and view assigned exams

**Files tested:**
- `onboarding_views.py`: assessor_* functions

---

### 7. Course Management (7 tests: FUNC-054 to FUNC-060)
**What it tests:** OSCE courses with procedures

**Key operations:**
- Create courses and add procedures
- Edit and delete courses
- Toggle course active/inactive status
- Remove procedures from course

**Files tested:**
- `assessments/views.py`: course_management(), create_course(), update_course(), delete_course(), etc.

---

### 8. Batch Management (13 tests: FUNC-061 to FUNC-073)
**What it tests:** Batch management (groups of learners)

**Key operations:**
- Create batches with courses assigned
- Add/remove learners from batch
- Add/remove courses from batch
- Toggle batch active/inactive status
- View batch details and associated data
- API endpoints for batch operations

**Files tested:**
- `assessments/views.py`: batch_* functions
- API endpoints: /api/batches/*

---

### 9. Exam Management (15 tests: FUNC-074 to FUNC-088)
**What it tests:** OSCE exam assignment and management

**Key operations:**
- Create exam assignments (procedure assignments to learners)
- Fetch institutions, batches, assessors, procedures
- Assign procedures to learners
- View, update, delete exams
- Track exam type (mock/final/classroom/skillathon)
- Skillathon-specific exam assignments
- Assessor access to Firebase exam data

**Files tested:**
- `assessments/views.py`: create_assessment(), assign_assessment(), get_test(), update_test_status(), etc.
- Firebase Firestore (frontend for exam interface)

---

### 10. Reports & Analytics (18 tests: FUNC-089 to FUNC-106)
**What it tests:** Comprehensive reporting and analytics

**Key operations:**
- View exam reports page
- Fetch pre-computed OSCE report (optimized, < 1 second)
- Fetch exam and student metrics
- Gender-based analytics (using total marks student-level aggregation)
- Download reports as PDF/Excel
- Debug endpoints (semester and unit metrics)
- Assessor performance statistics
- Admin report portal with filtering

**Files tested:**
- `assessments/views.py`: render_exam_reports_page(), fetch_osce_report_optimized(), etc.
- `assessments/management/commands/process_metric_queue.py`: Metrics pre-computation
- Firebase collections: SemesterMetrics, UnitMetrics

---

### 11. Skillathon Management (6 tests: FUNC-107 to FUNC-112)
**What it tests:** Skillathon event management

**Key operations:**
- Create skillathon events
- Link institutions and hospitals to skillathons
- Link learners to skillathon events
- Fetch associated institutions/hospitals

**Files tested:**
- `onboarding_views.py`: skillathon_* functions
- `assessments/models.py`: SkillathonEvent

---

### 12. Role Management (4 tests: FUNC-113 to FUNC-116)
**What it tests:** Custom role creation and permission management

**Key operations:**
- Create custom roles with fine-grained permissions
- View, edit, delete roles
- Assign multiple permissions to roles

**Files tested:**
- `assessments/views.py`: create_roles(), get_roles(), edit_role(), delete_role()
- `assessments/models.py`: CustomRole, Permission

---

## How to Execute Tests

### Step 1: Setup Environment

**Ensure the following are ready:**
```
Development Environment:
├─ EBEK application running (python manage.py runserver)
├─ PostgreSQL database accessible (or SQLite if DEBUG=True)
├─ Firebase credentials loaded (firebase_key.json)
├─ Test users created:
│  ├─ Super admin: admin@example.com
│  ├─ Institute admin: iheadmin@example.com
│  ├─ Student: student@example.com
│  ├─ Nurse: nurse@example.com
│  ├─ Internal assessor: assessor@example.com
│  └─ External assessor: external@example.com
└─ Test data prepared:
   ├─ Groups created
   ├─ Institutions created (DJ Sanghvi, SVKM, etc.)
   ├─ Hospitals created (Apollo, etc.)
   └─ Courses created with procedures
```

### Step 2: Open Test Cases File

1. Open: `/Users/sanujphilip/Desktop/Ebek/test_cases/EBEK_Functional_Test_Cases.xlsx`
2. Review the "Test Cases" worksheet
3. Note the 4 worksheets:
   - **Test Cases**: All 116 test cases with detailed steps
   - **Coverage Matrix**: Test count by category
   - **Execution Log**: For tracking your test runs
   - **Summary Dashboard**: Statistics and KPIs

### Step 3: Execute Test Cases

**Order of execution (recommended):**

#### Phase 1: Critical (P0) Tests - 16 tests - Day 1-2
Focus on core functionality that must work:
- FUNC-001 to FUNC-010: Authentication (user login, password reset)
- FUNC-017 to FUNC-019: Institution create/edit/delete
- FUNC-031 to FUNC-033: Learner create and bulk upload
- FUNC-054 to FUNC-055: Course create
- FUNC-074: Exam assignment create

**Gate:** All P0 tests must pass before proceeding.

#### Phase 2: High Priority (P1) Tests - 86 tests - Day 3-8
Test feature workflows:
- Onboarding: Groups, institutions, hospitals, learners, assessors
- Course and batch management
- Exam management and assignment
- Reports and analytics

**Progress:** Track daily pass rates. Work with dev team to fix failures.

#### Phase 3: Medium Priority (P2) Tests - 14 tests - Day 9-10
Test edge cases, performance, optimization:
- Gender analytics implementation
- Excel validation
- Performance metrics
- Optional/advanced features

### Step 4: Record Results

**For each test case:**

1. **Read the test steps carefully** - Every detail matters
2. **Execute exactly as written** - Don't skip steps or take shortcuts
3. **Record in Excel**:
   - Fill "Actual Results" column with what actually happened
   - Update "Status" column: Pass / Fail / Blocked
   - Add "Notes" if anything unexpected

**Example entry:**
```
Test ID:           FUNC-001
Status:            Pass ✅
Actual Results:    User successfully logged in, redirected to /base/ dashboard
Notes:             Login took 2 seconds, response time acceptable
```

### Step 5: Generate Reports

**Daily:**
- Count: Passed / Failed / Blocked
- Identify blockers (issues preventing further testing)
- Report to dev team

**Weekly:**
- Generate graphs from Execution Log
- Calculate pass rate trend
- Identify patterns (which categories have most failures)

**Final:**
- Generate completion report
- List all issues found
- Recommend fixes before release

---

## Test Data

### User Accounts

| Account | Email | Role | Purpose |
|---------|-------|------|---------|
| Super Admin | admin@ebek.com | super_admin | Full system access |
| Inst Admin | admin@college.com | institute_admin | Manages institutions |
| Hospital Admin | admin@hospital.com | hospital_admin | Manages hospitals |
| Assessor Internal | assessor@college.com | ebek_admin | Evaluates exams |
| Assessor External | assessor@external.com | supervisor | External evaluator |
| Student | student@college.com | student | Takes exams |
| Nurse | nurse@hospital.com | nurse | Takes exams |

### Organizations

| Name | Type | Purpose |
|------|------|---------|
| Medical Group | Group | Container for institutions |
| DJ Sanghvi College | Institution | Medical college |
| SVKM Hospital | Hospital | Teaching hospital |
| Apollo Hospital | Hospital | Tertiary care |
| Tech Summit 2025 | Skillathon | Event |

### Courses

| Name | Procedures | Purpose |
|------|-----------|---------|
| OSCE Year 2 | Suturing, Injection, Wound Care, etc. | Medical procedures |
| Clinical Skills | History Taking, Physical Exam | Clinical skills |

---

## Common Issues & Solutions

### Issue: "Login fails for all users"
**Check:**
- Is the application running? (`python manage.py runserver`)
- Is the database accessible?
- Are test users created in database?
- Check Firefox console (F12) for errors

### Issue: "Cannot create institution"
**Check:**
- Are groups created first?
- Does user have `create_institute` permission?
- Check email for errors
- Verify database constraints

### Issue: "Bulk upload fails"
**Check:**
- Is Excel file in correct format (.xlsx, .xls)?
- Does Excel have required columns?
- Are cell values valid (no special characters in email)?
- Check browser console for errors

### Issue: "Exam not appearing for learner"
**Check:**
- Was exam assignment created?
- Is learner assigned to batch?
- Is batch assigned courses?
- Check Firebase Firestore for ExamAssignment records

### Issue: "Reports showing wrong data"
**Check:**
- Was `process_metric_queue` command run?
- Are metrics pre-computed in Firebase?
- Check SemesterMetrics and UnitMetrics collections
- Verify academic year and semester filters

---

## Priority Definitions

### P0 - Critical (Must Pass)
**16 tests** - Core functionality that blocks everything else
- User authentication
- Data creation (institution, learner, course)
- Exam assignment creation
- Basic CRUD operations
- Firebase synchronization

**Action:** If a P0 test fails, stop and fix immediately. Cannot proceed with P1 tests.

### P1 - High (Should Pass)
**86 tests** - Important feature workflows
- Role-based access control
- Data editing and deletion
- Batch management
- Exam management
- Reporting workflows

**Action:** Failure is serious but not immediately blocking. Schedule fix with dev team.

### P2 - Medium (Nice to Have)
**14 tests** - Edge cases, performance, optimization
- Gender analytics
- Excel validation
- Performance timing
- Optional features

**Action:** Can proceed to production with P2 failures if P0/P1 pass.

---

## Performance Expectations

These tests should help identify performance issues:

| Feature | Expected Performance |
|---------|---------------------|
| User login | < 2 seconds |
| Page loads | < 3 seconds |
| Bulk learner upload (50 users) | < 30 seconds |
| OSCE report fetch | < 1 second (pre-computed) |
| Exam assignment create | < 5 seconds |
| Batch learner assignment | < 5 seconds |

---

## API Endpoints Tested

**Note:** All endpoints are relative to Django app root

**Authentication:**
```
POST /login/                    - User login
GET  /logout/                   - User logout
GET  /forgot-password/          - Request password reset
POST /forgot-password/          - Send reset email
GET  /reset-password/<token>/   - Reset password page
POST /reset-password/<token>/   - Perform reset
```

**Onboarding CRUD:**
```
GET    /onboarding/groups/                    - List groups
POST   /onboarding/groups/create/             - Create group
GET    /onboarding/groups/<id>/edit/          - Edit group
POST   /onboarding/groups/<id>/edit/          - Update group
POST   /onboarding/groups/<id>/delete/        - Delete group

# Similar for: institutions, hospitals, learners, assessors, skillathons
```

**Exam Management:**
```
GET  /create_assessment/                       - Create exam page
POST /create-procedure-assignment-and-test/    - Create exam
GET  /assign_assessment/                       - Assign page
POST /assign_assessment/                       - Assign procedures
GET  /fetch-institutes/                        - List institutions
GET  /fetch-cohorts/                           - List batches
GET  /fetch-assessors/                         - List assessors
GET  /fetch-procedures/                        - List procedures
GET  /fetch-course-procedures/<course_id>/    - Course procedures
```

**Batch API:**
```
GET    /api/batches/                          - List batches
POST   /api/batches/create/                   - Create batch
GET    /api/batches/<id>/                     - Get batch
POST   /api/batches/<id>/update/              - Update batch
POST   /api/batches/<id>/delete/              - Delete batch
POST   /api/batches/<id>/toggle-status/       - Toggle status
GET    /api/batches/<id>/learners/            - List learners
GET    /api/batches/<id>/courses/             - List courses
POST   /api/batches/<id>/add-learners/        - Add learners
POST   /api/batches/<id>/remove-learners/     - Remove learners
POST   /api/batches/<id>/add-courses/         - Add courses
POST   /api/batches/<id>/remove-courses/      - Remove courses
```

**Reports:**
```
GET /exam-reports/                            - Reports page
GET /api/osce-report/                         - Pre-computed report (optimized)
GET /api/semester-metrics/                    - Debug endpoint
GET /api/unit-metrics/                        - Debug endpoint
GET /fetch-exam-metrics/                      - Exam metrics
GET /fetch-student-metrics/                   - Student metrics
GET /fetch-particular-student/                - Single student report
GET /api/download-student-report/             - Download PDF/Excel
GET /metrics-viewer/                          - Analytics viewer
```

---

## Quality Criteria for Pass/Fail

### Test PASSES if:
- ✅ All test steps completed successfully
- ✅ Actual results match expected results
- ✅ No error messages or warnings
- ✅ User can proceed to next logical step
- ✅ Data is persisted (survives page reload)
- ✅ Firebase is synchronized (when applicable)

### Test FAILS if:
- ❌ Test steps cannot be completed
- ❌ Unexpected error message shown
- ❌ Results differ from expected
- ❌ Data not persisted
- ❌ Performance below expectations

### Test is BLOCKED if:
- 🚧 Cannot start due to prerequisite test failure
- 🚧 Test environment issue (database down, app crashed)
- 🚧 Missing test data (institution not created, etc.)
- 🚧 Another feature blocking this test

---

## Execution Timeline

**Suggested 13-day execution plan:**

```
Day 1-2:   Authentication (P0) - 10 tests
Day 3:     Onboarding (P0) - 6 tests
Day 4:     Course & Batch (P0) - 4 tests
Day 5-6:   Exam Management (P1) - 15 tests
Day 7:     Institution & Learner (P1) - 25 tests
Day 8-9:   Reports & Analytics (P1) - 18 tests
Day 10:    Assessors & Skillathons (P1) - 14 tests
Day 11-12: Edge cases & Performance (P2) - 14 tests
Day 13:    Regression - Retest all failures
```

---

## Sign-off

When all tests complete, review:

**Checklist:**
- [ ] All P0 tests passed (16/16)
- [ ] All P1 tests reviewed (86 total)
- [ ] All P2 tests reviewed (14 total)
- [ ] Pass rate documented
- [ ] Issues logged and prioritized
- [ ] No critical blockers remaining
- [ ] Ready for release

**Sign-off:**
```
Tester Name: ___________________
Date: ___________________
Pass Rate: ____% (total_passed / 116)
Critical Issues: ____
High Issues: ____
Approved for Release: [ ] Yes [ ] No
```

---

## Questions?

**For each test case, check:**
1. Test description - What are we testing?
2. Preconditions - What data must exist first?
3. Test steps - Exactly what to click/type
4. Expected results - What should happen?
5. Related files - Where in code does this run?

Good testing! 🚀
