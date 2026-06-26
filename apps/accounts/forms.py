"""
IntelliHub AI — Account Forms
================================
Registration, login, and profile forms with IntelliHub
glassmorphism dark-theme styling applied to all widgets.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


# ------------------------------------------------------------------
# Shared widget attributes — IntelliHub dark glassmorphism inputs
# ------------------------------------------------------------------
INTELLIHUB_INPUT_ATTRS = {
    'style': (
        'background: rgba(255,255,255,0.05);'
        'border: 1px solid var(--card-border);'
        'border-radius: 10px;'
        'padding: 14px 16px;'
        'color: white;'
        'font-family: Inter, sans-serif;'
        'font-size: 14px;'
        'width: 100%;'
        'outline: none;'
        'transition: border-color 0.3s ease, box-shadow 0.3s ease;'
    ),
}


def _styled(widget_class, attrs=None, **kwargs):
    """
    Return a widget instance with IntelliHub input styling merged
    with any additional attrs or keyword arguments.
    """
    merged = {**INTELLIHUB_INPUT_ATTRS}
    if attrs:
        merged.update(attrs)
    return widget_class(attrs=merged, **kwargs)


# ==================================================================
# Registration Form
# ==================================================================
class RegisterForm(UserCreationForm):
    """
    User registration form with all required profile fields.

    Sets the dataset_quota automatically based on the selected role
    in the view layer. All widgets use IntelliHub dark-theme styling.
    """

    username = forms.CharField(
        max_length=150,
        widget=_styled(forms.TextInput, {'placeholder': 'Choose a username'}),
        help_text='Required. 150 characters or fewer.',
    )
    email = forms.EmailField(
        max_length=254,
        widget=_styled(forms.EmailInput, {'placeholder': 'you@example.com'}),
        help_text='A valid email address.',
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=_styled(forms.TextInput, {'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=_styled(forms.TextInput, {'placeholder': 'Last name'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=_styled(forms.PasswordInput, {'placeholder': 'Create a password'}),
        help_text='At least 8 characters.',
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=_styled(forms.PasswordInput, {'placeholder': 'Repeat the password'}),
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=_styled(forms.Select),
    )
    institution = forms.CharField(
        max_length=200,
        required=False,
        widget=_styled(forms.TextInput, {'placeholder': 'University or company'}),
    )
    bio = forms.CharField(
        max_length=500,
        required=False,
        widget=_styled(forms.Textarea, {'placeholder': 'Tell us about yourself…', 'rows': '3'}),
    )
    profile_photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            **INTELLIHUB_INPUT_ATTRS,
            'accept': 'image/*',
        }),
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2', 'role', 'institution',
            'bio', 'profile_photo',
        ]

    def clean_email(self):
        """Ensure the email address is not already registered."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


# ==================================================================
# Login Form
# ==================================================================
class LoginForm(forms.Form):
    """
    Simple username + password login form.

    Not a ModelForm — authentication is handled in the view.
    """

    username = forms.CharField(
        max_length=150,
        widget=_styled(forms.TextInput, {'placeholder': 'Username', 'autofocus': 'true'}),
    )
    password = forms.CharField(
        widget=_styled(forms.PasswordInput, {'placeholder': 'Password'}),
    )


# ==================================================================
# Profile Edit Form
# ==================================================================
class ProfileForm(forms.ModelForm):
    """
    Profile editing form for authenticated users.

    Excludes sensitive fields (password, role, quota) which are
    managed through other flows.
    """

    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=_styled(forms.TextInput, {'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=_styled(forms.TextInput, {'placeholder': 'Last name'}),
    )
    email = forms.EmailField(
        max_length=254,
        widget=_styled(forms.EmailInput, {'placeholder': 'you@example.com'}),
    )
    bio = forms.CharField(
        max_length=500,
        required=False,
        widget=_styled(forms.Textarea, {'placeholder': 'Tell us about yourself…', 'rows': '3'}),
    )
    institution = forms.CharField(
        max_length=200,
        required=False,
        widget=_styled(forms.TextInput, {'placeholder': 'University or company'}),
    )
    github_url = forms.URLField(
        max_length=300,
        required=False,
        label='GitHub URL',
        widget=_styled(forms.URLInput, {'placeholder': 'https://github.com/username'}),
    )
    linkedin_url = forms.URLField(
        max_length=300,
        required=False,
        label='LinkedIn URL',
        widget=_styled(forms.URLInput, {'placeholder': 'https://linkedin.com/in/username'}),
    )
    profile_photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            **INTELLIHUB_INPUT_ATTRS,
            'accept': 'image/*',
        }),
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'bio',
            'institution', 'github_url', 'linkedin_url', 'profile_photo',
        ]

    def clean_email(self):
        """Ensure the new email is not taken by another user."""
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use by another account.')
        return email
