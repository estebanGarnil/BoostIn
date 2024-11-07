import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class email_sender:
    def __init__(self):
        self.__sender_email = "team@scrooge.finance"
        self.__password = "Scrooge2020!"
        self.__smtp_server = "mail.scrooge.finance"
        self.__smtp_port = 465
    
    def send_email(self, receiver, subject, corp):
        msg = MIMEMultipart()
        msg['From'] = self.__sender_email
        msg['To'] = receiver
        msg['Subject'] = subject

        # Attacher le corps du message à l'email
        msg.attach(MIMEText(corp, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP(self.__smtp_server, self.__smtp_port)
            server.starttls()  # Démarrer la connexion sécurisée
            # Encodez le mot de passe en UTF-8
            server.login(self.__sender_email, self.__password.encode('utf-8').decode('latin1'))
            
            # Envoi de l'email
            server.sendmail(self.__sender_email, receiver, msg.as_string())
            
            # Déconnexion du serveur SMTP
            server.quit()
            
            print("Email envoyé avec succès!")
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}")


