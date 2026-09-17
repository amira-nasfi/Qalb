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
        # Generate 8-digit number, ensuring it doesn't start with 0 if desired,
        # but a string of 8 random digits is fine.
        new_id = "".join(random.choices(string.digits, k=8))
        if not User.objects.filter(username=new_id).exists():
            return new_id

def generate_secure_password(length=12) -> str:
    """Generates a secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=length))

def create_practitioner_account(first_name: str, last_name: str, date_of_birth: str, email: str, creator_user=None) -> User:
    """
    Creates a new practitioner (PHYSICIAN) account.
    Generates credentials, forces password change, and sends an email.
    """
    username = generate_unique_8_digit_id()
    temp_password = generate_secure_password()
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=temp_password,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        role=Role.PHYSICIAN,
        force_password_change=True
    )
    
    # Send email
    subject = "Vos identifiants de connexion Qalb"
    message = (
        f"Bonjour Dr. {last_name},\n\n"
        f"Votre compte sur la plateforme Qalb a été créé.\n"
        f"Voici vos identifiants temporaires :\n"
        f"Identifiant : {username}\n"
        f"Mot de passe temporaire : {temp_password}\n\n"
        f"Lors de votre première connexion, il vous sera demandé de modifier ce mot de passe pour des raisons de sécurité.\n\n"
        f"Cordialement,\nL'équipe Qalb"
    )
    
    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@qalb.com'),
        [email],
        fail_silently=False,
    )
    
    return user
