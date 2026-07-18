from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["author_name", "author_email", "content"]
        widgets = {
            "author_name": forms.TextInput(attrs={"placeholder": "Имя", "class": "form-control"}),
            "author_email": forms.EmailInput(attrs={"placeholder": "Email", "class": "form-control"}),
            "content": forms.Textarea(attrs={"placeholder": "Комментарий", "class": "form-control", "rows": 4}),
        }
