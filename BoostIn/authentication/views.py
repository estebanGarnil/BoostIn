from django.db import IntegrityError
from django.shortcuts import redirect, render

from .models import Users

from .form import CustomUserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import logging
from django.contrib.auth.models import User

# Create your views here.
def inscription(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()

                print(user.id)
                cuser = Users(id=user.id)
                cuser.save()

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('campagnes')
            except IntegrityError:
                form.add_error('email', 'Un compte avec cet email existe déjà.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'authentication/inscription.html', {'form': form})

def connexion(request):
    if request.method == 'POST':
        login_input = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=login_input, password=password)
        
        if user is None:  # Si l'authentification par nom d'utilisateur échoue, essayez par email
            user = User.objects.filter(email=login_input).first()
            if user:
                user = authenticate(request, username=user.username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('campagnes')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')

    return render(request, 'authentication/connexion.html')


@login_required
def acceuil(request):
    id = request.user.id


    return render(request, 'authentication/acceuil.html')    

def deconnexion(request):
    logout(request)
    return redirect('connexion')