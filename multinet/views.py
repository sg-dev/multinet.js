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
import hashlib

from flask import render_template, jsonify, Flask, request, redirect, url_for

from werkzeug import secure_filename

from multinet import app, VISUALIZATION_DIR
import multinet.render
import celery
from multinet.render import graph_layout

from flask.ext.mail import Message, Mail


"""
#celery support
try:
    from celery import Celery
    from multinet import app
    app.config.update(
        USE_CELERY=True
    )
    
    app.config['CELERY_BROKER_URL'] = "amqp://guest:guest@localhost:5672//"
    app.config['CELERY_RESULT_BACKEND'] = "amqp" # ://guest:guest@localhost:5672//"

    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    print "configured app"
except:
    
    app.config.update(
        USE_CELERY=False
    )
"""

ALLOWED_EXTENSIONS = set(['csv',])

HOST = "multinets.io/"
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
    print "token from url", token
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

    #if app.config['USE_CELERY']
    data = graph_layout(
        os.path.join(base_path, '{}.csv'.format(dataset)),
        os.path.join(base_path, '{}_node_data.csv'.format(dataset))
    )
    """
    res = graph_layout.delay(
        os.path.join(base_path, '{}.csv'.format(dataset)),
        os.path.join(base_path, '{}_node_data.csv'.format(dataset))
    )

    print "bend",res.backend
    
    print "app",res.app
    print "astuple",res.as_tuple()
    data = res.get()
    print "data",data
    #for d in res.collect(): #(timeout=None):
    #    print "d",d
    """
    if "errors" in data.keys():
        return jsonify(graph_ready=False, errors=data["errors"])
    
    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload/', methods=['POST',])
def upload_file():
    
    #check if client reached quota
    if not check_quota():
        return jsonify(graph_ready=False, errors="Quota Reached. You can upload one edgelist every 10 minutes.")
        
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
        ret = insert_file(path)
    else:
        return jsonify(graph_ready=False, errors='Invalid file uploaded. Only .csv files are supported')

    data_path = None
    if data_file and allowed_file(data_file.filename):
        data_path = os.path.join(app.config['UPLOAD_FOLDER'], '{}_{}_node_data.csv'.format(dataset, hash))
        data_file.save(data_path)

    layout_algorithm = request.form.get('layout_algorithm', 'Fruchterman-Reingold')
    data = graph_layout(path, data_path, directed_graph=request.form.get('is_directed', 'true')=='true', ly_alg=layout_algorithm)
    
    #print "dat",data
    if "errors" in data.keys():
        print "ERRORS",data["errors"]
        return jsonify(graph_ready=False, errors=data["errors"])
    
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



@app.route('/flush/')
def delete_user_data():

    try:
        token = _session['_current_token']
    except:
        token = None
        return jsonify(errors="Couldn't delete data: No token found.")
    
    try:
        args = [ 1, token ]
        ret = query_db( "update files set removed=? where token=?", args, type = "delete" )  
        _fdata = query_db('select * from files where token = ?', [token], one=False)
        
        fct = 0
        
        for _f in _fdata:
            _file = _f[1]
            print "deleting file for", token, _file
            if os.path.isfile(_file):
                
                try:
                    os.remove( _file )
                    fct += 1
                    print fct
                except OSError, e:
                    print ("Error: %s - %s." % (e.filename,e.strerror))
                """
                print 
                cmd = "rm -rf %s" % ( _file )
                ret = subprocess.call( [cmd] )
                print ret
                
                except Exception,e:
                    print "file remove error", _file
                """
        
    except Exception,e:
        print "file delete error",e
        return jsonify(errors="Couldn't delete data: %s" % ("No data for this account.",) )
    
    if fct == 0:
        print "ret0"
        return jsonify(errors="Couldn't delete data: %s" % ("No data for this account.",) )
    else:
        
        print "ret1"
        return jsonify(success=True )
    
    
    


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
from flask import g 
from flask import session as _session #_app_ctx_stack as appstack

#TODO: use canonical path here, and read it from appconfig 
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
    try:
        db.execute('''CREATE TABLE files (token text, file text, removed integer  )''')
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
                    rv = cur.fetchone()
                else:
                    rv = cur.fetchall()
                return rv if len(rv) > 0 else False 
            else:
                return True

    except Exception,e:
        print e
        return False #Todo: db error, lock
    




def check_quota():

    #token = getattr(appstack, '_current_token', None)
    try:
        token = _session['_current_token']
    except:
        token = None
    
    if token == "veimfo":
        return True
    
    print "checking quota for", token
    print _session.__dict__

    if token is None:
        return False

    udata = query_db('select * from users where token = ?', [token], one=True)
    
    #last access time is in the last item 
    _dstr = udata[-1]
    if _dstr != '':
        _last = datetime.strptime(_dstr, TIMEFORMAT )
        _now = datetime.now()
        _diff = _now - _last
        if _diff.seconds < 60 * 10:
            print token, ": last upload in less than 10 mins ago"
            return False
   
    #update last_access_date
    ret = query_db( 'update users set date_last_access=? where token=?', [datetime.now().strftime( TIMEFORMAT ), token ] , type = "update")
    return True
    

def check_token(token):
    
    #ct = getattr(appstack, '_current_token', None)
    try:
        ct = _session['_current_token']
    except:
        ct = None
    udata = query_db('select * from users where token = ?', [token], one=True)

    print "current token" , ct, udata
    if udata:
        _session['_current_token'] = token
        print _session.__dict__
        return True
    
    #appstack._current_token = None
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



def insert_file( path ):
    try:
        token = _session['_current_token']
        #maybe instead of token, use email as key
    except:
        return False
    
    args = [ token, path, 0 ]
    ret = query_db( "insert into files VALUES (?,?,?)", args, type = "insert" )  

    print "inserted file", path
    return True
