import os

from flask import Flask


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'

VISUALIZATION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static/graph-samples'
)


import multinet.views

try:
    import multinet.secrets
    """
    app.config['MAIL_SERVER'] = secrets.MAIL_SERVER
    app.config['MAIL_PORT'] = secrets.MAIL_PORT
    app.config['MAIL_USE_TLS'] = secrets.MAIL_USE_TLS
    app.config['MAIL_USERNAME'] = secrets.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = secrets.MAIL_PASSWORD
    """
    app.config.update(
        DEBUG=False,
        #EMAIL SETTINGS
        MAIL_SERVER = secrets.MAIL_SERVER,
        MAIL_PORT = secrets.MAIL_PORT,
        MAIL_USE_TLS = secrets.MAIL_USE_TLS,
        MAIL_USERNAME = secrets.MAIL_USERNAME,
        MAIL_PASSWORD = secrets.MAIL_PASSWORD
    )

except:
    app.config['MAIL_SERVER'] = None
    app.config['MAIL_PORT'] = None
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USERNAME'] = None
    app.config['MAIL_PASSWORD'] = None







