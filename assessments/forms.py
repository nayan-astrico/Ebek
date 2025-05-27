from django import forms
import mimetypes
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import EbekUser

class ExcelUploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        file = self.cleaned_data['file']
        # Validate file extension
        if not file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError("Only Excel files are allowed.")
        # Validate MIME type
        mime_type, _ = mimetypes.guess_type(file.name)
        if mime_type not in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
            raise forms.ValidationError("The uploaded file is not a valid Excel file.")
        # Validate file size
        if file.size > 10 * 1024 * 1024:  # 10 MB limit
            raise forms.ValidationError("File size exceeds 10MB.")
        return file


class EbekUserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = EbekUser
        fields = ('email', 'user_role')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class EbekUserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on the user, but replaces the password field with admin's password hash display field."""
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = EbekUser
        fields = ('email', 'password', 'is_active', 'is_staff', 'is_superuser', 'user_role', 'groups', 'user_permissions', 'full_name', 'phone_number')

    def clean_password(self):
        return self.initial["password"]