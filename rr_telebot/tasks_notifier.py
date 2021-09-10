from celery import shared_task

from rr_telebot.progress_notifier import ProgressNotifier


@shared_task
def send_progress_message(chat_id, text):
    pn = ProgressNotifier(chat_id)
    pn.send_message(text)


@shared_task
def delete_last_progress_message(chat_id):
    pn = ProgressNotifier(chat_id)
    pn.delete_last_message()
