import os
import json
import threading
import bottle
import ssl
from wsgiref.simple_server import make_server
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
            app_state['reload_spotify'] = True # dynamically reload spotify client
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
        except Exception as e:
            return f"Error saving settings: {str(e)}"
        
        redirect('/')

    @app.route('/logout')
    def logout():
        if os.path.exists(".cache"):
            os.remove(".cache")
        app_state['reload_spotify'] = True
        redirect('/')

    def run_web_server():
        cert_dir = os.path.dirname(os.path.abspath(__file__))
        cert_file = os.path.join(cert_dir, 'cert.pem')
        key_file = os.path.join(cert_dir, 'key.pem')

        # Auto-generate self-signed cert if it doesn't exist
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            import subprocess
            print("Generating self-signed SSL certificates for HTTPS...")
            subprocess.call([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                '-keyout', key_file, '-out', cert_file,
                '-days', '3650', '-nodes', '-subj', '/CN=matrix.local'
            ])
            # chmod to ensure dietpi can read them if needed
            os.chmod(cert_file, 0o644)
            os.chmod(key_file, 0o644)

        # Create a standard WSGI server
        srv = make_server('0.0.0.0', 443, app)
        
        # Wrap it with our self-signed certificates
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        srv.socket = context.wrap_socket(srv.socket, server_side=True)
        
        srv.serve_forever()

    def run_http_redirect_server():
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(301)
                self.send_header('Location', 'https://matrix.local' + self.path)
                self.end_headers()
                
            def do_POST(self):
                self.do_GET()
                
        # Running on port 80 since systemd script starts this as root
        app_redirect = HTTPServer(('0.0.0.0', 80), RedirectHandler)
        app_redirect.serve_forever()

    # Start HTTPS web interface in the background
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start HTTP redirect server in the background
    redirect_thread = threading.Thread(target=run_http_redirect_server, daemon=True)
    redirect_thread.start()