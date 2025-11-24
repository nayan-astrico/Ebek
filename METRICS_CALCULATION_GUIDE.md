# OSCE Metrics Calculation Guide

## Overview
This document explains how the OSCE metrics dashboard calculates and displays three key metrics: **Average Score (KPI Card)**, **Grade Distribution**, and **Category Performance**. All three use consistent student-level averaging methodology.

---

## 1. Average Score (KPI Card)

### What it shows
The **Average Score** displayed in the KPI card is the overall performance of all students in a semester/unit.

### Calculation Logic

**Step 1: Calculate each student's overall percentage**
```python
for each student:
    overall_percentage = (total_marks_obtained / total_max_marks) * 100
```

**Step 2: Average all student percentages**
```python
avg_score = sum(all_student_percentages) / number_of_students
grade_letter = get_grade(avg_score)  # A=90+, B=80-89, C=70-79, D=60-69, E=<60
```

### Code Location
- **Backend:** `assessments/management/commands/process_metric_queue.py` (lines 533-547)
- **Frontend Display:** `assessments/templates/assessments/metrics_viewer.html` (line 1470)

### Example
**12 Students with Overall Percentages:**
```
Ananya Singh:      80%
Nisha Menon:       73.47%
Arjun Mehta:       70%
Aarav Sharma:      67.87%
Kavya Iyer:        64.56%
Kunal Joshi:       64.1%
Rohit Verma:       62.9%
Sneha Reddy:       62.69%
Rohan Nair:        60%
Meera Krishnan:    57.5%
Aditya Patel:      55.26%
Priya Deshmukh:    38.46%
───────────────────────
Sum:               796.81%
Average:           66.40%
Grade:             D (60-69%)
```

**KPI Card displays:** `66.40% [D]`

---

## 2. Grade Distribution (Pie Chart)

### What it shows
Distribution of students across grade buckets (A, B, C, D, E) based on their **overall grade**.

### Calculation Logic

**Step 1: Calculate each student's overall grade**
```python
for each student:
    overall_percentage = (total_marks_obtained / total_max_marks) * 100
    overall_grade = get_grade(overall_percentage)
```

**Step 2: Count students in each grade bucket**
```python
grade_distribution = {
    'A': count of students with grade A,
    'B': count of students with grade B,
    'C': count of students with grade C,
    'D': count of students with grade D,
    'E': count of students with grade E
}
```

### Grade Mapping
| Grade | Percentage Range |
|-------|-----------------|
| A | 90-100% |
| B | 80-89% |
| C | 70-79% |
| D | 60-69% |
| E | <60% |

### Code Location
- **Backend:** `assessments/management/commands/process_metric_queue.py` (line 363, updated in Phase 4)
- **Frontend Display:** `assessments/templates/assessments/metrics_viewer.html` (lines 1516-1620)

### Example
From the 12 students above:
```
Grade A (90-100%):  0 students
Grade B (80-89%):   1 student  (Ananya = 80%)
Grade C (70-79%):   2 students (Nisha = 73.47%, Arjun = 70%)
Grade D (60-69%):   6 students (Aarav, Kavya, Kunal, Rohit, Sneha, Rohan)
Grade E (<60%):     3 students (Meera = 57.5%, Aditya = 55.26%, Priya = 38.46%)
```

**Pie Chart shows:** 50% D, 25% E, 17% C, 8% B, 0% A

---

## 3. Category Performance (Bar Chart)

### What it shows
Average performance of students in each skill category (e.g., Communication, Clinical Examination, etc.).

### Calculation Logic

**Step 1: For each category, calculate each student's category percentage**
```python
for each category:
    for each student:
        category_percentage = (category_marks_obtained / category_max_marks) * 100
```

**Step 2: Average all student percentages for that category**
```python
for each category:
    category_performance[category] = average(all_student_category_percentages)
```

### Code Location
- **Backend:** `assessments/management/commands/process_metric_queue.py` (lines 549-557)
- **Frontend Display:** `assessments/templates/assessments/metrics_viewer.html` (lines 1510-1513)

### Example
Assume we have 3 categories and 3 students:

**Communication Category:**
```
Student A: 70% (obtained 70/100)
Student B: 75% (obtained 75/100)
Student C: 85% (obtained 85/100)
─────────────────
Average: 76.67%
```

**Clinical Examination Category:**
```
Student A: 65%
Student B: 72%
Student C: 80%
─────────────────
Average: 72.33%
```

**Bar chart displays:** Communication (76.67%), Clinical (72.33%), ...

---

## 4. Student Batch Report (Table)

### What it shows
Individual student performance with Overall grade, Classroom/Mock/Final scores, and breakdown by category.

### Calculation Logic

**For each student:**
```python
# Overall grade (from total marks)
overall_avg = (total_marks_obtained / total_max_marks) * 100
overall_grade = get_grade(overall_avg)

# By exam type
classroom_avg = (classroom_marks_obtained / classroom_max_marks) * 100
mock_avg = (mock_marks_obtained / mock_max_marks) * 100
final_avg = (final_marks_obtained / final_max_marks) * 100

# Category breakdown
for each category:
    category_avg = (category_marks_obtained / category_max_marks) * 100
```

### Code Location
- **Backend:** `assessments/management/commands/process_metric_queue.py` (lines 599-661)
- **Frontend Display:** `assessments/templates/assessments/metrics_viewer.html` (lines 1563-1585)

### Example
```
Name: Ananya Singh
Overall Grade: B (80%)
  Classroom: B (80%)
  Mock: B (80%)
  Final: Not attempted

Category Breakdown:
  - Communication: 85%
  - Clinical Examination: 78%
  - Procedural Skills: 80%
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. DATA COLLECTION (process_metric_queue.py - PHASE 2)             │
│                                                                       │
│ For each student's exam:                                            │
│   - Get marks_obtained and max_marks from exam metadata             │
│   - Calculate percentage: (marks / max) * 100                       │
│   - Store in students_data[student_id]                             │
│   - Also store by: exam_type, category, procedure                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. AGGREGATION (process_metric_queue.py - PHASE 4)                 │
│                                                                       │
│ From students_data, calculate:                                      │
│   - Average Score: avg(all_student_overall_percentages)            │
│   - Grade Distribution: count(students_by_grade)                   │
│   - Category Performance: avg(all_student_category_percentages)     │
│   - Student Report: individual student details                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. FIRESTORE STORAGE (process_metric_queue.py - PHASE 5)           │
│                                                                       │
│ SemesterMetrics document:                                           │
│   {                                                                  │
│     avg_score: 66.40,                                              │
│     grade_letter: 'D',                                              │
│     grade_distribution: {A: 0, B: 1, C: 2, D: 6, E: 3},           │
│     category_performance: {...},                                    │
│     student_batch_report: [...]                                    │
│   }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. API ENDPOINT (/api/semester-metrics/)                            │
│                                                                       │
│ Returns SemesterMetrics from Firestore                             │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. FRONTEND DISPLAY (metrics_viewer.html)                           │
│                                                                       │
│ renderSemesterDashboard(data):                                      │
│   - KPI Card: ${data.avg_score}% [${data.grade_letter}]           │
│   - Grade Chart: renderGradeDistributionChart(data.grade_dist)     │
│   - Category Chart: renderCategoryChart(data.category_perf)        │
│   - Student Table: renderStudentBatchReport(data.student_report)   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Consistency Points

✅ **All three metrics are calculated from the same source:** `students_data` dictionary

✅ **All use student-level averaging:** Not exam-wise or procedure-wise

✅ **Same grade mapping:** A=90+, B=80-89, C=70-79, D=60-69, E=<60

✅ **Same marks calculation:** Total marks obtained ÷ Total max marks × 100

---

## Important Notes

### 1. Total Marks Method (NOT Averaging Percentages)
```python
# CORRECT - Total marks method
overall = (sum_of_all_marks_obtained / sum_of_all_max_marks) * 100

# WRONG - Averaging percentages (can skew results)
overall = average([exam1_pct, exam2_pct, exam3_pct])
```

### 2. Student-Level Aggregation (NOT Exam-Level)
```python
# CORRECT - Student-level (what we now do)
student_overall_percentages = [80%, 73.47%, 70%, ...]
avg_score = average(student_overall_percentages)

# WRONG - Exam-level (old method)
all_exam_percentages = [80%, 80%, 73.47%, 73.47%, 70%, 70%, ...]
avg_score = average(all_exam_percentages)  # Counts each exam equally
```

### 3. Firestore Structure
Each Semester generates one `SemesterMetrics` document with:
```
Document ID: "{unit_name}_{year}_{semester}"
Example: "DJ Sanghvi College_2025_1"

Fields:
  - avg_score: float (e.g., 66.40)
  - grade_letter: string (e.g., "D")
  - grade_distribution: object {A: 0, B: 1, C: 2, D: 6, E: 3}
  - category_performance: object {category_name: avg_score, ...}
  - student_batch_report: array of student objects
  - ... other fields
```

---

## Running Metrics Computation

```bash
# Process unprocessed queue items (normal operation)
python manage.py process_metric_queue

# Force recomputation of all data (for debugging/testing)
# Temporarily modify: .where('processed', '==', False)
# To: .limit(1000)  # Process all items regardless of status
```

---

## Testing & Verification

### Manual Verification
1. Get a semester's metrics from Firestore: `SemesterMetrics/{unit}_{year}_{semester}`
2. Verify `avg_score` = average of all student overall percentages
3. Verify `grade_distribution` counts students by their overall grade
4. Verify `category_performance` = average of each student's category percentage

### API Testing
```bash
# Get semester metrics
curl "http://localhost:8000/api/semester-metrics/?unit_name=DJ%20Sanghvi%20College&year=2025&semester=1"

# Expected response includes avg_score, grade_distribution, category_performance
```

---

## References
- Backend: `assessments/management/commands/process_metric_queue.py`
- Frontend: `assessments/templates/assessments/metrics_viewer.html`
- Database: Firestore `SemesterMetrics` and `UnitMetrics` collections
