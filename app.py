from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect
import MySQLdb       
import math
import time
import configparser as ConfigParser
import random
import serial

async_mode = None

app = Flask(__name__)


config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print(myhost)

ser = serial.Serial('/dev/ttyUSB0',9600)
read_ser = ser.readline()

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 


def background_thread(args):
    count = 0  
    dataCounter = 0 
    dataList = []  
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)

    while True:
        if args:
          A = dict(args).get('A')
          dbV = dict(args).get('db_value')
        else:
          A = 1
          dbV = 'nieco'  
        #print A
        print(dbV) 
        print(args)
        print(float(ser.readline()))
        socketio.sleep(2)
        count += 1
        dataCounter +=1
        prem = random.random()
        if dbV == 'start':
          dataDict = {
            "t": time.time(),
            "x": dataCounter,
            "y": float(ser.readline()),
            }
          dataList.append(dataDict)
        else:
          if len(dataList)>0:
            print('---------')
            print(str(dataList))
            fuj = str(dataList).replace("'", "\"")
            print(fuj)
            cursor = db.cursor()
            cursor.execute("SELECT MAX(id) FROM graph3")
            maxid = cursor.fetchone()
            index = maxid[0] + 1
            cursor.execute("INSERT INTO graph3 (id, hodnoty) VALUES (%s, %s)", (index, fuj))
            db.commit()
            fo = open("static/files/test.txt","a+")    
            fo.write("%s\r\n" %fuj)

            
          dataList = []
          dataCounter = 0
          socketio.emit('my_response',
                      {'data': float(ser.readline()), 'count': count},
                      namespace='/test')  
    db.close()

@app.route('/file', methods=['GET', 'POST'])
def file():
    return render_template('file.html', async_mode=socketio.async_mode)
    

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)
    
@app.route('/db')
def db():
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute('''SELECT  hodnoty FROM  graph3 WHERE id=1''')
  rv = cursor.fetchall()
  return str(rv)    

@app.route('/read/<string:num>',methods=['GET', 'POST'])
def readmyfile(num):
    fo = open("static/files/test.txt","r")
    rows = fo.readlines()
    return str(rows[int(num)-1])

@app.route('/dbdata/<string:num>', methods=['GET', 'POST'])
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)  
  cursor = db.cursor()
  print('hodnota       '+num)
  cursor.execute("SELECT hodnoty FROM  graph3 WHERE id=%s", num)
  rv = cursor.fetchone()
  print('hodnota       '+str(rv[0]))

  return str(rv[0])
    
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['A'] = message['value']    
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count']})

@socketio.on('db_event', namespace='/test')
def db_message(message):   
#    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['db_value'] = message['value']    
#    emit('my_response',
#         {'data': message['value'], 'count': session['receive_count']})

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
   # emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
