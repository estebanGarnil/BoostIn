import datetime
import json
import time as tm
from django.http import HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render

from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .form import NouvelleCampagne, MessageForm

from .models import Con, Users, Campagne, Fonctionement, Message, Manager, Prospects, Statutes, NomChamp, ValeurChamp, Erreur, TachesProgrammes, codeerreur, ActionErreur, ListAction

from .services.LD import LDManager

from .services.Donnees import Etat
from django.core.exceptions import ObjectDoesNotExist

from .utilitaire import fetch_google_sheet_data, clean_lien, InsertionForm

from .utils import automatisation

from datetime import datetime

from django.db import connection

from django_redis import get_redis_connection

from .pubsub import subscribe_to_channel, publish_message, subscribe_to_channel_continu

import logging

logger = logging.getLogger(__name__)

def send_message_and_wait_response(request):
    # Publier le message
    publish_message('request_channel', json.dumps({"action": "NONE"}))

    # Attendre la réponse sur le canal de réponse
    response = subscribe_to_channel('response_channel')

    # Retourner la réponse dès réception
    return JsonResponse({'response': response.decode('utf-8')})

@login_required
def redirect_message(request, id_campagne, id_con, step_message, nombre_message):
    request.session['form_step'] = step_message
    request.session['con_id'] = id_con
    request.session['campagne_id'] = id_campagne
    request.session['nombre_message'] = nombre_message
    return redirect('nouvelle_campagne')

@login_required
def update_message(request, id_message, step_message, nombre_message):
    request.session['form_step'] = step_message
    request.session['nombre_message'] = nombre_message
    return redirect('maj_message', id_message=id_message)
    
@login_required
def delete_campagne(request, id_con):

    etat_response = etat_campagne(request)
    etat_data = etat_response.content.decode('utf-8')
    etat_data = json.loads(etat_data)
    
    if etat_data.get('status') == 'started':
        arret_campagne(request)
    
    con = Con.objects.get(id=id_con)

    message = Message.objects.filter(idcon=con)
    for m in message:
        m.delete()

    nchamp = NomChamp.objects.filter(idcon=con)
    vchamp = ValeurChamp.objects.filter(id_champ__in=nchamp)

    for v in vchamp:
        v.delete()
    
    for n in nchamp:
        n.delete()

    prospect = Prospects.objects.filter(idcon=con)
    for p in prospect:
        s = p.statutes
        p.delete()
        s.delete()

    con.delete()

    return redirect('campagnes')

@login_required
def delete_prospect(request, id_prospect):
    p = Prospects.objects.get(id=id_prospect)

    v = ValeurChamp.objects.filter(id_prospect=p)

    for val in v:
        val.delete()

    s = p.statutes
    p.delete()
    s.delete()

    next_url = request.GET.get('next', request.META.get('HTTP_REFERER', '/'))
    
    return redirect(next_url)

@login_required
def campagnes(request):
    request.session['page'] = 'campagnes'
    con = Con.objects.filter(iduser=request.user.id)

    t = []

    for c in con:
        with connection.cursor() as cursor:
            cursor.callproc('VerifierErreur', [c.id])

        error = ""
        err = Erreur.objects.filter(idcon=c)
        for e in err:
            error += e.code_err.description_code
            
        t.append({"titre_campagne" : c.name, "type_campagne" : c.idcampagne.name, "id_campagne" : c.id, "error" : error})
    
    step = request.session.get('form_step', 0)
    if step != 0:
        del request.session['form_step']

    return render(request, 'campagnes/campagnes.html', {"campagneitem" : t})

@login_required
def suivi_campagne(request, id_campagne):
    """
    Page de suivi des prospect, graphiques, lancement, tab des prospect
    """
    request.session['page'] = 'campagne/'+str(id_campagne) 
    request.session['form_step'] = 0

    #

    con = Con.objects.get(id=id_campagne)
    campagne = con.idcampagne

    f = Fonctionement.objects.filter(idcampagne=campagne)

    nb_message = len(f)

    message_reel = 0
    i = 1
    for f_item in f:
        try: 
            message_reel += 1
        except ObjectDoesNotExist:
            pass
        i+=1
    #if message_reel == nb_message and 1 in [e.code_err.id for e in Erreur.objects.filter(idcon=con, etat=0)]:
        #e = Erreur.objects.get(idcon=con, code_err=codeerreur.objects.get(id=1))
        #e.delete()
    #else:
    #    e = Erreur()
    #    e.save()

    # err = [e.code_err.description_code for e in Erreur.objects.filter(idcon=con, etat=0)]

    # if 2 in [e.code_err.id for e in Erreur.objects.filter(idcon=con, etat=0)]:
    #     if automatisation.etat_db(con.id):
    #         automatisation.stop(con.id)

    err = [[e.code_err.id, e.code_err.description_code, []] for e in Erreur.objects.filter(idcon=con, etat=0)]

    for e in err:
        e[2] = [a.idaction.action for a in ListAction.objects.filter(idcode=e[0])]
        
    logger.info(f'erreur : {err}')
    

    prospect_item = Prospects.objects.filter(idcon=con).values(
    'name', 'linkedin_profile', 'statutes__statutes', 'id')
    prospect = list(prospect_item)

    nb_acc = get_stat_connexion(con)
    nb_mes = get_stat_message(con)

    # etat_campagne = automatisation.etat(id_campagne)

    date_creation = con.date_creation

    #pro_exe = automatisation.prochaine_execution('C'+str(id_campagne))

    ## automatisation.prochaine_execution('C'+str(id_campagne))
    message = {
        'action': 'PROCHAINE_EXECUTION',
        'object_id': 'C'+str(id_campagne)
    }
    publish_message('request_channel', json.dumps(message))

    # Attendre la réponse sur le canal de réponse
    pro_exe = subscribe_to_channel('response_channel')
    exe_dict = json.loads(pro_exe)
    logger.info(f"pro_exe : {exe_dict}")
    if exe_dict["message"] != "None":
        pro_exe = datetime.fromisoformat(exe_dict["message"])
    else:
        pro_exe = "None"


    return render(request, 'campagnes/suivi.html', {'con' : con, 'campagne' : campagne, 'prospect' : prospect, 'stat_con' : nb_acc, 'stat_mes' : nb_mes, "error" : err, "pro" : pro_exe, 'date_creation' : date_creation})

@login_required
def delete_error(request, id_error, id_campagne):
    con = Con.objects.get(id=id_campagne)
    err = [e.code_err.id for e in Erreur.objects.filter(idcon=con, etat=0)]
    if id_error in err:
        codeerr = codeerreur.objects.get(id=id_error)
        supr = Erreur.objects.filter(idcon=con, code_err=codeerr)
        supr.delete()

    return redirect('suivi_campagne', con.id)

@login_required
def message_campagne(request, id_campagne):
    """
    Page de parametrage des messages
    """
    request.session['page'] = 'campagne/'+str(id_campagne) 
    request.session['form_step'] = 0
    con = Con.objects.get(id=id_campagne)

    campagne = con.idcampagne

    f = Fonctionement.objects.filter(idcampagne=campagne)

    nb_message = len(f)

    message_item = []
    i = 1
    for f_item in f:
        try: 
            message_item.append([Message.objects.get(idcon=con, idfonc=f_item), i, nb_message])
        except ObjectDoesNotExist:
            message_item.append([None, i, {"id_campagne" : campagne.id, "id_con" : con.id, "step_message" : i, "nombre_message" : nb_message}])
        i+=1
    return render(request, 'campagnes/message.html', {"message_item":message_item, 'con' : con})

@login_required
def nouvelle_campagne(request, step=0, id_campagne=None, edit=False, id_message=None):

    if request.method == 'POST':
        referer = request.session['referer']

        if step == 0:
            form = NouvelleCampagne(request.POST)
            if form.is_valid():
                f = InsertionForm(form, id_campagne, id_message, edit)

                id_campagne = f.insert_con(request)
                f.insert_prospect()

        elif step > 0:
            form = MessageForm(request.POST)
            if form.is_valid():
                f = InsertionForm(form, id_campagne, id_message, edit)
                continuer = f.insert_message(request, step)

            ## Si arrivé au dernier message
            if continuer and edit is False:           
                return redirect(reverse('campagnes'))
        
        if edit:
            return HttpResponseRedirect(referer)
        else:
            return redirect('nouvelle_campagne_step_id', step=step+1, id_campagne=id_campagne)

    ## GET
    else:
        request.session['referer'] = request.META.get('HTTP_REFERER', None)

        if id_message is not None:
            message_instance = Message.objects.get(id=id_message)
        if id_campagne is not None:
            con_instance = Con.objects.get(id=id_campagne)

        nombre_message = Fonctionement.objects.filter(idcampagne=id_campagne).count()

        if step == 0:
            if edit:
                titre = "Modifiez votre campagne : "+con_instance.name
                initial_data = {'nom_campagne': con_instance.name, 'token': str(con_instance.token)[2:-1], 'compte_linkedin' : con_instance.linkedin_lien,'jour_debut' : int(str(con_instance.jouractivite)[0]), 'jour_fin' : int(str(con_instance.jouractivite[2])), 'heure_debut' : int(str(con_instance.heureactivite[:2])), 'heure_fin' : int(str(con_instance.heureactivite[3:]))}
                form = NouvelleCampagne(initial=initial_data)
                validation = "valider les modification"
            else:
                titre = "Creez une nouvelle campagne"
                form = NouvelleCampagne()
                validation = "etape suivante"
        elif step > 0:

            nchamp = NomChamp.objects.filter(idcon=con_instance).values('nom')

            output = f"""Les variables disponibles sont : {' '.join([f"#{i['nom']}#" if i == nchamp[len(nchamp)-1] else f"#{i['nom']}# |" for i in nchamp])}\nUtilisez # avant et après pour déclarer une variable dans votre message."""
            
            if edit and id_message is not None:
                titre = "Modifiez le message n°"+str(step)
                initial_data = {'corp' : message_instance.corp}
                form = MessageForm(initial=initial_data, instruction=output)
            else:
                titre = "Ajouter le message n°"+str(step)
                form = MessageForm(instruction=output)
                validation = "etape suivante"
                    
            if step == nombre_message:
                validation = "Valider le formulaire"
            if edit:
                validation = "valider les modification"

        else:
            form = NouvelleCampagne()  # Défaut
        
        if edit and id_message is None and step==0:
            return render(request, 'campagnes/setting_campagne.html', {'form': form, 'step': step, 'titre' : titre, 'validation' : validation, 'con' : con_instance})

        return render(request, 'campagnes/nouvelle_campagne.html', {'form': form, 'step': step, 'titre' : titre, 'validation' : validation})

@login_required
def etat_campagne(request):
    """
    renvoie l'etat de la campagne actuel
    """
    p = request.session['page']
    id_con = p[p.index('/')+1:]

    con = Con.objects.get(id=id_con)

    m = Manager.objects.filter(idcon=con)

    # if 1 in [e.code_err.id for e in Erreur.objects.filter(idcon=con, etat=0)]:
    #     return JsonResponse({'status' : 'error'})

    if m.count() > 0:
        return JsonResponse({'status' : 'started'})
    
    return JsonResponse({'status' : 'stopped'})

## Js
@login_required
def lancement_campagne(request):
    if request.method == 'POST':
        try:
            p = request.session['page']
            id_con = p[p.index('/')+1:]

            ## LDManager.add(id_con)
            message = {
                'action': 'ADD',
                'object_id': id_con
            }
            publish_message('request_channel', json.dumps(message))
            ## LDManager.start(id_con)
            message = {
                'action': 'START',
                'object_id': id_con
            }
            
            publish_message('request_channel', json.dumps(message))
            return JsonResponse({'status': 'success'})
        except KeyError:
            return JsonResponse({'status': 'error', 'message': 'Session key missing'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def vue_sse(request):
    return render(request, 'campagnes/test.html')

def sse_view(request):
    def event_stream():
        try:
            # Envoie la demande pour démarrer le suivi
            message = {
                'action': 'SUIVI',
                'object_id': 'None'
            }

            publish_message('request_channel', json.dumps(message))
            response = subscribe_to_channel('response_channel')
            
            decoded_str = response.decode('utf-8')

            try:
                response_dict = json.loads(decoded_str)
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de décodage JSON : {e}")
                response_dict = {}

            suivi_channel = response_dict.get("suivi_channel")

            logger.info(f'canal de suivi reçu : {suivi_channel}')

            # Si aucun canal de suivi n'est reçu, on arrête ici
            if not suivi_channel:
                logger.error("Impossible d'obtenir un canal de suivi.")
                yield "data: Erreur lors de l'obtention du canal de suivi\n\n"
                return

            logger.info(f"Écoute des messages sur le canal : {suivi_channel}")
            suivi_generator = subscribe_to_channel_continu(suivi_channel)

            for message in suivi_generator:
                logger.info("Message reçu du canal de suivi")
                decoded_message = message.decode('utf-8')
                yield f"data: {decoded_message}\n\n"
                logger.info("Message envoyé au client SSE")

        except GeneratorExit:
            logger.info("Client déconnecté")
            return
        except Exception as e:
            logger.error(f"Erreur dans le flux SSE : {e}")
            yield f"data: Erreur : {str(e)}\n\n"

    # Configure la réponse HTTP pour le SSE
    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response['Cache-Control'] = 'no-cache'
    response['Transfer-Encoding'] = 'chunked'
    return response


@login_required
def test_lancement(request):
    try:
        if request.method == 'POST':
            p = request.session.get('page', '')
            if '/' in p:
                id_con = p.split('/')[-1]
            else:
                logger.error("Caractère '/' non trouvé dans p")
                id_con = None

            message = {
                'action': 'ETAT_LANCEMENT',
                'object_id': id_con
            }
            publish_message('request_channel', json.dumps(message))
            response = subscribe_to_channel('response_channel')
            
            decoded_str = response.decode('utf-8')

            try:
                response_dict = json.loads(decoded_str)
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de décodage JSON : {e}")
                response_dict = {}

            f = response_dict.get("message")

            # Handle the response based on 'f'
            if f == "True":
                message = {
                    'action': 'ADD_MANAGER',
                    'object_id': id_con
                }
                publish_message('request_channel', json.dumps(message))
                # Additional logic...
                logger.info('test_lancement -> success')
                return JsonResponse({'status': 'success'})
            elif f == "False":
                logger.info('test_lancement -> false')
                return JsonResponse({'status': 'unsuccess'})
            else:
                logger.info('test_lancement -> on hold')
                return JsonResponse({'status': 'on_hold'})
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    except Exception as e:
        logger.error(f"test_lancement -> erreur : {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def arret_campagne(request):
    p = request.session['page']
    id_con = p[p.index('/')+1:]

    #automatisation.stop(id_con)

    ## automatisation.stop(id_con)
    message = {
        'action': 'STOP',
        'object_id': id_con
    }
    publish_message('request_channel', json.dumps(message))
    return JsonResponse({'status': 'success'})

# ------------------------------
def get_stat_connexion(con):
    all_prospect = Prospects.objects.filter(idcon=con)

    stat = {"ACC" : 0, "REF" : 0, "ATT" : 0, "NENV" : 0, "SUC" : 0}
    
    for p in all_prospect:
        if p.statutes.statutes.upper() in ["ACCEPTED", "1ST", "2ND", "3RD"]:
            stat["ACC"] += 1
        elif p.statutes.statutes.upper() == "ON HOLD":
            stat["ATT"] += 1
        elif p.statutes.statutes.upper() == "NOT SENT":
            stat["NENV"] += 1
        elif p.statutes.statutes.upper() == "SUCCESS":
            stat["SUC"] += 1
        else :
            stat["REF"] += 1
    return stat

def get_stat_message(con):
    all_prospect = Prospects.objects.filter(idcon=con)

    stat = {"M1ST" : 0, "M2ND" : 0, "M3RD" : 0, "NENV" : 0}
    

    for p in all_prospect:
        if p.statutes.statutes.upper() == "1ST":
            stat["M1ST"] += 1
        elif p.statutes.statutes.upper() == "2ND":
            stat["M2ND"] += 1
        elif p.statutes.statutes.upper() == "3RD":
            stat["M3RD"] += 1
        else:
            stat["NENV"] += 1

    return stat

from django.db.models import Count
from collections import defaultdict

@login_required
def get_stat_by_day(request):
    if request.method == 'POST':

        con = request.session['page']
        con_id = con[con.index('/')+1:]

        con = Con.objects.get(id=con_id)

        body_unicode = request.body.decode('utf-8')
        body_data = json.loads(body_unicode)

        date_ref = body_data.get('date')

        all_prospect = Prospects.objects.filter(idcon=con).values_list('id', flat=True)

        result = defaultdict(list)

        s = Statutes.objects.filter(id_prospect__in=all_prospect)

        for statut in s:
            result[statut.id_prospect].append(statut)
        result = dict(result)

        all_statut_by_day = []
        for stat in result.values():
            if len(stat) > 1:
                date_possible = []
                for s in stat:
                    if s.changedate <= date_ref:
                        date_possible.append(s)
                if date_possible:
                    date_max = max([i.changedate for i in date_possible])
                    all_statut_by_day.append([s.id for s in date_possible if s.changedate == date_max][0])
            else:
                all_statut_by_day.append(stat[0])
                        

        stat = [0,0,0,0,0]
        stat_mes = [0,0,0,0]

        

        for s in all_statut_by_day:
            if s.statutes.upper() in ["ACCEPTED", "1ST", "2ND", "3RD"]:
                stat[0] += 1
            elif s.statutes.upper() == "ON HOLD":
                stat[1] += 1
            elif s.statutes.upper() == "NOT SENT":
                stat[2] += 1
            elif s.statutes.upper() == "SUCCESS":
                stat[3] += 1
            else :
                stat[4] += 1

            if s.statutes.upper() == "1ST":
                stat_mes[0] += 1
            elif s.statutes.upper() == "2ND":
                stat_mes[1] += 1
            elif s.statutes.upper() == "3RD":
                stat_mes[2] += 1
            else:
                stat_mes[3] += 1
        
        return JsonResponse({'stat_mes' : stat_mes, 'stat_con' : stat})



