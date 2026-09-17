import random
import string
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import Role

User = get_user_model()

def generate_unique_8_digit_id() -> str:
    """Generates a strictly unique 8-digit random number string for the username."""
    while True:
        new_id = "".join(random.choices(string.digits, k=8))
        if not User.objects.filter(username=new_id).exists():
            return new_id

def generate_secure_password(length=12) -> str:
    """Generates a secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=length))

def create_practitioner_account(
    first_name: str,
    last_name: str,
    date_of_birth: str,
    email: str,
    role: str = Role.FIELD_AGENT,
    license_number: str = None,
    creator_user=None
) -> User:
    """
    Creates a new user account:
    - FIELD_AGENT (Praticien): username is auto-generated 8-digit unique ID.
    - PHYSICIAN (Médecin): username is medical license / RPPS number.
    Generates a secure temporary password, forces password change on first login, and sends credentials.
    """
    if role == Role.PHYSICIAN and license_number and license_number.strip():
        username = license_number.strip()
    else:
        username = generate_unique_8_digit_id()

    temp_password = generate_secure_password()
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=temp_password,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        role=role,
        force_password_change=True
    )
    
    # Send customized email according to role
    if role == Role.PHYSICIAN:
        subject = "Vos identifiants d'accès au Portail Médecin Qalb (Télé-expertise)"
        role_label = "Médecin Télé-expert"
        id_label = "N° de Licence Médicale (RPPS)"
    else:
        subject = "Vos identifiants d'accès au Portail Praticien Qalb"
        role_label = "Praticien de Terrain"
        id_label = "Identifiant Unique (8 chiffres)"

    message = (
        f"Bonjour {first_name} {last_name},\n\n"
        f"Votre compte {role_label} sur la plateforme cardiologique Qalb a été créé par l'administrateur.\n\n"
        f"Voici vos identifiants de connexion :\n"
        f"• {id_label} : {username}\n"
        f"• Mot de passe temporaire : {temp_password}\n\n"
        f"Lors de votre première connexion, il vous sera demandé de modifier ce mot de passe pour des raisons de sécurité.\n\n"
        f"Accès à la plateforme : http://localhost:5173/login\n\n"
        f"Cordialement,\nL'administration de la plateforme Qalb"
    )
    
    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@qalb.com'),
        [email],
        fail_silently=False,
    )
    
    return user
