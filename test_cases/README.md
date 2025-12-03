# EBEK OSCE Platform - Functional Test Cases

**Module 1: User Onboarding, Authentication & Feature Testing**

Welcome! This folder contains comprehensive functional test cases for the EBEK OSCE Platform. Everything you need to execute thorough testing is included here.

---

## 📋 Quick Start (5 Minutes)

### What's in this folder?

```
test_cases/
├── README.md                              ← You are here
├── CODEBASE_ANALYSIS.md                  ← Detailed codebase reference (optional reading)
├── EBEK_Functional_Test_Cases.xlsx       ← All 116 test cases (MAIN FILE)
├── EXECUTION_GUIDE.md                    ← How to execute tests (REQUIRED READING)
├── functional_test_cases.py               ← Test case data (technical reference)
└── generate_excel.py                     ← Excel generation script (technical reference)
```

### Files You Need

**Essential (Required to execute tests):**
1. ✅ **EBEK_Functional_Test_Cases.xlsx** - Open this in Excel/Google Sheets to see all 116 tests
2. ✅ **EXECUTION_GUIDE.md** - Read this before starting any testing

**Reference (Optional):**
3. 📖 **CODEBASE_ANALYSIS.md** - Deep dive into EBEK architecture (read if curious about implementation)
4. 🔧 **functional_test_cases.py** - Python data structure (for developers)
5. ⚙️ **generate_excel.py** - How Excel file was generated (for developers)

---

## 🚀 How to Get Started

### Step 1: Open the Test Cases (2 minutes)

```bash
# On Mac/Linux
open EBEK_Functional_Test_Cases.xlsx

# Or use any spreadsheet application
# - Microsoft Excel
# - Google Sheets
# - LibreOffice Calc
```

### Step 2: Read the Execution Guide (10 minutes)

```bash
# Read this markdown file
cat EXECUTION_GUIDE.md

# Or open in your text editor
# - VS Code
# - Sublime Text
# - Any text editor
```

### Step 3: Review Test Structure (5 minutes)

The spreadsheet has **4 worksheets**:

**Worksheet 1: Test Cases (MAIN)**
- **116 rows** of functional test cases
- **13 columns** with complete test information:
  - Test ID (FUNC-001 to FUNC-116)
  - Category (12 different categories)
  - Priority (P0=Critical, P1=High, P2=Medium)
  - Test Name
  - Description
  - Preconditions (setup required)
  - Test Steps (how to execute)
  - Test Data (what values to use)
  - Expected Results (correct behavior)
  - Actual Results (fill during testing)
  - Status (Pass/Fail/Blocked/Not Run)
  - Notes (additional info)
  - Related Files (code references)

**Worksheet 2: Coverage Matrix**
- Visual overview of test coverage
- Tests per category breakdown
- Tests per priority breakdown

**Worksheet 3: Execution Log**
- Template for tracking test execution
- Columns: Date, Time, Tester Name, Test ID, Category, Status, Notes

**Worksheet 4: Summary Dashboard**
- Real-time KPI statistics
- Total test count: 116
- Pass/Fail tracking
- Category breakdown

### Step 4: Set Up Test Environment (1 hour)

See EXECUTION_GUIDE.md section "Environment Setup" for:
- Test user accounts to create
- Test institutions/hospitals to set up
- Test data to prepare
- Application state to configure

### Step 5: Start Testing

**Phase 1 (Days 1-3):** Execute all P0 tests (Critical - 16 tests)
- These are blocking issues affecting core functionality
- Must pass before proceeding to P1

**Phase 2 (Days 4-7):** Execute all P1 tests (High Priority - 86 tests)
- Important features and workflows
- Should have 85%+ pass rate

**Phase 3 (Days 8-10):** Execute all P2 tests (Medium Priority - 14 tests)
- Edge cases and polish
- Should have 70%+ pass rate

---

## 📊 Test Case Distribution

### By Priority Level

| Priority | Count | Pass Criteria | Typical Issues |
|----------|-------|---------------|----------------|
| **P0 (Critical)** | 16 | 95%+ pass | System crashes, lost data, can't login |
| **P1 (High)** | 86 | 85%+ pass | Feature doesn't work, wrong output |
| **P2 (Medium)** | 14 | 70%+ pass | Edge cases, nice-to-have fixes |

### By Feature Category (12 Total)

| Category | Count | Examples |
|----------|-------|----------|
| Authentication | 10 | Login, logout, password reset, inactive users |
| Group Management | 5 | Create groups, assign members |
| Institution Management | 10 | CRUD operations, toggle status |
| Hospital Management | 5 | CRUD operations, toggle status |
| Learner Management | 15 | Create, bulk upload, toggle status, type validation |
| Assessor Management | 8 | CRUD operations, assignment validation |
| Course Management | 7 | CRUD operations, toggle status |
| Batch Management | 13 | CRUD, learner assignment, status management |
| Exam Management | 15 | Create, assign, update status, delete |
| Reports & Analytics | 18 | Pre-computed metrics, semester reports, exports |
| Skillathon Management | 6 | Event creation, learner assignment |
| Role & Permissions | 4 | Role assignment, permission checking |
| **TOTAL** | **116** | **Complete coverage of all features** |

---

## 🔍 Understanding Test Case Fields

### Example Test Case

```
Test ID:        FUNC-001
Category:       Authentication
Priority:       P0 (Critical)

Test Name:      Login with valid credentials

Description:    User can login with correct email and password
                and is directed to the dashboard

Preconditions:  1. User account must exist in the system
                2. User account must be active (is_active=True)
                3. Application must be running

Test Steps:     1. Navigate to /login/ page
                2. Enter valid email in email field
                3. Enter valid password in password field
                4. Click "Login" button
                5. Verify redirected to dashboard

Test Data:      email: test@example.com
                password: Test@1234

Expected:       User logged in successfully
                Session created
                Redirected to /base/ dashboard
                User name displayed in top-right

Actual:         [FILL THIS IN DURING TESTING]

Status:         Not Run → Pass/Fail/Blocked
                (update after executing)

Notes:          Optional notes
                - If failed, describe the issue
                - If blocked, explain the dependency
                - Add any additional context

Related Files:  assessments/views.py:login_view()
                assessments/models.py:EbekUser
                assessments/middleware.py:CheckInactiveUserMiddleware
```

### Field Definitions

| Field | Purpose | When Executing |
|-------|---------|----------------|
| **Preconditions** | What must be set up before test | Read and verify all conditions met |
| **Test Steps** | Exact sequence to follow | Follow precisely, step by step |
| **Test Data** | Specific values to use | Use these exact values (don't improvise) |
| **Expected** | What should happen if test passes | Compare with actual behavior |
| **Actual** | What really happened | Fill this in after executing each step |
| **Status** | Test result | Choose: Pass, Fail, Blocked, or Not Run |
| **Notes** | Additional context | Add details about failures or blockers |
| **Related Files** | Code references | If curious, look at these files in the codebase |

---

## 📝 How to Execute a Test

### Step-by-Step Execution Process

```
1. SELECT a test from the spreadsheet (start with P0 tests)

2. READ the preconditions
   → Verify all setup is done
   → If preconditions aren't met, mark as "Blocked"

3. PREPARE test data
   → Have required usernames, passwords, institutions ready
   → Open the application in browser

4. EXECUTE the steps
   → Follow test steps exactly
   → Do NOT skip steps or improvise
   → Note what happens after each step

5. VERIFY the result
   → Compare actual behavior with "Expected" field
   → Check all expected behaviors occurred

6. RECORD the status
   → Pass: All expected results matched actual
   → Fail: Expected results did NOT match
   → Blocked: Could not execute (dependency missing)
   → Not Run: Did not attempt (haven't tested yet)

7. ADD NOTES
   → If failed: Describe what went wrong
   → If blocked: Explain why you couldn't test
   → If passed: No notes needed (unless relevant)

8. MOVE TO NEXT TEST
   → Update the spreadsheet
   → Save the file
   → Continue with next test
```

### Example Execution (Real Test)

```
TEST: FUNC-001 - Login with valid credentials

PRECONDITIONS:
□ User account exists? → CREATE TEST USER (testuser@ebek.com)
□ User is active? → CHECK is_active=True in database
□ App running? → START: python manage.py runserver

TEST STEPS:
1. Navigate to /login/
   ✓ Page loaded, form visible

2. Enter email: test@ebek.com
   ✓ Email entered in field

3. Enter password: Test@1234
   ✓ Password entered (masked)

4. Click "Login"
   ✓ Button clicked, page processing...

5. Verify dashboard
   ✓ Redirected to /base/ dashboard
   ✓ Top-right shows "Test User" name
   ✓ All menu items visible

RESULT:
Status: PASS ✓
Notes: Login working as expected
```

---

## ✅ Quality Criteria

### How to Determine Pass vs Fail

**PASS** means:
- All expected results occurred
- No error messages appeared
- Data saved correctly (if applicable)
- Redirects happened as specified
- UI shows correct state

**FAIL** means:
- Expected result did NOT occur
- Got an error message instead
- Data was not saved
- Wrong redirect or page shown
- UI in incorrect state

**BLOCKED** means:
- Could not execute due to dependency missing
- System not available
- Precondition not met
- External service down

**NOT RUN** means:
- Haven't tested yet
- Will test later
- Skipped for a reason

---

## 📈 Progress Tracking

### Daily Tracking

Each day, update the spreadsheet:
- Fill in "Actual Results" for tests you executed
- Update "Status" column (Pass/Fail/Blocked/Not Run)
- Add notes if status is Fail or Blocked
- Save the file

### Weekly Summary

Calculate:
```
Total Tests Executed = Tests with status (Pass/Fail/Blocked)
Pass Rate = Passed Tests / Total Executed × 100

Example:
- Executed 20 tests
- 18 passed, 2 failed
- Pass Rate = 18/20 = 90%
```

### Overall Success Criteria

**Phase 1 (P0 Critical):**
- ✅ Target: 95%+ pass rate (15/16 minimum)
- 🎯 If missed: All P0 failures must be fixed before Phase 2

**Phase 2 (P1 High Priority):**
- ✅ Target: 85%+ pass rate (73/86 minimum)
- 🎯 If missed: Log issues, prioritize fixes

**Phase 3 (P2 Medium Priority):**
- ✅ Target: 70%+ pass rate (10/14 minimum)
- 🎯 If missed: Document for later fixes

**Overall Success:**
- ✅ 90%+ overall pass rate (104/116 tests pass)
- ✅ 0 P0 failures (all 16 critical tests pass)
- ✅ All failures documented with root cause
- ✅ Blockers tracked with resolution plan

---

## 🆘 Common Issues & Troubleshooting

### Issue: Test says "Preconditions not met"
**Solution:**
- Check EXECUTION_GUIDE.md "Environment Setup" section
- Create required test users
- Set up institutions/hospitals
- Verify application is running

### Issue: Test marks as "Blocked"
**Solution:**
- Identify the blocker in Notes
- Report to development team
- Wait for fix, then re-test

### Issue: Getting unexpected error
**Solution:**
- Note the exact error message
- Record in Notes field
- Check if error is in "Expected" results (might be P0 failure)
- Report to team

### Issue: Not sure if test passed
**Solution:**
- Re-read the "Expected" field
- Compare EXACTLY with what you see
- Check all bullet points in expected results
- If ANY expected item is missing → FAIL

### Issue: Application won't start
**Solution:**
- Check dependencies: `pip install -r requirements.txt`
- Check database: `python manage.py migrate`
- Check Django: `python manage.py runserver`
- Check logs in `logs/` folder

---

## 📂 File Descriptions

### EBEK_Functional_Test_Cases.xlsx
- **Type:** Excel Spreadsheet
- **Format:** 4 worksheets with 116 test cases
- **Purpose:** Execute tests, record results, track progress
- **Usage:** Open in Excel/Google Sheets, update as you test

### EXECUTION_GUIDE.md
- **Type:** Markdown Document
- **Length:** 500+ lines
- **Purpose:** Complete instructions for executing all tests
- **Contains:** Setup, phases, troubleshooting, templates
- **Read First:** Yes, before starting any testing

### CODEBASE_ANALYSIS.md
- **Type:** Markdown Document
- **Length:** 1000+ lines
- **Purpose:** Deep dive into EBEK architecture
- **Contains:** Models, endpoints, views, Firebase integration
- **Read If:** Curious about implementation or debugging

### functional_test_cases.py
- **Type:** Python Script
- **Purpose:** Data structure containing all 116 test cases
- **Technical:** For developers and Excel generation
- **Usage:** Referenced by generate_excel.py

### generate_excel.py
- **Type:** Python Script
- **Purpose:** Generates EBEK_Functional_Test_Cases.xlsx
- **Technical:** Shows how test data was formatted
- **Usage:** Run if you want to regenerate the Excel file

---

## 🔐 Security & Privacy

### When Testing

- **Use Test Accounts Only** - Don't use production user accounts
- **Fake Data Only** - Use test emails, addresses, not real users
- **No Real Passwords** - Use simple test passwords like "Test@1234"
- **Sensitive Operations** - Password resets, permission changes verified by team
- **File Uploads** - Test with dummy CSV files, not real learner data (initially)

### Protecting Data

- Keep test spreadsheet secure (may contain test credentials)
- Don't share test accounts or passwords in emails
- Report security issues to team immediately
- Clear test data after testing phase (optional)

---

## 📞 Support & Questions

### If You Get Stuck

1. **Check EXECUTION_GUIDE.md** - Most answers are there
2. **Read Test Description** - Re-read the test you're executing
3. **Ask Team** - Slack/email development team
4. **Check Related Files** - Look at code references for context
5. **Review Notes** - Check if similar test was already executed

### Reporting Issues

**For Failed Tests:**
- Note the exact error message
- List steps to reproduce
- Mention test ID (FUNC-XXX)
- Include test data used
- Add screenshots if helpful

**For Blocked Tests:**
- Explain what's blocking
- What needs to be fixed
- Reference related test IDs
- Note priority/timeline

---

## 📚 Useful References

### EBEK Platform Information
- **CLAUDE.md** - Project overview and architecture (in project root)
- **DEPLOYMENT_GUIDE.md** - Production deployment info (in project root)
- **METRICS_SETUP.md** - Analytics system details (in project root)

### Application Locations
- **Django Admin:** http://localhost:8000/admin/
- **Main Dashboard:** http://localhost:8000/base/
- **Login Page:** http://localhost:8000/login/

### Helpful Commands
```bash
# Start application
python manage.py runserver

# Create test user
python manage.py createsuperuser

# Reset database
python manage.py migrate --fake-initial

# Check logs
tail -f logs/error.log
```

---

## 🎯 Testing Timeline

### Recommended Execution Schedule

```
Week 1:
  Day 1-2: Setup environment, create test users
  Day 3-5: Execute P0 tests (16 critical tests)
    → Must achieve 95%+ pass rate before proceeding

Week 2:
  Day 6-9: Execute P1 tests (86 high-priority tests)
    → Should achieve 85%+ pass rate
    → Fix P0 failures discovered

Week 3:
  Day 10-12: Execute P2 tests (14 medium-priority tests)
    → Should achieve 70%+ pass rate
  Day 13: Retest all failures, prepare final report
    → Overall: 90%+ pass rate (104/116)
```

---

## ✨ Success Indicators

You'll know testing is complete when:

✅ All 116 tests have a status (Pass, Fail, Blocked, or Not Run)
✅ P0 tests show 95%+ pass rate (at least 15/16)
✅ P1 tests show 85%+ pass rate (at least 73/86)
✅ P2 tests show 70%+ pass rate (at least 10/14)
✅ Overall pass rate: 90%+ (at least 104/116)
✅ All failures documented with root cause
✅ All blockers have resolution plan
✅ Team reviewed and approved results

---

## 📄 Document Information

**Created:** November 29, 2025
**Module:** 1 - User Onboarding, Authentication & Features
**Total Tests:** 116 Functional Test Cases
**Status:** Ready for Testing
**Next:** Will proceed to Module 2 after approval

---

## 🚀 Ready to Start?

1. ✅ Open **EBEK_Functional_Test_Cases.xlsx**
2. ✅ Read **EXECUTION_GUIDE.md** (10 minutes)
3. ✅ Set up test environment (1 hour)
4. ✅ Start with FUNC-001 (P0 tests first)
5. ✅ Update spreadsheet as you test

**Good luck!** 🎯

---

**Questions?** Check EXECUTION_GUIDE.md or ask your team.
