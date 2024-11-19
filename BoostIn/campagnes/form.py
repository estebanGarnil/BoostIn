from django import forms

JOURS_SEMAINE = [
    (1, 'Lundi'),
    (2, 'Mardi'),
    (3, 'Mercredi'),
    (4, 'Jeudi'),
    (5, 'Vendredi'),
    (6, 'Samedi'),
    (7, 'Dimanche')
]

HEURE_ACTIVITE = [
    (0, "00:00"),
    (1, "01:00"),
    (2, "02:00"),
    (3, "03:00"),
    (4, "04:00"),
    (5, "05:00"),
    (6, "06:00"),
    (7, "07:00"),
    (8, "08:00"),
    (9, "09:00"),
    (10, "10:00"),
    (11, "11:00"),
    (12, "12:00"),
    (13, "13:00"),
    (14, "14:00"),
    (15, "15:00"),
    (16, "16:00"),
    (17, "17:00"),
    (18, "18:00"),
    (19, "19:00"),
    (20, "20:00"),
    (21, "21:00"),
    (22, "22:00"),
    (23, "23:00"),
]

class NouvelleCampagne(forms.Form):
    separation_0 = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'w-full border-none bg-gray-100 text-gray-500 text-center font-semibold my-4',
            'value': 'Informations de base',
            'readonly': 'readonly',
        })
    )
        
    nom_campagne = forms.CharField(label="Nom de la campagne", max_length=100, widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))
    type = forms.ChoiceField(
        choices=[
            (1, "Message 1-5-5"),
        ],
        label="Selectionez le type de campagne souhaité",
        initial=1,  
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
    )

    separation_1 = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'w-full border-none bg-gray-100 text-gray-500 text-center font-semibold my-4',
            'value': 'Connexion et paramètres associés',
            'readonly': 'readonly',
        })
    )

    token = forms.CharField(label="Token de connexion", max_length=1000, widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
)
    compte_linkedin = forms.CharField(label="Compte linkedin associé", max_length=300, widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))

    separation_2 = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'w-full border-none bg-gray-100 text-gray-500 text-center font-semibold my-4',
            'value': 'Base de prospects',
            'readonly': 'readonly',
        })
    )

    sheet = forms.CharField(label="Google sheet des prospects", max_length=1000, required=False, widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))
    col_principale = forms.CharField(label="Colonne des profils linkedin", max_length=1000, required=False, widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))
    col_nom = forms.CharField(label='Colonne des nom-prenom des prospect', max_length=1000, required=False, widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))

    separation_3 = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'w-full border-none bg-gray-100 text-gray-500 text-center font-semibold my-4',
            'value': 'Jours de fonctionnement',
            'readonly': 'readonly',
        })
    )

    jour_debut = forms.ChoiceField(choices=JOURS_SEMAINE, label="Jour de début", initial=JOURS_SEMAINE[0],         widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))
    jour_fin = forms.ChoiceField(choices=JOURS_SEMAINE, label="Jour de fin", initial=JOURS_SEMAINE[4],         widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))

    heure_debut = forms.ChoiceField(choices=HEURE_ACTIVITE, label="Heure de début", initial=HEURE_ACTIVITE[7],         widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))
    heure_fin = forms.ChoiceField(choices=HEURE_ACTIVITE[1:], label="Heure de fin", initial=HEURE_ACTIVITE[19], widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }))


    def clean(self):
        cleaned_data = super().clean()
        debut = int(cleaned_data.get('jour_debut'))
        fin = int(cleaned_data.get('jour_fin'))
        heure_debut = int(cleaned_data.get('heure_debut'))
        heure_fin = int(cleaned_data.get('heure_fin'))

        if heure_debut >= heure_fin:
            raise forms.ValidationError("L'heure de début doit etre avant l'heure de fin")

        if debut > fin:
            raise forms.ValidationError("Le jour de début doit être avant le jour de fin.")

        return cleaned_data

from django import forms

class MessageForm(forms.Form):
    corp = forms.CharField(
        max_length=900,
        widget=forms.Textarea(attrs={
            'class': 'block w-full p-3 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 mt-0',  # Styles pour Tailwind
            'placeholder': 'Écrivez votre message ici...',  # Ajout d'un placeholder
            'rows': 6,  # Nombre de lignes du textarea
        })
    )
    instruction = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'block w-full p-3 bg-gray-100 text-gray-500 border border-transparent rounded-md cursor-not-allowed',  # Styles pour un champ non éditable
            'rows': 3,
            'readonly': 'readonly',  # Rendre le champ non éditable
        })
    )

    def __init__(self, *args, **kwargs):
        instruction_text = kwargs.pop('instruction', '')
        super(MessageForm, self).__init__(*args, **kwargs)
        # Définir l'instruction spécifique à l'utilisateur
        self.fields['instruction'].initial = instruction_text


