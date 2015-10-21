import os

from flask import Flask


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'

VISUALIZATION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static/graph-samples'
)


import multinet.views


ADMINS = ['semre@ethz.ch']


try:
    import multinet.secrets

    app.config.update(
        DEBUG=False,
        #EMAIL SETTINGS
        MAIL_SERVER = secrets.MAIL_SERVER,
        MAIL_PORT = secrets.MAIL_PORT,
        MAIL_USE_TLS = secrets.MAIL_USE_TLS,
        MAIL_USERNAME = secrets.MAIL_USERNAME,
        MAIL_PASSWORD = secrets.MAIL_PASSWORD,
        SECRET_KEY = secrets.SECRET_KEY
    )

    if False: #not app.debug:
        import logging
        from logging.handlers import SMTPHandler
        
        mail_handler = SMTPHandler( ( secrets.MAIL_SERVER,secrets.MAIL_PORT ),
                                    secrets.MAIL_USERNAME,
                                    ADMINS, '[multinets.io error]', 
                                    credentials = ( secrets.MAIL_USERNAME, secrets.MAIL_PASSWORD ), secure=() )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

except:
    
    app.config.update(
        DEBUG=True,
        MAIL_SERVER = None,
        MAIL_PORT = None,
        MAIL_USE_TLS = False,
        MAIL_USERNAME = None,
        MAIL_PASSWORD = None,
        SECRET_KEY = 'testKey!'
    )



#celery support
try:
    from celery import Celery
 
    #app.config['CELERY_BROKER_URL'] = "amqp://guest:guest@localhost:5672//"
    #app.config['CELERY_RESULT_BACKEND'] = "amqp" # ://guest:guest@localhost:5672//"

    celery = Celery(app.name, broker="amqp://guest:guest@localhost:5672//",unclude=["multinet.render"])
    #celery.conf.update(app.config)
    
    celery.config.update(
        #USE_CELERY=True,
        CELERY_RESULT_BACKEND="amqp",
        #CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//"
    )
except:
    
    app.config.update(
        USE_CELERY=False
    )
    


