from flask import Flask, request, jsonify
import json
import os
import time
import requests
import subprocess
import sys

app = Flask(__name__)

@app.route('/api/watchtime', methods=['GET', 'POST'])
def watchtime():
    channel = request.args.get('channel')
    action = request.args.get('action')

    if not channel:
        return 'Empty channel', 400
    if not action:
        return 'Empty action (get/update)', 400

    channel = html_escape(channel)
    file_path = f"{channel}.watchtime.json"

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                return 'Error reading watchtime data', 500
    else:
        data = {}

    if not isinstance(data, dict):
        data = {}

    if '$' not in data:
        data['$'] = int(time.time())

    if action == 'update':
        now = int(time.time())
        if '$' in data and now - data['$'] < 600:
            queries = [
                ('mods', '{user(login: "' + channel + '") { channel { chatters { moderators { login } } } } }'),
                ('viewers', '{user(login: "' + channel + '") { channel { chatters { viewers { login } } } } }'),
                ('vips', '{user(login: "' + channel + '") { channel { chatters { vips { login } } } } }'),
                ('viewer_count', '{user(login: "' + channel + '") { stream { viewersCount } } }')
            ]
            headers = {
                'Client-Id': 'kimne78kx3ncx6brgo4mv6wki5h1ko'
            }

            results = {}
            for key, query in queries:
                response = requests.post("https://gql.twitch.tv/gql", json={'query': query}, headers=headers)
                if response.status_code != 200:
                    return f"HTTP status code: {response.status_code}\nResponse: {response.text}", 500
                results[key] = response.json()

            mods = results.get('mods', {}).get('data', {}).get('user', {}).get('channel', {}).get('chatters', {}).get('moderators', [])
            vips = results.get('vips', {}).get('data', {}).get('user', {}).get('channel', {}).get('chatters', {}).get('vips', [])
            viewers = results.get('viewers', {}).get('data', {}).get('user', {}).get('channel', {}).get('chatters', {}).get('viewers', [])
            stream = results.get('viewer_count', {}).get('data', {}).get('user', {}).get('stream')

            if not stream:
                print("!!!!!Streamer NOT Online!!!!!!")
                return "Not Online", 200

            chatters = mods + vips + viewers
            passed = now - data['$']
            for viewer in chatters:
                viewer_login = viewer['login']
                if viewer_login not in data:
                    data[viewer_login] = 0
                data[viewer_login] += passed

            data['$'] = now
            with open(file_path, 'w') as file:
                json.dump(data, file)
            return "Finished", 200

    elif action == 'get':
        if not data:
            return 'Empty watchtime, update it first!', 200
        username = request.args.get('user')
        if not username:
            return 'Empty username', 400
        username = html_escape(username)
        if username in data:
            passed = int(time.time()) - data['$']
            if passed > 600:
                passed = 0
            total_seconds = data[username] + passed

            m, s = divmod(total_seconds, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)

            time_str = ', '.join(f"{value} {name}" for value, name in zip([d, h, m, s], ["days", "hours", "minutes", "seconds"]) if value)
            return f'{username} watched the stream for {time_str}!', 200
        else:
            return f'Invalid username "{username}": moderator, too new or nonexistent', 200
    else:
        return 'Invalid action', 400

def html_escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

if __name__ == '__main__':
    app.run(debug=True)
