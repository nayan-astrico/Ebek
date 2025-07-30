from django import forms
from .models import Group, Institution, Hospital, Learner, Assessor, SkillathonEvent

class GroupForm(forms.ModelForm):
    group_head_name = forms.CharField(label='Group Head Name', max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    group_head_email = forms.EmailField(label='Group Head Email', required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    group_head_phone = forms.CharField(label='Group Head Phone', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Group
        fields = ['name', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check if a group with this name already exists
            existing_group = Group.objects.filter(name__iexact=name)
            if self.instance.pk:
                # Exclude current instance when editing
                existing_group = existing_group.exclude(pk=self.instance.pk)
            
            if existing_group.exists():
                raise forms.ValidationError('A group with this name already exists.')
        
        return name

class InstitutionForm(forms.ModelForm):
    unit_head_name = forms.CharField(label='Unit Head Name', max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    unit_head_email = forms.EmailField(label='Unit Head Email', required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    unit_head_phone = forms.CharField(label='Unit Head Phone', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Institution
        fields = ['name', 'group', 'address', 'state', 'district', 'pin_code', 'onboarding_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
            'onboarding_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter group queryset to show only institution type groups
        self.fields['group'].queryset = Group.objects.filter(type='institution', is_active=True)

class HospitalForm(forms.ModelForm):
    unit_head_name = forms.CharField(label='Unit Head Name', max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    unit_head_email = forms.EmailField(label='Unit Head Email', required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    unit_head_phone = forms.CharField(label='Unit Head Phone', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Hospital
        fields = ['name', 'group', 'address', 'state', 'district', 'pin_code', 'nurse_strength', 'number_of_beds', 'onboarding_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
            'number_of_beds': forms.NumberInput(attrs={'class': 'form-control'}),
            'onboarding_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter group queryset to show only hospital type groups
        self.fields['group'].queryset = Group.objects.filter(type='hospital', is_active=True)

class LearnerForm(forms.ModelForm):
    learner_name = forms.CharField(label='Learner Name', max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    learner_email = forms.EmailField(label='Learner Email', required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    learner_phone = forms.CharField(label='Learner Phone', max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    class Meta:
        model = Learner
        fields = ['onboarding_type', 'learner_type',
                 'college', 'course', 'stream', 'year_of_study', 'hospital', 'designation',
                 'years_of_experience', 'educational_qualification', 'educational_institution',
                 'speciality', 'state', 'district', 'pincode', 'address', 'date_of_birth',
                 'certifications', 'learner_gender', 'skillathon_event']
        widgets = {
            'onboarding_type': forms.Select(attrs={'class': 'form-control'}),
            'learner_type': forms.Select(attrs={'class': 'form-control'}),
            'college': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'stream': forms.Select(attrs={'class': 'form-control'}),
            'year_of_study': forms.NumberInput(attrs={'class': 'form-control'}),
            'hospital': forms.Select(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'educational_qualification': forms.Select(attrs={'class': 'form-control'}),
            'educational_institution': forms.TextInput(attrs={'class': 'form-control'}),
            'speciality': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'certifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'learner_gender': forms.Select(attrs={'class': 'form-control'}),
            'skillathon_event': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add JavaScript to show/hide fields based on learner_type
        self.fields['learner_type'].widget.attrs.update({
            'onchange': 'toggleLearnerFields(this.value)'
        })

class AssessorForm(forms.ModelForm):
    UNIT_TYPE_CHOICES = [
        ('institution', 'Institution'),
        ('hospital', 'Hospital'),
    ]
    unit_type = forms.ChoiceField(choices=UNIT_TYPE_CHOICES, widget=forms.RadioSelect, required=False)
    institution = forms.ModelChoiceField(queryset=Institution.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    hospital = forms.ModelChoiceField(queryset=Hospital.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    assessor_name = forms.CharField(label='Assessor Name', max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    assessor_email = forms.EmailField(label='Assessor Email', required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    assessor_phone = forms.CharField(label='Assessor Phone', max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    class Meta:
        model = Assessor
        fields = [
            'assessor_type',
            'staff_id', 'branch', 'location',
            'qualification', 'designation', 'specialization', 'is_verifier', 'is_active'
        ]
        widgets = {
            'assessor_type': forms.Select(attrs={'class': 'form-control'}),
            'staff_id': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.Select(attrs={'class': 'form-control'}),
            'is_verifier': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assessor_type'].widget.attrs.update({
            'onchange': 'toggleAssessorFields(this.value)'
        })
        
        # Add onclick handlers to unit_type radio buttons
        self.fields['unit_type'].widget.attrs.update({
            'onclick': 'loadInstitutionsHospitals(this.value)'
        })
        
        # Set unit_type based on instance data when editing
        if self.instance and self.instance.pk:
            if self.instance.institution:
                self.fields['unit_type'].initial = 'institution'
            elif self.instance.hospital:
                self.fields['unit_type'].initial = 'hospital'

    def clean_assessor_email(self):
        email = self.cleaned_data.get('assessor_email')
        if email:
            # Check if an assessor with this email already exists
            existing_assessor = Assessor.objects.filter(assessor_user__email__iexact=email)
            if self.instance.pk:
                # Exclude current instance when editing
                existing_assessor = existing_assessor.exclude(pk=self.instance.pk)
            
            if existing_assessor.exists():
                raise forms.ValidationError('An assessor with this email already exists.')
        
        return email

    def clean_assessor_phone(self):
        phone = self.cleaned_data.get('assessor_phone')
        if phone:
            # Check if an assessor with this phone number already exists
            existing_assessor = Assessor.objects.filter(assessor_user__phone_number=phone)
            if self.instance.pk:
                # Exclude current instance when editing
                existing_assessor = existing_assessor.exclude(pk=self.instance.pk)
            
            if existing_assessor.exists():
                raise forms.ValidationError('An assessor with this phone number already exists.')
        
        return phone

class SkillathonEventForm(forms.ModelForm):
    class Meta:
        model = SkillathonEvent
        fields = ['name', 'date', 'state', 'city']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BulkLearnerUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Upload a CSV file with learner details'
    ) 