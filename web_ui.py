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
        
        /* Toggle Switch CSS */
        .setting-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .setting-row label { margin-bottom: 0; }
        .switch { position: relative; display: inline-block; width: 50px; height: 28px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider.round { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #535353; transition: .4s; border-radius: 34px; }
        .slider.round:before { position: absolute; content: ""; height: 20px; width: 20px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider.round { background-color: var(--spotify-green); }
        input:checked + .slider.round:before { transform: translateX(22px); }
        
        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
            vertical-align: middle;
            margin-left: 5px;
            margin-top: -2px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Custom Modal CSS */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; opacity: 0; pointer-events: none; transition: opacity 0.2s; backdrop-filter: blur(2px); }
        .modal-overlay.active { opacity: 1; pointer-events: all; }
        .modal { background-color: var(--card-bg); padding: 24px; border-radius: 12px; width: 85%; max-width: 360px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); transform: translateY(20px); transition: transform 0.2s; text-align: center; }
        .modal-overlay.active .modal { transform: translateY(0); }
        .modal-actions { display: flex; gap: 10px; margin-top: 25px; }
        .modal-actions .btn { margin-top: 0; flex: 1; }
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
            <div class="setting-row">
                <label>Track Progress Bar</label>
                <label class="switch">
                    <input type="checkbox" name="show_progress" {{'checked' if show_progress else ''}}>
                    <span class="slider round"></span>
                </label>
            </div>
            
            <div class="setting-row">
                <label>Bar Color</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="color" name="progress_color" value="{{progress_color}}" style="width: 50px; height: 35px; padding: 0; border: none; border-radius: 4px; cursor: pointer; background: transparent;">
                    <button type="submit" name="action" value="reset_color" style="background: transparent; border: 1px solid var(--text-secondary); color: var(--text-secondary); border-radius: 4px; padding: 5px 10px; font-size: 0.8rem; cursor: pointer;">Reset</button>
                </div>
            </div>
            
            <label>Brightness</label>
            <input type="range" name="brightness" min="1" max="100" value="{{brightness}}">
            <div class="slider-values">
                <span>Dim</span>
                <span>Bright</span>
            </div>
            
            <button type="submit" class="btn btn-blue">Apply Settings</button>
        </form>
    </div>

    <div class="card">
        <h3>System Management</h3>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0; margin-bottom: 5px;">Manage updates and device power.</p>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0; margin-bottom: 15px;">Version: <span style="color: var(--spotify-green);">{{version}}</span></p>
        <div style="display: flex; gap: 10px; flex-direction: column;">
            <button type="button" id="checkUpdateBtn" class="btn btn-blue" style="margin-top: 5px;" onclick="checkUpdates()">Check For Updates</button>
            <form id="updateForm" action="/system_update" method="POST" style="display: none;"></form>
            
            <div style="display: flex; gap: 10px; margin-top: 10px;">
                <form action="/system_power" method="POST" style="flex: 1;">
                    <button type="submit" name="command" value="reboot" class="btn btn-red" style="margin-top: 0;">Reboot</button>
                </form>
                <form action="/system_power" method="POST" style="flex: 1;">
                    <button type="submit" name="command" value="shutdown" class="btn btn-red" style="margin-top: 0;">Shutdown</button>
                </form>
            </div>
        </div>
    </div>
    
    <!-- Custom Modal UI -->
    <div id="customModal" class="modal-overlay">
        <div class="modal">
            <h3 id="modalTitle" style="margin-bottom: 10px; font-size: 1.3rem;">Title</h3>
            <p id="modalMessage" style="color: var(--text-secondary); font-size: 0.95rem;">Message text goes here.</p>
            <div class="modal-actions">
                <button id="modalCancel" class="btn btn-red" onclick="hideModal()">Cancel</button>
                <button id="modalConfirm" class="btn btn-green">OK</button>
            </div>
        </div>
    </div>

    <script>
    var confirmAction = null;
    function showModal(title, message, showCancel, callback) {
        document.getElementById('modalTitle').innerText = title;
        document.getElementById('modalMessage').innerText = message;
        document.getElementById('modalCancel').style.display = showCancel ? 'block' : 'none';
        document.getElementById('customModal').classList.add('active');
        confirmAction = callback;
    }
    function hideModal() {
        document.getElementById('customModal').classList.remove('active');
    }
    document.getElementById('modalConfirm').onclick = function() {
        hideModal();
        if(confirmAction) confirmAction();
    };

    var localHash = "{{local_hash}}";

    function checkUpdates() {
        var btn = document.getElementById('checkUpdateBtn');
        var originalText = "Check For Updates";
        btn.innerHTML = 'Checking... <div class="spinner"></div>';
        btn.disabled = true;
        
        fetch('https://api.github.com/repos/jonasradke/spotify-matrix-mvp/commits/main')
        .then(res => res.json())
        .then(data => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            
            if (data.sha && data.sha.trim() !== localHash) {
                showModal("Update Available", "Updates are available! Do you want to install them now and restart the matrix?", true, function() {
                    btn.innerHTML = 'Updating & Restarting... <div class="spinner"></div>';
                    btn.disabled = true;
                    btn.classList.remove('btn-blue');
                    btn.classList.add('btn-green');
                    document.getElementById('updateForm').submit();
                });
            } else if (data.sha && data.sha.trim() === localHash) {
                btn.innerHTML = 'Up to Date ✓';
                btn.disabled = true;
                setTimeout(() => { 
                    btn.innerHTML = originalText; 
                    btn.disabled = false; 
                }, 3000);
            } else {
                showModal("Update Error", "Could not verify update status.", false, null);
            }
        })
        .catch(err => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            showModal("Network Error", "Network error while checking for updates.", false, null);
        });
    }
    </script>
</body>
</html>
"""

def start_web_server(app_state, sp_oauth):
    app = bottle.Bottle()

    def get_current_version():
        import subprocess
        try:
            cwd_path = os.path.dirname(os.path.abspath(__file__))
            commits = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], cwd=cwd_path).decode('utf-8').strip()
            return f"v1.0.{commits}"
        except:
            return "Unknown Version"

    def get_current_hash():
        import subprocess
        try:
            cwd_path = os.path.dirname(os.path.abspath(__file__))
            return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd_path).decode('utf-8').strip()
        except:
            return ""

    @app.route('/')
    def index():
        has_token = bool(sp_oauth.get_cached_token())
        return template(HTML_TEMPLATE, 
                        has_token=has_token, 
                        brightness=app_state['brightness'], 
                        show_progress=app_state.get('show_progress', False),
                        progress_color=app_state.get('progress_color', '#1ED760'),
                        version=get_current_version(),
                        local_hash=get_current_hash())

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
            p = request.forms.get('show_progress') == 'on'
            
            if request.forms.get('action') == 'reset_color':
                c = '#1ED760'
                app_state['progress_color'] = c
            else:
                c = request.forms.get('progress_color')
                if c:
                    app_state['progress_color'] = c

            if b:
                app_state['brightness'] = b
                app_state['show_progress'] = p
                # Save settings persistently to a JSON file
                settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
                with open(settings_path, 'w') as f:
                    json.dump({'brightness': b, 'show_progress': p, 'progress_color': app_state.get('progress_color', '#1ED760')}, f)
        except Exception as e:
            return f"Error saving settings: {str(e)}"
        
        redirect('/')

    @app.route('/logout')
    def logout():
        if os.path.exists(".cache"):
            os.remove(".cache")
        app_state['reload_spotify'] = True
        redirect('/')

    @app.route('/api/check_updates', method='POST')
    def check_updates():
        import subprocess
        try:
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
            cwd_path = os.path.dirname(os.path.abspath(__file__))
            
            # Super fast checking: query remote github hash directly without downloading files
            local_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd_path).decode('utf-8').strip()
            remote_output = subprocess.check_output(['git', 'ls-remote', 'origin', 'HEAD'], env=env, cwd=cwd_path).decode('utf-8').strip()
            
            if not remote_output:
                return {'status': 'unknown', 'message': 'Could not connect to GitHub.'}
            
            remote_hash = remote_output.split()[0]
            if local_hash != remote_hash:
                return {'status': 'available', 'remote_version': f"New Update"}
            else:
                commits = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], cwd=cwd_path).decode('utf-8').strip()
                return {'status': 'up_to_date', 'remote_version': f"v1.0.{commits}"}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': 'Git fetch failed (Authentication required). Ensure your Git remote URL contains the Personal Access Token.'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @app.route('/system_power', method='POST')
    def system_power():
        import subprocess
        command = request.forms.get('command')
        if command == 'reboot':
            subprocess.Popen(['sudo', 'reboot'])
            msg = "Rebooting device..."
        elif command == 'shutdown':
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
            msg = "Shutting down device... You can safely unplug the power in 15 seconds."
        else:
            redirect('/')
            return
        
        return f"""
        <body style="background-color:#121212; color:white; font-family:sans-serif; text-align:center; padding:50px;">
            <h2>{msg}</h2>
        </body>
        """

    @app.route('/system_update', method='POST')
    def system_update():
        import subprocess
        try:
            # Tell the Pi to pull the absolute newest changes from GitHub
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
            cwd_path = os.path.dirname(os.path.abspath(__file__))
            
            subprocess.check_call(['git', 'pull'], env=env, cwd=cwd_path)
        except Exception as e:
            print(f"Error pulling updates: {e}")
        
        # Trigger graceful systemd restart in main.py
        app_state['restart'] = True
        
        return """
        <html>
        <head>
            <style>
                body { background-color:#121212; color:white; font-family:sans-serif; text-align:center; padding:50px; }
                p { color:#b3b3b3; }
                .spinner { display: inline-block; width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #1DB954; animation: spin 1s ease-in-out infinite; margin-top: 20px; }
                @keyframes spin { to { transform: rotate(360deg); } }
            </style>
            <meta http-equiv="refresh" content="15;url=/" />
        </head>
        <body>
            <h2>Updating & Restarting...</h2>
            <div class="spinner"></div>
            <p style="margin-top: 30px;">The matrix is downloading new code and rebooting.</p>
            <p>This page will auto-refresh in 15 seconds.</p>
        </body>
        </html>
        """

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

        # Create a multithreaded WSGI server so background checks don't block the UI
        import socketserver
        from wsgiref.simple_server import WSGIServer
        class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
            daemon_threads = True

        srv = make_server('0.0.0.0', 443, app, server_class=ThreadingWSGIServer)
        
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