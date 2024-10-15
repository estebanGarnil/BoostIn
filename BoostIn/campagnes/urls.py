from django.urls import path
from . import views

urlpatterns = [
    path('', views.campagnes, name='campagnes'),  # Vue principale de la campagne
    path('nouveau/', views.nouvelle_campagne, name='nouvelle_campagne'),
    path('c/<int:id_campagne>', views.suivi_campagne, name='suivi_campagne'),
    path('c/message/<int:id_campagne>/<int:id_con>/<int:step_message>/<int:nombre_message>', views.redirect_message, name='redirect_message'),
    path('u/<int:id_campagne>', views.nouvelle_campagne, name='update'),
    path('u/message/<int:id_message>', views.nouvelle_campagne, name='maj_message'),
    path('u/message/<int:id_message>/<int:step_message>/<int:nombre_message>', views.update_message, name='update_message'),
    path('d/campagne/<int:id_con>', views.delete_campagne, name='delete_campagne'),
    path('d/prospect/<int:id_prospect>', views.delete_prospect, name='delete_prospect'),
    path('a/start', views.lancement_campagne, name='lancement_campagne'),
    path('a/stop', views.arret_campagne, name='arret_campagne'),
    path('a/etat', views.etat_campagne, name='etat_campagne'),
    path('a/message/<int:id_campagne>', views.message_campagne, name='message'),
    path('loading/', views.test_lancement, name='loading'),
    path('stat', views.get_stat_by_day, name='stat_by_day'),

    path('nouvelle_campagne/', views.nouvelle_campagne, name='nouvelle_campagne'),
    path('nouvelle_campagne/<int:step>/', views.nouvelle_campagne, name='nouvelle_campagne_step'),
    path('nouvelle_campagne/<int:step>/<int:id_campagne>', views.nouvelle_campagne, name='nouvelle_campagne_step_id'),
    path('nouvelle_campagne/<int:step>/<int:id_campagne>/edit/', views.nouvelle_campagne, {'edit': True}, name='maj_campagne_edit'),
    path('nouvelle_campagne/<int:step>/<int:id_campagne>/edit/<int:id_message>/', views.nouvelle_campagne, {'edit': True}, name='maj_message_edit'),

]
