import requests
from celery import shared_task


@shared_task
def send_sms_otp(to):
    data = {
        "to": to,
    }
    response = requests.post(
        "https://console.melipayamak.com/api/send/otp/6a00ec9f1f7d4c2b911c24cc904f48e1",
        json=data,
    )
    return {"response": response.json(), "status_code": response.status_code}
