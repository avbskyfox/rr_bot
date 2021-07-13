from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from os import path


login = 'info@terragent.ru'
password = 'Ast0n_martiN'
smtp_host = 'smtp.timeweb.ru'
smtp_port = 465

from_addr = login


def send_mail(to_addr, subject, text, files=None):
    message = MIMEMultipart()
    message['From'] = from_addr
    message['To'] = to_addr
    message['Subject'] = subject
    message['User-Agent'] = 'TIMEWEB> WEBMAIL 1.2'
    message.attach(MIMEText(f'{text}\n'))

    if files:
        for extension, data in files.items():
            app = MIMEApplication(data, _subtype=extension)
            app.add_header('Content-Disposition', 'attachment', filename=f'exerpt.{extension}')
            message.attach(app)

    with SMTP_SSL(host=smtp_host,  port=smtp_port, ) as smtp:
        smtp.login(login, password)
        smtp.send_message(message)


if __name__ == '__main__':
    send_mail('info@terragent.ru', 'nelfestrum@gmail.com', 'Тестовое сообщение', 'Привет')
