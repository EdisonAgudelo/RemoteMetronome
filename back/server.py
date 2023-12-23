
from flask import Flask, request, render_template, send_from_directory
from back.metro import Metronome
import flask_sock
import os

#eventlet.monkey_patch()
app = Flask(__name__)
app.config["SECRET_KEY"] = "JesusKing"
sock = flask_sock.Sock(app)

metro: Metronome = None
index: str = 'index.html'

@app.route('/')
def index():
    global metro

    if not metro:
        return

    return render_template(index, metro_running = int(not metro.mute)), 200



@app.route('/start_metronome')
def start_metronome():
    global metro

    if not metro:
        return
    
    tempo = int(request.args.get('tempo', 120))
    beat = int(request.args.get('beat', 4))
    
    metro.set_bar_size(beat)
    metro.start(tempo)

    return 'Metrónomo iniciado', 200

@app.route('/stop_metronome')
def stop_metronome():
    global metro

    if not metro:
        return

    metro.stop()

    return 'Metrónomo detenido', 200


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'assets/metronome.ico', mimetype='image/vnd.microsoft.icon'),200


@sock.route('/bar')
def ws_bar(ws: flask_sock.Server):
    global metro
    if not metro:
        return
    metro.bar_reporter(ws)

@sock.route('/beat')
def ws_beat(ws: flask_sock.Server):
    global metro
    if not metro:
        return
    metro.beat_reporter(ws)

def set_metro(new_metro):
    global metro
    metro = new_metro

def set_data_folders(path):
    app.template_folder = path + "\\back\\templates"
    app.static_folder = path + "\\back\\static"

def set_index(index_path):
    global index
    index = index_path