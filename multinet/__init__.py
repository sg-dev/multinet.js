# Copyright (c) 2015, ETH Zurich, Chair of Systems Design
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os

from flask import Flask


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'

VISUALIZATION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static/graph-samples'
)


import multinet.views


ADMINS = []


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

    if not app.debug:
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
        SECRET_KEY = 'testKey'
    )



#celery support
try:
    from celery import Celery
    celery = Celery(app.name, broker="amqp://guest:guest@localhost:5672//",include=["multinet.render"])
    
    celery.config.update(
        CELERY_RESULT_BACKEND="amqp",
    )
except:
    
    app.config.update(
        USE_CELERY=False
    )
    


