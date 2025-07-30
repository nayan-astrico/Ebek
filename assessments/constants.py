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
        ('nurse', 'Working Nurse')
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