from datetime import timedelta, timezone
import re
from django.shortcuts import get_object_or_404

from ..models import Con, Prospects, Statutes, Message, Manager, TachesProgrammes, NomChamp, ValeurChamp
from django.contrib.auth.models import User

class bdd():
    def __init__(self):
        self.connBD = None
        self.curs = None
        self.config = {}


class LDDB(bdd):
    def __init__(self):
        super().__init__()

    def __call__(self, requete, *args):
        return super().__call__(requete, *args)

    ## LDC
    def getProspect(self, IDuser):
        """
        Recupere l'id, le nom et le li d'un prospect
        """
        p = Prospects.objects.filter(idcon__id=IDuser, statutes__statutes='not sent').values('id', 'name', 'linkedin_profile')
        return p
        # return self("""SELECT Prospects.ID, Name, LinkedIn_Profile FROM Prospects, Statutes, Users WHERE Users.ID = Prospects.ID_ AND Prospects.Statutes = Statutes.ID AND Statutes.Statutes = 'not sent' AND Users.ID = %s""", IDuser)
            
    def jourActivite(self, ID):
        """
        """
        c = Con.objects.get(id=ID)
        return c.jouractivite

        # return self("""SELECT JourActivite FROM con WHERE IDUser=%s""", IDuser)
    
    def heureActivite(self, ID):
        c = Con.objects.get(id=ID)
        return c.heureactivite
        # return self("""SELECT HeureActivite FROM con WHERE IDUser=%s""", IDuser)

    ## LDUser
    def getToken(self, ID):
        c = Con.objects.get(id=ID)
        return str(c.token)[2:-1]
        return self("""SELECT CONVERT(AES_DECRYPT(token, 'ABCDEFG') USING utf8) FROM con WHERE id = %s""", IDUser)
    
    def getEmail(self, ID):
        c = Con.objects.get(id=ID)

        u = c.iduser.id

        a = User.objects.get(id=u)
        return a.email
        # return self("SELECT email FROM Users WHERE ID = %s", IDUser)

    ## LDObserver 
    def getProspectObserver(self, IDUser):
        return Prospects.objects.filter(idcon_id=IDUser).exclude(statutes__statutes='Accepted').values('linkedin_profile', 'id')

        # return self("""SELECT LinkedIn_Profile, Statutes.ID FROM Prospects JOIN Statutes ON Prospects.statutes = Statutes.ID WHERE IDUser = %s AND statutes.statutes <> 'Accepted'""", IDUser)

    ## LDM
    def getMessage(self, IDUser):
        return Message.objects.filter(idcon__iduser_id=IDUser).values('id', 'corp', 'idfonc__tempsprochaineexec', 'idfonc__statutes_activation', 'idfonc__type')

        return self("SELECT M.ID, M.Corp, F.TempsProchaineExec, F.Statutes_Activation, F.TYPE FROM Message M, Fonctionement F WHERE M.IDFonc = F.ID AND M.IDCon = %s", IDUser)
    
    def getProspectDay(self, IDUser, statutes, time):
        return Prospects.objects.filter(
            idcon__iduser_id=IDUser,
            statutes__statutes=statutes,
            statutes__changedate__lte=timezone.now() - timedelta(days=time)
        ).values('id', 'name', 'linkedin_profile')

        return self("""SELECT P.ID, P.Name, P.LinkedIn_Profile FROM Prospects P, Statutes S 
        WHERE P.Statutes = S.ID 
        AND changeDate <= CURDATE() - INTERVAL %s DAY
        AND S.statutes = %s
        AND P.IDUser = %s""", time, statutes, IDUser)

    def update_prospect_statute(self, IDProspect, etat):
        """
        Met a jour l'etat d'un prospect
        """
        prospect = Prospects.objects.get(id=IDProspect)
        statute = prospect.statutes
        statute.statutes = etat
        statute.save()
    
    def get_lien_compte(self, IDCon):
        con = Con.objects.get(id=IDCon)
        return con.linkedin_lien
    
    def add_manager(self, IDCon):
        con = Con.objects.get(id=IDCon)

        if Manager.objects.filter(idcon=con).exists() == False:
            m = Manager(idcon=con)
            m.save()
    
    def del_manager(self, IDCon):
        con = Con.objects.get(id=IDCon)

        m = Manager.objects.get(idcon=con)
        m.delete()

        taches = TachesProgrammes.objects.filter(idcon=con)
        for tp in taches:
            tp.delete()

    def get_ldcon_manager(self):
        manager = Manager.objects.all()

        return manager
    
    def get_var_message(self, IDCon, id_prospect, corp):
        var = re.findall(r'#(.*?)#', corp)

        for v in var:
            variable = NomChamp.objects.get(idcon=IDCon, nom=v)
            p = Prospects.objects.get(id=id_prospect)

            val = ValeurChamp.objects.get(id_prospect=p, id_champ=variable)

            corp.replace(f'#{v}#', val.valeur)
        
        return corp
    
    def supr_manager(self, idm):
        m = Manager(idcon=idm)
        m.delete()

    def etat_db(self, idm):
        try:
            Manager.objects.get(idcon=idm)
            return True 
        except:
            return False

            






        