from flask import Flask, render_template, redirect
from datetime import datetime, timedelta
import MySQLdb
import json
import pandas as pd
import time
from ConfigParser import SafeConfigParser

mysqlConfig = SafeConfigParser()
mysqlConfig.read('mysqlConfig.ini')

"""
A example for creating a Table that is sortable by its header
"""

app = Flask(__name__, static_url_path = "", static_folder="static")
# init dictionary lookup
conv_dict = pd.read_csv('bokeh_ref.csv',index_col='id').drop('internal_name',1).to_dict()
global id_to_name
id_to_name = conv_dict['name']

def Hicon_lookup(hero_id):
    global id_to_name
    icon_head = "/hero_icon/"
    hero_name = id_to_name[int(hero_id)]
    return icon_head+str(hero_name)+"_icon.png"

def indexQ():
    t0=time.time()
    request_time = datetime.now() - timedelta(days=7)
    request_time = request_time.strftime("%Y-%m-%d %H:%M:%S")
    """return_data = "["+"\n\"H\", \"/hero_icon/Abaddon_icon.png\", \"1.00794\", 1, 1,\n\"He\", \"/hero_icon/Alchemist_icon.png\", \"4.002602\", 2, 1,\n\"Li\", \"/hero_icon/Ancient_Apparition_icon.png\", \"6.941\", 3, 1\n];"
    """

    return_data = "[\n"

    mhost = mysqlConfig.get('all', 'host')
    muser = mysqlConfig.get('all', 'user')
    mpass = mysqlConfig.get('all', 'password')
    conn = MySQLdb.connect(host=mhost,user=muser,passwd=mpass,db='dota',charset='utf8',use_unicode=True)
    cur = conn.cursor()

    attempts = 0
    while attempts < 3:
        try:
            qStr = """select match_id,player0Hero,player1Hero,player2Hero,player3Hero,player4Hero,player5Hero,player6Hero,player7Hero,player8Hero,player9Hero from Nmatch_history where replay_url is not null and parser_status=3 and start_time > \"%s\" limit 100""" %request_time
            cur.execute(qStr)
            returnQ = cur.fetchall()
            conn.close()
            cur.close()
            break
        except MySQLdb.Error, e:
            attempts += 1
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])

    t1=time.time()
    #print 'db query cost: %s' %(t1-t0)
    for x in returnQ:
        match_id = x[0]
        game_state = [0]*11
        game_state[0] = int(match_id)

        for k in range(1,11):
            game_state[k] = int(x[k])

        insert_str = "\""+str(game_state[0])+"\",1,1,"
        for i in range(0,10):
            insert_str += "\""+Hicon_lookup(int(game_state[i+1]))+"\","
        insert_str += "\n"
        return_data += insert_str
        #print game_state

    return_data += "];"
    return return_data

@app.route('/')
def index():
    formated_data = indexQ()
    return render_template("index.html", table=formated_data)

@app.route('/match')
def temp_bokeh():
    return redirect('http://192.168.1.149:5006')

if __name__ == '__main__':
	#print jdata
  app.run(host='0.0.0.0', debug=True)
