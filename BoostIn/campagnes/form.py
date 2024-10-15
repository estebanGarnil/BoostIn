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
    nom_campagne = forms.CharField(label="Nom de la campagne", max_length=100)
    type = forms.ChoiceField(
        choices=[
            (1, "Message 1-5-5"),
        ],
        label="Selectionez le type de campagne souhaité",
        initial=1,  # Option par défaut
    )
    token = forms.CharField(label="Token de connexion", max_length=1000)
    compte_linkedin = forms.CharField(label="Compte linkedin associé", max_length=300)

    sheet = forms.CharField(label="Google sheet des prospects", max_length=1000, required=False)
    col_principale = forms.CharField(label="Colonne des profils linkedin", max_length=1000, required=False)
    col_nom = forms.CharField(label='Colonne des nom-prenom des prospect', max_length=1000, required=False)

    jour_debut = forms.ChoiceField(choices=JOURS_SEMAINE, label="Jour de début", initial=JOURS_SEMAINE[0])
    jour_fin = forms.ChoiceField(choices=JOURS_SEMAINE, label="Jour de fin", initial=JOURS_SEMAINE[4])

    heure_debut = forms.ChoiceField(choices=HEURE_ACTIVITE, label="Heure de début", initial=HEURE_ACTIVITE[7])
    heure_fin = forms.ChoiceField(choices=HEURE_ACTIVITE[1:], label="Heure de fin", initial=HEURE_ACTIVITE[19])


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

class MessageForm(forms.Form):
    corp = forms.CharField(
        max_length=900, 
        widget=forms.Textarea(attrs={
            'rows': 10,  # Nombre de lignes du textarea
            'cols': 80   # Nombre de colonnes du textarea
        })
    )
    instruction = forms.CharField(
        required=False,  # Le champ n'est pas obligatoire
        widget=forms.Textarea(attrs={
            'rows': 3,
            'cols': 80,
            'style': 'border:none; background-color:transparent;'  # Style pour ressembler à un label
        })
    )

    def __init__(self, *args, **kwargs):
        instruction_text = kwargs.pop('instruction', '')
        super(MessageForm, self).__init__(*args, **kwargs)
        # Définir l'instruction spécifique à l'utilisateur
        self.fields['instruction'].initial = instruction_text
        self.fields['instruction'].widget.attrs['readonly'] = 'readonly'


