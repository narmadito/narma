from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_email_async(subject, message, recipient_email):
    send_mail(subject, message, 'no-reply@example.com', [recipient_email])