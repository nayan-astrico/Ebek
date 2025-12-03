# CREATE_ROLES Module - Functional Test Cases

**Module:** Create Roles (Role Management with Permissions)
**URL:** `/create-roles/`
**Related APIs:** `/api/roles/`, `/api/roles/<role_id>/edit/`, `/api/roles/<role_id>/delete/`, `/assign-roles/`
**Last Updated:** November 30, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Test Cases - Initial Page Load](#test-cases---initial-page-load)
3. [Test Cases - Create Role](#test-cases---create-role)
4. [Test Cases - Permissions Management](#test-cases---permissions-management)
5. [Test Cases - Role Validation](#test-cases---role-validation)
6. [Test Cases - Edit Role](#test-cases---edit-role)
7. [Test Cases - Delete Role](#test-cases---delete-role)
8. [Test Cases - Search & Filter](#test-cases---search--filter)
9. [Test Cases - Error Handling](#test-cases---error-handling)
10. [Test Environment Setup](#test-environment-setup)
11. [Test Data](#test-data)

---

## Overview

The Create Roles module allows administrators to:
1. Create custom user roles with specific permissions
2. Assign permissions to roles
3. View and manage existing roles
4. Edit role permissions
5. Delete roles and automatically update user permissions
6. Search and filter roles

**Key Features:**
- Dynamic permission assignment
- Permission categorization
- Bulk permission assignment via Select All/Category Select
- Role-to-user relationship management
- Automatic permission sync when role is edited

**Key Models:**
- `CustomRole` - User roles with M2M permissions
- `Permission` - Granular permissions assigned to roles
- `EbekUser` - Has ForeignKey to CustomRole + M2M to Permission

---

## Test Cases - Initial Page Load

### CR-001: Page Load with Permissions List (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-001 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Page loads with permissions list from database |
| **Description** | User navigates to /create-roles/ and page loads with active permissions grouped by category |
| **Preconditions** | 1. User is logged in as admin<br>2. Permission records exist in database<br>3. At least 10+ active permissions exist<br>4. Permissions have category assigned |
| **Test Steps** | 1. Navigate to http://localhost:8000/create-roles/<br>2. Wait for page to fully load<br>3. Verify header "Role Management" visible<br>4. Verify "Create Role" button visible<br>5. Verify permissions grouped by category<br>6. Verify search box present<br>7. Verify roles table visible (initially empty or with existing roles)<br>8. Verify browser console has no JavaScript errors |
| **Test Data** | User: admin@test.com, Password: Test@1234 |
| **Expected** | 1. Page loads in < 2 seconds<br>2. Permissions organized by category<br>3. Permissions checkbox list visible<br>4. Create Role button enabled<br>5. All 10+ permissions displayed<br>6. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check that only active permissions (is_active=True) are shown. |
| **Related Files** | assessments/views.py:create_roles() (lines 5851-5904)<br>assessments/models.py:Permission, CustomRole<br>create_roles.html |

---

### CR-002: Permission Categories Displayed (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-002 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Permissions are grouped and categorized correctly |
| **Description** | Permissions display organized by category with expand/collapse functionality |
| **Preconditions** | 1. User logged in<br>2. Permissions in database with categories:<br>   - "view" (5 permissions)<br>   - "create" (4 permissions)<br>   - "edit" (3 permissions)<br>   - "delete" (2 permissions) |
| **Test Steps** | 1. Navigate to /create-roles/<br>2. Observe permission list<br>3. Verify each category has a header<br>4. Verify category can be expanded/collapsed<br>5. Expand each category<br>6. Verify all permissions in category visible<br>7. Verify permission checkboxes present<br>8. Count permissions per category |
| **Test Data** | Permissions with categories: view, create, edit, delete |
| **Expected** | 1. Categories displayed with proper grouping<br>2. Expand/collapse toggles work<br>3. "view" shows 5 permissions<br>4. "create" shows 4 permissions<br>5. "edit" shows 3 permissions<br>6. "delete" shows 2 permissions<br>7. All permissions have checkboxes |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Permissions ordered by category then by name (line 5901). |
| **Related Files** | assessments/views.py:create_roles() (line 5901)<br>create_roles.html (lines 669-681) |

---

### CR-003: Empty State When No Roles (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-003 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Empty state shown when no roles exist |
| **Description** | If no CustomRole records exist, appropriate empty message displayed |
| **Preconditions** | 1. User logged in<br>2. All CustomRole records deleted (or fresh database)<br>3. Permissions exist |
| **Test Steps** | 1. Delete all roles from database<br>2. Navigate to /create-roles/<br>3. Observe roles table area<br>4. Verify empty state message shown<br>5. Verify "Create Role" button still enabled<br>6. Verify permissions list still visible |
| **Test Data** | No existing CustomRole records |
| **Expected** | 1. Empty state message shown (e.g., "No roles found")<br>2. Create Role button enabled<br>3. Permission list fully functional<br>4. Table columns headers visible |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if empty state has helpful message. |
| **Related Files** | create_roles.html (lines 131-155)<br>assessments/views.py:get_roles() (lines 5906-5927) |

---

## Test Cases - Create Role

### CR-004: Create Simple Role (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-004 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Create role with name and select permissions |
| **Description** | User can create new role with role name, description, and select permissions |
| **Preconditions** | 1. User logged in as admin<br>2. Page loaded at /create-roles/<br>3. No role named "Test Role" exists<br>4. At least 3 permissions available |
| **Test Steps** | 1. Click "Create Role" button<br>2. Observe form panel opens<br>3. Enter Role Name: "Test Role"<br>4. Enter Description: "Role for testing"<br>5. Select 3 permissions (check checkboxes)<br>6. Click "Create" button<br>7. Wait for response<br>8. Verify success message shown<br>9. Verify role appears in roles table<br>10. Verify role has correct permissions |
| **Test Data** | Role Name: "Test Role"<br>Description: "Role for testing"<br>Permissions: view_overall_report, view_institutes, create_institute |
| **Expected** | 1. Form validates name entered<br>2. Permissions selected (checkboxes checked)<br>3. POST request to /create-roles/ succeeds<br>4. Response: HTTP 200 with success message<br>5. New role appears in table<br>6. Role shows "Test Role" with 3 permissions<br>7. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check response JSON: success=true, message includes role name, role_id returned. |
| **Related Files** | assessments/views.py:create_roles() (lines 5854-5893)<br>create_roles.html (lines 768-821)<br>assessments/models.py:CustomRole |

---

### CR-005: Create Role with No Permissions (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-005 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Create role without selecting any permissions |
| **Description** | Role can be created with empty permission set (no permissions assigned) |
| **Preconditions** | 1. User logged in<br>2. Form open<br>3. No role named "Empty Role" exists |
| **Test Steps** | 1. Enter Role Name: "Empty Role"<br>2. Leave all permissions unchecked<br>3. Click "Create"<br>4. Observe response<br>5. Verify role created<br>6. Verify role shows 0 permissions in table |
| **Test Data** | Role Name: "Empty Role"<br>Permissions: (none selected) |
| **Expected** | 1. Role created successfully<br>2. Success message shown<br>3. Role appears in table<br>4. Role shows 0 permissions<br>5. Users assigned this role have no extra permissions |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Permission set can be empty - validation allows zero permissions. |
| **Related Files** | assessments/views.py:create_roles() (line 5859) |

---

### CR-006: Select All Permissions (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-006 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Select All button checks all permission checkboxes |
| **Description** | Clicking "Select All" button checks all permission checkboxes at once |
| **Preconditions** | 1. User logged in<br>2. Form panel open<br>3. 15+ permissions available<br>4. No permissions initially selected |
| **Test Steps** | 1. Click "Select All" button<br>2. Observe checkboxes<br>3. Verify ALL permission checkboxes are checked<br>4. Count checked permissions (should match total)<br>5. Create role with all permissions<br>6. Verify role created with all permissions |
| **Test Data** | Action: Click Select All<br>Expected: All 15+ permissions checked |
| **Expected** | 1. All permission checkboxes checked<br>2. Visual feedback shows all selected<br>3. Selection count updated<br>4. Role created successfully with all permissions |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check that count updates and UI reflects selection. |
| **Related Files** | create_roles.html (lines 656-666) |

---

### CR-007: Select Category Permissions (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-007 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Select all permissions in single category |
| **Description** | Clicking category select button selects only permissions in that category |
| **Preconditions** | 1. User logged in<br>2. Form open<br>3. "view" category has 5 permissions<br>4. "create" category has 4 permissions<br>5. No permissions selected |
| **Test Steps** | 1. Expand "view" category<br>2. Click "Select Category" for "view"<br>3. Verify 5 permissions in "view" checked<br>4. Verify "create" permissions NOT checked<br>5. Click "Select Category" for "create"<br>6. Verify 4 permissions in "create" now checked<br>7. Verify 9 total permissions checked |
| **Test Data** | Select view category (5 perms)<br>Then select create category (4 perms) |
| **Expected** | 1. First action: 5 "view" permissions checked<br>2. Second action: 9 total (5+4) permissions checked<br>3. Only specified category permissions selected<br>4. Count updated correctly |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Category select should be cumulative (add to existing selection). |
| **Related Files** | create_roles.html (lines 683-697) |

---

## Test Cases - Permissions Management

### CR-008: Permission Search Filter (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-008 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Search field filters permissions by name |
| **Description** | Typing in permission search box filters permissions matching the search term |
| **Preconditions** | 1. User logged in<br>2. Form open<br>3. Permissions: "view_overall_report", "view_institutes", "create_institute", "edit_learner"<br>4. 4+ permissions available |
| **Test Steps** | 1. Locate permission search box<br>2. Type "view"<br>3. Observe permission list<br>4. Verify only permissions with "view" shown<br>5. Should show: "view_overall_report", "view_institutes"<br>6. Should NOT show: "create_institute", "edit_learner"<br>7. Clear search, type "institute"<br>8. Verify shows "view_institutes", "create_institute" |
| **Test Data** | Search terms: "view", "institute" |
| **Expected** | 1. Search is case-insensitive<br>2. "view" search shows 2 results<br>3. "institute" search shows 2 results<br>4. Search in real-time (as typing)<br>5. Clear clears filter |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Search should filter in real-time via JavaScript. |
| **Related Files** | create_roles.html (lines 732-762) |

---

### CR-009: Deselect All Permissions (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-009 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Deselect All button unchecks all permissions |
| **Description** | Clicking "Deselect All" unchecks all permission checkboxes |
| **Preconditions** | 1. User logged in<br>2. Form open<br>3. Some permissions already selected |
| **Test Steps** | 1. Select some permissions (e.g., 5)<br>2. Verify they are checked<br>3. Click "Deselect All"<br>4. Verify ALL permissions unchecked<br>5. Verify selection count shows 0 |
| **Test Data** | Initial: 5 permissions selected<br>Action: Click Deselect All |
| **Expected** | 1. All checkboxes unchecked<br>2. Selection count = 0<br>3. No visual indication of selection<br>4. Can reselect after deselecting |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Should work regardless of current selection state. |
| **Related Files** | create_roles.html (lines 656-666) |

---

## Test Cases - Role Validation

### CR-010: Duplicate Role Name Rejected (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-010 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Cannot create role with name that already exists |
| **Description** | Creating role with duplicate name returns error and prevents creation |
| **Preconditions** | 1. User logged in<br>2. Role "Manager" already exists in database<br>3. Form open |
| **Test Steps** | 1. Try to create role with name: "Manager"<br>2. Select any permissions<br>3. Click "Create"<br>4. Observe response<br>5. Verify error message: "Role with this name already exists"<br>6. Verify role NOT created (check database)<br>7. Verify form stays open for retry |
| **Test Data** | Role Name: "Manager" (existing name)<br>Permissions: Any |
| **Expected** | 1. HTTP 400 error returned<br>2. Error message displayed: "Role with this name already exists"<br>3. Form does not close<br>4. User can correct and retry<br>5. No duplicate role created |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Uses get_or_create() - if exists, created=False, returns error. Line 5883. |
| **Related Files** | assessments/views.py:create_roles() (lines 5875-5884)<br>assessments/models.py:CustomRole.name |

---

### CR-011: Empty Role Name Rejected (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-011 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Role name is required |
| **Description** | Cannot create role with empty or whitespace-only name |
| **Preconditions** | 1. User logged in<br>2. Form open |
| **Test Steps** | 1. Leave Role Name field empty<br>2. Select some permissions<br>3. Try to click "Create"<br>4. Observe behavior<br>5. Try with name = "   " (spaces only)<br>6. Try to create<br>7. Verify error in both cases |
| **Test Data** | Role Name: "" (empty)<br>Role Name: "   " (spaces) |
| **Expected** | 1. Empty name: HTTP 400, error "Role name is required"<br>2. Whitespace-only: Stripped to empty, same error<br>3. Form stays open<br>4. No role created<br>5. User prompted to enter valid name |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Name is stripped before validation (line 5857). |
| **Related Files** | assessments/views.py:create_roles() (lines 5857, 5861-5862) |

---

### CR-012: Duplicate Permission Set Rejected (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-012 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Cannot create role with identical permission set as existing role |
| **Description** | System prevents creating two roles with exact same permissions |
| **Preconditions** | 1. User logged in<br>2. Role "Editor" exists with permissions: [view_institutes, edit_learner]<br>3. Form open |
| **Test Steps** | 1. Try to create new role: "Editor 2"<br>2. Select SAME permissions: view_institutes, edit_learner<br>3. Click "Create"<br>4. Observe response<br>5. Verify error: "Role with the same set of permissions already exists"<br>6. Verify role NOT created<br>7. Try different permission set - should succeed |
| **Test Data** | Existing Role: "Editor" with [view_institutes, edit_learner]<br>New Role: "Editor 2" with [view_institutes, edit_learner] |
| **Expected** | 1. HTTP 400 error<br>2. Error message: "Role with the same set of permissions already exists"<br>3. Role not created<br>4. Different permission set works<br>5. Same name with different permissions works |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Checks exact set match by comparing permission IDs (lines 5869-5872). |
| **Related Files** | assessments/views.py:create_roles() (lines 5868-5872) |

---

### CR-013: Role Creation with Description (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-013 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Description field is optional but saved |
| **Description** | Role can be created with or without description; if provided, saved correctly |
| **Preconditions** | 1. User logged in<br>2. Form open |
| **Test Steps** | 1. Create role with name and description: "Manager - Full access except deletion"<br>2. Select some permissions<br>3. Click "Create"<br>4. Verify success<br>5. Check database: role.description = "Manager - Full access except deletion"<br>6. Create another role WITHOUT description<br>7. Verify description is empty string or null |
| **Test Data** | Role 1: "Manager" with description "Full access except deletion"<br>Role 2: "Viewer" with no description |
| **Expected** | 1. Role 1 created with description saved<br>2. Role 2 created with empty description<br>3. Both roles visible in table<br>4. Description displayed in role table (if column present)<br>5. Description editable later |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Description is stripped (line 5858), optional field. |
| **Related Files** | assessments/views.py:create_roles() (line 5858)<br>assessments/models.py:CustomRole.description |

---

## Test Cases - Edit Role

### CR-014: Edit Role Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-014 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Edit existing role name |
| **Description** | User can update role name to a new value |
| **Preconditions** | 1. User logged in<br>2. Role "Old Name" exists with ID 5<br>3. No role named "New Name" exists |
| **Test Steps** | 1. Click Edit icon on "Old Name" role<br>2. Observe edit form opens<br>3. Verify current name shown: "Old Name"<br>4. Clear name field<br>5. Enter new name: "New Name"<br>6. Click "Save"<br>7. Wait for response<br>8. Verify role updated<br>9. Verify table shows "New Name"<br>10. Verify users assigned this role still have correct permissions |
| **Test Data** | Role ID: 5<br>Old Name: "Old Name"<br>New Name: "New Name"<br>Permissions: unchanged |
| **Expected** | 1. POST to /api/roles/5/edit/ succeeds<br>2. HTTP 200 response<br>3. Role name updated in database<br>4. Table refreshed with new name<br>5. All users assigned role still have same permissions |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Edit endpoint: POST /api/roles/<role_id>/edit/ (lines 5929-5994). |
| **Related Files** | assessments/views.py:edit_role() (lines 5949-5992)<br>create_roles.html (lines 910-952) |

---

### CR-015: Edit Role Permissions (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-015 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Edit role permissions - users automatically get updated permissions |
| **Description** | When role permissions are changed, all users assigned to that role automatically receive the new permissions |
| **Preconditions** | 1. User logged in<br>2. Role "Manager" exists with permissions: [view_institutes, create_institute]<br>3. User "john@example.com" assigned to "Manager" role<br>4. john currently has 2 permissions |
| **Test Steps** | 1. Click Edit on "Manager" role<br>2. Verify current permissions: view_institutes, create_institute<br>3. Uncheck create_institute<br>4. Check: edit_learner<br>5. Click "Save"<br>6. Wait for response<br>7. Verify role updated: [view_institutes, edit_learner]<br>8. Check john's permissions in database<br>9. Verify john now has: [view_institutes, edit_learner]<br>10. Verify john's user_permissions_custom updated |
| **Test Data** | Role: "Manager"<br>User: john@example.com<br>Old Permissions: [view_institutes, create_institute]<br>New Permissions: [view_institutes, edit_learner] |
| **Expected** | 1. Role permissions updated<br>2. HTTP 200 response<br>3. All users assigned role updated (lines 5979-5982)<br>4. john.user_permissions_custom updated to new set<br>5. User permissions sync completed |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Line 5981-5982: Automatically sets user.user_permissions_custom to role.permissions.all(). Critical feature! |
| **Related Files** | assessments/views.py:edit_role() (lines 5979-5982) |

---

### CR-016: Edit Role Description (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-016 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Edit role description |
| **Description** | Role description can be updated |
| **Preconditions** | 1. User logged in<br>2. Role "Assistant" exists with description: "Limited access"<br>3. Edit form open |
| **Test Steps** | 1. Click Edit on "Assistant"<br>2. Observe description: "Limited access"<br>3. Change to: "Limited access - No deletion rights"<br>4. Click "Save"<br>5. Verify role updated<br>6. Check database: description updated |
| **Test Data** | Role: "Assistant"<br>Old Description: "Limited access"<br>New Description: "Limited access - No deletion rights" |
| **Expected** | 1. Description field updated<br>2. POST succeeds<br>3. Table shows new description (if visible)<br>4. Database updated |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Description is optional and editable. |
| **Related Files** | assessments/views.py:edit_role() (lines 5965-5974) |

---

## Test Cases - Delete Role

### CR-017: Delete Role (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-017 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Delete role from system |
| **Description** | Role can be deleted; users assigned to it have role removed |
| **Preconditions** | 1. User logged in<br>2. Role "Temporary" exists with ID 10<br>3. No critical users depend on this role |
| **Test Steps** | 1. Locate "Temporary" role in table<br>2. Click Delete icon<br>3. Observe delete confirmation modal<br>4. Modal shows role name: "Temporary"<br>5. Click "Confirm" button<br>6. Wait for response<br>7. Verify role removed from table<br>8. Check database: role ID 10 does NOT exist<br>9. Verify users no longer have this role assigned |
| **Test Data** | Role: "Temporary" (ID: 10) |
| **Expected** | 1. Delete modal appears<br>2. Modal shows role name<br>3. POST to /api/roles/10/delete/ succeeds<br>4. HTTP 200 response<br>5. Role deleted from database<br>6. Table refreshed without role<br>7. Users assigned role have custom_roles cleared |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Deletion removes role from all users (lines 6002-6006 in delete_role). |
| **Related Files** | assessments/views.py:delete_role() (lines 5996-6017)<br>create_roles.html (lines 159-182) |

---

### CR-018: Delete Modal Confirmation (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-018 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Delete confirmation modal with role name |
| **Description** | Delete modal shows role name to confirm deletion of correct role |
| **Preconditions** | 1. User logged in<br>2. Multiple roles exist: "Editor", "Viewer", "Manager"<br>3. No roles deleted yet |
| **Test Steps** | 1. Click Delete on "Editor" role<br>2. Observe modal appears<br>3. Verify modal text includes: "Editor"<br>4. Click "Cancel"<br>5. Verify modal closes<br>6. Verify role still in table<br>7. Click Delete on "Manager"<br>8. Verify modal shows: "Manager"<br>9. Verify different role name than before |
| **Test Data** | Roles: "Editor", "Viewer", "Manager" |
| **Expected** | 1. Modal shows correct role name<br>2. Cancel button closes modal<br>3. Role not deleted after cancel<br>4. Correct role name shown each time<br>5. Confirm button triggers deletion |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Modal should display role name dynamically (line 6050). |
| **Related Files** | create_roles.html (lines 159-182, 955-959) |

---

## Test Cases - Search & Filter

### CR-019: Search Roles by Name (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-019 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Search roles table by name |
| **Description** | User can search existing roles by name/description to filter results |
| **Preconditions** | 1. User logged in<br>2. Roles exist: "Administrator", "Admin Assistant", "Viewer", "Editor"<br>3. Search box at top of roles table |
| **Test Steps** | 1. Locate search box above roles table<br>2. Type "admin"<br>3. Observe table updates<br>4. Verify shows: "Administrator", "Admin Assistant"<br>5. Does NOT show: "Viewer", "Editor"<br>6. Clear search, type "view"<br>7. Verify shows only "Viewer"<br>8. Type "xyz123" (no match)<br>9. Verify empty results |
| **Test Data** | Search: "admin", "view", "xyz123" |
| **Expected** | 1. Search is case-insensitive<br>2. "admin" returns 2 results<br>3. "view" returns 1 result<br>4. "xyz123" returns 0 results<br>5. Search updates in real-time<br>6. Clear shows all roles again |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Frontend JavaScript filters roles table (lines 894-907). |
| **Related Files** | create_roles.html (lines 894-907)<br>assessments/views.py:get_roles() |

---

## Test Cases - Error Handling

### CR-020: Invalid JSON Error (P0)
| Field | Value |
|-------|-------|
| **Test ID** | CR-020 |
| **Category** | Create Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Invalid JSON in POST request handled gracefully |
| **Description** | If client sends malformed JSON, server returns clear error |
| **Preconditions** | 1. Access to API testing tool (curl, Postman)<br>2. Server running |
| **Test Steps** | 1. Send POST to /create-roles/<br>2. With body: `{"name": "Test", invalid json}`<br>3. Observe response<br>4. Verify HTTP 400 status<br>5. Verify error message: "Invalid JSON data"<br>6. Try another malformed payload<br>7. Verify same error handling |
| **Test Data** | Invalid JSON payloads |
| **Expected** | 1. HTTP 400 status<br>2. Error message: "Invalid JSON data"<br>3. No server exception<br>4. Request handled gracefully |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Line 5895 catches JSONDecodeError. |
| **Related Files** | assessments/views.py:create_roles() (lines 5895-5896) |

---

### CR-021: Server Exception Handling (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-021 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Unhandled exceptions return 500 error |
| **Description** | If unexpected error occurs, server returns 500 with error details |
| **Preconditions** | 1. Server running<br>2. Database connection active |
| **Test Steps** | 1. Create valid role request<br>2. If database temporarily unavailable, trigger error<br>3. Observe response<br>4. Verify HTTP 500 status<br>5. Verify error message returned<br>6. Check server logs for exception |
| **Test Data** | Valid role data when database is down |
| **Expected** | 1. HTTP 500 status<br>2. Error message returned (not blank page)<br>3. User sees informative error<br>4. Server logs exception |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Line 5897-5898 catches all other exceptions. |
| **Related Files** | assessments/views.py:create_roles() (lines 5897-5898) |

---

### CR-022: Inactive Permissions Filtered (P1)
| Field | Value |
|-------|-------|
| **Test ID** | CR-022 |
| **Category** | Create Roles |
| **Priority** | P1 (High) |
| **Test Name** | Only active permissions can be assigned |
| **Description** | If permission marked as inactive (is_active=False), it cannot be assigned to roles |
| **Preconditions** | 1. User logged in<br>2. Permission "view_reports" exists with is_active=True<br>3. Permission "view_old_system" exists with is_active=False<br>4. Form open |
| **Test Steps** | 1. Observe available permissions in form<br>2. Verify "view_reports" visible<br>3. Verify "view_old_system" NOT visible<br>4. Try to manually send role creation with inactive permission code<br>5. Use API testing tool<br>6. Send: `{"name": "Test", "permissions": ["view_old_system"]}`<br>7. Observe response |
| **Test Data** | Active: view_reports<br>Inactive: view_old_system<br>Request includes inactive permission |
| **Expected** | 1. Inactive permissions not shown in form<br>2. API request ignores inactive permission<br>3. Role created without inactive permission<br>4. Validation filters only active permissions (line 5865) |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Line 5865 filters by is_active=True. Inactive permissions excluded from role. |
| **Related Files** | assessments/views.py:create_roles() (line 5865)<br>assessments/models.py:Permission.is_active |

---

## Test Environment Setup

### Database Setup

**Required Models:**
1. Permission - At least 15+ records with categories (view, create, edit, delete)
2. CustomRole - Initial records (empty or with test roles)
3. EbekUser - Admin user for testing

**Sample Data:**

```sql
-- Permissions
INSERT INTO assessments_permission (code, name, category, is_active) VALUES
('view_overall_report', 'View Overall Report', 'view', TRUE),
('view_institutes', 'View Institutions', 'view', TRUE),
('view_learners', 'View Learners', 'view', TRUE),
('create_institute', 'Create Institution', 'create', TRUE),
('create_learner', 'Create Learner', 'create', TRUE),
('edit_learner', 'Edit Learner', 'edit', TRUE),
('delete_learner', 'Delete Learner', 'delete', TRUE),
('view_old_system', 'View Old System', 'view', FALSE);  -- Inactive

-- Admin User
INSERT INTO assessments_ebekuser (email, password, is_active, is_superuser) VALUES
('admin@test.com', 'hashed_password', TRUE, TRUE);
```

### User Setup

**Admin User:**
```
Email: admin@test.com
Password: Test@1234
Role: super_admin
Access: Full access to /create-roles/
```

---

## Test Data & Templates

### Permission Categories Expected
- view (5+ permissions)
- create (4+ permissions)
- edit (3+ permissions)
- delete (2+ permissions)

### Success Criteria

- ✅ All tests CR-001 to CR-022 show "Pass" status
- ✅ No unhandled JavaScript errors
- ✅ No 500 server errors for valid input
- ✅ All validation messages clear and helpful
- ✅ Role creation completes in < 2 seconds
- ✅ User permissions sync correctly when role edited

### Critical Path (P0 Tests)

- ✅ CR-001: Page loads with permissions
- ✅ CR-004: Create simple role succeeds
- ✅ CR-010: Duplicate role name rejected
- ✅ CR-011: Empty role name rejected
- ✅ CR-012: Duplicate permission set rejected
- ✅ CR-015: Role permissions edit syncs to users
- ✅ CR-017: Delete role succeeds
- ✅ CR-020: Invalid JSON handled

---

**Document Version:** 1.0
**Last Updated:** November 30, 2025
**Module:** Create Roles (/create-roles/)
**Status:** Ready for Testing
