from __future__ import division

import pandas as pd
import pymongo
from time import sleep
import json

from bokeh.io import curdoc
from bokeh.layouts import row, column, widgetbox
from bokeh.models import LinearAxis, ColumnDataSource, HoverTool
from bokeh.models.widgets import Slider, Toggle, CheckboxButtonGroup, DataTable, TableColumn, Panel, Tabs, Div
from bokeh.models.glyphs import ImageURL, Segment
from bokeh.plotting import figure
from bokeh.models.callbacks import CustomJS

from ConfigParser import SafeConfigParser
global mongoConfig
mongoConfig = SafeConfigParser()
mongoConfig.read('/home/bokeh/mongoConfig.ini')

styleCSS = """"""

def timeConverter(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

def coor_finder(mongo_client, time):
    return 0

def icon_finder(hero_id, id_to_name): #input: hero_id, dictionary used for id to name conversion
    icon_head = "http://mf.luokerenz.com/hero_icon/"
    hero_name = id_to_name[int(hero_id)]
    return icon_head+str(hero_name)+"_icon.png"

# Set up callbacks
def update_plot(attrname, old, new):
    global ahl
    tick = int(time_slider.value)
    time_slider.title = timeConverter(tick)
    cd = col.find_one({"tag": 1, "matchid": int(match_id), "time":int(tick)})["data"]
    cgd = [int(0)]*10
    cexp = [int(0)]*10
    cdmg_h = [int(0)]*10
    cdmg_l = [int(0)]*10
    ahl = [0]*10
    circleX = []
    circleY = []
    for i in range(10):
        player_hero = cd[i]['h']
        ahl[i] = int(player_hero)
        hero_url = icon_finder(player_hero, id_to_name)
        columnDict["player"+str(i)] = [hero_url]
        columnDict["x"+str(i)] = [cd[i]["d"][0]]
        circleX.extend([cd[i]["d"][0]])
        columnDict["y"+str(i)] = [cd[i]["d"][1]]
        circleY.extend([cd[i]["d"][1]])
        cgd[i] = cd[i]["d"][2]
        cexp[i] = cd[i]["d"][3]
        cdmg_h[i] = cd[i]["d"][7]
        cdmg_l[i] = cd[i]["d"][8]

    max_y = max(cgd+cexp)+200

    source.data = columnDict
    circle_source.data['x'] = circleX
    circle_source.data['y'] = circleY
    g_source.data['height'] = cgd
    exp_source.data['height'] = cexp
    dmgH_source.data['height'] = cdmg_h
    dmgL_source.data['height'] = cdmg_l

    updateBracket('data',{'value':0},{'value':0})
    hero_img_source.data = dict(url=heroURL_list, x=[ind+0.5 for ind in range(1,20,2)], y=[max_y*0.1]*10, h=[1/(21/max_y)]*10)

def toggle_cc(arg):
    global play_state
    play_state = arg

def constant_update():
    global play_state
    if play_state:
        time_slider.value += 1
        interStrigger.data = dict(value=[time_slider.value])

def analysis_update(new):
    switch = analysis_grp.active
    if 0 in switch: # switch for bracket data
        segdata_3.data['alphacc']=[1]*20
    else:
        segdata_3.data['alphacc']=[0]*20
    updateBracket('data',{'value':0},{'value':1})

def updateBracket(attrname, old, new):
    global ahl
    if 0 in analysis_grp.active:
        #update gold analysis
        tick = int(time_slider.value)
        floor_tick = int(tick/60)*60
        if old['value']==new['value']:
            pre_tick = segdata_3.data['tickCheck'][0]
        else:
            pre_tick = 70 # bypass to force update
        # if new tick is out of range of previous tick, update
        if abs(pre_tick-floor_tick)>=60:
            current_y = segdata_3.data['y0']
            dmg_currentY = segdata_3.data['y0_dmg']
            #print 'looking for time: %s' %floor_tick
            anad = db.aggreResult.find({"$and": [{"_id.time":floor_tick},{"$or": [{"_id.h":ahl[0]},{"_id.h":ahl[1]},{"_id.h":ahl[2]},{"_id.h":ahl[3]},{"_id.h":ahl[4]},{"_id.h":ahl[5]},{"_id.h":ahl[6]},{"_id.h":ahl[7]},{"_id.h":ahl[8]},{"_id.h":ahl[9]},]},{"_id.avg_mmrk": int(bracket_input.value)}]})
            for inda in anad:
                update_playerID = ahl.index(int(inda['_id']['h']))
                current_y[int(update_playerID)*2] = inda['g_avg']
                current_y[int(update_playerID)*2+1] = inda['exp_avg']
                dmg_currentY[int(update_playerID)*2] = inda['dmgH_avg']
                #dmg_currentY[int(update_playerID)*2+1] = inda['exp_avg']

            segdata_3.data['y0'] = current_y
            segdata_3.data['y1'] = current_y
            segdata_3.data['y0_dmg'] = dmg_currentY
            segdata_3.data['y1_dmg'] = dmg_currentY
            segdata_3.data['alphacc'] = [0]*20
            segdata_3.data['alphacc'] = [1]*20
            segdata_3.data['tickCheck'] = [floor_tick]*20

# init global
global play_state, match_id
global ahl # global hero name list
play_state = False
ahl = [0]*10
args = curdoc().session_context.request.arguments

try:
    match_id = str(args.get('match_id')[0])
except:
    match_id = "3084610354"
print match_id

# init local & db connection
url_map = "http://mf.luokerenz.com/minimap.jpg"
mhost = mongoConfig.get('all', 'host')
muser = mongoConfig.get('all', 'user')
mpass = mongoConfig.get('all', 'password')
columnDict = dict()
mongo_client = pymongo.MongoClient(mhost, 27011)
db = mongo_client['dota']
db.authenticate(muser, mpass)

global col
col = db.zoneResult

# init dictionary lookup
conv_dict = pd.read_csv('bokeh_ref.csv',index_col='id').drop('internal_name',1).to_dict()
id_to_name = conv_dict['name']
name_to_id = {v: y for y, v in id_to_name.iteritems()}

# init data from db
cur = col.find({"tag": 1, "matchid": int(match_id), "time": {"$exists": True}}, sort=[("time", pymongo.ASCENDING)], limit=1)
for doc in cur:
    start_time = doc['time']
cur = col.find({"tag": 1, "matchid": int(match_id), "time": {"$exists": True}}, sort=[("time", pymongo.DESCENDING)], limit=1)
for doc in cur:
    end_time = doc['time']

# init dataFrame
cd_parent = col.find_one({"tag": 1, "matchid": int(match_id), "time":int(start_time)})
cavg_mmr = int(cd_parent['avg_mmr'])
cd = cd_parent["data"]
name_list = [' ']*10
gd = [int(0)]*10
exp = [int(0)]*10
dmg_h = [int(0)]*10
dmg_l = [int(0)]*10
heroURL_list = [""]*10
circleX = []
circleY = []
for i in range(10):
    #player_hero = stat_dict.keys()[stat_dict.values().index(str(i))]
    player_hero = cd[i]['h']
    hero_url = icon_finder(player_hero, id_to_name)
    columnDict["player"+str(i)] = [hero_url]
    heroURL_list[i] = hero_url
    columnDict["x"+str(i)] = [cd[i]["d"][0]]
    circleX.extend([cd[i]["d"][0]])
    columnDict["y"+str(i)] = [cd[i]["d"][1]]
    circleY.extend([cd[i]["d"][1]])
    gd[i] = cd[i]["d"][2]
    exp[i] = cd[i]["d"][3]
    dmg_h[i] = cd[i]["d"][7]
    dmg_l[i] = cd[i]["d"][8]
    name_list[i] = id_to_name[int(player_hero)].replace('_', ' ')

source = ColumnDataSource(data=columnDict)
circle_source = ColumnDataSource(data=dict(x=circleX,y=circleY,color=["#95cc4b","#95cc4b","#95cc4b","#95cc4b","#95cc4b","#ca4633","#ca4633","#ca4633","#ca4633","#ca4633"]))

g_source = ColumnDataSource(data=dict(x=[ind+0.25 for ind in range(1,20,2)], height=gd, y=[0]*10, hero=name_list))
exp_source = ColumnDataSource(data=dict(x=[ind-0.25 for ind in range(2,21,2)], height=exp, y=[0]*10, hero=name_list))
dmgH_source = ColumnDataSource(data=dict(x=[ind+0.25 for ind in range(1,20,2)], height=dmg_h, y=[0]*10, hero=name_list))
dmgL_source = ColumnDataSource(data=dict(x=[ind-0.25 for ind in range(2,21,2)], height=dmg_l, y=[0]*10, hero=name_list))
img_source = ColumnDataSource(data=dict(url=[url_map],x=[0],y=[0],w=[32768],h=[32768]))
hero_img_source = ColumnDataSource(data=dict(url=heroURL_list, x=[ind+0.5 for ind in range(1,20,2)], y=[200]*10, h=[40]*10))
segx0 = [1,1.5,3,3.5,5,5.5,7,7.5,9,9.5,11,11.5,13,13.5,15,15.5,17,17.5,19,19.5]
segdata_3 = ColumnDataSource(data=dict(x0=segx0,y0=[0]*20,x1=[ind+0.5 for ind in segx0],y1=[0]*20,alphacc=[0]*20,tickCheck=[0]*20,y0_dmg=[0]*20,y1_dmg=[0]*20))
info_source = ColumnDataSource(data=dict(mmr=[cavg_mmr]))
minimap = ImageURL(url="url",x="x", y="y", w="w", h="h", anchor="center", global_alpha=0.7)
divStr = styleCSS+"""<a href=https://www.opendota.com/matches/"""+str(match_id)+""">OpenDota Link</a>"""

# Set up plot
p = figure(plot_height=600, plot_width=600, title="", toolbar_location=None)
p.add_glyph(img_source, minimap)
#p.circle("x", "y", source=source, size=7, line_color=None, fill_alpha=1)
p.circle(x='x', y='y', source=circle_source, fill_alpha=0.8, radius=950, fill_color='color',line_alpha=0)
p.image_url(url="player0", x="x0", y="y0", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player1", x="x1", y="y1", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player2", x="x2", y="y2", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player3", x="x3", y="y3", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player4", x="x4", y="y4", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player5", x="x5", y="y5", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player6", x="x6", y="y6", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player7", x="x7", y="y7", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player8", x="x8", y="y8", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.image_url(url="player9", x="x9", y="y9", w=1500, h=1500, anchor="center", global_alpha=1, source=source)
p.x_range.start = p.y_range.start = -18000
p.y_range.end = p.x_range.end = 18000
ptab = Panel(child=p, title="Minimap view")

map_tabs = Tabs(tabs=[ ptab ],width=600)

p2Hover = HoverTool(tooltips=[('Hero','@hero'),('Value','@height')])
p2 = figure(plot_height=600, plot_width=600, title="", toolbar_location=None, tools=[p2Hover])
p2.vbar(x="x", width=0.5, top="height", source=g_source, fill_color="#ff7f0e", line_color="#ff7f0e", legend="Gold")
p2.vbar(x="x", width=0.5, top="height", source=exp_source, fill_color="#1f77b4", line_color="#1f77b4", legend="Experience")
p2.segment(x0="x0", y0="y0", x1="x1", y1="y1", source=segdata_3, line_alpha='alphacc', line_color="#ff0000", line_width=10, legend="Bracket Average")
p2.image_url(url="url", x="x", y="y", w=1, h="h", anchor="center", source=hero_img_source)
p2.y_range.start = 0
p2tab = Panel(child=p2, title="Gold/Experience")

p3Hover = HoverTool(tooltips=[('Hero','@hero'),('Value','@height')])
p3 = figure(plot_height=600, plot_width=600, title="", toolbar_location=None, tools=[p3Hover])
p3.vbar(x="x", width=0.5, top="height", source=dmgH_source, fill_color="#ff7f0e", line_color="#ff7f0e", legend="Hero damage")
p3.vbar(x="x", width=0.5, top="height", source=dmgL_source, fill_color="#1f77b4", line_color="#1f77b4", legend="Lane creep damage")
p3.segment(x0="x0", y0="y0_dmg", x1="x1", y1="y1_dmg", source=segdata_3, line_alpha='alphacc', line_color="#ff0000", line_width=10, legend="Bracket Average")
p3.image_url(url="url", x="x", y="y", w=1, h="h", anchor="center", source=hero_img_source)
p3.y_range.start = 0
p3tab = Panel(child=p3, title="Cumulated Damage")

data_tabs = Tabs(tabs=[ p2tab, p3tab ],width=600)

# Set up widgets
time_slider = Slider(title='Game time (s)', value=int(start_time), start=int(start_time), end=int(end_time), step=1, callback_policy="mouseup")
play_but = Toggle(label="Play", active=False)
analysis_grp = CheckboxButtonGroup(labels=['Bracket data'])
bracket_input = Slider(title='Ranking bracket (k)', value=3, start=0, end=9, step=1, callback_policy="mouseup")
link_html = Div(text=divStr)
info_columns = [
        TableColumn(field="mmr", title="average mmr",sortable=False)
    ]
info_table = DataTable(source=info_source, columns=info_columns,height=100,fit_columns=True,selectable=False,sortable=False,row_headers=False)

###### custom intermediate trigger for slider mouseup ######
interStrigger = ColumnDataSource(data=dict(value=[]))
interStrigger.on_change('data', update_plot)
time_slider.callback = CustomJS(args=dict(source=interStrigger), code="""
    source.data = { value: [cb_obj.value] }
""")
bracketTrigger = ColumnDataSource(data=dict(value=[]))
bracketTrigger.on_change('data', updateBracket)
bracket_input.callback = CustomJS(args=dict(source=bracketTrigger), code="""
    source.data = { value: [cb_obj.value] }
""")
#####

# widgets action link
play_but.on_click(toggle_cc)
analysis_grp.on_click(analysis_update)

curdoc().add_periodic_callback(constant_update, 500)

# Set up layouts and add to document
time_widget = widgetbox(time_slider,play_but)
bracket_widget = widgetbox(bracket_input,analysis_grp)
info_widget = widgetbox(link_html,info_table)
#link_widget = widgetbox(link_html)

curdoc().add_root(column(row(map_tabs, data_tabs,width=1400),row(time_widget,bracket_widget,info_widget)))
curdoc().title = "Sliders"
