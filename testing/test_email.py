import os
from flask_mail import Mail, Message
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

with app.app_context():
    try:
        msg = Message(
            subject='Test Email',
            recipients=['test@example.com']  # Replace with a valid email
        )
        msg.body = 'This is a test email.'
        mail.send(msg)
        print("Email sent successfully")
    except Exception as e:
        print("Error:", e)