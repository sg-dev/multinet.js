import os

from flask import Flask


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'

VISUALIZATION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static/graph-samples'
)


import multinet.views

#notification mails to registered users

"""
app.config['MAIL_SERVER'] = 'mail.ethz.ch' 
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
#MAIL_USE_SSL : default False
#MAIL_DEBUG : default app.debug
app.config['MAIL_USERNAME'] = 'sg-it@ethz.ch' 
app.config['MAIL_PASSWORD'] = 'cTQyBwef95@Q7' 
#DEFAULT_MAIL_SENDER : default None


ADMINS = ['semre@ethz.ch']
"""
"""

if not app.debug:
    import logging
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler('mail.ethz.ch',
                               'sg-it@ethz.ch',
                               ADMINS, 'YourApplication Failed', 
                               credentials = ( "sg-it@ethz.ch", "cTQyBwef95@Q7" ))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
    
""" 
