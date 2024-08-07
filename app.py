import random
import time

from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

players = {}
game_state = {
    "is_playing": False,
    "round_start_time": 0,
    "round_duration": 0,
    "seated_players": 0
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin')
def admin():
    return render_template('admin.html', players=players, game_state=game_state)


@app.route('/admin/start_game', methods=['POST'])
def admin_start_game():
    start_game()
    return redirect(url_for('admin'))


@app.route('/admin/stop_game', methods=['POST'])
def admin_stop_game():
    stop_game()
    return redirect(url_for('admin'))


@socketio.on('connect')
def handle_connect():
    player_id = request.sid
    players[player_id] = {"seated": False}
    emit('player_connected', {'id': player_id, 'player_count': len(players)}, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    if player_id in players:
        del players[player_id]
    emit('player_disconnected', {'player_count': len(players)}, broadcast=True)


@socketio.on('start_game')
def handle_start_game():
    start_game()


@socketio.on('player_seated')
def player_seated():
    player_id = request.sid
    if game_state["is_playing"] and not players[player_id]["seated"]:
        players[player_id]["seated"] = True
        game_state["seated_players"] += 1
        emit('player_seated', {'id': player_id}, broadcast=True)
        check_round_end()


def start_game():
    if len(players) > 1:
        game_state["is_playing"] = True
        game_state["round_start_time"] = time.time()
        game_state["round_duration"] = random.randint(5, 15)
        game_state["seated_players"] = 0
        socketio.emit('game_started', {
            'start_time': game_state["round_start_time"],
            'duration': game_state["round_duration"]
        })


def stop_game():
    game_state["is_playing"] = False
    reset_round()
    socketio.emit('game_stopped')


def check_round_end():
    if game_state["seated_players"] == len(players) - 1:
        game_state["is_playing"] = False
        eliminated_player = next(id for id, player in players.items() if not player["seated"])
        socketio.emit('round_ended', {'eliminated': eliminated_player})
        reset_round()


def reset_round():
    for player in players.values():
        player["seated"] = False
    game_state["seated_players"] = 0


if __name__ == '__main__':
    socketio.run(app, debug=True)
