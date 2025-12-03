# BATCH_DETAIL Module - Functional Test Cases

**Module:** Batch Detail (Batch Edit & Management)
**URL:** `/batch-management/<batch_id>/`
**Related URLs:** `/api/batches/<batch_id>/learners/`, `/api/batches/<batch_id>/courses-paginated/`
**Last Updated:** December 1, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Test Cases - Page Load & Display](#test-cases---page-load--display)
3. [Test Cases - Batch Information Editing](#test-cases---batch-information-editing)
4. [Test Cases - Learners Tab](#test-cases---learners-tab)
5. [Test Cases - Courses Tab](#test-cases---courses-tab)
6. [Test Cases - Add Learner Functionality](#test-cases---add-learner-functionality)
7. [Test Cases - Add Course Functionality](#test-cases---add-course-functionality)
8. [Test Cases - Delete Operations](#test-cases---delete-operations)
9. [Test Cases - Error Handling](#test-cases---error-handling)
10. [Test Environment Setup](#test-environment-setup)
11. [Test Data](#test-data)

---

## Overview

The Batch Detail module allows administrators to:
1. View and edit batch information (name, semester, year)
2. Manage learners in the batch (add, remove, search)
3. Manage courses assigned to the batch (add, remove)
4. View detailed batch information and metadata
5. Navigate between Learners and Courses tabs
6. Search within learner and course lists
7. Paginate through large learner/course lists
8. Delete entire batch if permitted

**Key Features:**
- Batch information header with editable batch name and semester
- Batch overview card with batch details (unit type, unit name, semester, learners count)
- Tab navigation with Learners and Courses tabs
- Learners tab with searchable table and lazy loading
- Courses tab with searchable table and lazy loading
- Add Learner side panel with learner multi-select
- Add Course side panel with course multi-select
- Remove learner/course from batch functionality
- Delete batch confirmation modal
- Back to Batches navigation button
- Real-time data updates

**Key Models:**
- `Batch` - Batch records
- `Learner` - Student/Nurse records
- `Course` - Course records
- `Unit` - Hospital or Institution reference

---

## Test Cases - Page Load & Display

### BD-001: Batch Detail Page Loads (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BD-001 |
| **Category** | Batch Detail |
| **Priority** | P0 (Critical) |
| **Test Name** | Batch detail page loads with all information |
| **Description** | User navigates to batch detail page and all batch information displays correctly |
| **Preconditions** | 1. User is logged in as admin<br>2. Batch "B-2025-SEM1-A" exists in database with:<br>   - Name: B-2025-SEM1-A<br>   - Unit Type: Institution<br>   - Unit Name: DJ Sanghvi College<br>   - Semester: 1<br>   - Learner Count: 45<br>3. Database connection working |
| **Test Steps** | 1. Navigate to /batch-management/<br>2. Click edit button for batch "B-2025-SEM1-A"<br>3. Wait for detail page to load (< 3 seconds)<br>4. Verify page title includes batch name: "B-2025-SEM1-A"<br>5. Verify "Back to Batches" button visible (arrow + text)<br>6. Verify batch name displayed in header: "B-2025-SEM1-A"<br>7. Verify edit icon button next to batch name<br>8. Verify batch information section visible<br>9. Verify "Batch Information" heading<br>10. Verify Unit Type: "Institution"<br>11. Verify Unit Name: "DJ Sanghvi College"<br>12. Verify Semester: "Semester 1" (or "1")<br>13. Verify Learners count: "45"<br>14. Verify two tabs: "Learners" and "Courses"<br>15. Verify Learners tab active by default<br>16. Verify Learners table shows batch members<br>17. Check browser console for JavaScript errors |
| **Test Data** | Batch ID: B-2025-SEM1-A<br>Expected Data: As above |
| **Expected** | 1. Page loads in < 3 seconds<br>2. All batch information displayed correctly<br>3. Batch name, unit type, unit name visible<br>4. Semester and learner count shown<br>5. Tabs visible and functional<br>6. Learners table populated<br>7. Back button functional<br>8. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify page title matches batch name. Check that edit icon is visible and styled correctly. |
| **Related Files** | batch_detail.html (lines 13-97 - header & info)<br>assessments/views.py:batch_detail()<br>assessments/models.py:Batch |

---

### BD-002: Batch Information Card Display (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-002 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Batch information overview card displays all fields |
| **Description** | Batch information card shows all required details in grid format |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded for "B-2025-SEM1-A"<br>3. Batch has year set to 2025<br>4. Batch has semester set to 1 |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Locate "Batch Information" section<br>3. Verify grid layout with 4 columns<br>4. Verify Unit Type field:<br>   - Label: "Unit Type" (uppercase, gray)<br>   - Value: "Institution"<br>5. Verify Unit Name field:<br>   - Label: "Unit Name"<br>   - Value: "DJ Sanghvi College"<br>6. Verify Year of Batch field:<br>   - Label: "Year of Batch"<br>   - Value: "2025" (or "-" if not set)<br>7. Verify Semester field:<br>   - Label: "Semester"<br>   - Edit icon visible<br>   - Value: "Semester 1"<br>8. Verify Learners field:<br>   - Label: "Learners"<br>   - Value: "45"<br>9. Verify all values right-aligned in their cells<br>10. Verify card border: 1px solid #e2e8f0<br>11. Verify background color: white |
| **Test Data** | Batch: B-2025-SEM1-A |
| **Expected** | 1. All fields display in grid layout<br>2. Labels styled in gray uppercase<br>3. Values styled in dark text (bold)<br>4. Grid responsive to screen size<br>5. Card has proper border and shadow<br>6. Edit icon visible for Semester field<br>7. No truncation of values |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check responsive behavior at mobile resolution (320px). Verify label text styling. |
| **Related Files** | batch_detail.html (lines 45-96 - info grid)<br>batch_detail.html (lines 561-603 - CSS styles) |

---

### BD-003: Back to Batches Navigation (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-003 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Back to Batches button navigates to batch list |
| **Description** | Clicking back button returns user to batch management list page |
| **Preconditions** | 1. User is logged in<br>2. Currently on batch detail page<br>3. Batch management list page is accessible |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify "Back to Batches" button visible in header<br>3. Verify button shows arrow icon and text<br>4. Verify button styling (light background on hover)<br>5. Click "Back to Batches" button<br>6. Verify navigation to /batch-management/ page<br>7. Verify batch list displays<br>8. Verify URL changed to batch management page<br>9. Verify browser back button also works<br>10. Verify correct batch row is highlighted (if any) |
| **Test Data** | Navigation: Detail → List |
| **Expected** | 1. Button visible and styled correctly<br>2. Click navigates to /batch-management/<br>3. Batch list page loads<br>4. Browser history works correctly<br>5. No data loss on navigation<br>6. Page loads in < 3 seconds |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify button has proper hover state. Check that navigation preserves pagination state if desired. |
| **Related Files** | batch_detail.html (lines 7-11 - back button)<br>batch_detail.html (lines 320-331 - back button CSS) |

---

## Test Cases - Batch Information Editing

### BD-004: Edit Batch Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-004 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Edit batch name inline |
| **Description** | User can click edit icon next to batch name and update it |
| **Preconditions** | 1. User is logged in with edit permission<br>2. Batch detail page loaded<br>3. Current batch name: "B-2025-SEM1-A"<br>4. Page has edit permissions enabled |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Locate batch name in header: "B-2025-SEM1-A"<br>3. Verify edit icon (pencil) visible next to name<br>4. Click edit icon<br>5. Verify batch name display hides<br>6. Verify input field appears with current name<br>7. Verify input field is focused and text selected<br>8. Clear input and type: "B-2025-BATCH-UPDATED"<br>9. Verify text updated in input<br>10. Verify save button (checkmark icon) visible<br>11. Verify cancel button (X icon) visible<br>12. Click save button<br>13. Verify loading spinner appears<br>14. Wait for API response (< 2 seconds)<br>15. Verify success message shown<br>16. Verify batch name updated: "B-2025-BATCH-UPDATED"<br>17. Verify edit mode exits<br>18. Verify updated name persists on page reload |
| **Test Data** | Old Name: B-2025-SEM1-A<br>New Name: B-2025-BATCH-UPDATED |
| **Expected** | 1. Edit mode activates on icon click<br>2. Input field focused with text selected<br>3. Save and cancel buttons visible<br>4. API call successful<br>5. Batch name updated in database<br>6. Success message displayed<br>7. Name persists after page reload |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify Enter key saves, Escape key cancels. Check input validation (no empty names). |
| **Related Files** | batch_detail.html (lines 16-32 - edit name section)<br>batch_detail.html (lines 1331-1422 - edit name JS)<br>assessments/views.py:batch_update() |

---

### BD-005: Edit Batch Semester (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-005 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Edit batch semester via dropdown |
| **Description** | User can click edit icon next to semester and update it |
| **Preconditions** | 1. User is logged in with edit permission<br>2. Batch detail page loaded<br>3. Current semester: 1<br>4. Batch unit type: Institution (not Hospital)<br>5. Page has edit permissions enabled |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Locate semester field showing "Semester 1"<br>3. Verify edit icon visible next to semester<br>4. Click edit icon<br>5. Verify semester display hides<br>6. Verify select dropdown appears<br>7. Verify current semester (1) is selected<br>8. Verify dropdown options 1-8 visible (Semester 1 to 8)<br>9. Click dropdown and select "Semester 3"<br>10. Verify "Semester 3" selected in dropdown<br>11. Verify save button visible<br>12. Verify cancel button visible<br>13. Click save button<br>14. Verify loading spinner appears<br>15. Wait for API response<br>16. Verify success message shown<br>17. Verify semester updated to "Semester 3"<br>18. Verify display mode restores<br>19. Verify updated semester persists on reload |
| **Test Data** | Current Semester: 1<br>New Semester: 3 |
| **Expected** | 1. Edit mode activates on icon click<br>2. Dropdown shows all semester options (1-8)<br>3. Selected option highlighted<br>4. API call successful<br>5. Semester updated in database<br>6. Success message displayed<br>7. Semester persists after page reload |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify Hospital batches have semester disabled (fixed to 1). Check dropdown styling. |
| **Related Files** | batch_detail.html (lines 62-89 - semester edit)<br>batch_detail.html (lines 1974-2060 - semester edit JS)<br>assessments/views.py:batch_update() |

---

## Test Cases - Learners Tab

### BD-006: Learners Tab Displays All Batch Members (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BD-006 |
| **Category** | Batch Detail |
| **Priority** | P0 (Critical) |
| **Test Name** | Learners tab shows all batch learners |
| **Description** | Learners tab displays all learners in batch in paginated table |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded<br>3. Batch has 45 learners<br>4. Learners tab accessible |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify "Learners" tab is active by default<br>3. Verify "Batch Learners" heading visible<br>4. Verify subtitle: "Manage learners in this batch"<br>5. Verify "Add Learner" button visible<br>6. Verify search box visible: "Search learners..."<br>7. Verify learners table displayed<br>8. Verify table columns: Learner Name, Email, Actions<br>9. Verify first page shows up to 10 learners<br>10. Count displayed learners (should be 10)<br>11. Verify learner data displayed:<br>    - Learner 1: John Doe, john@student.com<br>    - Learner 2: Amar Singh, amar@student.com<br>    - etc.<br>12. Verify remove button (trash icon) for each learner<br>13. Verify "Show More" button visible below table<br>14. Verify no errors in table |
| **Test Data** | Batch: B-2025-SEM1-A<br>Learners: 45 total |
| **Expected** | 1. Learners tab active by default<br>2. Table shows 10 learners initially<br>3. Learner names and emails displayed correctly<br>4. Remove buttons visible for each learner<br>5. Show More button visible<br>6. Table properly formatted |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify API pagination loads 10 learners per page. Check learner name formatting. |
| **Related Files** | batch_detail.html (lines 185-228 - learners tab)<br>batch_detail.html (lines 1178-1226 - learners loading JS) |

---

### BD-007: Search Learners in Batch (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-007 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Search filters learners by name/email |
| **Description** | Search input filters learner list in real-time |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded<br>3. Learners visible in table<br>4. Batch has learners: John Doe, Amar Singh, Diana Prince |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify Learners tab active<br>3. Locate search input in learners section<br>4. Click search input<br>5. Type "John"<br>6. Verify search results update (1 learner: John Doe)<br>7. Clear search and type "Diana"<br>8. Verify results show Diana Prince<br>9. Type "singh@"<br>10. Verify results show Amar Singh (email search)<br>11. Type "NonExistent"<br>12. Verify no results displayed<br>13. Verify message: "No learners found"<br>14. Clear search completely<br>15. Verify all learners reappear |
| **Test Data** | Search terms: "John", "Diana", "singh@", "NonExistent" |
| **Expected** | 1. Search filters in real-time (< 500ms)<br>2. Case-insensitive search<br>3. Name and email search work<br>4. Partial matches work<br>5. Empty results show appropriate message<br>6. Clearing search restores full list |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify search is triggered on input change. Check pagination resets when searching. |
| **Related Files** | batch_detail.html (lines 200-204 - search input)<br>batch_detail.html (lines 1228-1231 - search handler) |

---

### BD-008: Pagination - Show More Learners (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-008 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Show More button loads additional learners |
| **Description** | Clicking Show More loads next 10 learners in batch |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded<br>3. Batch has 45 learners<br>4. Initial page shows 10 learners |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify learners table shows 10 learners<br>3. Verify "Show More" button visible<br>4. Click "Show More" button<br>5. Verify loading spinner appears briefly<br>6. Wait for additional learners to load (< 2 seconds)<br>7. Verify spinner disappears<br>8. Count visible learners (should be 20)<br>9. Verify new learners appended to table<br>10. Verify "Show More" button still visible<br>11. Click "Show More" again<br>12. Verify additional 10 learners load<br>13. Count visible learners (should be 30)<br>14. Click "Show More" again (2 times)<br>15. Count visible learners (should be 40)<br>16. Click "Show More" again<br>17. Count visible learners (should be 45)<br>18. Verify "Show More" button hides (all loaded) |
| **Test Data** | Batch: B-2025-SEM1-A<br>Learners: 45 total |
| **Expected** | 1. Each click loads 10 more learners<br>2. Learners append to list (not replace)<br>3. Loading spinner visible during fetch<br>4. Button hides when all loaded<br>5. Scroll position preserved<br>6. No page reload |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify API returns correct offset/limit pagination. Check scroll behavior during load. |
| **Related Files** | batch_detail.html (lines 225-227 - show more button)<br>batch_detail.html (lines 1178-1226 - learner loading JS) |

---

## Test Cases - Courses Tab

### BD-009: Courses Tab Displays Batch Courses (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BD-009 |
| **Category** | Batch Detail |
| **Priority** | P0 (Critical) |
| **Test Name** | Courses tab shows all courses assigned to batch |
| **Description** | Courses tab displays all courses in batch with procedures and OSCE types |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded<br>3. Batch has 8 courses assigned<br>4. Courses tab accessible |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Click "Courses" tab<br>3. Wait for courses to load (< 2 seconds)<br>4. Verify "Batch Courses" heading visible<br>5. Verify subtitle: "Manage courses assigned to this batch"<br>6. Verify "Add Course" button visible<br>7. Verify search box visible: "Search courses..."<br>8. Verify courses table displayed<br>9. Verify table columns: Course Name, Procedures, OSCE Types, Actions<br>10. Verify first page shows up to 10 courses<br>11. Verify course data displayed:<br>    - Course name visible<br>    - Procedures shown as pills (tags)<br>    - OSCE types listed<br>12. Verify remove button (trash icon) for each course<br>13. Verify "Show More" button visible if more courses exist<br>14. Verify loading spinner during initial load |
| **Test Data** | Batch: B-2025-SEM1-A<br>Courses: 8 assigned |
| **Expected** | 1. Courses tab loads successfully<br>2. Table shows courses correctly<br>3. All required columns visible<br>4. Remove buttons present<br>5. Procedures displayed as pills<br>6. OSCE types listed<br>7. Pagination functional if needed |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify courses loaded from API. Check procedure pill styling. |
| **Related Files** | batch_detail.html (lines 231-277 - courses tab)<br>batch_detail.html (lines 1259-1298 - courses loading JS) |

---

### BD-010: Search Courses in Batch (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-010 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Search filters courses by name |
| **Description** | Search input filters course list in real-time |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded<br>3. Courses tab active<br>4. Batch has courses: "Anatomy 101", "Physiology 101", "Surgery" |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Click Courses tab<br>3. Verify courses displayed<br>4. Locate search input in courses section<br>5. Click search input<br>6. Type "Anatomy"<br>7. Verify results filter to show only "Anatomy 101"<br>8. Clear search and type "Physio"<br>9. Verify results show "Physiology 101"<br>10. Type "Surgery"<br>11. Verify results show "Surgery"<br>12. Type "NonExistent"<br>13. Verify no results displayed<br>14. Verify message: "No courses found"<br>15. Clear search completely<br>16. Verify all courses reappear |
| **Test Data** | Search terms: "Anatomy", "Physio", "Surgery", "NonExistent" |
| **Expected** | 1. Search filters in real-time (< 500ms)<br>2. Case-insensitive search<br>3. Partial matches work<br>4. Empty results show message<br>5. Clearing search restores list |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify search is on course name only. Check pagination resets on search. |
| **Related Files** | batch_detail.html (lines 248-252 - course search)<br>batch_detail.html (lines 1309-1312 - course search handler) |

---

### BD-011: Pagination - Show More Courses (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-011 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Show More button loads additional courses |
| **Description** | Clicking Show More loads next 10 courses in batch |
| **Preconditions** | 1. User is logged in<br>2. Batch detail page loaded on Courses tab<br>3. Batch has 25 courses assigned<br>4. Initial page shows 10 courses |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Click Courses tab<br>3. Verify courses table shows 10 courses<br>4. Verify "Show More" button visible<br>5. Click "Show More" button<br>6. Verify loading spinner appears briefly<br>7. Wait for additional courses to load (< 2 seconds)<br>8. Verify spinner disappears<br>9. Count visible courses (should be 20)<br>10. Verify new courses appended<br>11. Verify "Show More" button still visible<br>12. Click "Show More" again<br>13. Count visible courses (should be 25)<br>14. Verify "Show More" button hides (all loaded) |
| **Test Data** | Batch: B-2025-SEM1-A<br>Courses: 25 total |
| **Expected** | 1. Each click loads 10 more courses<br>2. Courses append to list<br>3. Loading spinner visible<br>4. Button hides when all loaded<br>5. No page reload |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify API pagination. Check scroll preservation. |
| **Related Files** | batch_detail.html (lines 273-275 - show more button)<br>batch_detail.html (lines 1259-1298 - course loading JS) |

---

## Test Cases - Add Learner Functionality

### BD-012: Add Learner Panel Opens (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-012 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Add Learner side panel opens |
| **Description** | Clicking "Add Learner" button opens side panel for learner selection |
| **Preconditions** | 1. User is logged in with add learner permission<br>2. Batch detail page loaded on Learners tab<br>3. Side panel not already open |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify Learners tab active<br>3. Locate "Add Learner" button in learners header<br>4. Click "Add Learner" button<br>5. Verify side panel slides in from right<br>6. Verify panel title: "Add Learners to Batch"<br>7. Verify close button (X) present<br>8. Verify search input: "Search available learners..."<br>9. Verify available learners section visible<br>10. Verify list of available learners shown (not yet in batch)<br>11. Verify "Cancel" button at bottom<br>12. Verify "Add Learners" submit button visible<br>13. Verify overlay appears behind panel |
| **Test Data** | None required |
| **Expected** | 1. Side panel opens smoothly<br>2. Panel title: "Add Learners to Batch"<br>3. Form sections visible<br>4. Available learners list populated<br>5. Buttons functional<br>6. Overlay visible |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify only learners not currently in batch are shown. |
| **Related Files** | batch_detail.html (lines 113-145 - add learner panel)<br>batch_detail.html (lines 1480-1496 - panel open JS) |

---

### BD-013: Add Learner Multi-Select (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-013 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Select multiple learners to add to batch |
| **Description** | User can select multiple available learners and add them to batch |
| **Preconditions** | 1. User is logged in with add learner permission<br>2. Batch detail page loaded<br>3. Add Learner panel open<br>4. At least 10 available learners exist |
| **Test Steps** | 1. Open Add Learner panel<br>2. Verify available learners list displayed<br>3. Verify each learner has checkbox and name/email<br>4. Verify search input works<br>5. Select 3 learners by clicking checkboxes<br>6. Verify checkboxes marked<br>7. Click "Add Learners" button<br>8. Verify loading spinner appears<br>9. Wait for API response (< 2 seconds)<br>10. Verify success message shown<br>11. Verify panel closes<br>12. Verify new learners appear in Learners tab<br>13. Verify learner count updated in batch info |
| **Test Data** | Learners to add: 3 available learners |
| **Expected** | 1. Checkboxes selectable<br>2. Multiple selections allowed<br>3. API call successful<br>4. Panel closes on success<br>5. New learners visible in table<br>6. Learner count updated<br>7. Success message displayed |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify only unchecked learners can be selected. Check duplicate prevention. |
| **Related Files** | batch_detail.html (lines 127-131 - learner selection)<br>batch_detail.html (lines 1587-1643 - add learner submission) |

---

## Test Cases - Add Course Functionality

### BD-014: Add Course Panel Opens (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-014 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Add Course side panel opens |
| **Description** | Clicking "Add Course" button opens side panel for course selection |
| **Preconditions** | 1. User is logged in with add course permission<br>2. Batch detail page loaded on Courses tab<br>3. Side panel not already open |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Click Courses tab<br>3. Locate "Add Course" button in courses header<br>4. Click "Add Course" button<br>5. Verify side panel slides in from right<br>6. Verify panel title: "Add Courses to Batch"<br>7. Verify close button (X) present<br>8. Verify search input: "Search available courses..."<br>9. Verify available courses section visible<br>10. Verify list of available courses shown (not yet in batch)<br>11. Verify course details displayed (name, procedures, OSCE types)<br>12. Verify "Cancel" button at bottom<br>13. Verify "Add Courses" submit button visible |
| **Test Data** | None required |
| **Expected** | 1. Side panel opens smoothly<br>2. Panel title: "Add Courses to Batch"<br>3. Available courses displayed<br>4. Buttons functional<br>5. Overlay visible |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify only courses not currently in batch are shown. |
| **Related Files** | batch_detail.html (lines 147-180 - add course panel)<br>batch_detail.html (lines 1645-1661 - panel open JS) |

---

### BD-015: Add Course Multi-Select (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-015 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Select multiple courses to add to batch |
| **Description** | User can select multiple available courses and add them to batch |
| **Preconditions** | 1. User is logged in with add course permission<br>2. Batch detail page loaded on Courses tab<br>3. Add Course panel open<br>4. At least 5 available courses exist |
| **Test Steps** | 1. Open Add Course panel<br>2. Verify available courses list displayed<br>3. Verify each course has checkbox<br>4. Verify course name visible<br>5. Verify course procedures shown<br>6. Verify OSCE types shown<br>7. Select 2 courses by clicking checkboxes<br>8. Verify checkboxes marked<br>9. Click "Add Courses" button<br>10. Verify loading spinner appears<br>11. Wait for API response (< 2 seconds)<br>12. Verify success message shown<br>13. Verify panel closes<br>14. Verify courses redirects to Courses tab<br>15. Verify new courses appear in table |
| **Test Data** | Courses to add: 2 available courses |
| **Expected** | 1. Checkboxes selectable<br>2. Multiple selections allowed<br>3. API call successful<br>4. Panel closes on success<br>5. New courses visible in table<br>6. Success message displayed<br>7. Redirect to Courses tab |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify duplicate course prevention. Check batch cannot add same course twice. |
| **Related Files** | batch_detail.html (lines 162-167 - course selection)<br>batch_detail.html (lines 1755-1814 - add course submission) |

---

## Test Cases - Delete Operations

### BD-016: Remove Learner from Batch (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-016 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Remove learner from batch |
| **Description** | Clicking remove button on learner removes them from batch |
| **Preconditions** | 1. User is logged in with remove learner permission<br>2. Batch detail page loaded on Learners tab<br>3. Batch has at least 1 learner: "John Doe"<br>4. Learner visible in table |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify Learners tab active<br>3. Locate learner "John Doe" in table<br>4. Verify remove button (trash icon) visible<br>5. Click remove button<br>6. Verify confirmation dialog appears<br>7. Verify message: "Are you sure you want to remove this learner from the batch?"<br>8. Verify "Cancel" button<br>9. Verify "Yes, Remove" button<br>10. Click "Cancel"<br>11. Verify learner still in table<br>12. Click remove button again<br>13. Click "Yes, Remove" button<br>14. Verify loading state<br>15. Wait for API response (< 2 seconds)<br>16. Verify success message shown<br>17. Verify learner removed from table<br>18. Verify learner count decremented |
| **Test Data** | Learner: John Doe |
| **Expected** | 1. Confirmation dialog appears<br>2. Cancel keeps learner in batch<br>3. Confirm removes learner<br>4. Success message shown<br>5. Learner no longer visible<br>6. Learner count updated |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify learner can be re-added to batch if removed by mistake. |
| **Related Files** | batch_detail.html (lines 1849-1880 - remove learner JS)<br>assessments/views.py:remove_learner_from_batch() |

---

### BD-017: Remove Course from Batch (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-017 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Remove course from batch |
| **Description** | Clicking remove button on course removes it from batch |
| **Preconditions** | 1. User is logged in with remove course permission<br>2. Batch detail page loaded on Courses tab<br>3. Batch has at least 1 course: "Anatomy 101"<br>4. Course visible in table |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Click Courses tab<br>3. Verify courses displayed<br>4. Locate course "Anatomy 101" in table<br>5. Verify remove button (trash icon) visible<br>6. Click remove button<br>7. Verify confirmation dialog appears<br>8. Verify message: "Are you sure you want to remove this course from the batch?"<br>9. Verify "Cancel" button<br>10. Verify "Yes, Remove" button<br>11. Click "Cancel"<br>12. Verify course still in table<br>13. Click remove button again<br>14. Click "Yes, Remove" button<br>15. Verify loading state<br>16. Wait for API response (< 2 seconds)<br>17. Verify success message shown<br>18. Verify course removed from table |
| **Test Data** | Course: Anatomy 101 |
| **Expected** | 1. Confirmation dialog appears<br>2. Cancel keeps course in batch<br>3. Confirm removes course<br>4. Success message shown<br>5. Course no longer visible<br>6. Page updates without reload |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify course can be re-added if removed by mistake. |
| **Related Files** | batch_detail.html (lines 1816-1847 - remove course JS)<br>assessments/views.py:remove_course_from_batch() |

---

### BD-018: Delete Batch (P0)
| Field | Value |
|-------|-------|
| **Test ID** | BD-018 |
| **Category** | Batch Detail |
| **Priority** | P0 (Critical) |
| **Test Name** | Delete batch with confirmation |
| **Description** | User can delete entire batch with confirmation modal |
| **Preconditions** | 1. User is logged in with delete batch permission<br>2. Batch detail page loaded<br>3. Batch "B-2024-DEL" exists (test batch for deletion)<br>4. Delete permission enabled in UI |
| **Test Steps** | 1. Navigate to batch detail page<br>2. Verify batch name in header<br>3. Verify delete button (trash icon) visible in header (if permission granted)<br>4. Click delete button<br>5. Verify confirmation dialog appears<br>6. Verify warning icon displayed<br>7. Verify heading: "Delete Batch"<br>8. Verify message: "This action cannot be undone"<br>9. Verify "Cancel" button<br>10. Verify "Yes, Delete" button (red color)<br>11. Click "Cancel"<br>12. Verify dialog closes<br>13. Verify batch still exists<br>14. Click delete button again<br>15. Click "Yes, Delete"<br>16. Verify loading state<br>17. Wait for API response (< 2 seconds)<br>18. Verify success message shown<br>19. Verify redirected to batch management page<br>20. Verify deleted batch not in list |
| **Test Data** | Batch: B-2024-DEL |
| **Expected** | 1. Confirmation dialog appears with warning<br>2. Cancel keeps batch intact<br>3. Confirm deletes batch from database<br>4. Success message shown<br>5. Redirected to batch list<br>6. Deleted batch no longer visible |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | This is destructive action - verify only admins see delete button. Warn user of irreversibility. |
| **Related Files** | batch_detail.html (lines 37-41 - delete button)<br>batch_detail.html (lines 1882-1905 - delete batch JS)<br>assessments/views.py:delete_batch() |

---

## Test Cases - Error Handling

### BD-019: Handle Network Error During Add Learner (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-019 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Network error when adding learner shows error message |
| **Description** | If network error occurs during learner addition, user sees error notification |
| **Preconditions** | 1. User is logged in<br>2. Add Learner panel open<br>3. Learners selected<br>4. Network disconnected (simulated) |
| **Test Steps** | 1. Open Add Learner panel<br>2. Select 2 learners<br>3. Disconnect network (dev tools)<br>4. Click "Add Learners" button<br>5. Verify loading spinner appears<br>6. Wait for timeout (> 5 seconds)<br>7. Verify error notification appears<br>8. Verify error message: "Error adding learners"<br>9. Verify notification dismissible<br>10. Verify button remains enabled<br>11. Verify selections retained<br>12. Reconnect network<br>13. Click "Add Learners" again<br>14. Verify success this time |
| **Test Data** | Network: Disconnected<br>Learners: 2 selected |
| **Expected** | 1. Error notification displayed<br>2. Error message visible<br>3. Button enabled for retry<br>4. Selections preserved<br>5. Retry successful after reconnect |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Use browser dev tools Network tab to simulate disconnection. |
| **Related Files** | batch_detail.html (lines 1613-1641 - error handling)<br>batch_detail.html (lines 1424-1463 - error notifications) |

---

### BD-020: Handle Duplicate Learner Addition (P1)
| Field | Value |
|-------|-------|
| **Test ID** | BD-020 |
| **Category** | Batch Detail |
| **Priority** | P1 (High) |
| **Test Name** | Cannot add learner already in batch |
| **Description** | If user tries to add learner already in batch, backend prevents duplicate |
| **Preconditions** | 1. User is logged in<br>2. Batch has learner "John Doe"<br>3. Add Learner panel open<br>4. Available learners list shown |
| **Test Steps** | 1. Open Add Learner panel<br>2. Verify "John Doe" NOT in available learners list<br>3. Verify only learners not in batch shown<br>4. Select a different available learner<br>5. Click "Add Learners"<br>6. Verify success message<br>7. Open Add Learner panel again<br>8. Verify newly added learner no longer in available list |
| **Test Data** | Existing learner: John Doe<br>New learner to add: Amar Singh |
| **Expected** | 1. Only non-member learners shown in panel<br>2. Members cannot be selected<br>3. No duplicate additions possible<br>4. Panel updates after addition |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify backend validation prevents duplicates if frontend filter bypassed. |
| **Related Files** | batch_detail.html (lines 1534-1560 - display available learners)<br>assessments/views.py:add_learner_to_batch() |

---

## Test Environment Setup

### Prerequisites
- Django 5.2.3 running on localhost:8000
- PostgreSQL/SQLite database configured
- Firebase Firestore connected
- User logged in with appropriate permissions (view, edit, add/remove learners/courses)
- Browser: Chrome/Firefox/Safari (latest version)
- Screen resolution: 1920x1080 minimum

### Setup Steps
1. Start Django development server: `python manage.py runserver`
2. Create test batch with learners and courses
3. Navigate to batch detail page
4. Verify all features accessible
5. Clear browser cache and cookies

---

## Test Data

### Sample Batch Data
| Batch Name | Unit Type | Unit Name | Semester | Learners | Courses |
|-----------|-----------|-----------|----------|----------|---------|
| B-2025-SEM1-A | Institution | DJ Sanghvi College | 1 | 45 | 8 |
| B-2025-SEM2-B | Institution | Mumbai University | 2 | 52 | 10 |
| B-2025-HOSP1 | Hospital | City Hospital | - | 20 | 5 |

### Sample Learner Data
| Learner Name | Email | ID | Batch |
|------------|-------|-----|-------|
| John Doe | john@student.com | learner-001 | B-2025-SEM1-A |
| Amar Singh | amar@student.com | learner-002 | B-2025-SEM1-A |
| Diana Prince | diana@student.com | learner-003 | B-2025-SEM1-A |
| Esha Kumar | esha@student.com | learner-004 | B-2025-SEM1-A |
| Farah Khan | farah@student.com | learner-005 | B-2025-SEM1-A |

### Sample Course Data
| Course Name | Procedures | OSCE Types |
|------------|-----------|-----------|
| Anatomy 101 | Palpation, Inspection | Mock, Final |
| Physiology 101 | Auscultation | Final |
| Surgery | Suturing, Incision | Mock, Classroom, Final |
| Pediatrics | Assessment | Mock, Final |
| Gynecology | Examination | Final |

---

## Related Documentation

See also:
- BATCH_MANAGEMENT_TEST_CASES.md (for batch list page tests)
- COURSE_DETAIL_TEST_CASES.md (for course-related tests)
- batch_detail.html (source template - 2872 lines)
- batch_management.html (source template - 2189 lines)
