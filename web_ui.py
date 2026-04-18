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
        :root {
            --bg-color: #121212;
            --card-bg: #181818;
            --text-color: #ffffff;
            --text-secondary: #b3b3b3;
            --spotify-green: #1DB954;
            --spotify-green-hover: #1ed760;
            --danger-color: #e91429;
            --danger-hover: #ff1a33;
        }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 20px; 
            max-width: 500px; 
            margin: auto; 
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        h2 { text-align: center; margin-bottom: 30px; font-weight: 700; letter-spacing: -0.04em; }
        h3 { margin-top: 0; font-size: 1.2rem; font-weight: 600; }
        .card { 
            background-color: var(--card-bg); 
            padding: 24px; 
            border-radius: 12px; 
            margin-bottom: 24px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        .status { margin: 15px 0; font-size: 1rem; color: var(--text-secondary); display: flex; align-items: center; gap: 8px; }
        .status.success { color: var(--spotify-green); }
        .btn { 
            display: block; 
            width: 100%; 
            padding: 14px; 
            margin-top: 15px; 
            border: none; 
            border-radius: 500px; 
            font-size: 1rem; 
            font-weight: 700; 
            text-align: center; 
            cursor: pointer; 
            text-decoration: none; 
            color: white; 
            box-sizing: border-box;
            transition: all 0.2s ease;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .btn-green { background-color: var(--spotify-green); color: #000; }
        .btn-green:hover { background-color: var(--spotify-green-hover); transform: scale(1.02); }
        .btn-red { background-color: transparent; border: 1px solid var(--text-secondary); color: var(--text-color); }
        .btn-red:hover { border-color: var(--text-color); transform: scale(1.02); }
        .btn-blue { background-color: #ffffff; color: #000; }
        .btn-blue:hover { background-color: #f0f0f0; transform: scale(1.02); }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: var(--text-secondary); }
        input[type=range] { 
            -webkit-appearance: none;
            width: 100%; 
            background: transparent;
            margin: 15px 0 25px 0;
        }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none;
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: #ffffff;
            cursor: pointer;
            margin-top: -8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }
        input[type=range]::-webkit-slider-runnable-track {
            width: 100%;
            height: 4px;
            cursor: pointer;
            background: #535353;
            border-radius: 2px;
        }
        .slider-values { display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 0.8rem; margin-top: -15px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <h2>Spotify Matrix</h2>

    <div class="card">
        <h3>Spotify Connection</h3>
        % if has_token:
            <div class="status success">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                Successfully Linked
            </div>
            <a href="/logout" class="btn btn-red">Disconnect Account</a>
        % else:
            <div class="status">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                Not Linked
            </div>
            <a href="/login" class="btn btn-green">Link to Spotify</a>
        % end
    </div>

    <div class="card">
        <h3>Display Settings</h3>
        <form action="/save_settings" method="POST">
            <label>Brightness</label>
            <input type="range" name="brightness" min="1" max="100" value="{{brightness}}">
            <div class="slider-values">
                <span>Dim</span>
                <span>Bright</span>
            </div>
            <button type="submit" class="btn btn-blue">Apply Settings</button>
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
            redirect('/')
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