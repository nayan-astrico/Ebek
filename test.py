from django.contrib.auth import get_user_model
from assessments.models import Institution, Learner
import random
import string

User = get_user_model()

# List of institutions to create
institutions = [
    "AIIMS Delhi",
    "PGIMER Chandigarh",
    "MAMC Delhi",
    "GMC Mumbai",
    "KEM Hospital Mumbai",
    "JIPMER Puducherry",
    "MGM Medical College Indore",
    "GMC Nagpur",
    "BMC Bangalore",
    "CMC Vellore"
]

# Create institutions
created_institutions = []
for inst_name in institutions:
    institution, created = Institution.objects.get_or_create(
        name=inst_name,
        defaults={
            'is_active': True,
            'state': 'Delhi' if 'Delhi' in inst_name else 'Other',
        }
    )
    created_institutions.append(institution)
    print(f"{'Created' if created else 'Found'} institution: {inst_name}")

# Get all existing learners
existing_learners = Learner.objects.all()
print(f"Found {existing_learners.count()} existing learners")

# Assign random institutions to existing learners
for learner in existing_learners:
    # Update learner user data
    user = learner.learner_user
    if user:
        # Generate random phone if not exists
        if not user.phone_number:
            user.phone_number = ''.join(random.choices(string.digits, k=10))
        
        # Set user role if not exists
        if not hasattr(user, 'user_role'):
            user.user_role = 'learner'
        
        # Set random name if not exists
        if not user.full_name:
            user.full_name = f"Learner {random.randint(1000, 9999)}"
        
        # Set random password if not set
        if not user.has_usable_password():
            default_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user.set_password(default_password)
        
        user.save()
        print(f"Updated user: {user.email}")

    # Randomly assign institution
    learner.college = random.choice(created_institutions)
    
    # Randomly assign other fields if they're empty
    if not learner.learner_type:
        learner.learner_type = random.choice(['student', 'doctor'])
    if not learner.onboarding_type:
        learner.onboarding_type = random.choice(['college', 'hospital'])
    if not learner.course:
        learner.course = random.choice(['MBBS', 'MD', 'MS'])
    if not learner.stream:
        learner.stream = random.choice(['Medicine', 'Surgery', 'Pediatrics'])
    if not learner.year_of_study:
        learner.year_of_study = random.randint(1, 5)
    if not learner.learner_gender:
        learner.learner_gender = random.choice(['male', 'female'])
    if not learner.state:
        learner.state = 'Delhi'
    if not learner.district:
        learner.district = 'New Delhi'
    if not learner.pincode:
        learner.pincode = '110001'
    if not learner.address:
        learner.address = 'Sample Address'
    
    learner.save()
    print(f"Updated learner: {learner.learner_user.full_name} at {learner.college.name}")

print(f"Successfully created {len(created_institutions)} institutions and updated {existing_learners.count()} learners")
