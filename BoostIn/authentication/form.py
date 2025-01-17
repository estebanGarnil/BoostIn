from django import forms
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
            label="Email",
            required=True,
            help_text="Entrez une adresse email valide."
        )

    password1 = forms.CharField(
        label="Password", 
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete' : 'new-password'}),
    )
    password2= forms.CharField(
        label="Password confirmation", 
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete' : 'new-password'}),
    )

    cledeconnexion= forms.CharField(
        label="Clé de connexion",
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = UserCreationForm.Meta.model
        fields = UserCreationForm.Meta.fields + ("email", "password1", "password2")
