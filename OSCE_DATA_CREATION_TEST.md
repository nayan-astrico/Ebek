# OSCE Data Creation - Comprehensive Test Cases

## Overview
This document contains test cases for creating and managing all foundational data required for the OSCE Metrics Dashboard, including institutions, hospitals, learners, assessors, courses, batches, and assessments.

---

## Part 1: Onboarding Setup

### 1.1 Groups

#### Test Case 1.1.1: Create a Group
- **Steps:**
  1. Navigate to Onboarding → Groups
  2. Click "Create New Group"
  3. Fill in:
     - Group Name: "Medical Group 2025"
     - Description: "Group for medical college and hospital"
  4. Click Submit
- **Expected Result:**
  - Group created successfully
  - Unique `group_id` (UUID) assigned
  - Group appears in list with status "Active"
  - Confirmation message displayed

#### Test Case 1.1.2: Edit a Group
- **Steps:**
  1. Navigate to Groups list
  2. Click Edit on "Medical Group 2025"
  3. Change Description to "Updated description"
  4. Click Save
- **Expected Result:**
  - Changes saved successfully
  - Updated timestamp reflected
  - Group name cannot be changed after creation

#### Test Case 1.1.3: View Group Details
- **Steps:**
  1. Click on group name to view details
- **Expected Result:**
  - Group ID displayed
  - Associated institutions/hospitals listed
  - Associated users listed
  - Creation and modification timestamps shown

---

### 1.2 Institutions

#### Test Case 1.2.1: Create Multiple Institutions in Same Group
- **Steps:**
  1. Navigate to Onboarding → Institutions
  2. Click "Create New Institution"
  3. Fill in:
     - Institution Name: "DJ Sanghvi College of Engineering"
     - Group: "Medical Group 2025"
     - Unit Head: Select or create user "Dr. Rajesh Kumar"
     - City: "Mumbai"
     - State: "Maharashtra"
  4. Click Submit
  5. Repeat for:
     - "APOLLO COLLEGE OF NURSING"
     - "St. Xavier's Medical College"
- **Expected Result:**
  - Three institutions created with unique `institute_id` (UUID)
  - Each institution linked to same group
  - Unit heads assigned as institute_admin role automatically
  - Each institution appears in list with edit/delete options

#### Test Case 1.2.2: Verify Institution Auto-Assign Admin Role
- **Steps:**
  1. Create institution with unit head "Dr. Rajesh Kumar"
  2. Go to user management
  3. Search for "Dr. Rajesh Kumar"
- **Expected Result:**
  - User role automatically set to `institute_admin`
  - User can only access their assigned institution
  - User permissions updated to institution-level access

#### Test Case 1.2.3: Edit Institution Details
- **Steps:**
  1. Edit "DJ Sanghvi College of Engineering"
  2. Change City to "Pune"
  3. Change Unit Head to "Dr. Priya Sharma"
  4. Save
- **Expected Result:**
  - Changes saved successfully
  - Previous unit head role reverted
  - New unit head assigned `institute_admin` role
  - Institution name cannot be changed

---

### 1.3 Hospitals

#### Test Case 1.3.1: Create Multiple Hospitals
- **Steps:**
  1. Navigate to Onboarding → Hospitals
  2. Click "Create New Hospital"
  3. Fill in:
     - Hospital Name: "Apollo Hospital Mumbai"
     - Group: "Medical Group 2025"
     - Hospital Head: Select/create "Dr. Vikram Singh"
     - City: "Mumbai"
     - State: "Maharashtra"
  4. Submit
  5. Repeat for:
     - "Breach Candy Hospital"
     - "Fortis Hospital Pune"
- **Expected Result:**
  - Three hospitals created with unique `hospital_id` (UUID)
  - Each linked to same group
  - Hospital heads assigned `hospital_admin` role automatically
  - Hospitals appear in institution dropdown when selecting learner hospital

#### Test Case 1.3.2: Hospital Admin Role Assignment
- **Steps:**
  1. Create hospital with head "Dr. Vikram Singh"
  2. Check user management
- **Expected Result:**
  - User role set to `hospital_admin`
  - User can access only their assigned hospital
  - Hospital-level permissions applied

---

## Part 2: User Management

### 2.1 Create Assessors

#### Test Case 2.1.1: Create Multiple Assessors
- **Steps:**
  1. Navigate to Onboarding → Assessors
  2. Click "Create New Assessor"
  3. Fill in:
     - Name: "Dr. Anita Desai"
     - Email: "anita.desai@college.com"
     - Phone: "9876543210"
     - Specialization: "Clinical Skills"
     - Role: "Supervisor"
     - Associated Institution: "DJ Sanghvi College"
  4. Submit
  5. Create 8 more assessors:
     - "Dr. Rajesh Patel" - Specialization: "Communication" - Institution: "DJ Sanghvi"
     - "Dr. Meera Iyer" - Specialization: "Infection Control" - Institution: "DJ Sanghvi"
     - "Nurse Sarah Khan" - Specialization: "Nursing Skills" - Hospital: "Apollo"
     - "Nurse Priya Singh" - Specialization: "Documentation" - Hospital: "Apollo"
     - "Dr. Vikram Sharma" - Specialization: "Pre-Procedure" - Institution: "APOLLO College"
     - "Dr. Emma Johnson" - Specialization: "Critical Thinking" - Institution: "St. Xavier's"
     - "Nurse Arun Kumar" - Specialization: "Clinical Skills" - Hospital: "Breach Candy"
     - "Dr. Lisa Wong" - Specialization: "Clinical Skills" - Hospital: "Fortis"
- **Expected Result:**
  - 9 assessors created with unique `assessor_id` (UUID)
  - Each assigned `supervisor` role
  - Email verification sent to each assessor
  - Assessors appear in dropdown for OSCE assignment

#### Test Case 2.1.2: Create Assessor for Multiple Institutions
- **Steps:**
  1. Create assessor "Dr. Multi Expert"
  2. Assign to multiple institutions (DJ Sanghvi + APOLLO College)
- **Expected Result:**
  - Assessor can assess students from both institutions
  - Appears in assessor list for both institutions

---

## Part 3: Learner (Student/Nurse) Management

### 3.1 Create Students

#### Test Case 3.1.1: Create Batch and Enroll Students
- **Steps:**
  1. Navigate to Onboarding → Learners
  2. Click "Create New Batch"
  3. Fill in:
     - Batch Name: "B.Tech 2024-2028 Batch A"
     - Institution: "DJ Sanghvi College"
     - Learner Type: "Student"
     - Academic Year: "2024-2025"
     - Semester: "1"
  4. Click Submit
  5. Click "Add Learners to Batch"
  6. Create/Add 30 students:
     - Upload CSV with student data OR manually enter
     - Fields: Name, Email, Roll Number, Phone
  7. Submit
- **Expected Result:**
  - Batch created with unique `batch_id`
  - All 30 students enrolled with unique `learner_id` (UUID)
  - Students linked to institution
  - Students assigned `student` role
  - Email notifications sent
  - Students appear in batch list

#### Test Case 3.1.2: Create Multiple Batches in Same Institution
- **Steps:**
  1. Create Batch B: "B.Tech 2024-2028 Batch B" - Same institution, semester 1
  2. Enroll 25 students
  3. Create Batch C: "B.Tech 2023-2027 Batch A" - Same institution, semester 3
  4. Enroll 28 students
- **Expected Result:**
  - Three batches created
  - Total 83 students across batches
  - Batches searchable by name, year, semester
  - Each batch maintains separate learner list

#### Test Case 3.1.3: Create Batches in Multiple Institutions
- **Steps:**
  1. Create batch in "APOLLO College of Nursing" - Semester 2 - 35 students
  2. Create batch in "St. Xavier's Medical College" - Semester 1 - 40 students
- **Expected Result:**
  - Batches created in respective institutions
  - Dashboard later shows data per institution
  - Students correctly associated with their institution

---

### 3.2 Create Nurses in Hospitals

#### Test Case 3.2.1: Create Nurse Batches
- **Steps:**
  1. Navigate to Learners
  2. Create Batch: "Nursing Batch 2024 Apollo"
     - Learner Type: "Nurse"
     - Hospital: "Apollo Hospital Mumbai"
     - Academic Year: "2024-2025"
     - Semester: "1"
  3. Enroll 20 nurses
  4. Repeat for:
     - "Nursing Batch 2024 Breach Candy" - 18 nurses
     - "Nursing Batch 2024 Fortis" - 22 nurses
- **Expected Result:**
  - 60 nurses created with unique `learner_id`
  - Nurses linked to respective hospitals
  - Nurses assigned `nurse` role
  - Separate batches for each hospital

---

## Part 4: Course and Procedure Setup

### 4.1 Create Courses

#### Test Case 4.1.1: Create Multiple Courses
- **Steps:**
  1. Navigate to Course Management
  2. Create Course 1:
     - Course Code: "CS101"
     - Course Name: "Clinical Skills Fundamentals"
     - Institution: "DJ Sanghvi College"
     - Semester: "1"
     - Duration: "6 weeks"
  3. Create Course 2:
     - Course Code: "CC101"
     - Course Name: "Infection Control Practices"
     - Institution: "DJ Sanghvi College"
     - Semester: "1"
  4. Create Course 3:
     - Course Code: "COM101"
     - Course Name: "Patient Communication"
     - Institution: "DJ Sanghvi College"
     - Semester: "1"
- **Expected Result:**
  - 3 courses created
  - Each linked to institution and semester
  - Courses appear in procedure selection dropdown

---

### 4.2 Create Procedures/Skills

#### Test Case 4.2.1: Create Procedures Under Categories
- **Steps:**
  1. Navigate to Procedure Management
  2. Under "Core Skills" category, create:
     - Procedure: "Patient Assessment" - Duration: 10 min - Max Marks: 20
     - Procedure: "Vital Signs Monitoring" - Duration: 8 min - Max Marks: 15
     - Procedure: "Infection Control Protocols" - Duration: 12 min - Max Marks: 25
  3. Under "Communication" category, create:
     - Procedure: "Patient Counseling" - Duration: 10 min - Max Marks: 20
     - Procedure: "Team Communication" - Duration: 8 min - Max Marks: 15
  4. Under "Pre-Procedure" category, create:
     - Procedure: "Instrument Preparation" - Duration: 15 min - Max Marks: 30
     - Procedure: "Environment Setup" - Duration: 10 min - Max Marks: 20
  5. Repeat for categories:
     - "Documentation" (3 procedures)
     - "Critical Thinking" (2 procedures)
     - "Infection Control" (3 procedures)
- **Expected Result:**
  - 17 procedures created across 6 categories
  - Each has unique ID, category, duration, max marks
  - Procedures searchable by name, category
  - Procedures available for OSCE assignment

#### Test Case 4.2.2: Assign Procedures to Courses
- **Steps:**
  1. Go to Course "Clinical Skills Fundamentals"
  2. Add Procedures:
     - "Patient Assessment" (Max Marks: 20)
     - "Vital Signs Monitoring" (Max Marks: 15)
     - "Infection Control Protocols" (Max Marks: 25)
  3. Save
- **Expected Result:**
  - Procedures linked to course
  - Total marks calculated (60)
  - Procedures appear in OSCE selection when creating tests

---

## Part 5: OSCE Assessment Setup

### 5.1 Create Exam Assignments

#### Test Case 5.1.1: Create Classroom OSCE
- **Steps:**
  1. Navigate to Assessment → Create Exam Assignment
  2. Fill in:
     - Exam Name: "Clinical Skills Classroom OSCE - Semester 1"
     - Exam Type: "Classroom"
     - Institution: "DJ Sanghvi College"
     - Academic Year: "2024-2025"
     - Semester: "1"
     - Batch: "B.Tech 2024-2028 Batch A" (30 students)
     - Procedures: Select all 3 procedures from above
     - Total Marks: 60
     - Passing Marks: 48 (80%)
     - Duration: 45 minutes
     - Scheduled Date: "2024-01-15"
     - Scheduled Time: "10:00 AM"
  3. Click Submit
- **Expected Result:**
  - Exam assignment created with unique ID
  - Status: "Draft"
  - 30 student assignments created (one per learner in batch)
  - Email invitations sent to students
  - Exam appears in upcoming exams list

#### Test Case 5.1.2: Create Mock OSCE
- **Steps:**
  1. Create Exam Assignment:
     - Exam Name: "Clinical Skills Mock OSCE - Semester 1"
     - Exam Type: "Mock"
     - Same institution, batch, procedures
     - Scheduled Date: "2024-02-20"
  2. Submit
- **Expected Result:**
  - Mock exam created
  - Status: "Draft"
  - 30 student assignments created
  - Students can attempt multiple times

#### Test Case 5.1.3: Create Final OSCE
- **Steps:**
  1. Create Exam Assignment:
     - Exam Name: "Clinical Skills Final OSCE - Semester 1"
     - Exam Type: "Final"
     - Same institution, batch, procedures
     - Scheduled Date: "2024-04-10"
     - Passing Marks: 48
  2. Submit
- **Expected Result:**
  - Final exam created
  - Status: "Draft"
  - 30 student assignments created

#### Test Case 5.1.4: Create OSCEs Across Different Categories
- **Steps:**
  1. Create exam for "Communication" procedures
     - Classroom variant (30 students)
  2. Create exam for "Infection Control" procedures
     - Classroom variant (30 students)
  3. Create exam for "Pre-Procedure" procedures
     - Classroom variant (30 students)
- **Expected Result:**
  - 3 additional exams created
  - Total: 6 exams across different categories
  - All 30 students in batch assigned to each

---

### 5.2 Conduct OSCEs and Record Results

#### Test Case 5.2.1: Publish OSCE for Assessment
- **Steps:**
  1. Select "Clinical Skills Classroom OSCE - Semester 1"
  2. Click "Publish"
  3. Confirm
- **Expected Result:**
  - Status changed to "Published"
  - Students can now attempt the exam
  - Notifications sent to assessors
  - Exam appears as "Active" for students

#### Test Case 5.2.2: Record Student Scores for Classroom OSCE
- **Steps:**
  1. Navigate to Active Assessment
  2. Select "Clinical Skills Classroom OSCE"
  3. For each of 30 students, record:
     - Student Name: "Student A"
     - Procedure Marks:
       - Patient Assessment: 18/20
       - Vital Signs Monitoring: 13/15
       - Infection Control Protocols: 22/25
       - Total: 53/60 (88.33%) - Grade: A
     - Comments: "Excellent performance"
  4. Save after each entry
- **Expected Result:**
  - 30 student scores recorded
  - Grades auto-calculated (88.33% = A)
  - Passing status calculated (53 >= 48)
  - Each record timestamped
  - Data synced to Firebase in real-time

#### Test Case 5.2.3: Record Varied Performance Scores
- **Steps:**
  1. Continue recording for mock OSCE
  2. Create varied distribution:
     - 5 students: 85-95% (Grade A) - Pass
     - 8 students: 75-84% (Grade B) - Pass
     - 10 students: 65-74% (Grade C) - Pass
     - 4 students: 55-64% (Grade D) - Fail
     - 3 students: Below 55% (Grade E) - Fail
- **Expected Result:**
  - 30 students with varied grades
  - Grades correctly calculated
  - Pass/Fail status correct (80% threshold)
  - Distribution: 23 Pass, 7 Fail

#### Test Case 5.2.4: Record Final OSCE Results
- **Steps:**
  1. Publish Final OSCE
  2. Record 30 student scores for final OSCE
  3. Use similar distribution as mock
- **Expected Result:**
  - All 30 students have final OSCE scores
  - Each student now has:
     - Classroom score: 53/60 (88%)
     - Mock score: varies
     - Final score: varies

---

## Part 6: Multi-Batch and Multi-Semester Testing

### 6.1 Create Semester 2 Data (Same Institution)

#### Test Case 6.1.1: Create Semester 2 Batch and OSCEs
- **Steps:**
  1. Create Batch: "B.Tech 2024-2028 Batch A - Semester 2"
     - Same 30 students as Semester 1
     - Semester: "2"
     - Academic Year: "2024-2025"
  2. Assign 5 procedures (different from Semester 1)
  3. Create 3 OSCEs (Classroom, Mock, Final)
  4. Record scores for all 30 students
- **Expected Result:**
  - Semester 2 data created
  - Students can have different scores in each semester
  - Dashboard shows separate metrics per semester
  - Total of 6 exams per student so far

#### Test Case 6.1.2: Create Semester 3 Data (Different Batch)
- **Steps:**
  1. Create Batch C "B.Tech 2023-2027 Batch A - Semester 3"
     - 28 students
     - Semester: "3"
  2. Create and score 3 OSCEs (Classroom, Mock, Final)
- **Expected Result:**
  - Different cohort with different scores
  - Data isolated per batch
  - Dashboard distinguishes between batches

---

### 6.2 Create Data Across Multiple Institutions

#### Test Case 6.2.1: Create OSCE Data in Second Institution
- **Steps:**
  1. Go to "APOLLO College of Nursing"
  2. Create batch with 35 nurses
  3. Create 5 procedures specific to nursing
  4. Create 3 OSCEs (Classroom, Mock, Final)
  5. Record 35 × 3 = 105 scores
- **Expected Result:**
  - Complete OSCE data for second institution
  - Dashboard shows separate metrics for each institution
  - Can filter by institution

#### Test Case 6.2.2: Create Data for Hospital Nurses
- **Steps:**
  1. For "Apollo Hospital Mumbai" batch (20 nurses)
  2. Create 4 procedures
  3. Create 2 OSCEs (Mock, Final - no classroom)
  4. Record scores for 40 assessments
- **Expected Result:**
  - Hospital-based assessment data
  - Different OSCE types than college
  - Separate metrics for hospital vs college

---

## Part 7: Data Variation and Edge Cases

### 7.1 Create Data with Performance Variations

#### Test Case 7.1.1: Create High Performing Cohort
- **Steps:**
  1. Create batch "Elite Batch 2024"
  2. Enroll 15 high performers
  3. Record high scores across all OSCEs:
     - Average: 88-95% (mostly A grades)
     - All pass threshold
- **Expected Result:**
  - Cohort with mostly A and B grades
  - High pass rate (100%)
  - Dashboard shows excellent metrics

#### Test Case 7.1.2: Create Low Performing Cohort
- **Steps:**
  1. Create batch "Remedial Batch 2024"
  2. Enroll 12 struggling students
  3. Record lower scores:
     - Average: 55-70% (mostly C and D grades)
     - Lower pass rate
- **Expected Result:**
  - Cohort with mostly C, D, E grades
  - Lower pass rate (~50%)
  - Clear performance gaps visible in dashboard

#### Test Case 7.1.3: Create Bimodal Distribution
- **Steps:**
  1. Create batch "Mixed Batch 2024"
  2. Enroll 30 students
  3. Record:
     - 15 students: 85-95% (Grade A/B)
     - 15 students: 45-65% (Grade D/E)
- **Expected Result:**
  - Two distinct performance groups
  - Dashboard shows bimodal distribution in grade chart
  - High variance in metrics

---

### 7.2 Create Data with Missing/Incomplete Attempts

#### Test Case 7.2.1: Students with Incomplete OSCE Types
- **Steps:**
  1. Create batch with 25 students
  2. Record Classroom OSCE for all 25
  3. Record Mock OSCE for only 20 students
  4. Record Final OSCE for only 15 students
- **Expected Result:**
  - Dashboard correctly shows:
     - Classroom: 25 attempted
     - Mock: 20 attempted
     - Final: 15 attempted
  - Percentages calculated correctly
  - Missing data handled gracefully

#### Test Case 7.2.2: Students with No OSCE Attempts
- **Steps:**
  1. Create batch with 10 students
  2. Do NOT record any OSCE scores
  3. View in dashboard
- **Expected Result:**
  - Students listed but marked as not assessed
  - Dashboard shows 0 assessed
  - No errors in calculations

---

### 7.3 Procedure Performance Edge Cases

#### Test Case 7.3.1: Procedure with All High Scores
- **Steps:**
  1. Create procedure "Easy Skill"
  2. Record 50 student attempts
  3. Scores: 85-98% (all passing)
- **Expected Result:**
  - Avg Score: ~92% (Grade A)
  - Pass Rate: 100%

#### Test Case 7.3.2: Procedure with All Low Scores
- **Steps:**
  1. Create procedure "Difficult Skill"
  2. Record 50 student attempts
  3. Scores: 35-60% (all failing)
- **Expected Result:**
  - Avg Score: ~48% (Grade E)
  - Pass Rate: 0%

#### Test Case 7.3.3: Procedure with Perfect Spread
- **Steps:**
  1. Create procedure "Balanced Skill"
  2. Record 50 scores:
     - 10 students: 92-100% (A)
     - 10 students: 82-91% (B)
     - 10 students: 72-81% (C)
     - 10 students: 62-71% (D)
     - 10 students: 50-61% (E)
- **Expected Result:**
  - Even distribution across grades
  - Dashboard shows balanced performance

---

## Part 8: Data Consistency and Validation

### 8.1 Cross-Tab Data Verification

#### Test Case 8.1.1: Verify Total Student Count
- **Steps:**
  1. Sum all students across batches:
     - Batch A: 30
     - Batch B: 25
     - Batch C: 28
     - Total: 83 students in institution
  2. Go to dashboard
  3. Check "Total Students" in KPI
- **Expected Result:**
  - KPI shows 83 total students
  - Count matches manual sum

#### Test Case 8.1.2: Verify Average Calculation Across Exams
- **Steps:**
  1. Student "Student A" scores:
     - Classroom: 88.33%
     - Mock: 82.5%
     - Final: 85%
  2. Manual average: (88.33 + 82.5 + 85) / 3 = 85.28%
  3. Check dashboard "Overall Average"
- **Expected Result:**
  - Dashboard shows 85.28% (or similar calculation method)
  - Methodology clearly defined

#### Test Case 8.1.3: Verify Category Performance Calculation
- **Steps:**
  1. Collect all student scores for "Core Skills" category procedures
  2. Calculate average manually
  3. Check Category Performance chart
- **Expected Result:**
  - Chart shows calculated percentage
  - Matches manual calculation

#### Test Case 8.1.4: Verify Pass Rate Calculation
- **Steps:**
  1. In Classroom OSCE with 30 students:
     - 23 passed (≥80%)
     - 7 failed (<80%)
  2. Pass rate: (23/30) × 100 = 76.67%
  3. Check dashboard
- **Expected Result:**
  - Dashboard shows 76.67% pass rate
  - Or round to 77%

---

### 8.2 Data Synchronization with Firebase

#### Test Case 8.2.1: Verify Firestore Sync on Score Entry
- **Steps:**
  1. Record score for 1 student in classroom OSCE
  2. Open Firebase console
  3. Check `MetricUpdateQueue` collection
  4. Verify entry created with:
     - exam_id, student_id, semester, institution_id
     - processed: false
- **Expected Result:**
  - Entry appears in queue within 1 second
  - Correct data structure
  - Ready for metrics computation

#### Test Case 8.2.2: Verify Pre-Computed Metrics After Queue Processing
- **Steps:**
  1. Record scores for 30 students (complete classroom OSCE)
  2. Run `python manage.py process_metric_queue`
  3. Check Firebase `SemesterMetrics` collection
  4. Look for document with key: "Institution_2024-2025_1"
- **Expected Result:**
  - Document created with:
     - unit_name, year, semester
     - students_assessed: 30
     - avg_score, pass_rate, grade_letter
     - category_performance: {...}
     - skills_performance: {...}
     - osce_activity_timeline: [...]
     - student_batch_report: [...]

---

## Part 9: Dashboard Verification with Created Data

### 9.1 Semester 1 Dashboard Verification

#### Test Case 9.1.1: Load Dashboard with Semester 1 Data
- **Steps:**
  1. Go to Metrics Dashboard
  2. Select Institution: "DJ Sanghvi College"
  3. Select Academic Year: "2024-2025"
  4. Click "Go"
- **Expected Result:**
  - KPI cards show:
     - Total Students: 30 + 25 = 55 (if loading Semester 1 for both batches)
     - Or 30 (if batch-specific filtering works)
  - Charts render with data
  - Data matches what was entered

#### Test Case 9.1.2: Verify Category Performance Chart
- **Steps:**
  1. Load semester data with filters
  2. Check Category Performance chart
  3. Verify categories:
     - Core Skills, Communication, Pre-Procedure, etc.
     - Each with correct average score
- **Expected Result:**
  - All 6 categories shown
  - Scores calculated correctly
  - Colors match grade scale

#### Test Case 9.1.3: Verify Skills Analysis Table
- **Steps:**
  1. Load semester data
  2. Scroll to Skills Analysis table
  3. Verify each of 17 procedures listed with:
     - Skill Name
     - Category
     - OSCE Types: "Classroom, Mock, Final"
     - Students Attempted: 30 (for each OSCE type)
     - Average Score: Calculated correctly
     - Grade: Auto-derived from score
- **Expected Result:**
  - All 17 procedures listed
  - Correct categories
  - OSCE types shown
  - Grades color-coded

#### Test Case 9.1.4: Verify Student Batch Report
- **Steps:**
  1. Load semester data
  2. Scroll to Student Batch Report
  3. Verify 30 students listed with:
     - Name
     - Overall: Grade (%) format
     - Marks: x/60
     - Classroom, Mock, Final: Grade (%) format
- **Expected Result:**
  - All 30 students displayed
  - Grades formatted correctly
  - Scores match entered data
  - Sorting works (Overall grade)

---

### 9.2 Multi-Semester Dashboard Verification

#### Test Case 9.2.1: Compare Semester 1 vs Semester 2
- **Steps:**
  1. Load dashboard for Semester 1
  2. Record metrics (avg score, pass rate, etc.)
  3. Load dashboard for Semester 2
  4. Compare metrics
- **Expected Result:**
  - Different metrics for each semester
  - Clear separation of data
  - Students may have different performance

#### Test Case 9.2.2: Unit-Level Metrics (Across All Semesters)
- **Steps:**
  1. Go to Unit Metrics tab
  2. Enter Unit Name: "DJ Sanghvi College"
  3. Enter Year: "2024-2025"
  4. Click "Load Data"
- **Expected Result:**
  - Shows aggregated metrics across:
     - Semester 1 (30 or 55 students depending on batches)
     - Semester 2 (30 students)
     - Semester 3 (28 students)
  - Total students: 83+
  - Semester comparison table shows all semesters

---

### 9.3 Multi-Institution Dashboard Verification

#### Test Case 9.3.1: Dashboard for College vs Hospital
- **Steps:**
  1. Load "DJ Sanghvi College" metrics (student-based)
  2. Load "Apollo Hospital Mumbai" metrics (nurse-based)
  3. Compare KPIs
- **Expected Result:**
  - College: Shows all 55+ students, classroom/mock/final OSCE types
  - Hospital: Shows 20 nurses, mock/final OSCE types (no classroom)
  - Different metrics appropriately

#### Test Case 9.3.2: Dashboard for Multiple Hospitals
- **Steps:**
  1. Create similar data for "Breach Candy" and "Fortis" hospitals
  2. Load dashboard for each
  3. Verify data isolation
- **Expected Result:**
  - Each hospital shows only their nurses' data
  - No cross-contamination of metrics
  - Each has unique metrics

---

## Part 10: Performance and Load Testing

### 10.1 Large Scale Data Creation

#### Test Case 10.1.1: Create 1000+ Student Records
- **Steps:**
  1. Create 5 batches with 200+ students each
  2. Create 15 OSCEs (3 per batch × 5 batches)
  3. Record 3000+ student-exam attempts
  4. Load dashboard
- **Expected Result:**
  - All data created successfully
  - Dashboard loads within 2 seconds
  - No timeout errors
  - Calculations accurate

#### Test Case 10.1.2: Dashboard with 1000+ Students
- **Steps:**
  1. Load dashboard with large institution data
  2. Scroll through Student Batch Report
  3. Apply search/sort
- **Expected Result:**
  - Dashboard renders smoothly
  - Sorting completes within 500ms
  - Search filters in real-time
  - No lag or freezing

---

### 10.2 Data Integrity Under Load

#### Test Case 10.2.1: Concurrent Score Entry
- **Steps:**
  1. Have 2 assessors simultaneously enter scores:
     - Assessor 1: Records 15 students (Classroom OSCE A)
     - Assessor 2: Records 15 students (Classroom OSCE B)
  2. Monitor data consistency
- **Expected Result:**
  - All 30 scores recorded correctly
  - No data loss or corruption
  - No duplicate entries
  - Each record properly attributed

---

## Part 11: Data Export and Reporting

### 11.1 Generate Reports from Created Data

#### Test Case 11.1.1: Export Student Report
- **Steps:**
  1. Load semester metrics for 30 students
  2. Click "Export" (if available)
  3. Download as Excel/CSV
  4. Verify data in file
- **Expected Result:**
  - All 30 students exported
  - All columns included (Name, Scores, Grades)
  - Data matches dashboard display
  - File properly formatted

#### Test Case 11.1.2: Generate Summary Report
- **Steps:**
  1. Create report for institution
  2. Include metrics like:
     - Total Students: 83
     - Avg Score: X%
     - Pass Rate: Y%
     - Grade Distribution: A (10), B (25), C (35), D (10), E (3)
  3. Export as PDF
- **Expected Result:**
  - Professional report generated
  - All metrics included
  - Correct calculations
  - Proper formatting

---

## Part 12: Regression Testing

### 12.1 Data Migration/Update Testing

#### Test Case 12.1.1: Edit Student Score and Verify Recalculation
- **Steps:**
  1. Change 1 student's classroom score from 53 to 45
  2. Run metrics recomputation
  3. Check if:
     - Student grade changes from A to D
     - Class average updates
     - Pass rate updates
     - Skills affected by score change update
- **Expected Result:**
  - Cascade updates correctly
  - All dependent metrics recalculated
  - Dashboard reflects changes

#### Test Case 12.1.2: Delete an OSCE Assessment
- **Steps:**
  1. Delete Mock OSCE for one batch
  2. Verify impact on:
     - Student profiles (no longer show mock score)
     - Overall metrics (recalculated without mock)
     - Dashboard (updates correctly)
- **Expected Result:**
  - Data properly deleted
  - Metrics rebuild correctly
  - No orphaned data

---

## Test Data Summary

After completing all tests, you should have:

### Institution: DJ Sanghvi College
- **Batches:** 3 (A: 30 students, B: 25 students, C: 28 students)
- **Total Students:** 83
- **Semesters:** 1, 2, 3
- **OSCEs Created:** 9 (3 types × 3 semesters or batches)
- **Procedures:** 17 across 6 categories
- **Total Assessments:** 249+ (83 students × 3 OSCE types)
- **Assessors:** 3 dedicated to institution

### Hospital: Apollo Hospital Mumbai
- **Nurse Batches:** 1 (20 nurses)
- **Total Nurses:** 20
- **OSCEs:** 2 (Mock, Final - no classroom)
- **Procedures:** 4 (nursing-specific)
- **Total Assessments:** 40+ (20 nurses × 2 OSCE types)
- **Assessors:** 2 dedicated

### Other Institutions & Hospitals
- APOLLO College of Nursing: 35 students
- St. Xavier's Medical College: 40 students
- Breach Candy Hospital: 18 nurses
- Fortis Hospital: 22 nurses

### Total Across All Data
- **Total Learners:** 200+
- **Total OSCEs:** 15+
- **Total Assessments:** 600+
- **Total Scores Recorded:** 600+
- **Categories:** 6
- **Procedures:** 20+
- **Assessors:** 9

---

## Quality Checklist

- [ ] All data created without errors
- [ ] All student enrollments completed
- [ ] All assessor roles assigned correctly
- [ ] All OSCE assessments created
- [ ] All scores recorded (600+ entries)
- [ ] Dashboard loads successfully with all data
- [ ] Calculations verified (manual vs dashboard)
- [ ] Grades auto-calculated correctly
- [ ] Pass/Fail logic working (80% threshold)
- [ ] Firebase sync verified
- [ ] Metrics pre-computation completed successfully
- [ ] Multi-institution data isolation verified
- [ ] Performance acceptable with large dataset
- [ ] Export functionality working
- [ ] No errors in browser console
- [ ] No data corruption detected

---

## Notes for QA Team

1. **Test Data Retention:** Keep all created test data for:
   - Dashboard refinement testing
   - Performance testing
   - Regression testing

2. **Backup Recommendations:**
   - Backup database after all test data creation
   - Export Firebase collections
   - Save CSV of all test records

3. **Known Issues to Monitor:**
   - Check for any calculation discrepancies
   - Monitor for data sync delays
   - Track performance metrics under load

4. **Future Test Cycles:**
   - Use this data as baseline
   - Add new assessment periods
   - Test data archival functionality
   - Test bulk update operations
