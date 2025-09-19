role = (
    ('super_admin', 'super_admin'),
    ('ebek_admin', 'ebek_admin'),
    ('group_admin', 'group_admin'),
    ('institute_admin', 'institute_admin'),
    ('hospital_admin', 'hospital_admin'),
    ('student', 'student'),
    ('nurse', 'nurse'),
    ('supervisor', 'supervisor'),
    ('skillathon_admin', 'skillathon_admin'),
)

ONBOARDING_TYPES = [
        ('b2b', 'B2B'),
        ('b2c', 'B2C')
    ]

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other')
]

LEARNER_TYPES = [
        ('student', 'Student'),
        ('nurse', 'Working Nurse'),
        ('not_applicable', 'Not Applicable')
    ]
    
STREAM_CHOICES = [
        ('bsc_4y', 'BSc (4Y)'),
        ('gnm_3y', 'GNM (3Y Diploma)'),
        ('post_basic_2y', 'Post-basic (2Y)'),
        ('msc', 'MSc (Speciality)')
    ]

TYPE_OF_EVENT = [
    ('skillathon', 'Skillathon'),
    ('mock', 'Mock'),
    ('classroom', 'Classroom'),
    ('final', 'Final')
]

PERMISSIONS = [
    ('view_overall_report', 'View Overall Report'),
    ('view_candidate_report', 'View Candidate Report'),
    ('download_candidate_report', 'Download Candidate Report'),
    ('update_course_status', 'Update Course Status'),
    ('edit_course', 'Edit Course'),
    ('delete_course', 'Delete Course'),
    ('create_course', 'Create Course'),
    ('view_courses', 'View Courses'),
    ('view_batches', 'View Batches'),
    ('edit_batch', 'Edit Batch'),
    ('delete_batch', 'Delete Batch'),
    ('create_batch', 'Create Batch'),
    ('add_learner_in_batch', 'Add Learner in Batch'),
    ('remove_learner_from_batch', 'Remove Learner from Batch'),
    ('add_course_in_batch', 'Add Course in Batch'),
    ('remove_course_from_batch', 'Remove Course from Batch'),
    ('create_institute', 'Create Institute'),
    ('edit_institute', 'Edit Institute'),
    ('delete_institute', 'Delete Institute'),
    ('view_institutes', 'View Institutes'),
    ('create_hospital', 'Create Hospital'),
    ('edit_hospital', 'Edit Hospital'),
    ('delete_hospital', 'Delete Hospital'),
    ('view_hospitals', 'View Hospitals'),
    ('create_group', 'Create Group'),
    ('edit_group', 'Edit Group'),
    ('delete_group', 'Delete Group'),
    ('view_groups', 'View Groups'),
    ('view_skillathons', 'View Skillathons'),
    ('add_learner', 'Add Learner'),
    ('edit_learner', 'Edit Learner'),
    ('delete_learner', 'Delete Learner'),
    ('view_learners', 'View Learners'),
    ('bulk_upload_learners', 'Bulk Upload Learners'),
    ('add_assessor', 'Add Assessor'),
    ('edit_assessor', 'Edit Assessor'),
    ('delete_assessor', 'Delete Assessor'),
    ('view_assessors', 'View Assessors'),
    ('add_skillathon', 'Add Skillathon'),
    ('edit_skillathon', 'Edit Skillathon'),
    ('delete_skillathon', 'Delete Skillathon'),
    ('view_assignment', 'View Assignments'),
    ('assign_assignment', 'Assign Assignment'),
    ('delete_assignment', 'Delete Assignment'),
    ('edit_assignment', 'Edit Assignment')
]