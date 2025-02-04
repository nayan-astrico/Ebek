from django import forms
import mimetypes

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
