import os
import hashlib

from flask import render_template, jsonify, Flask, request, redirect, url_for

from werkzeug import secure_filename

from multinet import app, VISUALIZATION_DIR
from multinet.render import graph_layout

from flask.ext.mail import Message, Mail


ALLOWED_EXTENSIONS = set(['csv',])

HOST = "www.sg.ethz.ch/multinet/"
TIMEFORMAT = "%Y-%m-%d %H:%M:%S"

import sys, traceback
import random
import string
from datetime import datetime, timedelta
from werkzeug.routing import BaseConverter


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]
        
# Use the RegexConverter function as a converter method for mapped urls
app.url_map.converters['regex'] = RegexConverter

@app.route("/<regex('[a-zA-Z0-9]{6,6}'):token>/")
def client(token):
    print "token", token
    #TODO: first check to see if this is a valid url
    if check_token(token): 
        return render_template('main.html')
    else:
        return render_template('start.html', errors="Invalid token (%s). Please register to get a valid token" % ( token ) )

@app.route('/')
def main():
    return render_template('start.html')


@app.route('/share/<dataset>/')
@app.route('/share/<dataset>/<hash>/')
def share(dataset, hash=None):
    return render_template('main.html', fetch_url=url_for('data', dataset=dataset, hash=hash))


@app.route('/data/<dataset>/')
@app.route('/data/<dataset>/<hash>/')
def data(dataset, hash=None):
    if hash:
        base_path = app.config['UPLOAD_FOLDER']
        dataset = '{}_{}'.format(dataset, hash)
    else:
        base_path = VISUALIZATION_DIR

    data = graph_layout(
        os.path.join(base_path, '{}.csv'.format(dataset)),
        os.path.join(base_path, '{}_node_data.csv'.format(dataset))
    )

    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload/', methods=['POST',])
def upload_file():
    
    #check if client reached quota
    if not check_quota():
        return render_template('main.html', errors = "You can upload one edgelist every 10 minutes.")

        
    edge_file = request.files.get('file', None)
    data_file = request.files.get('nodefile', None)
    if edge_file and allowed_file(edge_file.filename):
        filename = secure_filename(edge_file.filename)
        hasher = hashlib.md5()
        hasher.update(edge_file.stream.read())
        hash = hasher.hexdigest()
        dataset = filename.rsplit('.', 1)[0]
        filename = '{}_{}.csv'.format(dataset, hash)
        edge_file.stream.seek(0)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        edge_file.save(path)
    else:
        return jsonify(graph_ready=False, errors='Invalid file uploaded. Only .csv files are supported')

    data_path = None
    if data_file and allowed_file(data_file.filename):
        data_path = os.path.join(app.config['UPLOAD_FOLDER'], '{}_{}_node_data.csv'.format(dataset, hash))
        data_file.save(data_path)

    layout_algorithm = request.form.get('layout_algorithm', 'Fruchterman-Reingold')
    data = graph_layout(path, data_path, directed_graph=request.form.get('is_directed', 'true')=='true', ly_alg=layout_algorithm)
    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)



def generate_id(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))



@app.route('/register/', methods=['POST',])
def register():
    owner = "semre@ethz.ch"
    sysadmin = "sg-it@ethz.ch"

    name = request.form.get('name', None)
    email = request.form.get('email', None)
    institute = request.form.get('institute', None)
    message = request.form.get('message', None)

    app =Flask(__name__)
    app.config.update(
        DEBUG=False,
        #EMAIL SETTINGS
        MAIL_SERVER='mail.ethz.ch',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME = 'sg-it@ethz.ch',
        MAIL_PASSWORD = 'cTQyBwef95@Q7'
        )
    
    mail=Mail(app)

    _subject = "[Multinet] Request Access Form: %s, %s" % ( name, email )
    
    #1.check if user exists, generate access url for user and save user to db
    _token = generate_id()
    udata = { "email" : email,"name" : name,"institute" : institute,"message" : message, "token": _token }
    
    ret = insert_user(udata)
    
    if not ret:
        return render_template('start.html',errors="This email address is already registered.")

    #2.send new user to admin
    try:
        msg = Message( subject=_subject , recipients=[ owner ], body=message, sender=sysadmin )
        mail.send(msg)
    except Exception,e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=5, file=sys.stdout)
        

    #TODO: shorten url
    access_url = "%s%s" % ( HOST, _token ) 
    #3.send access url to [email]
    print "new access url", access_url
    #msg = Message( subject , recipients=[ sysadmin ], body = message, sender=email )
    
    #TODO : w/ success message
    return render_template('start.html')





#Incomplete: use API properly
def google_url_shortener(longUrl):
    
    req = 'curl https://www.googleapis.com/urlshortener/v1/url?key=AIzaSyC7zIOF92nv2TCxUrH8IU_zIZpHvP8KTt8'
    req += " -H 'Content-Type: application/json' -d"
    req += "'{"
    req += '"longUrl": "http://www.google.com/"'
    req += "}'"

    print subprocess.check_output( [req] )
    




##################DB OPERATIONS################

import sqlite3
from flask import g # _app_ctx_stack as g
from flask import _app_ctx_stack as appstack


DATABASE = '/srv/www/htdocs/multinet.js/users.db'


def get_db():
    
    db = getattr(g, '_database', None)
    if db is None:
        print "db did not exist", g 
        db = g._database = sqlite3.connect(DATABASE) #_tmp #connect_to_database()
    try:
        db.execute('''CREATE TABLE users (email text, name text, message text,institute text, token text, date_created text, date_last_access text )''')
    except:
        pass
    print "app context db", db
    return db



@app.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.commit()
        db.close()


def query_db(query, args=(), one=False, type ="select"):

    try:
        with app.app_context():
 
            cur = get_db().execute(query, args)
            
            if type == "select":
                if one:
                    rv = cur.fetchall()
                else:
                    rv = cur.fetchone()
                return rv if len(rv) > 0 else False 
            else:
                return True

    except Exception,e:
        print e
        return False #Todo: db error, lock
    




def check_quota():

    token = getattr(appstack, '_current_token', None)
    print "checking quota for", token

    if token is None:
        return False

    udata = query_db('select * from users where token = ?', [token], one=True)
    
    #last access time is in the last item 
    _dstr = udata[0][-1]
    if _dstr != '':
        _last = datetime.strptime(_dstr, TIMEFORMAT )
        _now = datetime.now()
        _diff = _now - _last
        if _diff.seconds < 60 * 10:
            return False
   
    #update last_access_date
    ret = query_db( 'update users set date_last_access=? where token=?', [datetime.now().strftime( TIMEFORMAT ), token ] , type = "update")
    return True
    

def check_token(token):
    
    ct = getattr(appstack, '_current_token', None)
    print "current token" , ct
    
    udata = query_db('select * from users where token = ?', [token], one=True)
    
    if udata:
        appstack._current_token = token
        return True
    
    appstack._current_token = None
    return False



def insert_user( udata ):
    
    email = udata["email"]
    print "inserting user",udata
    if query_db('select * from users where email = ?', [email], one=True):
        print "user exists"
        return False
    
    udata["date_created"] = datetime.now().strftime( TIMEFORMAT )

    args = [ udata["email"], udata["name"], udata["message"], udata["institute"], udata["token"], udata["date_created"], "" ]
    ret = query_db( "insert into users VALUES (?,?,?,?,?,?,?)", args, type = "insert" )  

    print "inserted user", ret
    return True
    
