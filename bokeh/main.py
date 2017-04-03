from __future__ import division

import pandas as pd
import pymongo
from time import sleep
import json

from bokeh.io import curdoc
from bokeh.layouts import row, column, widgetbox
from bokeh.models import LinearAxis, ColumnDataSource, HoverTool
from bokeh.models.widgets import Slider, Toggle, CheckboxButtonGroup
from bokeh.models.glyphs import ImageURL, Segment
from bokeh.plotting import figure
from bokeh.models.callbacks import CustomJS

from ConfigParser import SafeConfigParser
global mongoConfig
mongoConfig = SafeConfigParser()
mongoConfig.read('/home/bokeh/mongoConfig.ini')

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
    tick = int(time_slider.value)
    time_slider.title = timeConverter(tick)
    cd = col.find_one({"tag": 1, "matchid": int(match_id), "time":int(tick)})["data"]
    cgd = [int(0)]*10
    cexp = [int(0)]*10
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

    max_y = max(cgd+cexp)+200
    #print p2.y_range.start
    #print p2.y_range.end

    source.data = columnDict
    circle_source.data['x'] = circleX
    circle_source.data['y'] = circleY
    g_source.data['height'] = cgd
    exp_source.data['height'] = cexp
    #g_source.data = dict(x=[ind+0.25 for ind in range(1,20,2)], height=cgd, y=[0]*10, color=["FF7F0E"]*10)
    #exp_source.data = dict(x=[ind-0.25 for ind in range(2,21,2)], height=cexp, y=[0]*10, color=["1F77B4"]*10)
    #hero_img_source.data = dict(url=heroURL_list, x=[ind+0.5 for ind in range(1,20,2)], y=[max_y*0.1]*10, h=[1/(21/max_y)]*10)

    if 0 in analysis_grp.active:
        #update gold analysis
        floor_tick = int(tick/60)*60
        pre_tick = segdata_3.data['tickCheck'][0]
        # if new tick is out of range of previous tick, update
        if abs(pre_tick-floor_tick)>=60:
            current_y = segdata_3.data['y0']
            print 'looking for time: %s' %floor_tick
            anad = db.aggreResult.find({"$and": [{"_id.time":floor_tick},{"$or": [{"_id.h":ahl[0]},{"_id.h":ahl[1]},{"_id.h":ahl[2]},{"_id.h":ahl[3]},{"_id.h":ahl[4]},{"_id.h":ahl[5]},{"_id.h":ahl[6]},{"_id.h":ahl[7]},{"_id.h":ahl[8]},{"_id.h":ahl[9]},]},{"_id.avg_mmrk": int(3)}]})
            for inda in anad:
                update_playerID = ahl.index(int(inda['_id']['h']))
                current_y[int(update_playerID)] = inda['g_avg']
    #segdata_3.data = dict(x0=[ind for ind in range(1,20,2)],y0=current_y,x1=[ind+0.5 for ind in range(1,20,2)],y1=current_y, alphacc=current_alpha)
            segdata_3.data['y0'] = current_y
            segdata_3.data['y1'] = current_y
            segdata_3.data['alphacc'] = [0]*10
            segdata_3.data['alphacc'] = [1]*10
            segdata_3.data['tickCheck'] = [floor_tick]*10

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
    for x in range(0,len(analysis_list)):
        if x in switch:
            segdata_3.data['alphacc']=[1]*10
        else:
            segdata_3.data['alphacc']=[0]*10

# init global
global play_state, match_id
play_state = False
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
conv_dict = pd.read_csv('/home/bokeh/bokeh_ref.csv',index_col='id').drop('internal_name',1).to_dict()
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
cd = col.find_one({"tag": 1, "matchid": int(match_id), "time":int(start_time)})["data"]
name_list = [' ']*10
gd = [int(0)]*10
exp = [int(0)]*10
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
    name_list[i] = id_to_name[int(player_hero)].replace('_', ' ')

source = ColumnDataSource(data=columnDict)
circle_source = ColumnDataSource(data=dict(x=circleX,y=circleY,color=["#95cc4b","#95cc4b","#95cc4b","#95cc4b","#95cc4b","#ca4633","#ca4633","#ca4633","#ca4633","#ca4633"]))

g_source = ColumnDataSource(data=dict(x=[ind+0.25 for ind in range(1,20,2)], height=gd, y=[0]*10, hero=name_list))
exp_source = ColumnDataSource(data=dict(x=[ind-0.25 for ind in range(2,21,2)], height=exp, y=[0]*10, hero=name_list))
img_source = ColumnDataSource(data=dict(url=[url_map],x=[0],y=[0],w=[32768],h=[32768]))
hero_img_source = ColumnDataSource(data=dict(url=heroURL_list, x=[ind+0.5 for ind in range(1,20,2)], y=[200]*10, h=[40]*10))
segdata_3 = ColumnDataSource(data=dict(x0=[ind for ind in range(1,20,2)],y0=[0]*10,x1=[ind+0.5 for ind in range(1,20,2)],y1=[0]*10,alphacc=[0]*10,tickCheck=[0]*10))
minimap = ImageURL(url="url",x="x", y="y", w="w", h="h", anchor="center", global_alpha=0.7)

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

p2Hover = HoverTool(tooltips=[('Hero','@hero'),('Value','@height')])
p2 = figure(plot_height=600, plot_width=600, title="", toolbar_location=None, tools=[p2Hover])
p2.vbar(x="x", width=0.5, top="height", source=g_source, fill_color="#ff7f0e", line_color="#ff7f0e", legend="Gold")
p2.vbar(x="x", width=0.5, top="height", source=exp_source, fill_color="#1f77b4", line_color="#1f77b4", legend="Experience")
segment_3 = p2.segment(x0="x0", y0="y0", x1="x1", y1="y1", source=segdata_3, line_alpha='alphacc', line_color="#ff0000", line_width=10, legend="Hero Average")
analysis_list = [segment_3]
p2.image_url(url="url", x="x", y="y", w=1, h="h", anchor="center", source=hero_img_source)
p2.y_range.start = 0

#p2.y_range.end = 1000
#p2.y_range = Range1d(0, 20000)

# Set up widgets
time_slider = Slider(title="time", value=int(start_time), start=int(start_time), end=int(end_time), step=1, callback_policy="mouseup")
play_but = Toggle(label="Play", active=False)
analysis_grp = CheckboxButtonGroup(labels=['Gold rank'])

######
interStrigger = ColumnDataSource(data=dict(value=[]))
interStrigger.on_change('data', update_plot)
time_slider.callback = CustomJS(args=dict(source=interStrigger), code="""
    source.data = { value: [cb_obj.value] }
""")
#####

# widgets action link
#time_slider.on_change('value', update_plot)
play_but.on_click(toggle_cc)
analysis_grp.on_click(analysis_update)

curdoc().add_periodic_callback(constant_update, 500)

# Set up layouts and add to document
inputs = widgetbox(time_slider,play_but,analysis_grp)

curdoc().add_root(column(inputs, row(p, p2, width=1400)))
curdoc().title = "Sliders"
