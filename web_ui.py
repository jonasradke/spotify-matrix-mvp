import os
import json
import threading
import bottle
from bottle import request, redirect, template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Spotify Matrix Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; padding: 20px; max-width: 600px; margin: auto; }
        .card { border: 1px solid #ccc; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .btn { display: inline-block; padding: 10px 15px; margin: 5px 0; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; color: white;}
        .btn-green { background-color: #1DB954; }
        .btn-blue { background-color: #007BFF; }
        .btn-red { background-color: #DC3545; }
        input[type=number] { width: 100%; padding: 8px; margin: 10px 0;  box-sizing: border-box;}
    </style>
</head>
<body>
    <h2>Spotify Matrix MVP</h2>

    <div class="card">
        <h3>1. Spotify Account</h3>
        % if has_token:
            <p>✅ Successfully linked to Spotify!</p>
            <a href="/logout" class="btn btn-red">Log Out (Reset)</a>
        % else:
            <p>❌ Not linked to Spotify.</p>
            <a href="/login" class="btn btn-green">Link Spotify Account</a>
        % end
    </div>

    <div class="card">
        <h3>2. Matrix Settings</h3>
        <form action="/save_settings" method="POST">
            <label>Brightness (1 - 100)</label>
            <input type="number" name="brightness" min="1" max="100" value="{{brightness}}">
            <button type="submit" class="btn btn-blue">Save & Apply Settings</button>
        </form>
    </div>
</body>
</html>
"""

def start_web_server(app_state, sp_oauth):
    app = bottle.Bottle()

    @app.route('/')
    def index():
        has_token = bool(sp_oauth.get_cached_token())
        return template(HTML_TEMPLATE, has_token=has_token, brightness=app_state['brightness'])

    @app.route('/login')
    def login():
        # Redirect user to Spotify's official login page
        auth_url = sp_oauth.get_authorize_url()
        redirect(auth_url)

    @app.route('/callback')
    def callback():
        # Spotify redirects here back with a code
        code = request.query.code
        if code:
            # This writes the .cache file automatically
            sp_oauth.get_access_token(code, as_dict=False)
            app_state['restart'] = True # Restart loop to re-initialize Spotify client
            return "Login successful! You can close this window and the matrix will update."
        return "Error generating token."

    @app.route('/save_settings', method='POST')
    def save_settings():
        try:
            b = request.forms.get('brightness', type=int)
            if b:
                app_state['brightness'] = b
                # Save settings persistently to a JSON file
                settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
                with open(settings_path, 'w') as f:
                    json.dump({'brightness': b}, f)
            redirect('/')
        except Exception as e:
            return f"Error saving settings: {str(e)}"

    @app.route('/logout')
    def logout():
        if os.path.exists(".cache"):
            os.remove(".cache")
        app_state['restart'] = True
        redirect('/')

    def run_web_server():
        # Running on port 80 since systemd script starts this as root
        app.run(host='0.0.0.0', port=80, quiet=True)

    # Start web interface in the background
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()