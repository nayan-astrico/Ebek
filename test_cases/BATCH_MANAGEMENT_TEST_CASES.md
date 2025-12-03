# BATCH_MANAGEMENT Module - Functional Test Cases

**Module:** Batch Management (Batch List & Management)
**URL:** `/batch-management/`
**Related URLs:** `/batch-management/<batch_id>/`, `/api/batches/create/`, `/api/batches/<batch_id>/update/`
**Last Updated:** December 1, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Test Cases - Initial Page Load](#test-cases---initial-page-load)
3. [Test Cases - Create Batch](#test-cases---create-batch)
4. [Test Cases - Search Functionality](#test-cases---search-functionality)
5. [Test Cases - Filter Functionality](#test-cases---filter-functionality)
6. [Test Cases - Pagination](#test-cases---pagination)
7. [Test Cases - Status Management](#test-cases---status-management)
8. [Test Cases - Edit Batch](#test-cases---edit-batch)
9. [Test Cases - Error Handling](#test-cases---error-handling)
10. [Test Environment Setup](#test-environment-setup)
11. [Test Data](#test-data)

---

## Overview

The Batch Management module allows administrators to:
1. View all training batches in the system
2. Create new batches with learners and courses
3. Search for batches by name
4. Filter batches by unit type (Hospital/Institution)
5. Edit batch information and manage learners/courses
6. Toggle batch active/inactive status
7. Paginate through large batch lists
8. View detailed batch information

**Key Features:**
- Batch list table with status indicators
- Create batch side panel with unit selection and learner multi-select
- Filter panel with unit type filtering
- Batch table with columns: Batch Name, Year, Semester, Unit Type, Unit Name, Learners, Status, Actions
- Status toggle with confirmation modal for marking inactive
- Search functionality with instant filtering
- Pagination support (lazy loading with "Show More")
- Unit Type dropdown with Hospital/Institution options
- Learner multi-select with search filtering
- Batch detail view for editing learners and courses

**Key Models:**
- `Batch` - Batch records containing learners
- `Unit` - Hospital or Institution reference
- `Learner` - Student/Nurse records linked to batches
- `Course` - Course references for batches
- Firebase sync for real-time data

---

## Test Cases - Initial Page Load

### BM-001: Page Load with Batches List (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BM-001 |
| **Category** | Batch Management |
| **Priority** | P0 (Critical) |
| **Test Name** | Page loads with batches list from database |
| **Description** | User navigates to /batch-management/ and page loads with batches table showing existing batches |
| **Preconditions** | 1. User is logged in as admin with batch management permissions<br>2. At least 5 batches exist in database<br>3. Database connection working<br>4. User has "view batches" permission |
| **Test Steps** | 1. Navigate to http://localhost:8000/batch-management/<br>2. Wait for page to fully load (< 3 seconds)<br>3. Verify page title "Batches" is visible<br>4. Verify subtitle "Manage your training batches" visible<br>5. Verify "Add Batch" button visible<br>6. Verify search bar visible with placeholder "Search batches..."<br>7. Verify filter button with "Filters" text visible<br>8. Verify batches table is displayed<br>9. Verify table columns: Batch Name, Year, Semester, Unit Type, Unit Name, Learners, Status, Actions<br>10. Verify at least 5 batches listed in table<br>11. Check browser console for JavaScript errors |
| **Test Data** | User: admin@test.com<br>Pre-existing: 5+ batches with various unit types |
| **Expected** | 1. Page loads in < 3 seconds<br>2. Header "Batches" visible<br>3. Subtitle text visible<br>4. Add Batch button enabled and functional<br>5. Batches table shows 5+ batches<br>6. All table columns visible<br>7. Status badges displayed (Active/Inactive)<br>8. Edit action button visible for each row<br>9. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify lazy loading pagination - initial page should show 10 batches with "Show More" button. Check that batch data from Firebase/database loads correctly. |
| **Related Files** | assessments/views.py:batch_management()<br>assessments/models.py:Batch<br>batch_management.html (lines 89-334)<br>assessments/static/assessments/css/list.css |

---

### BM-002: Empty State When No Batches Exist (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-002 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Empty state shown when no batches exist |
| **Description** | If no Batch records exist in database, appropriate empty message displayed with CTA |
| **Preconditions** | 1. User is logged in as admin<br>2. All Batch records deleted (or fresh database)<br>3. Page loaded |
| **Test Steps** | 1. Delete all batches from database (or use fresh DB)<br>2. Navigate to /batch-management/<br>3. Observe batches table area<br>4. Verify empty state message shown<br>5. Verify empty state has icon (box icon)<br>6. Verify message: "No batches found"<br>7. Verify subtitle: "Get started by creating your first batch"<br>8. Verify "Create Batch" button visible in empty state<br>9. Click "Create Batch" button in empty state<br>10. Verify create batch side panel opens |
| **Test Data** | No existing Batch records |
| **Expected** | 1. Empty state message shown<br>2. Box icon displayed (#cbd5e0 color)<br>3. "No batches found" heading visible<br>4. Subtitle text visible<br>5. Create Batch button visible and clickable<br>6. Create batch panel opens on button click |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Empty state provides good UX and guides user to create first batch. Verify styling matches design system. |
| **Related Files** | batch_management.html (lines 320-333 - empty state)<br>assessments/views.py:batch_management() |

---

### BM-003: Batch Data Displayed Correctly (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-003 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Batch data displays all required fields correctly |
| **Description** | Each batch row shows: name, year, semester, unit type, unit name, learner count, and status badge |
| **Preconditions** | 1. User is logged in<br>2. Batch "B-2025-1-SEM1" exists with:<br>   - Name: B-2025-1-SEM1<br>   - Year: 2025<br>   - Semester: 1<br>   - Unit Type: Institution<br>   - Unit Name: DJ Sanghvi College<br>   - Learner Count: 45<br>   - Status: Active<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate batch "B-2025-1-SEM1" in table<br>3. Verify batch name: "B-2025-1-SEM1"<br>4. Verify year: "2025"<br>5. Verify semester: "Semester 1" or "1"<br>6. Verify unit type: "Institution"<br>7. Verify unit name: "DJ Sanghvi College"<br>8. Verify learner count: "45"<br>9. Verify status badge displayed<br>10. Verify status shows "Active" (green badge)<br>11. Verify Edit button present<br>12. Verify all data visible in one row without truncation |
| **Test Data** | Batch: B-2025-1-SEM1<br>Year: 2025, Semester: 1<br>Unit: DJ Sanghvi College (Institution)<br>Learners: 45 |
| **Expected** | 1. All batch fields displayed correctly<br>2. Status badge shows "Active" with green background<br>3. Edit action button present and styled correctly<br>4. Year formatted as "2025"<br>5. Semester formatted as "Semester 1"<br>6. Unit Type capitalized: "Institution"<br>7. All data visible without truncation |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check that long unit names don't truncate. Verify formatting of year and semester fields. |
| **Related Files** | batch_management.html (lines 290-318 - table rendering)<br>assessments/views.py:batch_management() |

---

## Test Cases - Create Batch

### BM-004: Create Batch Panel Opens (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-004 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Create batch side panel opens on button click |
| **Description** | Clicking "Add Batch" button opens a side panel form to create new batch |
| **Preconditions** | 1. User is logged in as admin<br>2. Page loaded at /batch-management/<br>3. Side panel not already open |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate "Add Batch" button in header<br>3. Click "Add Batch" button<br>4. Observe side panel slides in from right<br>5. Verify panel title shows "Add New Batch"<br>6. Verify form is empty (except defaults)<br>7. Verify "Batch Name" field visible<br>8. Verify "Year of Batch" dropdown visible<br>9. Verify "Unit Type" dropdown visible<br>10. Verify "Semester" dropdown visible<br>11. Verify "Unit" field visible<br>12. Verify "Learners" multi-select field visible<br>13. Verify "Create Batch" button visible at bottom<br>14. Verify "Cancel" button visible<br>15. Verify close button (X) present in panel header<br>16. Verify overlay appears behind panel |
| **Test Data** | None required |
| **Expected** | 1. Side panel opens smoothly (< 500ms)<br>2. Panel title: "Add New Batch"<br>3. Form fields empty and ready for input<br>4. Submit button text: "Create Batch"<br>5. All form sections visible on scroll<br>6. Overlay darkens background<br>7. Close button functional |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check side panel styling - should slide from right with smooth animation. Verify overlay opacity is correct (0.5). |
| **Related Files** | batch_management.html (lines 122-229 - side panel)<br>batch_management.html (lines 1656-1677 - toggle panel JS) |

---

### BM-005: Create Batch with Unit Type Selection (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BM-005 |
| **Category** | Batch Management |
| **Priority** | P0 (Critical) |
| **Test Name** | Create batch requires valid unit type selection |
| **Description** | User can select unit type (Hospital/Institution) and available units load based on selection |
| **Preconditions** | 1. User is logged in as admin<br>2. Create batch side panel open<br>3. At least 3 hospitals and 3 institutions exist in database<br>4. Database connection working |
| **Test Steps** | 1. Open create batch side panel<br>2. Verify "Unit Type" dropdown shows "Select Unit Type"<br>3. Click "Unit Type" dropdown<br>4. Verify options available: "Hospital", "Institution"<br>5. Select "Hospital"<br>6. Verify "Unit" field becomes enabled<br>7. Verify units dropdown loads with hospital options<br>8. Verify hospitals list displayed (name visible)<br>9. Select "City Hospital" from units<br>10. Verify learners field becomes enabled<br>11. Verify learner list loads for Hospital<br>12. Click Unit Type again and select "Institution"<br>13. Verify units dropdown updates with institutions<br>14. Verify learners field resets<br>15. Verify new learner list loads for Institution |
| **Test Data** | Unit Type: Hospital → Select "City Hospital"<br>Unit Type: Institution → Select "DJ Sanghvi College" |
| **Expected** | 1. Unit Type dropdown opens with 2 options<br>2. Selecting Unit Type enables Unit field<br>3. Units list loads based on selected type<br>4. Hospital units show hospital names<br>5. Institution units show institution names<br>6. Learners field populates after unit selection<br>7. Switching unit type updates unit options<br>8. Learner list updates when unit type changes |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify API calls to /fetch-hospitals/ and /fetch-institutes/ work correctly. Check that unit dropdown is searchable. |
| **Related Files** | batch_management.html (lines 148-171 - unit type & unit selection)<br>batch_management.html (lines 1679-1733 - unit type change handler)<br>assessments/views.py |

---

### BM-006: Create Batch with Learner Selection (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BM-006 |
| **Category** | Batch Management |
| **Priority** | P0 (Critical) |
| **Test Name** | Create batch with multiple learner selection |
| **Description** | User can select multiple learners from multi-select dropdown and create batch |
| **Preconditions** | 1. User is logged in as admin<br>2. Create batch side panel open<br>3. Unit type and unit selected<br>4. At least 10 learners available in selected unit<br>5. Database connection working |
| **Test Steps** | 1. Fill in batch name: "B-2025-BATCH-1"<br>2. Select year: "2025"<br>3. Select unit type: "Institution"<br>4. Select unit: "DJ Sanghvi College"<br>5. Click learners dropdown<br>6. Verify "Select All" checkbox visible<br>7. Verify learner list shows available learners<br>8. Search for learner by name: "John"<br>9. Verify filtered results show matching learners<br>10. Select 5 learners individually by clicking checkboxes<br>11. Verify selected tags appear above field<br>12. Verify count shown for multiple selections (e.g., "Selected Learners (5)")<br>13. Verify "Select All" checkbox checks all visible learners<br>14. Click "Create Batch" button<br>15. Verify batch created successfully |
| **Test Data** | Batch Name: B-2025-BATCH-1<br>Unit: DJ Sanghvi College<br>Learners: 5 selected |
| **Expected** | 1. Learner dropdown opens with full list<br>2. Search filters learners by name/email<br>3. Checkboxes toggle learner selection<br>4. Selected learner tags appear below field<br>5. Summary tag shows "Selected Learners (5)" when >5 selected<br>6. Select All checkbox works correctly<br>7. Batch created with all selected learners<br>8. Success message displayed<br>9. Side panel closes<br>10. New batch visible in table |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify multi-select dropdown closes on outside click. Check that learner search is case-insensitive. Verify "Select All" behavior when filtering. |
| **Related Files** | batch_management.html (lines 194-218 - learner multi-select)<br>batch_management.html (lines 1821-1943 - learner handling)<br>assessments/views.py:batch_create() |

---

### BM-007: Create Batch Validation (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-007 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Create batch form validates all required fields |
| **Description** | Form prevents submission with missing required fields and shows error messages |
| **Preconditions** | 1. User is logged in as admin<br>2. Create batch side panel open<br>3. Form is empty |
| **Test Steps** | 1. Leave all fields blank<br>2. Click "Create Batch" button<br>3. Verify error message: "Batch name is required" (red text below field)<br>4. Enter batch name: "B-TEST"<br>5. Click "Create Batch" again<br>6. Verify error message: "Unit type is required"<br>7. Select Unit Type: "Institution"<br>8. Click "Create Batch" again<br>9. Verify error message: "Unit is required"<br>10. Select Unit: "DJ Sanghvi College"<br>11. Click "Create Batch" again<br>12. Verify error message: "Please select at least one learner"<br>13. Select 1 learner<br>14. Click "Create Batch" again<br>15. Verify no error messages<br>16. Verify batch created successfully |
| **Test Data** | Batch Name: B-TEST<br>Unit Type: Institution |
| **Expected** | 1. Error messages appear when required fields missing<br>2. Error text color: #e53e3e (red)<br>3. Error messages appear below respective fields<br>4. No API call made when validation fails<br>5. Error messages clear when field filled<br>6. Form submits successfully when all fields valid |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify validation happens client-side before API submission. Check that error messages are replaced when corrected. |
| **Related Files** | batch_management.html (lines 2016-2032 - form validation)<br>batch_management.html (lines 2081-2085 - error display) |

---

## Test Cases - Search Functionality

### BM-008: Search Batches by Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-008 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Search filters batch list by batch name |
| **Description** | User can search for batches by name and results filter in real-time |
| **Preconditions** | 1. User is logged in<br>2. Batches exist with names:<br>   - "B-2025-SEM1-A"<br>   - "B-2025-SEM2-A"<br>   - "B-2024-SEM1-B"<br>   - "Training Batch XYZ"<br>3. Page loaded at /batch-management/ |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate search input: "Search batches..."<br>3. Leave search empty - verify all batches displayed (4 shown)<br>4. Click search input<br>5. Type "SEM1"<br>6. Verify search results update (2 batches: "B-2025-SEM1-A", "B-2024-SEM1-B")<br>7. Clear search and type "2025"<br>8. Verify results show only 2025 batches (2 batches)<br>9. Type "Training"<br>10. Verify results show only "Training Batch XYZ"<br>11. Type "NonExistent"<br>12. Verify no results and empty state message shown<br>13. Clear search completely<br>14. Verify all batches reappear |
| **Test Data** | Search terms: "SEM1", "2025", "Training", "NonExistent" |
| **Expected** | 1. Search filters results in real-time (< 500ms)<br>2. Case-insensitive search<br>3. Partial matches work (e.g., "SEM" matches "SEM1")<br>4. Results update without page reload<br>5. Empty state shows when no results<br>6. Clearing search shows all batches again |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify search is triggered on input change, not on enter key. Check that pagination resets when searching. |
| **Related Files** | batch_management.html (lines 110-112 - search input)<br>batch_management.html (lines 1519-1523 - search event listener) |

---

## Test Cases - Filter Functionality

### BM-009: Filter Batches by Unit Type (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-009 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Filter batches by unit type (Hospital/Institution) |
| **Description** | User can open filter panel and filter batches by unit type |
| **Preconditions** | 1. User is logged in<br>2. Batches exist with:<br>   - 3 Hospital batches<br>   - 5 Institution batches<br>3. Page loaded at /batch-management/ |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate "Filters" button in search bar<br>3. Click "Filters" button<br>4. Verify filter panel opens from right<br>5. Verify panel title: "Filter Batches"<br>6. Verify "Unit Type" section visible<br>7. Verify checkbox for "Hospital"<br>8. Verify checkbox for "Institution"<br>9. Check "Hospital" checkbox<br>10. Click "Apply filter" button<br>11. Verify filter panel closes<br>12. Verify only 3 hospital batches displayed in table<br>13. Click "Filters" again<br>14. Verify "Hospital" checkbox still checked<br>15. Check "Institution" checkbox (both now checked)<br>16. Click "Apply filter"<br>17. Verify all 8 batches displayed<br>18. Click "Filters" and verify "Clear All" button<br>19. Click "Clear All"<br>20. Verify both checkboxes unchecked<br>21. Click "Apply filter"<br>22. Verify all batches shown |
| **Test Data** | Filter: Unit Type = Hospital<br>Filter: Unit Type = Hospital & Institution |
| **Expected** | 1. Filter panel opens smoothly<br>2. Unit Type options: Hospital, Institution<br>3. Filtering works correctly<br>4. Only matching batches displayed<br>5. Filter badge shows count of applied filters<br>6. "Clear All" resets all filters<br>7. Results update without page reload<br>8. Filter state persists on panel reopen |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify filter badge displays correct count. Check that "Select All" checkbox toggles all options. |
| **Related Files** | batch_management.html (lines 232-287 - filter panel)<br>batch_management.html (lines 1968-2001 - filter handling) |

---

## Test Cases - Pagination

### BM-010: Pagination with Show More Button (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-010 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Pagination loads more batches using Show More button |
| **Description** | Batches load lazily with "Show More" button when more results exist |
| **Preconditions** | 1. User is logged in<br>2. At least 25 batches exist in database<br>3. Page loaded at /batch-management/ |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Verify initial load shows 10 batches in table<br>3. Verify "Show More" button visible below table<br>4. Count visible batches: should be 10<br>5. Click "Show More" button<br>6. Verify loading spinner appears briefly<br>7. Wait for additional batches to load (< 2 seconds)<br>8. Verify spinner disappears<br>9. Count visible batches: should be 20<br>10. Verify "Show More" button still visible<br>11. Click "Show More" again<br>12. Verify additional batches load<br>13. Count visible batches: should be 30<br>14. If remaining batches < 10, verify "Show More" button hides<br>15. Scroll to top and verify previously loaded batches still visible |
| **Test Data** | 25+ batches in database |
| **Expected** | 1. Initial page shows 10 batches<br>2. "Show More" button appears when more exist<br>3. Each click loads 10 additional batches<br>4. Loading spinner visible during load<br>5. Batches append to existing list (not replace)<br>6. Button hides when all batches loaded<br>7. Pagination happens without page reload<br>8. Scroll position preserved |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify API pagination endpoint returns correct page size. Check that button disabled state during loading. |
| **Related Files** | batch_management.html (lines 317-318 - show more button)<br>batch_management.html (lines 1628-1654 - pagination handler)<br>assessments/views.py |

---

## Test Cases - Status Management

### BM-011: Toggle Batch Status Active to Inactive (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BM-011 |
| **Category** | Batch Management |
| **Priority** | P0 (Critical) |
| **Test Name** | Toggle batch status from active to inactive shows confirmation |
| **Description** | User can toggle batch status from active to inactive with confirmation modal |
| **Preconditions** | 1. User is logged in with batch update permission<br>2. Batch "B-2025-Active" exists<br>3. Batch status: Active<br>4. Toggle switch is checked (on)<br>5. Page loaded at /batch-management/ |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate batch "B-2025-Active" in table<br>3. Verify status toggle is checked (on/active)<br>4. Click the toggle switch<br>5. Verify confirmation modal appears with title "Mark Batch as Inactive"<br>6. Verify modal body shows warning icon<br>7. Verify modal shows message: "Please note the following:"<br>8. Verify bullet point: "This batch will no longer be visible in the create assessment dropdown"<br>9. Verify bullet point: "You can mark it as active again later if needed"<br>10. Verify modal shows: "Are you sure you want to mark this batch as inactive?"<br>11. Verify "Cancel" button present<br>12. Verify "Yes, Mark as Inactive" button present<br>13. Click "Cancel" button<br>14. Verify modal closes<br>15. Verify toggle remains checked (active)<br>16. Click toggle again<br>17. Verify modal appears again<br>18. Click "Yes, Mark as Inactive" button<br>19. Verify API call made (loading state visible)<br>20. Verify success message shown<br>21. Verify toggle unchecked (inactive)<br>22. Verify batch row shows status "Inactive" |
| **Test Data** | Batch: B-2025-Active<br>Initial Status: Active |
| **Expected** | 1. Confirmation modal appears on inactive toggle<br>2. Modal content matches design<br>3. Cancel reverts toggle state<br>4. Confirm updates batch status<br>5. Success message displayed<br>6. Toggle visual state changes<br>7. API call successful (HTTP 200)<br>8. Batch status updates in table |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify modal text styling and icon color. Check that toggle disabled during API call. |
| **Related Files** | batch_management.html (lines 372-399 - confirmation modal)<br>batch_management.html (lines 2112-2195 - status toggle handler)<br>assessments/views.py:toggle_batch_status() |

---

### BM-012: Toggle Batch Status Inactive to Active (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-012 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Toggle batch status from inactive to active (no confirmation) |
| **Description** | User can toggle batch status from inactive to active without confirmation |
| **Preconditions** | 1. User is logged in with batch update permission<br>2. Batch "B-2024-Inactive" exists<br>3. Batch status: Inactive<br>4. Toggle switch is unchecked (off)<br>5. Page loaded at /batch-management/ |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate batch "B-2024-Inactive" in table<br>3. Verify status toggle is unchecked (off/inactive)<br>4. Click the toggle switch<br>5. Verify NO confirmation modal appears<br>6. Verify API call made immediately<br>7. Verify loading state visible on toggle<br>8. Wait for completion (< 2 seconds)<br>9. Verify success message shown<br>10. Verify toggle becomes checked (active)<br>11. Verify batch row status updates to "Active"<br>12. Verify batch becomes visible in assessments dropdown |
| **Test Data** | Batch: B-2024-Inactive<br>Initial Status: Inactive |
| **Expected** | 1. No confirmation modal shown<br>2. API call made immediately<br>3. Loading state visible<br>4. Toggle updates without page reload<br>5. Status changes to Active in table<br>6. Success message displayed<br>7. Batch usable in assessments |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify that only inactive→active toggle skips confirmation. Active→inactive always shows confirmation. |
| **Related Files** | batch_management.html (lines 2112-2131 - status change handler)<br>assessments/views.py:toggle_batch_status() |

---

## Test Cases - Edit Batch

### BM-013: Edit Batch Opens Detail Page (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-013 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Edit batch button navigates to batch detail page |
| **Description** | Clicking edit button on batch row navigates to batch detail page |
| **Preconditions** | 1. User is logged in<br>2. Batch "B-2025-EDI" exists<br>3. Edit permission granted<br>4. Page loaded at /batch-management/ |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Locate batch "B-2025-EDI" in table<br>3. Verify edit button (pencil icon) visible in Actions column<br>4. Click edit button<br>5. Verify page navigates to /batch-management/B-2025-EDI/ (or similar)<br>6. Verify page title shows batch name<br>7. Verify batch information displayed<br>8. Verify two tabs visible: "Learners" and "Courses"<br>9. Verify "Back to Batches" button visible<br>10. Verify Learners tab active by default<br>11. Verify learners table shows batch members<br>12. Verify "Add Learner" button visible<br>13. Verify Courses tab accessible |
| **Test Data** | Batch: B-2025-EDI |
| **Expected** | 1. Navigation happens successfully<br>2. URL updates correctly<br>3. Batch detail page loads<br>4. All batch information visible<br>5. Tabs functional<br>6. Learners listed in table<br>7. Back button available<br>8. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify URL structure matches expected pattern. Check that back button returns to correct page. |
| **Related Files** | batch_management.html (lines 2102-2105 - edit button)<br>batch_detail.html (full page)<br>assessments/views.py:batch_detail() |

---

## Test Cases - Error Handling

### BM-014: Handle Network Error During Batch Creation (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-014 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Network error during batch creation shows error message |
| **Description** | If network error occurs during batch creation, user sees error notification |
| **Preconditions** | 1. User is logged in<br>2. Create batch side panel open<br>3. Form filled with valid data<br>4. Network disconnected (simulate or use dev tools) |
| **Test Steps** | 1. Open create batch side panel<br>2. Fill all required fields correctly<br>3. Disconnect network or throttle connection<br>4. Click "Create Batch" button<br>5. Verify loading spinner appears<br>6. Wait for timeout (> 5 seconds)<br>7. Verify error notification appears (red background)<br>8. Verify error message: "Error creating batch. Please try again."<br>9. Verify notification has dismiss button (X)<br>10. Verify "Create Batch" button remains enabled<br>11. Verify form data retained<br>12. Reconnect network<br>13. Click "Create Batch" again<br>14. Verify batch creation succeeds |
| **Test Data** | Network: Disconnected<br>Form: Valid data |
| **Expected** | 1. Error notification displays<br>2. Error message is clear<br>3. Notification styled in red (#dc3545)<br>4. Auto-dismiss after 5 seconds (or manual dismiss)<br>5. Button re-enabled for retry<br>6. Form data preserved<br>7. Retry succeeds with network |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Test using browser dev tools Network throttling. Verify error message matches backend error response. |
| **Related Files** | batch_management.html (lines 2044-2070 - API call & error handling)<br>batch_management.html (lines 2334-2352 - error notification) |

---

### BM-015: Duplicate Batch Name Validation (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BM-015 |
| **Category** | Batch Management |
| **Priority** | P1 (High) |
| **Test Name** | Creating batch with duplicate name shows error |
| **Description** | Backend validation prevents duplicate batch names and returns error |
| **Preconditions** | 1. User is logged in<br>2. Batch "B-2025-DUP" already exists in database<br>3. Create batch side panel open |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Click "Add Batch" button<br>3. Fill batch name: "B-2025-DUP"<br>4. Select unit type and unit<br>5. Select learners<br>6. Click "Create Batch"<br>7. Wait for API response<br>8. Verify error notification appears<br>9. Verify error message indicates duplicate: "Batch name already exists" or "Batch with this name already exists"<br>10. Verify side panel remains open<br>11. Verify form data retained<br>12. Verify "Create Batch" button enabled |
| **Test Data** | Duplicate Batch Name: B-2025-DUP |
| **Expected** | 1. Error notification displayed<br>2. Error message clear and helpful<br>3. Side panel stays open for correction<br>4. User can edit name and retry<br>5. Button enabled for retry |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify backend returns proper error code (e.g., 400). Check that error message is user-friendly. |
| **Related Files** | batch_management.html (lines 2053-2060 - error handling)<br>assessments/views.py:batch_create() |

---

## Test Environment Setup

### Prerequisites
- Django 5.2.3 running on localhost:8000
- PostgreSQL/SQLite database configured
- Firebase Firestore connected (for real-time data)
- User logged in with admin permissions
- Browser: Chrome/Firefox/Safari (latest version)
- Screen resolution: 1920x1080 minimum

### Setup Steps
1. Start Django development server: `python manage.py runserver`
2. Navigate to `http://localhost:8000/batch-management/`
3. Log in with admin credentials
4. Verify database has test batches, units, and learners
5. Clear browser cache and cookies

### Browser Dev Tools Recommendations
- Keep console open to check for JavaScript errors
- Use Network tab to monitor API calls
- Use Lighthouse for performance testing

---

## Test Data

### Sample Batch Data
| Batch Name | Year | Semester | Unit Type | Unit Name | Learners | Status |
|-----------|------|----------|-----------|-----------|----------|--------|
| B-2025-SEM1-A | 2025 | 1 | Institution | DJ Sanghvi College | 45 | Active |
| B-2025-SEM2-A | 2025 | 2 | Institution | DJ Sanghvi College | 48 | Active |
| B-2024-SEM1-B | 2024 | 1 | Institution | Mumbai University | 35 | Inactive |
| B-2025-HOSP1 | 2025 | - | Hospital | City Hospital | 20 | Active |
| B-2025-HOSP2 | 2025 | - | Hospital | Medical Center | 18 | Inactive |

### Sample Unit Data
**Institutions:**
- DJ Sanghvi College (id: inst-001)
- Mumbai University (id: inst-002)
- MIT Pune (id: inst-003)

**Hospitals:**
- City Hospital (id: hosp-001)
- Medical Center (id: hosp-002)
- State Hospital (id: hosp-003)

### Sample Learner Data (for DJ Sanghvi College)
| Learner Name | Email | ID |
|------------|-------|-----|
| Amar Singh | amar@student.com | learner-001 |
| Bhavna Sharma | bhavna@student.com | learner-002 |
| John Doe | john@student.com | learner-003 |
| Diana Prince | diana@student.com | learner-004 |
| Esha Kumar | esha@student.com | learner-005 |
| ... | ... | ... |

---

## Notes

### Key Testing Considerations
1. **Lazy Loading:** Pagination happens asynchronously - watch for loading spinners
2. **Filter Persistence:** Filter state should persist when opening/closing panel
3. **Search Reset:** Pagination resets when searching
4. **Status Confirmation:** Only inactive toggle requires confirmation modal
5. **Learner Multi-Select:** Summary tag shows when >5 learners selected
6. **Unit Type Dependency:** Unit dropdown depends on unit type selection

### Common Issues to Watch For
- Filter badge count doesn't match selected filters
- Show More button remains disabled after all items loaded
- Search results don't update in real-time
- Modal confirmation doesn't prevent status change
- Unit Type change doesn't reset learner selection
- Duplicate batch names allowed (validation bypass)

### Performance Benchmarks
- Page load: < 3 seconds
- Search filtering: < 500ms
- Show More pagination: < 2 seconds
- Toggle status: < 1 second

---

## Related Documentation

See also:
- BATCH_DETAIL_TEST_CASES.md (for batch detail/edit page tests)
- COURSE_MANAGEMENT_TEST_CASES.md (for course-related tests)
- INSTITUTE_LIST_TEST_CASES.md (for unit management tests)
- batch_management.html (source template - 2189 lines)
- batch_detail.html (source template - 2872 lines)
