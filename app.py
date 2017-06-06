from flask import Flask, render_template, redirect, request
from datetime import datetime, timedelta
import MySQLdb
import json
import pandas as pd
import time
from ConfigParser import SafeConfigParser
import dota2api

#date conversion function
def dateConv(unixInput): return datetime.fromtimestamp(int(unixInput)).strftime('%Y-%m-%d %H:%M:%S')

mysqlConfig = SafeConfigParser()
mysqlConfig.read('/home/flask/mysqlConfig.ini')
#mysqlConfig.read('mysqlConfig.ini')
conv_dict = pd.read_csv('/home/flask/bokeh_ref.csv',index_col='id').drop('internal_name',1).to_dict()
#conv_dict = pd.read_csv('bokeh_ref.csv',index_col='id').drop('internal_name',1).to_dict()

"""
A example for creating a Table that is sortable by its header
"""

app = Flask(__name__, static_url_path = "", static_folder="static")
global id_to_name
id_to_name = conv_dict['name']

def Hicon_lookup(hero_id):
    global id_to_name
    icon_head = "/hero_icon/"
    hero_name = id_to_name[int(hero_id)]
    return icon_head+str(hero_name)+"_icon.png"

def newEntryCheck(match_id, cur, conn):
    apikey = mysqlConfig.get('all', 'apikey')
    api = dota2api.Initialise(apikey)

    match_resp = api.get_match_details(match_id=match_id)
    lbt = int(match_resp['lobby_type'])
    gm = int(match_resp['game_mode'])
    dr = int(match_resp['duration'])
    if lbt == 7 and gm == 22 and dr >= 60*25:
        player_node = match_resp['players']
        if match_resp['radiant_win'] == True:
            rad_win = 1
        else:
            rad_win = 0
        try:
            cur.execute("""insert into Nmatch_history(match_id,game_mode,lobby_type,start_time) values(\'%s\',\'%s\',\'%s\',\'%s\')""" %(match_id,gm,lbt,dateConv(match_resp['start_time'])))
            conn.commit()
            cur.execute("""update Nmatch_history set rad_win=%s, parser_status=7, player0Hero=%s, player1Hero=%s, player2Hero=%s, player3Hero=%s, player4Hero=%s, player5Hero=%s, player6Hero=%s, player7Hero=%s, player8Hero=%s, player9Hero=%s where match_id=%s""" %(rad_win, player_node[0]['hero_id'],player_node[1]['hero_id'],player_node[2]['hero_id'],player_node[3]['hero_id'],player_node[4]['hero_id'],player_node[5]['hero_id'],player_node[6]['hero_id'],player_node[7]['hero_id'],player_node[8]['hero_id'],player_node[9]['hero_id'],match_id))
            conn.commit()
            return 'inserted, please check later'
        except MySQLdb.IntegrityError:
            return 'duplicate matchID %s' %'match_id'
        except Exception, e:
            return 'fatal error: %s' %e
            exit()
    else:
        return 'match is not ranked as well as all pick match or is too short'

def indexQ():
    t0=time.time()
    request_time = datetime.now() - timedelta(days=7)
    request_time = request_time.strftime("%Y-%m-%d %H:%M:%S")

    return_data = "[\n"

    mhost = mysqlConfig.get('all', 'host')
    muser = mysqlConfig.get('all', 'user')
    mpass = mysqlConfig.get('all', 'password')
    conn = MySQLdb.connect(host=mhost,user=muser,passwd=mpass,db='dota',charset='utf8',use_unicode=True)
    cur = conn.cursor()

    attempts = 0
    while attempts < 3:
        try:
            #qStr = """select match_id,player0Hero,player1Hero,player2Hero,player3Hero,player4Hero,player5Hero,player6Hero,player7Hero,player8Hero,player9Hero from Nmatch_history where replay_url is not null and (parser_status=3 or parser_status=6) and start_time > \"%s\" limit 100""" %request_time
            qStr = """select match_id,player0Hero,player1Hero,player2Hero,player3Hero,player4Hero,player5Hero,player6Hero,player7Hero,player8Hero,player9Hero from Nmatch_history where replay_url is not null and (parser_status=3 or parser_status=6) limit 100""" # temp fix for missing recent data
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

def replayC(match_id, reState):
    # init db connection
    mhost = mysqlConfig.get('all', 'host')
    muser = mysqlConfig.get('all', 'userRW')
    mpass = mysqlConfig.get('all', 'passwordRW')
    conn = MySQLdb.connect(host=mhost,user=muser,passwd=mpass,db='dota',charset='utf8',use_unicode=True)
    cur = conn.cursor()

    cur.execute("""select count(*) from Nmatch_history where match_id = %s""" %match_id)
    conn.commit()
    countR = cur.fetchone()
    if countR[0] > 0:
        # already exists
        cur.execute("""select match_id, parser_status from Nmatch_history where match_id=%s""" %match_id)
        conn.commit()
        passC = cur.fetchone()
        # parser_status code:
        # 0: unparsed, 1: too short, 2: opendota not parsed, 3: opendota parsed
        # 4: too short, 5: download fail, 6: parsed and stored 7: user-req parse
        if passC[1] == 6:
            #return 'match exists, please go to http://dota.luokerenz.com/replay?match_id=matchid for now'
            return 'redirect', ''
        elif passC[1] == 7:
            return 'match exists and still under processing, please check later', "disabled"
        elif passC[1] == 5:
            return 'replay file is expired', "disabled"
        elif passC[1] == 4:
            return 'match too short', "disabled"
        elif passC[1] == 3:
            cur.execute("""update Nmatch_history set parser_status=7 where match_id=%s""" %match_id)
            conn.commit()
            return 'parser state update to user-req, please check later', "disabled"
        elif passC[1] == 2:
            if reState:
                if int(reState) == 1:
                    cur.execute("""update Nmatch_history set parser_status=7 where match_id=%s""" %match_id)
                    conn.commit()
                    return 'parse request resubmited, please check later', "disabled"
            else:
                return 'please wait for opendota to parse the replay', ''
        elif passC[1] == 1:
            return 'match too short', "disabled"
        elif passC[1] == 0:
            cur.execute("""update Nmatch_history set parser_status=7 where match_id=%s""" %match_id)
            conn.commit()
            return 'parser state update to user-req, please check later', "disabled"
    else:
        # insert new matchid
        state = newEntryCheck(match_id, cur, conn)
        return state, "disabled"

@app.route('/')
def index():
    formated_data = indexQ()
    return render_template("index.html", table=formated_data)

@app.route('/replayc')
def replayc():
    match_id = request.args.get('match_id')
    reState = request.args.get('re')
    if not match_id:
        state = 'Please enter the correct match id in the search bar'
        buttonState = "disabled"
    else:
        state, buttonState = replayC(match_id, reState)
    #return state
    if state == 'redirect':
        return redirect("http://dota.luokerenz.com/replay?match_id=%s" %match_id)
    else:
        reLink = 'http://dota.luokerenz.com/replayc?match_id=%s&re=1' %match_id
        return render_template("replayc.html", state=state, buttonOF=buttonState, reLink=reLink)

if __name__ == '__main__':
  app.run(host='0.0.0.0')
  #app.run(host='0.0.0.0', debug=True)
