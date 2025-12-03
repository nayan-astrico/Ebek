# INSTITUTE_LIST Module - Functional Test Cases

**Module:** Institute List (Institute Management)
**URL:** `/onboarding/institutions/`
**Related URLs:** `/institutes/create/`, `/institutes/<pk>/edit/`, `/institutes/<pk>/delete/`
**Last Updated:** December 1, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Test Cases - Initial Page Load](#test-cases---initial-page-load)
3. [Test Cases - Create Institute](#test-cases---create-institute)
4. [Test Cases - Search Functionality](#test-cases---search-functionality)
5. [Test Cases - Pagination](#test-cases---pagination)
6. [Test Cases - Edit Institute](#test-cases---edit-institute)
7. [Test Cases - Delete Institute](#test-cases---delete-institute)
8. [Test Cases - Status Management](#test-cases---status-management)
9. [Test Cases - Error Handling](#test-cases---error-handling)
10. [Test Environment Setup](#test-environment-setup)
11. [Test Data](#test-data)

---

## Overview

The Institute List module allows administrators to:
1. View all institutions/colleges in the system
2. Create new institutes with name and configuration
3. Search for institutes by name
4. Edit existing institute information
5. Delete institutes from the system
6. Toggle institute active/inactive status
7. Paginate through large institute lists
8. View institute details and metadata

**Key Features:**
- Institute list table with status indicators
- Create institute modal form
- Edit institute functionality
- Search with instant filtering
- Pagination support (configurable per page)
- Status toggle (active/inactive)
- Empty state when no institutes exist
- Responsive design for mobile devices

**Key Models:**
- `Institution` - Institution/College records
- Django ORM with PostgreSQL/SQLite backend
- Firebase sync for real-time data

---

## Test Cases - Initial Page Load

### IL-001: Page Load with Institutes (P0)
| Field | Value |
|-------|-------|
| **Test ID** | IL-001 |
| **Category** | Institute List |
| **Priority** | P0 (Critical) |
| **Test Name** | Page loads with institute list from database |
| **Description** | User navigates to /onboarding/institutions/ and page loads with institutes table |
| **Preconditions** | 1. User is logged in as admin<br>2. At least 5 institutes exist in database<br>3. Database connection working<br>4. Page has proper permissions |
| **Test Steps** | 1. Navigate to http://localhost:8000/onboarding/institutions/<br>2. Wait for page to fully load (< 3 seconds)<br>3. Verify page title "Institutes" is visible<br>4. Verify subtitle "Manage your educational institutes" visible<br>5. Verify "Add Institute" button visible<br>6. Verify institutes table is displayed<br>7. Verify table columns: Institute Name, Status, Actions<br>8. Verify at least 5 institutes listed in table<br>9. Check browser console for JavaScript errors |
| **Test Data** | User: admin@test.com, Password: Test@1234<br>Pre-existing: 5+ institutes |
| **Expected** | 1. Page loads in < 3 seconds<br>2. Header "Institutes" visible<br>3. Subtitle text visible<br>4. Add Institute button enabled<br>5. Institutes table shows 5+ institutes<br>6. All table columns visible<br>7. Status badges displayed (Active/Inactive)<br>8. Edit action button visible for each row<br>9. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check pagination displays correctly for large datasets. Verify first page shows up to 10-25 institutes. |
| **Related Files** | assessments/views.py:institution_list()<br>assessments/models.py:Institution<br>institute_list.html |

---

### IL-002: Empty State When No Institutes (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-002 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Empty state shown when no institutes exist |
| **Description** | If no Institution records exist in database, appropriate empty message displayed |
| **Preconditions** | 1. User is logged in as admin<br>2. All Institute records deleted (or fresh database)<br>3. Page loaded |
| **Test Steps** | 1. Delete all institutes from database (or create new DB)<br>2. Navigate to /onboarding/institutions/<br>3. Observe institutes table area<br>4. Verify empty state message shown<br>5. Verify empty state has icon (school icon)<br>6. Verify message: "No institutes found"<br>7. Verify "Add Institute" button visible in empty state<br>8. Click "Add Institute" button in empty state<br>9. Verify create modal opens |
| **Test Data** | No existing Institution records |
| **Expected** | 1. Empty state message shown<br>2. School icon displayed<br>3. "No institutes found" text visible<br>4. Add Institute button visible and clickable<br>5. Create modal opens on button click |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Empty state provides good UX and guides user to create first institute. |
| **Related Files** | institute_list.html (lines 74-85 - empty state)<br>assessments/views.py |

---

### IL-003: Institute Data Displayed Correctly (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-003 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Institute data displays all required fields |
| **Description** | Each institute row shows: name with icon, status badge, and action buttons |
| **Preconditions** | 1. User is logged in<br>2. Institute "DJ Sanghvi College" exists with:<br>   - Name: DJ Sanghvi College<br>   - is_active: True<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Locate DJ Sanghvi College in table<br>3. Verify institute icon with first letter: "D"<br>4. Verify institute name: "DJ Sanghvi College"<br>5. Verify status badge displayed<br>6. Verify status shows "Active" (green badge)<br>7. Verify Edit button present (pencil icon)<br>8. Verify button is clickable<br>9. Verify no other institute data missing |
| **Test Data** | Institute: DJ Sanghvi College<br>Status: Active |
| **Expected** | 1. Icon displays first letter capitalized<br>2. Institute name fully displayed<br>3. Status badge shows "Active" with green background<br>4. Edit action button present and styled correctly<br>5. All data visible in one row |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify icon color matches design (should be teal/turquoise #1AA09A). |
| **Related Files** | institute_list.html (lines 49-73)<br>assessments/views.py |

---

## Test Cases - Create Institute

### IL-004: Create Institute Modal Opens (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-004 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Create institute modal opens on button click |
| **Description** | Clicking "Add Institute" button opens a modal form to create new institute |
| **Preconditions** | 1. User is logged in as admin<br>2. Page loaded at /onboarding/institutions/<br>3. Modal not already open |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Locate "Add Institute" button in header<br>3. Click "Add Institute" button<br>4. Observe modal opens<br>5. Verify modal title shows "Create Institute"<br>6. Verify form is empty<br>7. Verify "Institute Name" label visible<br>8. Verify text input field visible<br>9. Verify "Create" submit button visible<br>10. Verify close button (X) present in modal header |
| **Test Data** | None required |
| **Expected** | 1. Modal opens smoothly (< 500ms)<br>2. Modal title: "Create Institute"<br>3. Form fields empty and ready for input<br>4. Submit button text: "Create"<br>5. Close button functional<br>6. Modal centered on screen |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check modal styling - should match design system. Verify bootstrap modal classes work correctly. |
| **Related Files** | institute_list.html (lines 122-152 - modal)<br>institute_list.html (lines 485-540 - JavaScript) |

---

### IL-005: Create Institute with Valid Data (P0)
| Field | Value |
|-------|-------|
| **Test ID** | IL-005 |
| **Category** | Institute List |
| **Priority** | P0 (Critical) |
| **Test Name** | Create new institute with valid name |
| **Description** | User can create new institute by entering name and submitting form |
| **Preconditions** | 1. User is logged in as admin<br>2. Create modal open<br>3. No institute named "New Test College" exists<br>4. Database connection working |
| **Test Steps** | 1. Open create institute modal<br>2. Locate "Institute Name" input field<br>3. Enter name: "New Test College"<br>4. Verify text entered correctly<br>5. Click "Create" button<br>6. Observe loading spinner (optional)<br>7. Wait for submission (< 2 seconds)<br>8. Verify success response<br>9. Verify modal closes<br>10. Verify page reloads or updates<br>11. Verify "New Test College" now appears in table |
| **Test Data** | Institute Name: New Test College |
| **Expected** | 1. Form accepts input<br>2. Create button submits form<br>3. Loading spinner visible during submit<br>4. Success response received (HTTP 200)<br>5. Modal closes automatically<br>6. Page refreshes with new institute<br>7. New institute visible in table<br>8. Institute appears at appropriate position (last or sorted) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify API endpoint /institutes/create/ returns proper JSON response. Check Firebase sync if applicable. |
| **Related Files** | institute_list.html (lines 501-539 - form submission)<br>assessments/views.py:institute_create() |

---

### IL-006: Create Institute with Empty Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-006 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Create institute with empty name rejected |
| **Description** | Form validation prevents creating institute with empty name |
| **Preconditions** | 1. User is logged in<br>2. Create modal open<br>3. Institute Name field empty |
| **Test Steps** | 1. Open create institute modal<br>2. Leave "Institute Name" field empty<br>3. Click "Create" button<br>4. Observe validation behavior<br>5. Verify HTML5 validation message appears<br>6. Message should say: "Please fill in this field"<br>7. Verify form does not submit<br>8. Verify modal remains open |
| **Test Data** | Institute Name: (empty) |
| **Expected** | 1. HTML5 required validation triggers<br>2. Error message displayed<br>3. Submit prevented<br>4. Modal stays open<br>5. User can retry with valid input |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify HTML5 validation works (input has required attribute). Check browser behavior (Chrome, Firefox, Safari). |
| **Related Files** | institute_list.html (lines 135-140 - form input with required) |

---

### IL-007: Create Institute with Very Long Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-007 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Create institute with long name (255+ characters) |
| **Description** | Verify handling of very long institute names |
| **Preconditions** | 1. User is logged in<br>2. Create modal open<br>3. Database allows max 255 char names |
| **Test Steps** | 1. Open create institute modal<br>2. Enter very long name (255 characters):<br>   - Example: "A" repeated 255 times<br>3. Click "Create" button<br>4. Observe response<br>5. If name accepted: verify institute created and displayed<br>6. If rejected: verify error message shown<br>7. Test with 256+ characters and verify rejection |
| **Test Data** | Long name: 255 characters max<br>Over limit: 256+ characters |
| **Expected** | 1. Valid 255 char name: accepted and created<br>2. Over 255 chars: rejected with error<br>3. Error message: "Name too long" or similar<br>4. Modal remains open for retry |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check database field constraints. Verify error handling on server side. |
| **Related Files** | assessments/models.py:Institution.name<br>assessments/views.py:institute_create() |

---

## Test Cases - Search Functionality

### IL-008: Search Institute by Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-008 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Search institutes by name |
| **Description** | User can search institute list by entering name in search box |
| **Preconditions** | 1. User is logged in<br>2. Institutes in database:<br>   - DJ Sanghvi College<br>   - NMIMS University<br>   - MIT College<br>   - XYZ Institute<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Locate search box (with "Search institutes..." placeholder)<br>3. Type "sanghvi" in search<br>4. Verify table filters/updates<br>5. Verify shows: DJ Sanghvi College<br>6. Verify hidden: NMIMS, MIT, XYZ<br>7. Clear search box<br>8. Type "mit"<br>9. Verify shows: MIT College<br>10. Verify hidden: others<br>11. Type "xyz"<br>12. Verify shows: XYZ Institute<br>13. Type "college" (partial match)<br>14. Verify shows colleges only |
| **Test Data** | Search terms: "sanghvi", "mit", "xyz", "college" |
| **Expected** | 1. Search is case-insensitive<br>2. Partial matching works<br>3. Results update dynamically or on search button click<br>4. Correct institutes shown for each search<br>5. Clear search shows all institutes<br>6. No results shows empty state |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify if search is client-side (JavaScript) or server-side. Check URL parameters for persistence. |
| **Related Files** | institute_list.html (lines 22-34 - search box)<br>institute_list.html (lines 550-560 - search JavaScript)<br>assessments/views.py:institution_list() |

---

### IL-009: Search with No Results (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-009 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Search returns empty state when no matches |
| **Description** | Search that matches no institutes shows appropriate empty message |
| **Preconditions** | 1. User is logged in<br>2. Institutes in database exist<br>3. Search box visible |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Verify institutes shown initially<br>3. Enter search: "xyz123nonexistent"<br>4. Press Enter or click Search button<br>5. Observe results<br>6. Verify empty state message shown<br>7. Verify message says "No institutes found"<br>8. Verify "Add Institute" button still visible<br>9. Clear search<br>10. Verify all institutes shown again |
| **Test Data** | Search term: xyz123nonexistent |
| **Expected** | 1. No results displayed<br>2. Empty state message shown<br>3. User can clear search and retry<br>4. UI doesn't break or error |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify empty state is same as when no institutes exist. |
| **Related Files** | institute_list.html<br>assessments/views.py |

---

## Test Cases - Pagination

### IL-010: Pagination Displays Multiple Pages (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-010 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Pagination controls show when multiple pages exist |
| **Description** | When institutes exceed items per page, pagination controls appear |
| **Preconditions** | 1. User is logged in<br>2. Database has 25+ institutes<br>3. Page size is 10 or 15 items per page<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Verify page 1 shows 10-15 institutes<br>3. Scroll to bottom of table<br>4. Verify pagination controls visible<br>5. Verify page numbers shown: 1, 2, 3...<br>6. Verify current page highlighted (active)<br>7. Verify "Previous" arrow visible (disabled on page 1)<br>8. Verify "Next" arrow visible (enabled)<br>9. Count pages shown matches data |
| **Test Data** | 25+ institutes in database |
| **Expected** | 1. Pagination controls visible<br>2. Page numbers show correctly<br>3. Current page (1) is highlighted<br>4. Navigation buttons functional<br>5. Arrow buttons styled correctly |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify pagination is at bottom right. Check page numbers display format. |
| **Related Files** | institute_list.html (lines 91-117 - pagination)<br>assessments/views.py:institution_list() |

---

### IL-011: Navigate Between Pages (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-011 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Click pagination links to navigate between pages |
| **Description** | User can click page numbers to navigate to different pages |
| **Preconditions** | 1. User is logged in<br>2. 25+ institutes exist<br>3. Multiple pages visible in pagination<br>4. Page 1 loaded |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Verify page 1 displayed (institutes 1-10)<br>3. Locate pagination controls at bottom<br>4. Click page "2"<br>5. Wait for page load<br>6. Verify page 2 now shows (institutes 11-20)<br>7. Verify page 2 is highlighted in pagination<br>8. Verify URL shows ?page=2<br>9. Click Next arrow<br>10. Verify advances to page 3 (if exists)<br>11. Click Previous arrow<br>12. Verify returns to page 2 |
| **Test Data** | 25+ institutes<br>Page size: 10 per page |
| **Expected** | 1. Page changes on link click<br>2. Content updates with new institutes<br>3. Current page highlighted<br>4. URL updates with page parameter<br>5. Navigation arrows work in both directions<br>6. Pagination is fast (< 1 second) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify smooth page transitions. Check URL parameter preservation with search. |
| **Related Files** | institute_list.html (lines 91-117)<br>assessments/views.py:institution_list() |

---

## Test Cases - Edit Institute

### IL-012: Edit Institute Modal Opens (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-012 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Edit institute modal opens with current data |
| **Description** | Clicking Edit button on institute row opens modal with current name |
| **Preconditions** | 1. User is logged in as admin<br>2. Institute "DJ Sanghvi College" exists<br>3. Page loaded with institutes visible |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Locate "DJ Sanghvi College" in table<br>3. Click Edit button (pencil icon)<br>4. Observe modal opens<br>5. Verify modal title shows "Edit Institute"<br>6. Verify form fields populated with:<br>   - Institute Name: "DJ Sanghvi College"<br>7. Verify submit button text changed to "Update"<br>8. Verify close button present<br>9. Verify form fields are editable |
| **Test Data** | Institute: DJ Sanghvi College |
| **Expected** | 1. Modal opens smoothly<br>2. Modal title: "Edit Institute"<br>3. Form pre-populated with current data<br>4. Submit button: "Update"<br>5. Field is focus-ready for editing<br>6. Modal shows correct institute |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify no permissions issues. Check institute ID is hidden but passed correctly. |
| **Related Files** | institute_list.html (lines 542-548 - editInstitute JS)<br>institute_list.html (lines 122-152 - modal) |

---

### IL-013: Edit Institute with New Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-013 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Edit institute name and save changes |
| **Description** | User can change institute name and update it in database |
| **Preconditions** | 1. User is logged in as admin<br>2. Institute "Old Name College" exists<br>3. Edit modal open for this institute |
| **Test Steps** | 1. Click Edit on "Old Name College"<br>2. Observe modal opens with old name<br>3. Clear the name field<br>4. Type new name: "New Name College"<br>5. Click "Update" button<br>6. Wait for submission (< 2 seconds)<br>7. Verify success response<br>8. Verify modal closes<br>9. Verify page refreshes<br>10. Verify institute name changed in table<br>11. Verify "New Name College" now displays |
| **Test Data** | Old name: Old Name College<br>New name: New Name College |
| **Expected** | 1. Form accepts new input<br>2. Update succeeds (HTTP 200)<br>3. Modal closes automatically<br>4. Table updates with new name<br>5. Change persists after refresh<br>6. Database updated |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify Firebase sync if applicable. Check no duplicate names created. |
| **Related Files** | institute_list.html (lines 501-539)<br>assessments/views.py:institute_create() (handles both create/update) |

---

## Test Cases - Delete Institute

### IL-014: Delete Institute (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-014 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Delete institute from system |
| **Description** | Administrator can delete an institute from the system |
| **Preconditions** | 1. User is logged in as admin<br>2. Institute "Test Institute" exists<br>3. No critical dependencies<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Locate "Test Institute" in table<br>3. Verify Edit button present<br>4. Try to find Delete button (if available)<br>5. Verify expected delete functionality exists<br>6. Initiate delete operation<br>7. If confirmation modal: verify and confirm<br>8. Verify institute removed from table<br>9. Verify success message shown<br>10. Refresh page and verify deletion persisted |
| **Test Data** | Institute: Test Institute |
| **Expected** | 1. Delete option available<br>2. Confirmation requested if modal<br>3. Deletion succeeds<br>4. Institute removed from table<br>5. Institute no longer in database<br>6. Related data handled (learners, etc.) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if delete button exists in current UI. Verify cascade delete behavior for dependent records. |
| **Related Files** | institute_list.html<br>assessments/views.py |

---

## Test Cases - Status Management

### IL-015: Institute Status Display (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-015 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Institute status badge displays correctly |
| **Description** | Active institutes show green badge, inactive show red |
| **Preconditions** | 1. User is logged in<br>2. Database has:<br>   - Active institute: is_active=True<br>   - Inactive institute: is_active=False<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Locate active institute (is_active=True)<br>3. Verify status badge shows "Active"<br>4. Verify badge color is green (#C6F6D5 background)<br>5. Locate inactive institute (is_active=False)<br>6. Verify status badge shows "Inactive"<br>7. Verify badge color is red (#FED7D7 background)<br>8. Verify status consistent for all institutes |
| **Test Data** | Institute 1: Active (is_active=True)<br>Institute 2: Inactive (is_active=False) |
| **Expected** | 1. Active shows green badge<br>2. Inactive shows red badge<br>3. Colors are distinct and clear<br>4. Status text correct<br>5. All institutes display status |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check badge colors match design system. Verify accessibility (not color-only indicator). |
| **Related Files** | institute_list.html (lines 59-63 - status badge)<br>assessments/models.py:Institution.is_active |

---

## Test Cases - Error Handling

### IL-016: Database Error Handling (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-016 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Graceful handling of database errors |
| **Description** | If database is unavailable, user sees friendly error instead of 500 page |
| **Preconditions** | 1. User is logged in<br>2. Page loaded<br>3. Database connection can be simulated as down |
| **Test Steps** | 1. Navigate to /onboarding/institutions/<br>2. Verify page loads normally<br>3. Simulate database connection failure (disconnect DB)<br>4. Refresh page or try to create institute<br>5. Observe error handling<br>6. Verify friendly error message shown (not 500 stack trace)<br>7. Verify user can understand the issue<br>8. Restore database connection<br>9. Refresh page<br>10. Verify page loads normally again |
| **Test Data** | Valid admin user |
| **Expected** | 1. Database error caught<br>2. Friendly error message shown<br>3. No technical stack trace exposed<br>4. User informed of the problem<br>5. Can retry once fixed<br>6. System recovers properly |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify error handling in views. Check server logs for detailed errors. |
| **Related Files** | assessments/views.py:institution_list()<br>assessments/views.py error handling |

---

### IL-017: Duplicate Institute Name Prevention (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-017 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Cannot create duplicate institute names |
| **Description** | System prevents creating institute with name that already exists |
| **Preconditions** | 1. User is logged in as admin<br>2. Institute "Duplicate Name" already exists<br>3. Create modal open |
| **Test Steps** | 1. Open create institute modal<br>2. Enter name: "Duplicate Name" (existing)<br>3. Click "Create" button<br>4. Observe response<br>5. Verify error message shown: "Institute already exists" or similar<br>6. Verify institute NOT created<br>7. Verify modal remains open<br>8. Try with unique name and verify it works |
| **Test Data** | Existing name: Duplicate Name<br>Unique name: New Unique Name |
| **Expected** | 1. Duplicate rejected with error<br>2. Error message is clear<br>3. No duplicate created<br>4. User can retry with different name<br>5. Unique name creates successfully |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if validation is server-side or client-side. Verify case sensitivity. |
| **Related Files** | assessments/views.py:institute_create()<br>assessments/models.py:Institution |

---

## Test Cases - Responsive Design

### IL-018: Mobile Responsive Layout (P1)
| Field | Value |
|-------|-------|
| **Test ID** | IL-018 |
| **Category** | Institute List |
| **Priority** | P1 (High) |
| **Test Name** | Page layout adapts for mobile devices |
| **Description** | Institute list is responsive and usable on mobile screens |
| **Preconditions** | 1. User is logged in as admin<br>2. Browser with mobile viewport (360px - 768px)<br>3. Page loaded |
| **Test Steps** | 1. Open browser dev tools<br>2. Set viewport to mobile (iPhone 12: 390x844)<br>3. Navigate to /onboarding/institutions/<br>4. Verify header adapts (stacked layout)<br>5. Verify "Add Institute" button visible and clickable<br>6. Verify search box spans full width<br>7. Verify table is scrollable or columns hidden<br>8. Verify institute name still visible (primary column)<br>9. Verify action buttons accessible<br>10. Test on tablet (768px) and verify layout<br>11. Test on desktop (1920px) and verify full layout |
| **Test Data** | Responsive breakpoints: 360px, 768px, 1920px |
| **Expected** | 1. Mobile (< 768px): single column or compact table<br>2. Tablet (768px-1024px): two column layout<br>3. Desktop (> 1024px): full multi-column table<br>4. All content accessible<br>5. No horizontal scroll on mobile<br>6. Buttons easily tappable (44px minimum) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check CSS media queries. Test on real devices if possible. |
| **Related Files** | institute_list.html (lines 450-482 - media queries)<br>institute_list.html CSS |

---

## Test Environment Setup

### Database Setup

**Required Data:**

```sql
-- Institutes
INSERT INTO assessments_institution (name, is_active, group_id) VALUES
('DJ Sanghvi College', TRUE, 1),
('NMIMS University', TRUE, 1),
('MIT College', TRUE, 1),
('XYZ Institute', FALSE, 1),
('ABC Academy', TRUE, 1),
('Test Institute', TRUE, 1),
('Another College', TRUE, 1),
('Old Name College', TRUE, 1),
('New Test College', TRUE, 1),
('Sample Institute', FALSE, 1);
```

### User Credentials

**Admin User:**
```
Email: admin@test.com
Password: Test@1234
Role: super_admin
Access: Full access to /onboarding/institutions/
```

### Browser Requirements
- Chrome/Firefox/Safari (latest version)
- JavaScript enabled
- Cookies enabled
- Bootstrap CSS loaded
- Font Awesome icons available

---

## Test Data

### Institutes for Testing
| Name | Status | Group |
|------|--------|-------|
| DJ Sanghvi College | Active | Default Group |
| NMIMS University | Active | Default Group |
| MIT College | Active | Default Group |
| XYZ Institute | Inactive | Default Group |
| ABC Academy | Active | Default Group |
| Test Institute | Active | Default Group |
| Another College | Active | Default Group |
| Old Name College | Active | Default Group |
| New Test College | Active | Default Group |
| Sample Institute | Inactive | Default Group |

---

## Success Criteria

- ✅ All tests IL-001 to IL-018 show "Pass" status
- ✅ No unhandled JavaScript errors
- ✅ No 500 server errors for valid input
- ✅ Institute creation works correctly
- ✅ Search functionality operational
- ✅ Pagination works for 20+ institutes
- ✅ Edit institute updates database
- ✅ Status badges display correctly
- ✅ Mobile responsive layout works
- ✅ Graceful error handling implemented

### Critical Path (P0 Tests)
- ✅ IL-001: Page loads with institutes list
- ✅ IL-005: Create institute with valid data

---

**Document Version:** 1.0 (Functional Test Cases)
**Last Updated:** December 1, 2025
**Module:** Institute List (/onboarding/institutions/)
**Status:** Ready for Testing

