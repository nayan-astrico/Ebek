# CREATE_ASSESSMENT Module - Functional Test Cases

**Module:** Create Assessment (OSCE Procedure Management)
**URL:** `/create_assessment/`
**Related URLs:** `/upload-preview/`, `/upload-excel/`, `/fetch-assessments/`
**Last Updated:** November 29, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Test Cases - Initial Page Load](#test-cases---initial-page-load)
3. [Test Cases - Search & Filter](#test-cases---search--filter)
4. [Test Cases - Pagination](#test-cases---pagination)
5. [Test Cases - Excel Upload](#test-cases---excel-upload)
6. [Test Cases - Upload Validation](#test-cases---upload-validation)
7. [Test Cases - Error Handling](#test-cases---error-handling)
8. [Test Environment Setup](#test-environment-setup)
9. [Test Data & Templates](#test-data--templates)

---

## Overview

The Create Assessment module allows users to:
1. View existing OSCE procedures from Firestore
2. Search and filter procedures by name, status, category
3. Paginate through procedure lists
4. Upload new procedures via Excel file
5. Validate procedure structure before saving
6. Preview and correct data before final upload

**Key Components:**
- View: `create_assessment(request)` - Lines 110-141 in views.py
- Endpoints: `/upload-preview/`, `/upload-excel/`, `/fetch-assessments/`
- Template: `assessments/create_assessment.html`
- Helper: `parse_excel_to_json()` - Lines 49-108

---

## Test Cases - Initial Page Load

### CA-001: Page Load with Procedures (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-001 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Page loads with procedure list from Firestore |
| **Description** | User navigates to /create_assessment/ and page loads with procedures |
| **Preconditions** | 1. User is logged in as admin<br>2. Firestore contains 10+ procedures in ProcedureTable<br>3. All procedures have valid structure with examMetaData |
| **Test Steps** | 1. Navigate to http://localhost:8000/create_assessment/<br>2. Wait for page to fully load<br>3. Verify procedures table is visible<br>4. Verify columns: Procedure, Questions, Category, Actions<br>5. Verify first 5 procedures are displayed (pagination: 5 per page) |
| **Test Data** | User: admin@test.com, Password: Test@1234 |
| **Expected** | 1. Page loads in < 2 seconds<br>2. Procedures table visible with data<br>3. All 5 columns properly formatted<br>4. Pagination shows page 1 of N<br>5. Action buttons (Edit, Download) visible |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check browser console for errors. Verify Firestore connection working. |
| **Related Files** | assessments/views.py:create_assessment() (lines 110-141)<br>create_assessment.html |

---

### CA-002: Empty Procedure List (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-002 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Page shows empty state when no procedures exist |
| **Description** | If Firestore ProcedureTable has no documents, empty state is displayed |
| **Preconditions** | 1. User is logged in<br>2. Firestore ProcedureTable is empty or all procedures deleted<br>3. application running |
| **Test Steps** | 1. Delete all procedures from Firestore ProcedureTable<br>2. Navigate to /create_assessment/<br>3. Observe page state<br>4. Verify empty state message<br>5. Verify "Create Assessment" button still visible |
| **Test Data** | User: admin@test.com |
| **Expected** | 1. Page loads successfully<br>2. "No procedures found" or similar message shown<br>3. Create Assessment button enabled<br>4. Search bar present but grayed out or disabled |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if empty state message is user-friendly. Button should remain functional. |
| **Related Files** | create_assessment.html<br>assessments/views.py:create_assessment() |

---

### CA-003: Procedure Count Accuracy (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-003 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Question count accurately reflects examMetaData structure |
| **Description** | The "Questions" column shows correct count based on section_questions in examMetaData |
| **Preconditions** | 1. User logged in<br>2. At least 3 procedures in Firestore with varying question counts<br>3. Procedure 1: 5 questions<br>4. Procedure 2: 12 questions<br>5. Procedure 3: 20 questions |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Observe "Questions" column values<br>3. Click on Procedure 1, verify question count in details<br>4. Verify it matches value shown in table<br>5. Repeat for Procedures 2 and 3 |
| **Test Data** | Procedures with known question counts (5, 12, 20) |
| **Expected** | 1. Questions column shows: 5, 12, 20 respectively<br>2. When opened, detail view confirms counts<br>3. All counts accurate |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Potential bug: Code assumes examMetaData[0] exists. Test with procedure missing sections. |
| **Related Files** | assessments/views.py:create_assessment() (line 127)<br>parse_excel_to_json() |

---

### CA-004: Permission Check - Unauthorized User (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-004 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Unauthorized user cannot see Create Assessment button |
| **Description** | Student/nurse role user sees page but "Create Assessment" button is disabled/hidden |
| **Preconditions** | 1. Student user account exists<br>2. Student does NOT have 'bulk_upload_learners' or admin permission<br>3. User logged in as student |
| **Test Steps** | 1. Login as student user (e.g., student@test.com)<br>2. Navigate to /create_assessment/<br>3. Observe page content<br>4. Check for "Create Assessment" button<br>5. If visible, try to click it |
| **Test Data** | User: student@test.com (student role)<br>Password: Test@1234 |
| **Expected** | 1. Page loads (no 403 error)<br>2. Procedure list visible to read<br>3. "Create Assessment" button NOT visible/disabled<br>4. No way to access upload functionality |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Permission check done in template via user.get_all_permissions(). Should show button only if permission granted. |
| **Related Files** | create_assessment.html (lines 10-23)<br>assessments/models.py:EbekUser.get_all_permissions() |

---

### CA-005: Page Load Performance (P2)
| Field | Value |
|-------|-------|
| **Test ID** | CA-005 |
| **Category** | Create Assessment |
| **Priority** | P2 (Medium) |
| **Test Name** | Page load time acceptable with 100+ procedures |
| **Description** | Page loads and renders in reasonable time even with large procedure count |
| **Preconditions** | 1. User logged in<br>2. Firestore contains 100+ procedures<br>3. Network speed: 4G or faster |
| **Test Steps** | 1. Clear browser cache<br>2. Open DevTools Network tab<br>3. Navigate to /create_assessment/<br>4. Measure time until page interactive<br>5. Verify pagination works smoothly |
| **Test Data** | User: admin@test.com<br>Firestore: 100+ procedures |
| **Expected** | 1. Initial page load < 2 seconds<br>2. Page interactive < 3 seconds<br>3. Pagination responsive (no delay when clicking next)<br>4. Scroll smooth (not janky) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Monitor browser DevTools for performance metrics. Check Firestore query efficiency. |
| **Related Files** | assessments/views.py:create_assessment() (line 119)<br>Django Paginator (line 131-133) |

---

## Test Cases - Search & Filter

### CA-006: Search by Procedure Name (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-006 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Search filters procedures by name (case-insensitive) |
| **Description** | User can search procedures and get filtered results matching the search term |
| **Preconditions** | 1. User logged in<br>2. Procedures exist: "Vital Signs", "Wound Assessment", "Vital Monitoring"<br>3. At least 5+ other procedures |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Locate search input field<br>3. Type "vital" in search box<br>4. Observe procedure list updates<br>5. Verify only procedures with "vital" in name shown (case-insensitive)<br>6. Clear search, verify all procedures reappear |
| **Test Data** | Search term: "vital"<br>Expected matches: "Vital Signs", "Vital Monitoring" |
| **Expected** | 1. Search is case-insensitive<br>2. Results show only matching procedures<br>3. Pagination resets to page 1<br>4. Both "Vital Signs" and "Vital Monitoring" shown<br>5. Partial matches work (not exact match only) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Code filters on client-side for initial view, server-side via /fetch-assessments/ for dynamic loading. Both should work. |
| **Related Files** | assessments/views.py:create_assessment() (lines 125-127)<br>create_assessment.html (search filter logic) |

---

### CA-007: Search with No Results (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-007 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Search shows empty result when no matches |
| **Description** | Search returns empty state if no procedure matches search term |
| **Preconditions** | 1. User logged in<br>2. Procedures in system (at least 5)<br>3. None match the search term |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Type non-existent procedure name: "XYZ123NoMatch"<br>3. Observe results<br>4. Verify empty state message shown<br>5. Verify "Create Assessment" button still visible |
| **Test Data** | Search term: "XYZ123NoMatch" |
| **Expected** | 1. No results shown<br>2. "No procedures found" message displayed<br>3. Search field still active (can clear and search again)<br>4. Create Assessment button still accessible |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Empty state should be clear and not confusing. |
| **Related Files** | create_assessment.html |

---

### CA-008: Filter by Status (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-008 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Filter procedures by Active/Inactive status |
| **Description** | User can filter procedures showing only Active or only Inactive procedures |
| **Preconditions** | 1. User logged in<br>2. Procedures in Firestore:<br>   - 5 active procedures<br>   - 3 inactive procedures |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Click Filter button<br>3. Uncheck "Active" checkbox in filter panel<br>4. Click Apply Filters<br>5. Verify only inactive procedures shown<br>6. Uncheck "Inactive", check "Active"<br>7. Apply Filters again<br>8. Verify only active procedures shown |
| **Test Data** | Filter: Status = Active/Inactive |
| **Expected** | 1. Filter panel opens/closes correctly<br>2. Checkboxes work<br>3. Apply button filters correctly<br>4. Active filter shows 5 procedures<br>5. Inactive filter shows 3 procedures<br>6. Both checked shows all 8 |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify filter state persists when applying. Check filter applies correctly via API call. |
| **Related Files** | create_assessment.html (lines 91-177)<br>assessments/views.py:fetch_assessments() |

---

### CA-009: Filter by Category (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-009 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Filter procedures by category |
| **Description** | User can select one or multiple categories and see only procedures in those categories |
| **Preconditions** | 1. User logged in<br>2. Procedures with categories:<br>   - 4 procedures: "Core Skills"<br>   - 3 procedures: "Infection Control"<br>   - 2 procedures: "Documentation"<br>   - 1 procedure: "Communication" |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Click Filter button<br>3. In Category section, check "Core Skills"<br>4. Click Apply Filters<br>5. Verify 4 Core Skills procedures shown<br>6. Uncheck Core Skills, check Infection Control<br>7. Apply Filters<br>8. Verify 3 Infection Control procedures shown<br>9. Check both Core Skills AND Infection Control<br>10. Apply Filters<br>11. Verify 7 total procedures shown (4+3) |
| **Test Data** | Filter: Category = Core Skills, Infection Control, Documentation |
| **Expected** | 1. Category checkboxes selectable<br>2. Single category filter works<br>3. Multi-select filters work (OR logic)<br>4. Apply button executes correct filter<br>5. Counts accurate for each combination |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Multi-select should use OR logic (show procedures in ANY selected category). Verify this is implemented correctly. |
| **Related Files** | create_assessment.html (lines 91-177)<br>assessments/views.py:fetch_assessments() |

---

### CA-010: Combined Search and Filter (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-010 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Search and filter can be combined |
| **Description** | User can use search term AND category filter simultaneously |
| **Preconditions** | 1. User logged in<br>2. Procedures:<br>   - "Assessment Vital Signs" (Core Skills, active)<br>   - "Vital Monitoring Protocol" (Core Skills, inactive)<br>   - "Vital Signs Quick Check" (Communication, active)<br>   - "Other procedures..." |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Type "Vital" in search<br>3. Click Filter button<br>4. Check Category: "Core Skills"<br>5. Click Apply Filters<br>6. Observe results<br>7. Should show only procedures with "vital" AND "Core Skills" category<br>8. Change search to "Assessment"<br>9. Results should update accordingly |
| **Test Data** | Search: "Vital"<br>Filter: Category = Core Skills |
| **Expected** | 1. Results show only procedures matching BOTH search AND filter<br>2. Both "Assessment Vital Signs" and "Vital Monitoring Protocol" shown (both have "vital" and are Core Skills)<br>3. "Vital Signs Quick Check" NOT shown (not Core Skills)<br>4. Changing search updates results immediately |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify AND logic between search and filters (not OR). Check that pagination resets when filters change. |
| **Related Files** | create_assessment.html<br>assessments/views.py:fetch_assessments() |

---

## Test Cases - Pagination

### CA-011: Pagination - Navigate Pages (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-011 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Pagination allows navigation through procedure pages |
| **Description** | User can navigate between pages showing 5 procedures per page |
| **Preconditions** | 1. User logged in<br>2. Firestore contains 23 procedures (enough for multiple pages)<br>3. No search/filter applied |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Verify 5 procedures shown on page 1<br>3. Observe pagination controls<br>4. Click "Next" or go to page 2<br>5. Verify different 5 procedures shown (procedures 6-10)<br>6. Click "Next" again (page 3)<br>7. Verify procedures 11-15 shown<br>8. Click "Last" or page 5<br>9. Verify last 3 procedures shown (21-23)<br>10. Click "Previous"<br>11. Verify back to page 4 (procedures 16-20) |
| **Test Data** | Total procedures: 23<br>Per page: 5 |
| **Expected** | 1. Page 1 shows procedures 1-5<br>2. Page 2 shows procedures 6-10<br>3. Page 3 shows procedures 11-15<br>4. Page 4 shows procedures 16-20<br>5. Page 5 shows procedures 21-23<br>6. Navigation controls work (Previous/Next/Last/First)<br>7. Current page highlighted |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if pagination resets when search/filter applied. Verify page numbers shown correctly. |
| **Related Files** | assessments/views.py:create_assessment() (lines 131-133)<br>Django Paginator |

---

### CA-012: Pagination Reset on Search (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-012 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Pagination resets to page 1 when search applied |
| **Description** | When user performs search, results start from page 1 (not stay on current page) |
| **Preconditions** | 1. User logged in<br>2. 20+ procedures in system |
| **Test Steps** | 1. Navigate to /create_assessment/<br>2. Click to page 3<br>3. Type "test" in search box<br>4. Observe page number<br>5. Should reset to page 1 of search results<br>6. Verify first 5 matching results shown |
| **Test Data** | Navigate to page 3, then search |
| **Expected** | 1. Pagination resets to page 1<br>2. First 5 matching results shown<br>3. No results from previous page shown |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | This is important for UX - users expect search to reset pagination. |
| **Related Files** | create_assessment.html (search logic) |

---

## Test Cases - Excel Upload

### CA-013: Upload Panel Opens (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-013 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Upload panel opens when Create Assessment button clicked |
| **Description** | Clicking "Create Assessment" button opens upload panel overlay |
| **Preconditions** | 1. User logged in with admin permission<br>2. User on /create_assessment/ page<br>3. "Create Assessment" button visible |
| **Test Steps** | 1. Click "Create Assessment" button<br>2. Observe panel appearance<br>3. Verify upload form visible<br>4. Verify required fields shown:<br>   - File input (drag/drop area)<br>   - Procedure name input<br>   - Category dropdown<br>5. Verify buttons: Cancel, Upload<br>6. Verify close button (X) visible |
| **Test Data** | User: admin@test.com |
| **Expected** | 1. Panel slides in or appears<br>2. Overlay/backdrop visible<br>3. All form fields visible<br>4. Form is empty (ready for new entry)<br>5. Cancel button works (closes panel)<br>6. Focus set to file input |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check accessibility - focus management, keyboard support. Verify close button works. |
| **Related Files** | create_assessment.html (lines 240-411)<br>create_assessment.js:toggleUploadPanel() |

---

### CA-014: File Drag and Drop (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-014 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | File can be uploaded via drag and drop |
| **Description** | User can drag Excel file onto designated area and select it for upload |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Valid Excel file available on disk<br>4. File: valid_procedure.xlsx |
| **Test Steps** | 1. Open upload panel<br>2. Prepare Excel file with valid structure<br>3. Drag file onto drag-drop area in panel<br>4. Observe file selected<br>5. Verify file name shown<br>6. Verify Preview button appears |
| **Test Data** | File: valid_procedure.xlsx (valid Excel format with required columns) |
| **Expected** | 1. Drag and drop area is interactive<br>2. File accepted (shows file name)<br>3. File size shown (e.g., "45 KB")<br>4. Visual feedback on drag (highlight)<br>5. Preview button becomes clickable |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check browser console for any JS errors. Verify drag-drop works across browsers. |
| **Related Files** | create_assessment.html (lines 240-411)<br>create_assessment.js:previewExcel() |

---

### CA-015: File Browse/Select (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-015 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | File can be selected via browse button |
| **Description** | User can click browse button to select file from computer |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Excel file available |
| **Test Steps** | 1. Click on file input or "Browse" button<br>2. File dialog appears<br>3. Navigate to test file location<br>4. Select valid_procedure.xlsx<br>5. Click Open/Select<br>6. Verify file is selected in upload panel |
| **Test Data** | File: valid_procedure.xlsx |
| **Expected** | 1. File dialog opens<br>2. Can navigate file system<br>3. File selected shows in input<br>4. File size shown<br>5. Preview button enabled |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Test on different browsers if possible. |
| **Related Files** | create_assessment.html (file input element) |

---

### CA-016: Preview Excel Data (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-016 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Excel data preview shows first 10 rows |
| **Description** | When user clicks Preview after selecting file, first 10 rows of data are shown in preview table |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Valid Excel file selected: valid_procedure.xlsx<br>4. File has columns: Section, Parameters, Indicators, Category, Marks, Critical<br>5. File has 15+ data rows |
| **Test Steps** | 1. Select valid Excel file<br>2. Click "Preview" button<br>3. Wait for preview to load<br>4. Observe preview table<br>5. Verify first 10 rows displayed<br>6. Count rows shown (should be 10 or fewer if file has < 10 rows)<br>7. Verify all columns shown: Section, Parameters, Indicators, Category, Marks, Critical<br>8. Verify row numbers shown |
| **Test Data** | File: valid_procedure.xlsx with 15 rows |
| **Expected** | 1. Preview table appears below file input<br>2. Exactly 10 rows shown (or all if < 10)<br>3. All 6 columns visible<br>4. Data matches Excel file<br>5. No validation errors shown (data is valid)<br>6. "Upload" and "Cancel" buttons shown at bottom |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Endpoint: /upload-preview/ (POST). Check network response in DevTools. |
| **Related Files** | assessments/views.py:upload_preview() (lines 6607-6674)<br>create_assessment.html (preview section)<br>create_assessment.js:previewExcel() |

---

### CA-017: Required Fields Validation (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-017 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Validation errors shown for missing required fields |
| **Description** | If Excel is missing required columns (Section, Parameters, Marks, Critical), validation errors displayed |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Excel file with missing required column: no "Marks" column<br>4. File named: missing_marks.xlsx |
| **Test Steps** | 1. Select missing_marks.xlsx (no "Marks" column)<br>2. Click Preview<br>3. Observe validation section<br>4. Verify error message shown<br>5. Error should indicate missing "Marks" column<br>6. Preview table should NOT be shown or be grayed out |
| **Test Data** | File: missing_marks.xlsx (missing Marks column) |
| **Expected** | 1. Validation section appears with errors<br>2. Error message: "Missing required column: Marks"<br>3. Preview not shown or disabled<br>4. "Upload" button disabled<br>5. User can correct file and try again |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Validation happens in upload_preview endpoint. Check DevTools Network for request/response. |
| **Related Files** | assessments/views.py:upload_preview() (lines 6641-6653)<br>create_assessment.js:previewExcel() |

---

### CA-018: Marks Format Validation (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-018 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Marks column must contain numeric values |
| **Description** | Validation fails if Marks column contains non-numeric values |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Excel file with invalid marks: marks_invalid.xlsx<br>4. File has row with Marks = "ABC" (text, not number) |
| **Test Steps** | 1. Select marks_invalid.xlsx<br>2. Click Preview<br>3. Observe validation errors<br>4. Verify error indicates row number and issue<br>5. Error should show: "Row 5: Marks must be an integer"<br>6. Preview table should show error highlight on that row |
| **Test Data** | File: marks_invalid.xlsx<br>Row 5: Marks = "ABC" |
| **Expected** | 1. Validation error shown<br>2. Error specifies row number (5)<br>3. Error specifies field (Marks)<br>4. Error specifies issue (must be integer)<br>5. Upload button disabled until corrected<br>6. Row 5 highlighted in red or marked with error icon |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Validation in upload_preview endpoint. Check if conversion to int succeeds for numeric strings (e.g., "10.5" → 10). |
| **Related Files** | assessments/views.py:upload_preview() (lines 6645-6650) |

---

### CA-019: Critical Field Validation (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-019 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Critical column must be boolean or numeric (0/1, true/false) |
| **Description** | Validation fails if Critical column has invalid boolean values |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Excel file: critical_invalid.xlsx<br>4. Has row with Critical = "maybe" (invalid boolean) |
| **Test Steps** | 1. Select critical_invalid.xlsx<br>2. Click Preview<br>3. Observe validation errors<br>4. Verify error for invalid Critical value<br>5. Error should indicate expected format: true/false/1/0 |
| **Test Data** | File: critical_invalid.xlsx<br>Row 8: Critical = "maybe" |
| **Expected** | 1. Validation error shown<br>2. Error specifies Critical field<br>3. Error explains valid values: true, false, 1, 0<br>4. Row 8 highlighted/marked<br>5. Upload disabled until corrected |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Code should accept: true/false (strings), 1/0 (numbers). Check parsing logic. |
| **Related Files** | assessments/views.py:upload_preview() (lines 6648-6652)<br>parse_excel_to_json() (lines 80-100) |

---

## Test Cases - Upload Validation

### CA-020: Procedure Name Required (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-020 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Procedure name is required before upload |
| **Description** | User cannot upload without entering a procedure name |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Valid Excel file selected and previewed<br>4. Procedure name field is empty |
| **Test Steps** | 1. Select and preview valid Excel file<br>2. Leave "Procedure Name" field empty<br>3. Verify Category field is filled<br>4. Click "Upload" button<br>5. Observe validation behavior |
| **Test Data** | Procedure Name: (empty)<br>Category: "Core Skills"<br>File: valid_procedure.xlsx |
| **Expected** | 1. Upload button disabled if name is empty<br>2. OR error shown: "Procedure name is required"<br>3. File not uploaded<br>4. Panel remains open for correction |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Frontend validation before sending to server. Check form validation. |
| **Related Files** | create_assessment.html (procedure name input)<br>create_assessment.js:submitUpload() |

---

### CA-021: Category Required (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-021 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Category must be selected before upload |
| **Description** | User cannot upload without selecting a category |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Valid Excel selected and previewed<br>4. Category dropdown not selected (blank) |
| **Test Steps** | 1. Select and preview valid Excel file<br>2. Enter Procedure Name: "Test Procedure"<br>3. Do NOT select Category (leave blank)<br>4. Click "Upload" button<br>5. Observe validation |
| **Test Data** | Procedure Name: "Test Procedure"<br>Category: (not selected)<br>File: valid_procedure.xlsx |
| **Expected** | 1. Upload button disabled OR shows error<br>2. Error message: "Please select a category"<br>3. File not uploaded<br>4. Focus moved to Category field |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Category is critical for filtering/organization in system. |
| **Related Files** | create_assessment.html (category dropdown)<br>create_assessment.js:submitUpload() |

---

### CA-022: Procedure Name Uniqueness Check (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-022 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Duplicate procedure names are rejected |
| **Description** | Cannot create procedure with name that already exists in Firestore |
| **Preconditions** | 1. User logged in<br>2. Procedure "Vital Signs Assessment" already exists in Firestore<br>3. Upload panel open<br>4. Valid Excel file selected and previewed |
| **Test Steps** | 1. Select valid Excel file<br>2. Enter Procedure Name: "Vital Signs Assessment" (duplicate name)<br>3. Select Category: "Core Skills"<br>4. Click "Upload" button<br>5. Observe server response |
| **Test Data** | Procedure Name: "Vital Signs Assessment" (already exists)<br>Category: "Core Skills"<br>File: valid_procedure.xlsx |
| **Expected** | 1. Upload request sent to server<br>2. Server queries Firestore for existing procedure<br>3. Duplicate found → Error response<br>4. Error message shown: "Procedure 'Vital Signs Assessment' already exists. Please use a different name."<br>5. Panel remains open<br>6. User can edit name and retry |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Uniqueness check in upload_excel() at lines 6813-6823. Race condition possible if two simultaneous uploads of same name. |
| **Related Files** | assessments/views.py:upload_excel() (lines 6813-6823)<br>create_assessment.js:submitUpload() |

---

### CA-023: Excel Structure Conversion (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-023 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Excel data correctly converted to Firebase structure |
| **Description** | Excel data with Parameters and Indicators correctly mapped to examMetaData structure |
| **Preconditions** | 1. User logged in<br>2. Excel file with structure:<br>   Section: "Physical Exam"<br>   Parameters: "Heart Rate", "Blood Pressure"<br>   Indicators: (sub-questions for each)<br>   Marks: 5, 8<br>   Critical: true, false |
| **Test Steps** | 1. Select Excel with multi-level structure<br>2. Preview data<br>3. Upload with Procedure Name: "Cardiac Assessment"<br>4. Wait for successful upload<br>5. Verify upload success message<br>6. Go to Firestore console<br>7. Find "Cardiac Assessment" document<br>8. Examine examMetaData structure<br>9. Verify correct conversion |
| **Test Data** | File: cardiac_assessment.xlsx<br>Procedure Name: "Cardiac Assessment"<br>Category: "Core Skills" |
| **Expected** | 1. Upload succeeds<br>2. Success message shown<br>3. New document created in Firestore ProcedureTable<br>4. Document structure:<br>   - procedureName: "Cardiac Assessment"<br>   - examMetaData[0].section_name: "Physical Exam"<br>   - examMetaData[0].section_questions[0]:<br>     * question: "Heart Rate"<br>     * right_marks_for_question: 5<br>     * critical: true<br>   - examMetaData[0].section_questions[1]:<br>     * question: "Blood Pressure"<br>     * right_marks_for_question: 8<br>     * critical: false |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Complex conversion logic in parse_excel_to_json() (lines 49-108). Verify all data mapped correctly. |
| **Related Files** | assessments/views.py:parse_excel_to_json() (lines 49-108)<br>upload_excel() (line 6840) |

---

## Test Cases - Error Handling

### CA-024: Invalid File Format (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CA-024 |
| **Category** | Create Assessment |
| **Priority** | P0 (Critical) |
| **Test Name** | Non-Excel files are rejected |
| **Description** | User cannot upload CSV, PDF, or other non-Excel files |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Non-Excel files available (PDF, CSV, TXT, DOC) |
| **Test Steps** | 1. Try to select procedure_data.pdf<br>2. Observe file input behavior<br>3. Try CSV file: procedures.csv<br>4. Try TXT file: procedures.txt<br>5. Verify rejection or validation error |
| **Test Data** | Files: procedure.pdf, procedures.csv, procedures.txt |
| **Expected** | 1. File input rejects non-Excel files<br>2. OR preview fails with clear error<br>3. Error message: "Only Excel files (.xlsx, .xls) are supported"<br>4. User cannot proceed with upload |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if frontend restricts file type via input accept attribute. Also validate server-side. |
| **Related Files** | create_assessment.html (file input)<br>assessments/views.py:upload_preview() |

---

### CA-025: File Upload Error - Server Issue (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CA-025 |
| **Category** | Create Assessment |
| **Priority** | P1 (High) |
| **Test Name** | Graceful error handling when server is unavailable |
| **Description** | If Firestore or server is down, clear error message shown to user |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Valid Excel selected and previewed<br>4. Firestore connection temporarily unavailable (simulated) |
| **Test Steps** | 1. Stop Firestore service or block connection<br>2. Select and preview valid Excel file<br>3. Fill in Procedure Name and Category<br>4. Click "Upload"<br>5. Observe error handling<br>6. Restore Firestore connection<br>7. Try upload again |
| **Test Data** | Valid Excel file, with Firestore unavailable |
| **Expected** | 1. Upload fails gracefully<br>2. User sees error message (not blank page or 500 error)<br>3. Error message is clear: "Unable to save procedure. Please check your connection and try again."<br>4. Panel remains open<br>5. User can retry after service restored |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Simulating Firestore outage is difficult in test environment. May need to manually test with exception raising in code. |
| **Related Files** | assessments/views.py:upload_excel() (try-except at line 6875) |

---

### CA-026: Large File Upload (P2)
| Field | Value |
|-------|-------|
| **Test ID** | CA-026 |
| **Category** | Create Assessment |
| **Priority** | P2 (Medium) |
| **Test Name** | Large Excel files are handled or rejected appropriately |
| **Description** | System handles or rejects very large Excel files gracefully |
| **Preconditions** | 1. User logged in<br>2. Upload panel open<br>3. Large Excel file available: large_procedures.xlsx (20MB)<br>4. Medium Excel file: medium_procedures.xlsx (3MB) |
| **Test Steps** | 1. Try to upload 20MB file<br>2. Observe behavior (rejection or processing)<br>3. Try 3MB file<br>4. Verify upload succeeds or show appropriate message |
| **Test Data** | Large file: 20MB (1000+ procedures)<br>Medium file: 3MB (500 procedures) |
| **Expected** | 1. Large file (20MB) shows clear limit message<br>2. Message: "File too large. Maximum size: 10MB"<br>3. OR proceeds with upload and shows progress<br>4. Medium file (3MB) uploads successfully<br>5. Upload completes in reasonable time (< 30 seconds) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if file size limit is enforced frontend or backend. Forms.py shows 10MB limit. |
| **Related Files** | assessments/forms.py:ExcelUploadForm<br>create_assessment.js:previewExcel() |

---

## Test Environment Setup

### Database Setup

**Firestore Collections Needed:**

1. **ProcedureTable** (Main collection)
   ```json
   {
     "procedureName": "Vital Signs Assessment",
     "category": "Core Skills",
     "examMetaData": [
       {
         "section_name": "Initial Assessment",
         "section_questions": [
           {
             "question": "Check Heart Rate",
             "right_marks_for_question": 10,
             "answer_scored": 0,
             "critical": true,
             "category": "Core Skills",
             "sub_section_questions_present": false,
             "sub_section_questions": []
           }
         ]
       }
     ],
     "notes": "",
     "active": true
   }
   ```

2. **Required Test Procedures:**
   - "Vital Signs Assessment" (Core Skills, active, 5 questions)
   - "Infection Control Protocol" (Infection Control, active, 8 questions)
   - "Documentation Review" (Documentation, inactive, 3 questions)
   - "Communication Skills" (Communication, active, 6 questions)
   - "Wound Assessment" (Core Skills, active, 12 questions)
   - "Vital Monitoring" (Core Skills, active, 7 questions)
   - "Vital Signs Quick Check" (Communication, active, 4 questions)

### User Setup

**Admin User (for create assessment):**
```
Email: admin@test.com
Password: Test@1234
Role: super_admin OR ebek_admin
Permissions: bulk_upload_learners (checked)
```

**Student User (for permission test):**
```
Email: student@test.com
Password: Test@1234
Role: student
Permissions: None
```

---

## Test Data & Templates

### Sample Excel File Template

**Column Headers Required:**
```
Section | Parameters | Indicators | Category | Marks | Critical
```

**Example Row:**
```
Vital Signs | Heart Rate Assessment | Check pulse at wrist | Core Skills | 10 | true
Vital Signs | Heart Rate Assessment | Count beats for 1 minute | Core Skills | 5 | true
Vital Signs | Blood Pressure Assessment | Explain cuff placement | Communication | 3 | false
```

### Expected Excel File Validation Rules

| Field | Format | Validation |
|-------|--------|-----------|
| **Section** | String (max 255) | Required if Parameters present |
| **Parameters** | String (max 500) | Required, no duplicates within section |
| **Indicators** | String (max 500) | Optional (can be empty) |
| **Category** | Enum: Core Skills, Infection Control, Documentation, Communication, Critical Thinking, Pre-Procedure | Must match allowed categories |
| **Marks** | Integer or Float | Required, must be numeric, > 0 |
| **Critical** | Boolean | true/false, yes/no, 1/0 - case insensitive |

### Browser Compatibility

**Browsers to Test:**
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

---

## Success Criteria

### All Tests Must Pass
- ✅ CA-001 to CA-026 show "Pass" status
- ✅ No unhandled errors in browser console
- ✅ No 500/404 errors on server
- ✅ All validation messages clear and helpful
- ✅ Upload process completes in < 10 seconds

### Critical Path (P0 Tests)
- ✅ CA-001: Page loads with procedures
- ✅ CA-004: Permission checks work
- ✅ CA-006: Search filters correctly
- ✅ CA-016: Preview shows data
- ✅ CA-017: Validation catches missing fields
- ✅ CA-018: Marks validation works
- ✅ CA-020: Procedure name required
- ✅ CA-021: Category required
- ✅ CA-022: Duplicate names rejected
- ✅ CA-024: Invalid files rejected

---

**Document Version:** 1.0
**Last Updated:** November 29, 2025
**Module:** Create Assessment (/create_assessment/)
**Status:** Ready for Testing
