from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from .constants import role
import uuid
from datetime import timedelta
from django.utils import timezone

class EbekUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class EbekUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        max_length=255, unique=True,
        help_text='Required. A valid email address.',
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text='Designates whether this user can log in.')
    is_staff = models.BooleanField(default=False, help_text='Designates whether this user can access the admin site.')
    is_superuser = models.BooleanField(default=False, help_text='Designates whether this user has all permissions without explicitly assigning them.')
    user_role = models.CharField(
        max_length=200, choices=role, default='', null=True, blank=True, help_text='User Role'
    )
    date_joined = models.DateTimeField(auto_now_add=True, help_text='When the user account was created.')
    last_login = models.DateTimeField(null=True, blank=True, help_text='Last login timestamp.')
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='ebek_user_set',
        related_query_name='ebek_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='ebek_user_set',
        related_query_name='ebek_user'
    )
    mobile_number = models.CharField(max_length=20, blank=True, null=True)

    objects = EbekUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name or self.email

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class PasswordResetToken(models.Model):
    user = models.ForeignKey('EbekUser', on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # Check if token is less than 5 minutes old and not used
        return (timezone.now() - self.created_at) < timedelta(minutes=10) and not self.is_used

class Group(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=[('institution', 'Institution'), ('hospital', 'Hospital')])
    group_head = models.ForeignKey('EbekUser', on_delete=models.SET_NULL, null=True, related_name='group_head_of')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    group_id = models.CharField(max_length=50, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group_id = str(uuid.uuid4())
        
        self.group_head.user_role = 'group_admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Institution(models.Model):
    name = models.CharField(max_length=255)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField()
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    unit_head = models.ForeignKey('EbekUser', on_delete=models.SET_NULL, null=True, related_name='unit_head_of_institution')
    total_strength = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    institute_id = models.CharField(max_length=50, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.institute_id:
            self.institute_id = str(uuid.uuid4())
        self.unit_head.user_role = 'institute_admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class Hospital(models.Model):
    name = models.CharField(max_length=255)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField()
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    unit_head = models.ForeignKey('EbekUser', on_delete=models.SET_NULL, null=True, related_name='unit_head_of_hospital')
    nurse_strength = models.IntegerField(null=True, blank=True)
    number_of_beds = models.IntegerField(null=True, blank=True)
    hospital_id = models.CharField(max_length=50, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.hospital_id:
            self.hospital_id = str(uuid.uuid4())
        self.unit_head.user_role = 'hospital_admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Learner(models.Model):
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
    ONBOARDING_TYPES = [
        ('b2b', 'B2B'),
        ('b2c', 'B2C')
    ]

    onboarding_type = models.CharField(max_length=3, choices=ONBOARDING_TYPES)
    learner_type = models.CharField(max_length=10, choices=LEARNER_TYPES)
    
    # Student specific fields
    college = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.CharField(max_length=100, null=True, blank=True)
    stream = models.CharField(max_length=20, choices=STREAM_CHOICES, null=True, blank=True)
    year_of_study = models.IntegerField(null=True, blank=True)
    
    # Nurse specific fields
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    educational_qualification = models.CharField(max_length=20, choices=STREAM_CHOICES, null=True, blank=True)
    educational_institution = models.CharField(max_length=255, null=True, blank=True)
    
    # Common fields
    speciality = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField()
    certifications = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    learner_user = models.ForeignKey('EbekUser', on_delete=models.SET_NULL, null=True, blank=True)
    learner_id = models.CharField(max_length=50, unique=True, editable=False)

    def __str__(self):
        return self.learner_user.full_name
    
    def save(self, *args, **kwargs):
        if not self.learner_id:
            self.learner_id = str(uuid.uuid4())
        self.learner_user.user_role = 'learner'
        super().save(*args, **kwargs)

class Assessor(models.Model):
    ASSESSOR_TYPES = [
        ('internal', 'Internal'),
        ('external', 'External')
    ]
    SPECIALIZATION_CHOICES = [
        ('clinical', 'Clinical'),
        ('academic', 'Academic')
    ]

    assessor_type = models.CharField(max_length=10, choices=ASSESSOR_TYPES)
    
    # Internal specific fields
    staff_id = models.CharField(max_length=50, null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True)
    
    # External specific fields
    location = models.CharField(max_length=255, null=True, blank=True)
    
    # Common fields
    qualification = models.CharField(max_length=255)
    designation = models.CharField(max_length=100)
    specialization = models.CharField(max_length=20, choices=SPECIALIZATION_CHOICES)
    is_verifier = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    institution = models.ForeignKey('Institution', null=True, blank=True, on_delete=models.SET_NULL)
    hospital = models.ForeignKey('Hospital', null=True, blank=True, on_delete=models.SET_NULL)
    assessor_user = models.ForeignKey('EbekUser', on_delete=models.SET_NULL, null=True, blank=True)
    assessor_id = models.CharField(max_length=50, unique=True, editable=False)
    def __str__(self):
        return self.assessor_user.full_name
    
    def save(self, *args, **kwargs):
        if not self.assessor_id:
            self.assessor_id = str(uuid.uuid4())
        self.assessor_user.user_role = 'supervisor'
        super().save(*args, **kwargs)

class SkillathonEvent(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]

    name = models.CharField(max_length=255)
    date = models.DateField()
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def learner_count(self):
        return self.learner_set.count()

    @property
    def assessor_count(self):
        return self.assessor_set.count()