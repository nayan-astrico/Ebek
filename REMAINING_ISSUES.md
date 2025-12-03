# Remaining Issues Analysis

## Issues Identified

### 1. ✅ Grading System (FIXED)
- **Status:** COMPLETED
- **Changes:** Updated from A+/B+/C+ to A/B/C/D/E
  - A >= 90%
  - B >= 80%
  - C >= 70%
  - D >= 60%
  - E < 60%

### 2. ❓ Skills/Category Click Functionality
- **Status:** NEEDS INVESTIGATION
- **Problem:** "On clicking skills the functionality is not proper"
- **Current Implementation:**
  - Uses `/api/skills-for-category/` endpoint
  - NOT part of optimized pre-computed system
  - Still queries BatchAssignment directly
- **Possible Issue:**
  - May need to integrate with pre-computed `SemesterMetrics` data
  - Skills data should come from `skills_by_category` field in the optimized API response

### 3. ❓ Data Structure Inconsistency
- **Status:** NEEDS REVIEW
- **Issue:** Batches collection uses `unitType: "institution"` while BatchAssignment/BatchAssignmentSummary use `unitType: "institute"`
- **Impact:** Management command doesn't query Batches, so no immediate impact
- **Note:** Keep monitoring this inconsistency

### 4. ❓ Filter Behavior
- **Status:** NEEDS CLARIFICATION
- **Requirement:** "when certain filters are applied remove the existing analytics Client has given good breakdown"
- **Interpretation:** When semester/OSCE level filters are applied, only show data for that specific filter, not overall data
- **Current Implementation:**
  - Optimized API returns error for OSCE level/procedure filters
  - Need to implement filtered views

## Data Structure Reference (from user)

### BatchAssignment
```
unitType: "institute"  // Note: "institute" not "institution"
unit_name: "DJ Sanghvi College"
unit: /InstituteNames/51 (reference)
```

### BatchAssignmentSummary
```
unitType: "institute"  // Note: "institute" not "institution"
unit_id: "51"
unit_name: "DJ Sanghvi College"
```

### Batches
```
unitType: "institution"  // Note: "institution" not "institute" - INCONSISTENCY!
unit: /InstituteNames/51 (reference)
```

## Questions for User

1. **Skills Functionality:** What exactly is not working when clicking on a category/skill?
   - Does the skills section not appear?
   - Is the data incorrect?
   - Is there an error?

2. **Filter Behavior:** When filters are applied:
   - Should we hide all sections until filters are applied?
   - Should we show a different layout when filters are active?
   - Should certain KPIs change based on filters?

3. **Grade Distribution:** What specifically is wrong with the grade distribution pie chart?

## Next Steps

1. Test skills/category click functionality manually
2. Review optimized API response structure
3. Ensure skills data is properly returned from pre-computed metrics
4. Implement proper filter handling based on user requirements

