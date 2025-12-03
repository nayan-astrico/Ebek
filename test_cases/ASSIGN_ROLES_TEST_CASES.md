# ASSIGN_ROLES Module - Functional Test Cases

**Module:** Assign Roles (User Role Assignment & Management)
**URL:** `/assign-roles/`
**Related URLs:** `/api/roles/`, `/api/users/`
**Last Updated:** November 30, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Test Cases - Initial Page Load](#test-cases---initial-page-load)
3. [Test Cases - Assign Role to User](#test-cases---assign-role-to-user)
4. [Test Cases - User Management](#test-cases---user-management)
5. [Test Cases - Permission Inheritance](#test-cases---permission-inheritance)
6. [Test Cases - User Status Management](#test-cases---user-status-management)
7. [Test Cases - Search & Filter](#test-cases---search--filter)
8. [Test Cases - Error Handling](#test-cases---error-handling)
9. [Test Environment Setup](#test-environment-setup)
10. [Test Data](#test-data)

---

## Overview

The Assign Roles module allows administrators to:
1. View all users (excluding students/nurses)
2. Assign custom roles to users
3. Create new users with role assignment
4. Edit user information
5. Delete users from the system
6. Toggle user active/inactive status
7. View current role assignments
8. Manage user access levels

**Key Features:**
- User list with role assignments
- Multi-step user creation form
- Role assignment via dropdown
- User status toggle (active/inactive)
- Delete user with confirmation modal
- Permission inheritance from assigned roles
- Search and filter functionality

**Key Models:**
- `EbekUser` - User account with role assignment
- `CustomRole` - User roles with permissions
- `Permission` - Granular permissions assigned to roles

---

## Test Cases - Initial Page Load

### AR-001: Page Load with Users and Roles (P0)
| Field | Value |
|-------|-------|
| **Test ID** | AR-001 |
| **Category** | Assign Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Page loads with users list and available roles |
| **Description** | User navigates to /assign-roles/ and page loads with users table and create user form |
| **Preconditions** | 1. User is logged in as admin/super_admin<br>2. At least 5 non-learner users exist in database<br>3. At least 3 custom roles exist<br>4. Users have various role assignments |
| **Test Steps** | 1. Navigate to http://localhost:8000/assign-roles/<br>2. Wait for page to fully load (< 3 seconds)<br>3. Verify page title/header "User Management" is visible<br>4. Verify users table is displayed<br>5. Verify table columns: Checkbox, Name, Email, Status, Role, Actions<br>6. Verify at least 5 users listed in table<br>7. Verify "Create User" button visible and enabled<br>8. Verify no students/nurses in table (excluded)<br>9. Check browser console for JavaScript errors |
| **Test Data** | User: admin@test.com, Password: Test@1234<br>Pre-existing: 5+ users, 3+ roles |
| **Expected** | 1. Page loads in < 3 seconds<br>2. Header "User Management" visible<br>3. Users table shows 5+ users (non-learners only)<br>4. All table columns visible and formatted<br>5. Role badges/tags displayed for each user<br>6. Create User button enabled<br>7. Edit and Delete action buttons visible<br>8. No console errors |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Students and nurses are excluded from view (filtered by user_role). Verify learners are not shown. |
| **Related Files** | assessments/views.py:assign_roles() (lines 6019-6078)<br>assessments/models.py:EbekUser<br>assign_roles.html |

---

### AR-002: Learners Excluded from User List (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-002 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Students and nurses not shown in user list |
| **Description** | Users with learner roles (student/nurse) are excluded from the management table |
| **Preconditions** | 1. User logged in as admin<br>2. Database contains:<br>   - admin user (super_admin)<br>   - manager user (institute_admin)<br>   - student1 user (student)<br>   - nurse1 user (nurse)<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Observe users table<br>3. Verify admin user is visible<br>4. Verify manager user is visible<br>5. Verify student1 is NOT visible<br>6. Verify nurse1 is NOT visible<br>7. Count total users shown (should be 2)<br>8. Refresh page and verify filter still works |
| **Test Data** | Users: admin, manager, student1, nurse1 |
| **Expected** | 1. Only non-learner users shown (2 users)<br>2. admin visible<br>3. manager visible<br>4. student1 hidden<br>5. nurse1 hidden<br>6. Learner exclusion consistent across refreshes |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Backend filters by excluding user_role in ['nurse', 'student']. Verify this exclusion works correctly. |
| **Related Files** | assessments/views.py:assign_roles() (line 6056)<br>assign_roles.html |

---

### AR-003: User Data Displayed Correctly (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-003 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | User data displays all required fields |
| **Description** | Each user row shows: name, email, active status, assigned role, and action buttons |
| **Preconditions** | 1. User logged in<br>2. User "john@example.com" exists with:<br>   - Full name: John Doe<br>   - is_active: True<br>   - custom_role: Manager<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate john@example.com in table<br>3. Verify full name displayed: "John Doe"<br>4. Verify email displayed: "john@example.com"<br>5. Verify status toggle visible (should show active state)<br>6. Verify role displayed: "Manager" (as badge/tag)<br>7. Verify Edit button present<br>8. Verify Delete button present<br>9. Verify checkbox for row selection |
| **Test Data** | User: john@example.com (John Doe)<br>Role: Manager<br>Status: Active |
| **Expected** | 1. All fields displayed correctly<br>2. Name, email, status, role visible<br>3. Action buttons (Edit, Delete) present<br>4. Row checkbox functional<br>5. Role shown as badge/tag with proper styling |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify data is correctly serialized from database and displayed in template. |
| **Related Files** | assessments/views.py:assign_roles() (lines 6057-6068)<br>assign_roles.html |

---

## Test Cases - Assign Role to User

### AR-004: Assign Role to User (P0)
| Field | Value |
|-------|-------|
| **Test ID** | AR-004 |
| **Category** | Assign Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Assign role to existing user |
| **Description** | User can assign a custom role to an existing user via dropdown/form |
| **Preconditions** | 1. User logged in as admin<br>2. User "alice@test.com" exists with no role currently<br>3. Role "Supervisor" exists in database<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate alice@test.com in table<br>3. Click Edit button for alice<br>4. Observe edit panel/modal opens<br>5. Find Role dropdown field<br>6. Click dropdown and select "Supervisor"<br>7. Click "Save" button<br>8. Wait for confirmation (success message should appear)<br>9. Verify edit panel closes<br>10. Verify alice's role in table now shows "Supervisor" |
| **Test Data** | User: alice@test.com (no initial role)<br>Role to assign: Supervisor |
| **Expected** | 1. Edit panel opens correctly<br>2. Role dropdown shows available roles<br>3. Supervisor role can be selected<br>4. Save succeeds with success message<br>5. Role appears in table immediately<br>6. Refresh confirms role persisted |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify role assignment updates both database and UI immediately. Check for success notification. |
| **Related Files** | assessments/views.py:assign_roles() (lines 6037-6042)<br>assign_roles.html |

---

### AR-005: Assign Role from Create User Form (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-005 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Create new user and assign role simultaneously |
| **Description** | When creating a new user, role can be assigned in same form |
| **Preconditions** | 1. User logged in as admin<br>2. Role "Manager" exists<br>3. Email "newuser@test.com" does not exist<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Click "Create User" button<br>3. Observe multi-step form opens (Step 1: User Info)<br>4. Enter email: newuser@test.com<br>5. Enter full name: New User<br>6. Click Next/Continue button<br>7. Observe Step 2 form (Role assignment)<br>8. Click Role dropdown<br>9. Select "Manager" role<br>10. Continue through remaining steps (if any)<br>11. Click "Create User" final button<br>12. Verify success message<br>13. Verify new user appears in table with "Manager" role |
| **Test Data** | Email: newuser@test.com<br>Name: New User<br>Role: Manager |
| **Expected** | 1. Multi-step form opens<br>2. User info entered correctly<br>3. Role selection available in step 2<br>4. User created successfully<br>5. User appears in table with assigned role<br>6. User email sent with temporary password |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if multi-step form exists. Verify email notification sent to new user. |
| **Related Files** | assessments/views.py:assign_roles()<br>assign_roles.html (lines 36-181 - create user form) |

---

### AR-006: Change User Role (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-006 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Change existing user role to different role |
| **Description** | User currently assigned one role can be reassigned to different role |
| **Preconditions** | 1. User logged in as admin<br>2. User "bob@test.com" has role "Viewer"<br>3. Role "Editor" exists<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate bob@test.com in table<br>3. Verify role shows "Viewer"<br>4. Click Edit button<br>5. Find Role dropdown<br>6. Click dropdown and select "Editor"<br>7. Click "Save"<br>8. Verify success message<br>9. Check table - bob's role should now be "Editor"<br>10. Verify old role "Viewer" removed<br>11. Refresh page and verify change persisted |
| **Test Data** | User: bob@test.com<br>Old role: Viewer<br>New role: Editor |
| **Expected** | 1. Edit opens with current role selected<br>2. Can change to different role<br>3. Save succeeds<br>4. Table updates immediately<br>5. Old role replaced with new role<br>6. Change persists after refresh |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify old role is completely replaced (not added). Check database to confirm only one role assigned. |
| **Related Files** | assessments/views.py:assign_roles()<br>assign_roles.html |

---

## Test Cases - User Management

### AR-007: Edit User Information (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-007 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Edit user name and other details |
| **Description** | Administrator can edit user's name, email, and other profile information |
| **Preconditions** | 1. User logged in as admin<br>2. User "charlie@test.com" exists with name "Charlie Old"<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate charlie@test.com<br>3. Click Edit button<br>4. Observe edit form opens<br>5. Change full name to "Charlie New"<br>6. Verify email field (read-only or editable)<br>7. Click "Save"<br>8. Verify success message<br>9. Check table - name should be "Charlie New"<br>10. Refresh and verify name change persisted |
| **Test Data** | User: charlie@test.com<br>Old name: Charlie Old<br>New name: Charlie New |
| **Expected** | 1. Edit form opens<br>2. Name field editable<br>3. Changes saved successfully<br>4. Table updates immediately<br>5. Change visible after refresh<br>6. Email unchanged |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify which fields are editable. Check if email is protected. |
| **Related Files** | assessments/views.py:assign_roles()<br>assign_roles.html |

---

### AR-008: Delete User (P0)
| Field | Value |
|-------|-------|
| **Test ID** | AR-008 |
| **Category** | Assign Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | Delete user with confirmation |
| **Description** | Administrator can delete a user from system with confirmation modal |
| **Preconditions** | 1. User logged in as admin<br>2. User "dave@test.com" exists<br>3. No critical data dependencies (optional)<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate dave@test.com in table<br>3. Click Delete button (trash icon)<br>4. Observe confirmation modal appears<br>5. Modal shows: "Delete dave@test.com?"<br>6. Verify "Cancel" button present<br>7. Verify "Confirm Delete" button present<br>8. Click "Confirm Delete"<br>9. Wait for deletion (success message should appear)<br>10. Verify dave@test.com removed from table<br>11. Verify user no longer in database<br>12. Refresh page and verify deletion persisted |
| **Test Data** | User: dave@test.com |
| **Expected** | 1. Confirmation modal shows<br>2. Modal displays correct user email<br>3. Cancel prevents deletion<br>4. Confirm deletes user<br>5. Success message shown<br>6. User removed from table<br>7. User no longer exists in database<br>8. Deletion persists after refresh |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify confirmation prevents accidental deletion. Check for cascade delete of related records. |
| **Related Files** | assessments/views.py:delete_user()<br>assign_roles.html (lines 240-263 - delete modal) |

---

### AR-009: Cancel Delete Operation (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-009 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Cancel delete prevents user deletion |
| **Description** | Clicking Cancel in delete modal prevents user from being deleted |
| **Preconditions** | 1. User logged in as admin<br>2. User "eve@test.com" exists<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate eve@test.com<br>3. Click Delete button<br>4. Observe confirmation modal<br>5. Click "Cancel" button<br>6. Observe modal closes<br>7. Verify eve@test.com still in table<br>8. Verify no changes made<br>9. Refresh page and verify user still exists |
| **Test Data** | User: eve@test.com |
| **Expected** | 1. Modal opens<br>2. Cancel button closes modal<br>3. User NOT deleted<br>4. Table unchanged<br>5. User still in database after refresh |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify Cancel properly prevents deletion. |
| **Related Files** | assign_roles.html (lines 240-263 - delete modal) |

---

## Test Cases - Permission Inheritance

### AR-010: User Inherits Permissions from Role (P0)
| Field | Value |
|-------|-------|
| **Test ID** | AR-010 |
| **Category** | Assign Roles |
| **Priority** | P0 (Critical) |
| **Test Name** | User inherits all permissions from assigned role |
| **Description** | When role is assigned to user, user automatically inherits all permissions defined in that role |
| **Preconditions** | 1. User logged in as admin<br>2. Role "Reporter" exists with permissions:<br>   - view_overall_report<br>   - view_candidate_report<br>   - export_report<br>3. User "frank@test.com" has no role<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Assign "Reporter" role to frank@test.com<br>3. Verify success message<br>4. Logout and login as frank@test.com<br>5. Navigate to dashboard<br>6. Verify Reports tab is visible (permission inherited)<br>7. Click Reports tab<br>8. Verify frank can access reports<br>9. Verify report export button visible (has export_report permission)<br>10. Verify other restricted tabs are hidden (those without permissions) |
| **Test Data** | User: frank@test.com (no initial role)<br>Role: Reporter<br>Expected permissions: view_overall_report, view_candidate_report, export_report |
| **Expected** | 1. Role assigned successfully<br>2. User inherits all 3 permissions<br>3. User can access Reports section<br>4. Report export available<br>5. UI reflects inherited permissions<br>6. Restricted features hidden |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Login as assigned user to verify permissions actually grant access. Check navigation tabs show/hide based on permissions. |
| **Related Files** | assessments/models.py:EbekUser.get_all_permissions_from_roles()<br>assessments/models.py:EbekUser.check_icon_navigation_permissions() |

---

### AR-011: Permission Change Affects User Access (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-011 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Changing role permissions affects user access immediately |
| **Description** | When role's permissions are modified, assigned user's access changes immediately |
| **Preconditions** | 1. User logged in as admin<br>2. User "grace@test.com" has "Limited" role with only:<br>   - view_institutes permission<br>3. "Limited" role missing:<br>   - view_overall_report<br>4. grace is currently logged in (or can login)<br>5. Page loaded |
| **Test Steps** | 1. Navigate to /create-roles/ (role management)<br>2. Find "Limited" role<br>3. Edit it and add "view_overall_report" permission<br>4. Save role changes<br>5. Have grace@test.com logout and login again<br>6. Navigate to dashboard<br>7. Verify Reports tab now visible (permission was added)<br>8. Verify grace can now access reports<br>9. Return to assign-roles and remove permission from role<br>10. Have grace logout and login<br>11. Verify Reports tab hidden again |
| **Test Data** | User: grace@test.com (role: Limited)<br>Role: Limited<br>Permission to add: view_overall_report |
| **Expected** | 1. Role edit succeeds<br>2. Permission added to role<br>3. User's access updated immediately<br>4. Reports tab visible after re-login<br>5. User can access new permission<br>6. Removing permission removes user access<br>7. Changes reflected in both directions |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Permission inheritance is automatic. No need to reassign role. Verify sync happens correctly. |
| **Related Files** | assessments/models.py:CustomRole.get_permission_codes()<br>assessments/views.py:edit_role() |

---

### AR-012: Multiple Users with Same Role Share Permissions (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-012 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Multiple users assigned same role have identical permissions |
| **Description** | Different users assigned same role have same access and permissions |
| **Preconditions** | 1. User logged in as admin<br>2. Role "Viewer" exists with permissions:<br>   - view_overall_report<br>   - view_institutes<br>3. Users "henry@test.com" and "iris@test.com" both have "Viewer" role<br>4. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Verify both henry and iris show "Viewer" role<br>3. Login as henry@test.com<br>4. Verify Reports and Institutions tabs visible<br>5. Logout and login as iris@test.com<br>6. Verify same tabs visible for iris<br>7. Verify both have identical permissions<br>8. Test feature access - both should have same capabilities |
| **Test Data** | Users: henry@test.com, iris@test.com<br>Role: Viewer<br>Permissions: view_overall_report, view_institutes |
| **Expected** | 1. Both users show same role in table<br>2. Both have identical permissions<br>3. Both can access same features<br>4. Both see same UI tabs and buttons<br>5. No differences in access |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify permission inheritance is consistent across multiple users. |
| **Related Files** | assessments/models.py:EbekUser |

---

## Test Cases - User Status Management

### AR-013: Toggle User Active Status (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-013 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Toggle user active/inactive status |
| **Description** | Administrator can toggle user's active status; inactive users cannot login |
| **Preconditions** | 1. User logged in as admin<br>2. User "jack@test.com" exists with is_active=True<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate jack@test.com in table<br>3. Observe Status column shows "Active" (green indicator)<br>4. Click status toggle/button for jack<br>5. Observe status changes to "Inactive" (red indicator)<br>6. Verify database: is_active = False<br>7. Logout and try to login as jack@test.com<br>8. Verify login fails or shows "User inactive" message<br>9. Return to /assign-roles/ as admin<br>10. Toggle jack back to Active<br>11. Verify status shows "Active" again<br>12. Try to login as jack - should succeed |
| **Test Data** | User: jack@test.com |
| **Expected** | 1. Status toggle visible and functional<br>2. Visual feedback shows change (green/red)<br>3. Database updated (is_active field)<br>4. Inactive user blocked from login<br>5. Active user can login<br>6. Status persists after page refresh<br>7. Toggle works both directions |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check middleware that blocks inactive user login (CheckInactiveUserMiddleware). Verify status affects authentication. |
| **Related Files** | assessments/middleware.py:CheckInactiveUserMiddleware<br>assign_roles.html (status toggle) |

---

### AR-014: Inactive User Access Denied (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-014 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Inactive user cannot access system |
| **Description** | User with is_active=False is redirected to login on any page access |
| **Preconditions** | 1. Admin user logged in<br>2. User "kate@test.com" is currently logged in<br>3. Admin disables kate's account (sets is_active=False)<br>4. kate still has active session |
| **Test Steps** | 1. Have kate@test.com logged in and on dashboard<br>2. In another browser/window, login as admin<br>3. Navigate to /assign-roles/<br>4. Find kate@test.com and set to Inactive<br>5. In kate's session, refresh any page or navigate<br>6. Observe kate is logged out and redirected to login<br>7. Try to login as kate<br>8. Verify login fails with "User is inactive" or similar<br>9. Return to admin, set kate to Active<br>10. Try to login as kate - should succeed |
| **Test Data** | User: kate@test.com |
| **Expected** | 1. Inactive user logged out immediately<br>2. Redirected to login page<br>3. Cannot login while inactive<br>4. Activation restores access<br>5. Middleware enforces restriction<br>6. No access to protected pages when inactive |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify middleware redirects on each request. Check timing of logout (immediate or on next request). |
| **Related Files** | assessments/middleware.py:CheckInactiveUserMiddleware<br>assessments/views.py:assign_roles() |

---

## Test Cases - Search & Filter

### AR-015: Search Users by Email (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-015 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Search user table by email |
| **Description** | User can search table by email to find specific users |
| **Preconditions** | 1. User logged in as admin<br>2. Users exist in table:<br>   - alice@test.com<br>   - alice.admin@test.com<br>   - bob@test.com<br>   - charlie@test.com<br>   - david@test.com<br>3. Search box visible on page |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate search box at top of users table<br>3. Type "alice" in search<br>4. Observe table filters in real-time<br>5. Verify shows: alice@test.com, alice.admin@test.com<br>6. Verify hidden: bob, charlie, david<br>7. Clear search and type "bob"<br>8. Verify shows only: bob@test.com<br>9. Clear search and type "david"<br>10. Verify shows only: david@test.com<br>11. Type "xyz" (no match)<br>12. Verify empty results with "No users found" |
| **Test Data** | Search terms: "alice", "bob", "david", "xyz" |
| **Expected** | 1. Search case-insensitive<br>2. Real-time filtering<br>3. "alice" returns 2 results<br>4. "bob" returns 1 result<br>5. "david" returns 1 result<br>6. "xyz" returns 0 results<br>7. Clear search shows all users<br>8. Search icon/button functional |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify search is client-side (JavaScript) or server-side. Check partial matching works. |
| **Related Files** | assign_roles.html (search/filter JavaScript)<br>assessments/views.py:assign_roles() |

---

### AR-016: Filter Users by Role (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-016 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Filter users by assigned role |
| **Description** | Show only users with specific role assigned |
| **Preconditions** | 1. User logged in as admin<br>2. Users with roles:<br>   - alice, bob: Manager role<br>   - charlie, david: Viewer role<br>   - eve: Editor role<br>   - frank: No role<br>3. Filter dropdown visible |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Locate Role filter dropdown (or filter icon)<br>3. Click filter dropdown<br>4. Verify all role options shown<br>5. Select "Manager" filter<br>6. Observe table updates<br>7. Verify shows: alice, bob (2 results)<br>8. Verify hidden: charlie, david, eve, frank<br>9. Click "Viewer" filter<br>10. Verify shows: charlie, david (2 results)<br>11. Select "No role" filter<br>12. Verify shows: frank (1 result)<br>13. Clear filter<br>14. Verify all users shown again |
| **Test Data** | Roles: Manager, Viewer, Editor, No role<br>Users with assignments as described |
| **Expected** | 1. Filter dropdown shows role options<br>2. Manager filter works (2 results)<br>3. Viewer filter works (2 results)<br>4. "No role" filter works (1 result)<br>5. Multiple selection possible (if available)<br>6. Clear filter restores full list |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Check if filter is implemented. May require feature development. |
| **Related Files** | assign_roles.html<br>assessments/views.py:assign_roles() |

---

## Test Cases - Error Handling

### AR-017: Invalid Email Format (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-017 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Invalid email format rejected on user creation |
| **Description** | User creation form validates email format and rejects invalid emails |
| **Preconditions** | 1. User logged in as admin<br>2. Create User form accessible<br>3. Page loaded |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Click "Create User" button<br>3. Observe user creation form<br>4. Try to enter invalid emails:<br>   - Test 1: "notanemail" (no @ symbol)<br>   - Test 2: "@example.com" (no local part)<br>   - Test 3: "user@" (no domain)<br>   - Test 4: "user @example.com" (space)<br>5. For each invalid email, try to proceed<br>6. Verify form shows validation error<br>7. Verify error message: "Please enter a valid email"<br>8. Verify Create button disabled or form won't submit |
| **Test Data** | Invalid emails: "notanemail", "@example.com", "user@", "user @example.com" |
| **Expected** | 1. Invalid emails rejected<br>2. Validation error shown<br>3. Form won't submit<br>4. User not created<br>5. Error message clear and helpful |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify both HTML5 validation and server-side validation. |
| **Related Files** | assign_roles.html (form validation)<br>assessments/views.py |

---

### AR-018: Duplicate Email Prevention (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-018 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Cannot create user with existing email |
| **Description** | User creation fails if email already exists in system |
| **Preconditions** | 1. User logged in as admin<br>2. User "existing@test.com" already exists<br>3. Create User form accessible |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Click "Create User" button<br>3. Enter email: "existing@test.com"<br>4. Enter name: "Test User"<br>5. Try to proceed to next step<br>6. Observe error: "Email already exists" or similar<br>7. Verify user not created<br>8. Try again with different email<br>9. Verify creation succeeds |
| **Test Data** | Existing email: existing@test.com<br>New email: newuser@test.com |
| **Expected** | 1. Duplicate email rejected<br>2. Error message shown<br>3. Form won't proceed<br>4. User not created in database<br>5. Can proceed with different email |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify both client-side and server-side duplicate check. |
| **Related Files** | assign_roles.html<br>assessments/views.py |

---

### AR-019: Database Error Handling (P1)
| Field | Value |
|-------|-------|
| **Test ID** | AR-019 |
| **Category** | Assign Roles |
| **Priority** | P1 (High) |
| **Test Name** | Graceful handling of database errors |
| **Description** | If database is unavailable, user sees friendly error instead of 500 page |
| **Preconditions** | 1. User logged in as admin<br>2. Page loaded<br>3. Database connection can be simulated as down |
| **Test Steps** | 1. Navigate to /assign-roles/<br>2. Verify page loads normally<br>3. Simulate database connection failure (disconnect DB)<br>4. Try to perform action (assign role, delete user, etc.)<br>5. Observe error handling<br>6. Verify friendly error message shown (not 500 stack trace)<br>7. Verify user can retry once DB restored<br>8. Restore database connection<br>9. Retry operation<br>10. Verify operation succeeds |
| **Test Data** | Valid user and role data |
| **Expected** | 1. Database error caught<br>2. Friendly error message shown<br>3. No technical stack trace exposed<br>4. User informed DB is down<br>5. Can retry once fixed<br>6. System recovers properly |
| **Actual** | [Fill during testing] |
| **Status** | Not Run |
| **Notes** | Verify error handling in views and graceful degradation. Check server logs for detailed errors. |
| **Related Files** | assessments/views.py:assign_roles()<br>assessments/views.py error handling |

---

## Test Environment Setup

### Database Setup

**Required Data:**

```sql
-- Roles
INSERT INTO assessments_customrole (name, description) VALUES
('Manager', 'Full access to management features'),
('Viewer', 'Read-only access'),
('Editor', 'Edit access to content'),
('Supervisor', 'Supervision role'),
('Reporter', 'Report access only'),
('Limited', 'Limited access');

-- Permissions
INSERT INTO assessments_permission (code, name, category, is_active) VALUES
('view_overall_report', 'View Overall Report', 'view', TRUE),
('view_candidate_report', 'View Candidate Report', 'view', TRUE),
('view_institutes', 'View Institutions', 'view', TRUE),
('view_learners', 'View Learners', 'view', TRUE),
('create_institute', 'Create Institution', 'create', TRUE),
('create_user', 'Create User', 'create', TRUE),
('edit_learner', 'Edit Learner', 'edit', TRUE),
('delete_learner', 'Delete Learner', 'delete', TRUE),
('export_report', 'Export Report', 'export', TRUE);

-- Assign permissions to roles
INSERT INTO assessments_customrole_permissions (customrole_id, permission_id) VALUES
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8);  -- Manager: all
(2, 1), (2, 2);  -- Viewer: reports only
(5, 1), (5, 2), (5, 9);  -- Reporter: reports + export
(6, 3);  -- Limited: institutions only

-- Users for testing
INSERT INTO assessments_ebekuser (email, full_name, is_active, user_role) VALUES
('admin@test.com', 'Admin User', TRUE, 'super_admin'),
('alice@test.com', 'Alice Smith', TRUE, 'institute_admin'),
('alice.admin@test.com', 'Alice Admin', TRUE, 'group_admin'),
('bob@test.com', 'Bob Jones', TRUE, 'institute_admin'),
('charlie@test.com', 'Charlie Brown', TRUE, 'group_admin'),
('david@test.com', 'David White', TRUE, 'institute_admin'),
('eve@test.com', 'Eve Davis', TRUE, 'hospital_admin'),
('frank@test.com', 'Frank Miller', TRUE, 'supervisor'),
('student1@test.com', 'Student One', TRUE, 'student'),
('nurse1@test.com', 'Nurse One', TRUE, 'nurse');

-- Assign initial roles to users
UPDATE assessments_ebekuser SET custom_roles_id = 1 WHERE email = 'alice@test.com';  -- Manager
UPDATE assessments_ebekuser SET custom_roles_id = 2 WHERE email = 'bob@test.com';  -- Viewer
UPDATE assessments_ebekuser SET custom_roles_id = 2 WHERE email = 'charlie@test.com';  -- Viewer
UPDATE assessments_ebekuser SET custom_roles_id = 3 WHERE email = 'david@test.com';  -- Editor
UPDATE assessments_ebekuser SET custom_roles_id = 5 WHERE email = 'eve@test.com';  -- Reporter
```

### User Credentials

**Admin User:**
```
Email: admin@test.com
Password: Test@1234
Role: super_admin
Access: Full access to /assign-roles/
```

### Browser Requirements
- Chrome/Firefox/Safari (latest version)
- JavaScript enabled
- Cookies enabled
- Pop-ups allowed (for modals)

---

## Test Data

### Users for Testing
| Email | Name | Initial Role | Status |
|-------|------|--------------|--------|
| alice@test.com | Alice Smith | Manager | Active |
| bob@test.com | Bob Jones | Viewer | Active |
| charlie@test.com | Charlie Brown | Viewer | Active |
| david@test.com | David White | Editor | Active |
| eve@test.com | Eve Davis | Reporter | Active |
| frank@test.com | Frank Miller | No Role | Active |
| student1@test.com | Student One | student | Active |
| nurse1@test.com | Nurse One | nurse | Active |

### Roles for Testing
| Role Name | Permission Count | Key Permissions |
|-----------|-----------------|-----------------|
| Manager | 8 | All permissions |
| Viewer | 2 | view_overall_report, view_candidate_report |
| Editor | 3 | view_*, edit_*, create_* |
| Supervisor | 3 | view_overall_report, create_user, export_report |
| Reporter | 3 | view_overall_report, view_candidate_report, export_report |
| Limited | 1 | view_institutes |

---

## Success Criteria

- ✅ All tests AR-001 to AR-019 show "Pass" status
- ✅ No unhandled JavaScript errors
- ✅ No 500 server errors for valid input
- ✅ Role assignment works correctly
- ✅ Permission inheritance verified
- ✅ User status toggle functional
- ✅ Delete confirmation prevents accidental deletion
- ✅ Search and filter operational

### Critical Path (P0 Tests)
- ✅ AR-001: Page loads with users list
- ✅ AR-004: Assign role to user
- ✅ AR-008: Delete user with confirmation
- ✅ AR-010: User inherits permissions from role

---

**Document Version:** 2.0 (Functional Test Cases)
**Last Updated:** November 30, 2025
**Module:** Assign Roles (/assign-roles/)
**Status:** Ready for Testing

