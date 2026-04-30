import os
import json
import threading
import bottle
import ssl
from wsgiref.simple_server import make_server
from bottle import request, redirect, template, response

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Spotify Matrix Einstellungen</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#121212">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="manifest" href="/manifest.webmanifest">
    <link rel="icon" href="/icon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/icon.svg">
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
            max-width: 900px; 
            margin: auto; 
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        h2 { text-align: center; margin-bottom: 30px; font-weight: 700; letter-spacing: -0.04em; }
        h3 { margin-top: 0; font-size: 1.2rem; font-weight: 600; }
        .grid-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
        }
        @media (min-width: 768px) {
            .grid-container {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        .card { 
            background-color: var(--card-bg); 
            padding: 24px; 
            border-radius: 12px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
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
        
        .now-playing { display: flex; align-items: center; gap: 15px; margin-top: 15px; }
        .now-playing img { width: 80px; height: 80px; border-radius: 8px; object-fit: cover; box-shadow: 0 4px 12px rgba(0,0,0,0.5); background-color: #282828; }
        .now-playing-info { flex: 1; overflow: hidden; }
        .now-playing-title { font-weight: bold; font-size: 1.1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 2px; }
        .now-playing-artist { color: var(--text-secondary); font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .np-progress-wrap { margin-top: 12px; }
        .np-progress-track { height: 6px; background: #3a3a3a; border-radius: 999px; overflow: hidden; }
        .np-progress-fill { height: 100%; width: 0%; background: var(--spotify-green); transition: width 0.2s linear; }
        .np-progress-time { margin-top: 6px; color: var(--text-secondary); font-size: 0.78rem; text-align: right; }
        .controls { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 20px; }
        .control-btn { background: transparent; border: none; color: white; cursor: pointer; transition: transform 0.2s, color 0.2s; padding: 10px; border-radius: 50%; outline: none; }
        .control-btn:hover { transform: scale(1.1); color: var(--spotify-green); background: rgba(255,255,255,0.1); }
        .control-btn:active { transform: scale(0.95); }
        .control-btn svg { width: 28px; height: 28px; display: block; fill: currentColor; }
        .play-btn svg { width: 36px; height: 36px; }

        .matrix-settings-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
            margin-bottom: 18px;
        }

        @media (min-width: 700px) {
            .matrix-settings-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        .matrix-field input[type="number"] {
            width: 100%;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #121212;
            color: white;
            box-sizing: border-box;
            font-size: 1rem;
        }

        .matrix-readout {
            margin: 8px 0 16px;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        #unlinked-msg { display: none; margin-top: 15px; color: var(--text-secondary); font-size: 0.9rem; text-align: center; }
    </style>
</head>
<body>
    <h2>Spotify Matrix</h2>

    <div class="grid-container">
        <div class="card">
            <h3>Spotify Verbindung</h3>
            % if has_token:
            <div id="now-playing-container">
                <div class="now-playing">
                    <img id="np-img" src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" alt="Albumcover">
                    <div class="now-playing-info">
                        <div id="np-title" class="now-playing-title">Lädt...</div>
                        <div id="np-artist" class="now-playing-artist">Warten auf Spotify</div>
                    </div>
                </div>
                <div class="np-progress-wrap">
                    <div class="np-progress-track">
                        <div id="np-progress-fill" class="np-progress-fill"></div>
                    </div>
                    <div id="np-progress-time" class="np-progress-time">0:00 / 0:00</div>
                </div>
                <div class="controls">
                    <button class="control-btn" onclick="playbackCommand('previous')">
                        <svg viewBox="0 0 24 24"><path d="M16 4v16L6 12zM6 4v16h2V4z"/></svg>
                    </button>
                    <button id="np-playpause" class="control-btn play-btn" onclick="playbackCommand('play_pause')">
                        <!-- Play Icon Default -->
                        <svg id="icon-play" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                        <!-- Pause Icon Hidden -->
                        <svg id="icon-pause" viewBox="0 0 24 24" style="display:none;"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                    </button>
                    <button class="control-btn" onclick="playbackCommand('next')">
                        <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7zM20 5v14h-2V5z"/></svg>
                    </button>
                </div>
                <a href="/logout" class="btn btn-red" style="margin-top: 25px;">Konto trennen</a>
            </div>
        % else:
            <div class="status">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                Nicht verbunden
            </div>
            <a href="/login" class="btn btn-green">Mit Spotify verbinden</a>
        % end
    </div>

    <div class="card">
        <h3>Anzeigeeinstellungen</h3>
        <form action="/save_settings" method="POST">
            <div class="setting-row">
                <label>Fortschrittsbalken anzeigen</label>
                <label class="switch">
                    <input type="checkbox" name="show_progress" {{'checked' if show_progress else ''}}>
                    <span class="slider round"></span>
                </label>
            </div>
            
            <div class="setting-row">
                <label>Balkenfarbe</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="color" name="progress_color" value="{{progress_color}}" style="width: 50px; height: 35px; padding: 0; border: none; border-radius: 4px; cursor: pointer; background: transparent;">
                    <button type="submit" name="action" value="reset_color" style="background: transparent; border: 1px solid var(--text-secondary); color: var(--text-secondary); border-radius: 4px; padding: 5px 10px; font-size: 0.8rem; cursor: pointer;">Zurücksetzen</button>
                </div>
            </div>
            
            <label>Helligkeit</label>
            <input type="range" name="brightness" min="1" max="100" value="{{brightness}}">
            <div class="slider-values">
                <span>Dunkel</span>
                <span>Hell</span>
            </div>

            <label>Idle-Bildschirmmodus</label>
            <select name="idle_mode" style="width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 6px; border: 1px solid #333; background: #121212; color: white; box-sizing: border-box; font-size: 1rem;">
                <option value="off" {{'selected' if idle_mode == 'off' else ''}}>Aus (schwarzer Bildschirm)</option>
                <option value="clock" {{'selected' if idle_mode == 'clock' else ''}}>Uhr</option>
                <option value="clock_date" {{'selected' if idle_mode == 'clock_date' else ''}}>Uhr + Datum</option>
            </select>

            <label>Textfarbe im Idle-Modus</label>
            <input type="color" name="idle_color" value="{{idle_color}}" style="width: 100%; height: 42px; margin-bottom: 15px; border-radius: 6px; border: 1px solid #333; background: #121212; box-sizing: border-box;">

            <label>Idle-Bildschirm ausblenden zwischen</label>
            <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 15px;">
                <input type="time" name="idle_block_start" value="{{idle_block_start}}" style="flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #333; background: #121212; color: white; box-sizing: border-box;">
                <span style="color: var(--text-secondary);">bis</span>
                <input type="time" name="idle_block_end" value="{{idle_block_end}}" style="flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #333; background: #121212; color: white; box-sizing: border-box;">
            </div>
            <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: -8px; margin-bottom: 14px;">Setze beide Zeiten gleich, um diesen Zeitplan zu deaktivieren.</p>

            <h3 style="margin-top: 28px;">Matrix-Hardware</h3>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0; margin-bottom: 15px;">Änderungen an diesen Werten benötigen einen Neustart der Matrix.</p>
            <div class="matrix-settings-grid">
                <div class="matrix-field">
                    <label>Rows</label>
                    <input type="number" name="matrix_rows" min="1" max="256" value="{{matrix_rows}}">
                </div>
                <div class="matrix-field">
                    <label>Cols</label>
                    <input type="number" name="matrix_cols" min="1" max="256" value="{{matrix_cols}}">
                </div>
                <div class="matrix-field">
                    <label>GPIO Slowdown</label>
                    <input type="number" name="gpio_slowdown" min="0" max="10" value="{{gpio_slowdown}}">
                </div>
                <div class="matrix-field">
                    <label>Limit Refresh Rate (Hz)</label>
                    <input type="number" name="limit_refresh_rate_hz" min="1" max="1000" value="{{limit_refresh_rate_hz}}">
                </div>
                <div class="matrix-field">
                    <label>Slowdown / PWM LSB ns</label>
                    <input type="number" name="pwm_lsb_nanoseconds" min="0" max="10000" value="{{pwm_lsb_nanoseconds}}">
                </div>
                <div class="matrix-field">
                    <label>Chain Length</label>
                    <input type="number" name="chain_length" min="1" max="16" value="{{chain_length}}">
                </div>
                <div class="matrix-field">
                    <label>Parallel</label>
                    <input type="number" name="parallel" min="1" max="16" value="{{parallel}}">
                </div>
                <div class="matrix-field">
                    <label>Refresh-Rate auf Matrix anzeigen</label>
                    <div class="setting-row" style="margin-bottom: 0;">
                        <label style="margin-bottom: 0; color: var(--text-secondary);">Aktivieren</label>
                        <label class="switch">
                            <input type="checkbox" name="show_refresh_rate" {{'checked' if show_refresh_rate else ''}}>
                            <span class="slider round"></span>
                        </label>
                    </div>
                </div>
            </div>
            
            <button type="submit" class="btn btn-blue">Einstellungen anwenden</button>
        </form>
    </div>

    <div class="card">
        <h3>Netzwerkeinstellungen</h3>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0; margin-bottom: 15px;">Verbinde die Matrix mit einem neuen WLAN-Netzwerk.</p>
        <form action="/system_wifi" method="POST">
            <label style="margin-bottom: 5px;">WLAN-Name (SSID)</label>
            <input type="text" name="ssid" placeholder="WLAN-Namen eingeben" required style="width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 6px; border: 1px solid #333; background: #121212; color: white; box-sizing: border-box; font-size: 1rem;">
            
            <label style="margin-bottom: 5px;">WLAN-Passwort</label>
            <input type="text" name="password" placeholder="Leer lassen bei offenem Netzwerk" style="width: 100%; padding: 12px; margin-bottom: 20px; border-radius: 6px; border: 1px solid #333; background: #121212; color: white; box-sizing: border-box; font-size: 1rem;">
            
            <button type="submit" class="btn btn-green" style="margin-top: 0;">WLAN speichern & neu starten</button>
        </form>
    </div>

    <div class="card">
        <h3>Systemverwaltung</h3>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0; margin-bottom: 5px;">Updates und Stromversorgung verwalten.</p>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0; margin-bottom: 15px;">Version: <span style="color: var(--spotify-green);">{{version}}</span></p>
        <p class="matrix-readout">Aktuelle Refresh-Rate: <span style="color: var(--spotify-green);">{{limit_refresh_rate_hz}} Hz</span></p>
        <div style="display: flex; gap: 10px; flex-direction: column;">
            <button type="button" id="checkUpdateBtn" class="btn btn-blue" style="margin-top: 5px;" onclick="checkUpdates()">Auf Updates prüfen</button>
            <form id="updateForm" action="/system_update" method="POST" style="display: none;"></form>
            
            <div style="display: flex; gap: 10px; margin-top: 10px;">
                <form action="/system_power" method="POST" style="flex: 1;">
                    <button type="submit" name="command" value="reboot" class="btn btn-red" style="margin-top: 0;">Neustart</button>
                </form>
                <form action="/system_power" method="POST" style="flex: 1;">
                    <button type="submit" name="command" value="shutdown" class="btn btn-red" style="margin-top: 0;">Herunterfahren</button>
                </form>
            </div>
        </div>
    </div>
    </div>
    
    <!-- Custom Modal UI -->
    <div id="customModal" class="modal-overlay">
        <div class="modal">
            <h3 id="modalTitle" style="margin-bottom: 10px; font-size: 1.3rem;">Titel</h3>
            <p id="modalMessage" style="color: var(--text-secondary); font-size: 0.95rem;">Nachrichtentext erscheint hier.</p>
            <div class="modal-actions">
                <button id="modalCancel" class="btn btn-red" onclick="hideModal()">Abbrechen</button>
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
    var hasToken = {{ 'true' if has_token else 'false' }};

    if (hasToken) {
        setInterval(fetchNowPlaying, 1000);
        fetchNowPlaying();
    }

    function formatMs(ms) {
        var totalSec = Math.max(0, Math.floor((ms || 0) / 1000));
        var min = Math.floor(totalSec / 60);
        var sec = totalSec % 60;
        return min + ':' + (sec < 10 ? '0' + sec : sec);
    }

    function fetchNowPlaying() {
        fetch('/api/now_playing')
        .then(res => res.json())
        .then(data => {
            if (data.is_playing) {
                document.getElementById('np-title').innerText = data.track_name;
                document.getElementById('np-artist').innerText = data.artist_name;
                if (data.album_art) document.getElementById('np-img').src = data.album_art;
                
                document.getElementById('icon-play').style.display = 'none';
                document.getElementById('icon-pause').style.display = 'inline-block';

                var duration = data.duration_ms || 0;
                var progress = data.progress_ms || 0;
                var pct = duration > 0 ? Math.min(100, (progress / duration) * 100) : 0;
                document.getElementById('np-progress-fill').style.width = pct + '%';
                document.getElementById('np-progress-time').innerText = formatMs(progress) + ' / ' + formatMs(duration);
            } else {
                document.getElementById('np-title').innerText = "Pausiert";
                document.getElementById('np-artist').innerText = "Matrix wartet auf Musik...";
                document.getElementById('icon-play').style.display = 'inline-block';
                document.getElementById('icon-pause').style.display = 'none';
                document.getElementById('np-progress-fill').style.width = '0%';
                document.getElementById('np-progress-time').innerText = '0:00 / 0:00';
            }
        })
        .catch(err => console.log('Fehler beim Abrufen von "Jetzt läuft"', err));
    }

    function playbackCommand(cmd) {
        var btn = document.getElementById('np-playpause');
        btn.style.opacity = '0.5';

        if (cmd === 'play_pause') {
            var playVisible = document.getElementById('icon-play').style.display !== 'none';
            document.getElementById('icon-play').style.display = playVisible ? 'none' : 'inline-block';
            document.getElementById('icon-pause').style.display = playVisible ? 'inline-block' : 'none';
        }
        
        fetch('/api/playback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'command=' + cmd
        })
        .then(() => {
            btn.style.opacity = '1';
            setTimeout(fetchNowPlaying, 150);
        })
        .catch(err => {
            btn.style.opacity = '1';
            console.error('Fehler beim Abspielen-Befehl', err);
        });
    }

    function checkUpdates() {
        var btn = document.getElementById('checkUpdateBtn');
        var originalText = "Auf Updates prüfen";
        btn.innerHTML = 'Prüfe... <div class="spinner"></div>';
        btn.disabled = true;
        
        // Fast client-side check directly against GitHub API
        fetch('https://api.github.com/repos/jonasradke/spotify-matrix-mvp/commits/main')
        .then(res => {
            if (!res.ok) throw new Error('Abruf von GitHub fehlgeschlagen');
            return res.json();
        })
        .then(data => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            
            var remoteHash = data.sha;
            if (!localHash || localHash === "") {
                showModal("Update-Fehler", "Version konnte nicht geprüft werden. Lokaler Status unbekannt.", false, null);
            } else if (remoteHash && !remoteHash.startsWith(localHash)) {
                showModal("Update verfügbar", "Es sind Updates verfügbar! Möchtest du sie jetzt installieren und die Matrix neu starten?", true, function() {
                    btn.innerHTML = 'Update & Neustart... <div class="spinner"></div>';
                    btn.disabled = true;
                    btn.classList.remove('btn-blue');
                    btn.classList.add('btn-green');
                    document.getElementById('updateForm').submit();
                });
            } else {
                btn.innerHTML = 'Aktuell ✓';
                btn.disabled = true;
                setTimeout(() => { 
                    btn.innerHTML = originalText; 
                    btn.disabled = false; 
                }, 3000);
            }
        })
        .catch(err => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            showModal("Netzwerkfehler", "GitHub konnte nicht erreicht werden, um nach Updates zu suchen.", false, null);
        });
    }

        if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                        navigator.serviceWorker.register('/sw.js').catch(function(err) {
                                console.warn('Service worker registration failed:', err);
                        });
                });
        }
    </script>
</body>
</html>
"""

MANIFEST_CONTENT = """
{
    "name": "Spotify Matrix",
    "short_name": "Matrix",
    "description": "Weboberfläche für Spotify Matrix",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#121212",
    "theme_color": "#121212",
    "icons": [
        {
            "src": "/icon.svg",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable"
        }
    ]
}
"""

SERVICE_WORKER_CONTENT = """
const CACHE_NAME = 'spotify-matrix-pwa-v1';
const APP_SHELL = [
    '/',
    '/manifest.webmanifest',
    '/icon.svg'
];

const STATIC_ASSETS = new Set(APP_SHELL.concat(['/sw.js']));

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
        ))
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') {
        return;
    }

    const requestUrl = new URL(event.request.url);

    if (requestUrl.origin !== self.location.origin) {
        return;
    }

    if (requestUrl.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put('/', responseClone));
                    return response;
                })
                .catch(() => caches.match('/')
                    .then(response => response || caches.match('/icon.svg')))
        );
        return;
    }

    if (!STATIC_ASSETS.has(requestUrl.pathname)) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) {
                return cached;
            }
            return fetch(event.request).then(response => {
                if (response && response.ok) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
                }
                return response;
            });
        })
    );
});
"""

ICON_SVG_CONTENT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-labelledby="title desc">
    <title>Spotify Matrix</title>
    <desc>Green matrix grid inspired icon for the Spotify Matrix web app</desc>
    <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f0f0f"/>
            <stop offset="100%" stop-color="#1b1b1b"/>
        </linearGradient>
        <linearGradient id="green" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#1ED760"/>
            <stop offset="100%" stop-color="#1DB954"/>
        </linearGradient>
    </defs>
    <rect width="512" height="512" rx="112" fill="url(#bg)"/>
    <g fill="url(#green)">
        <rect x="108" y="108" width="56" height="56" rx="14"/>
        <rect x="176" y="108" width="56" height="56" rx="14" opacity="0.92"/>
        <rect x="244" y="108" width="56" height="56" rx="14" opacity="0.84"/>
        <rect x="312" y="108" width="56" height="56" rx="14" opacity="0.76"/>
        <rect x="108" y="176" width="56" height="56" rx="14" opacity="0.92"/>
        <rect x="176" y="176" width="56" height="56" rx="14" opacity="0.86"/>
        <rect x="244" y="176" width="56" height="56" rx="14" opacity="0.78"/>
        <rect x="312" y="176" width="56" height="56" rx="14" opacity="0.7"/>
        <rect x="108" y="244" width="56" height="56" rx="14" opacity="0.84"/>
        <rect x="176" y="244" width="56" height="56" rx="14" opacity="0.78"/>
        <rect x="244" y="244" width="56" height="56" rx="14" opacity="0.7"/>
        <rect x="312" y="244" width="56" height="56" rx="14" opacity="0.62"/>
        <rect x="108" y="312" width="56" height="56" rx="14" opacity="0.76"/>
        <rect x="176" y="312" width="56" height="56" rx="14" opacity="0.7"/>
        <rect x="244" y="312" width="56" height="56" rx="14" opacity="0.62"/>
        <rect x="312" y="312" width="56" height="56" rx="14" opacity="0.54"/>
    </g>
    <circle cx="364" cy="148" r="28" fill="#ffffff" opacity="0.92"/>
    <path d="M352 148l18-10v20z" fill="#0f0f0f"/>
</svg>
"""

def start_web_server(app_state, sp_oauth):
    app = bottle.Bottle()
    spotify_client = {'instance': None}

    def get_spotify_client():
        from spotipy import Spotify
        if spotify_client['instance'] is None:
            spotify_client['instance'] = Spotify(auth_manager=sp_oauth)
        return spotify_client['instance']

    def get_current_version():
        try:
            git_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.git')
            head_path = os.path.join(git_dir, 'HEAD')
            with open(head_path, 'r') as f:
                head_content = f.read().strip()

            if head_content.startswith('ref: '):
                ref_path = os.path.join(git_dir, head_content[5:])
                with open(ref_path, 'r') as ref_file:
                    commit_hash = ref_file.read().strip()
            else:
                commit_hash = head_content

            return f"v1.0.{commit_hash[:7]}"
        except:
            return "Unbekannte Version"

    def get_current_hash():
        try:
            git_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.git')
            head_path = os.path.join(git_dir, 'HEAD')
            with open(head_path, 'r') as f:
                head_content = f.read().strip()

            if head_content.startswith('ref: '):
                ref_path = os.path.join(git_dir, head_content[5:])
                with open(ref_path, 'r') as ref_file:
                    return ref_file.read().strip()

            return head_content
        except:
            return ""

    @app.route('/manifest.webmanifest')
    def manifest():
        response.content_type = 'application/manifest+json'
        response.set_header('Cache-Control', 'public, max-age=3600')
        return MANIFEST_CONTENT

    @app.route('/sw.js')
    def service_worker():
        response.content_type = 'application/javascript; charset=utf-8'
        response.set_header('Cache-Control', 'no-cache'
        )
        return SERVICE_WORKER_CONTENT

    @app.route('/icon.svg')
    def icon_svg():
        response.content_type = 'image/svg+xml'
        response.set_header('Cache-Control', 'public, max-age=86400')
        return ICON_SVG_CONTENT

    @app.route('/')
    def index():
        has_token = bool(sp_oauth.get_cached_token())
        return template(HTML_TEMPLATE, 
                        has_token=has_token, 
                        brightness=app_state['brightness'], 
                        show_progress=app_state.get('show_progress', False),
                        progress_color=app_state.get('progress_color', '#1ED760'),
                        idle_mode=app_state.get('idle_mode', 'clock'),
                        idle_color=app_state.get('idle_color', '#1ED760'),
                        idle_block_start=app_state.get('idle_block_start', '00:00'),
                        idle_block_end=app_state.get('idle_block_end', '00:00'),
                        matrix_rows=app_state.get('matrix_rows', 64),
                        matrix_cols=app_state.get('matrix_cols', 64),
                        gpio_slowdown=app_state.get('gpio_slowdown', 1),
                        limit_refresh_rate_hz=app_state.get('limit_refresh_rate_hz', 165),
                        pwm_lsb_nanoseconds=app_state.get('pwm_lsb_nanoseconds', 75),
                        chain_length=app_state.get('chain_length', 1),
                        parallel=app_state.get('parallel', 1),
                        show_refresh_rate=app_state.get('show_refresh_rate', False),
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
        return "Fehler beim Erzeugen des Tokens."

    @app.route('/save_settings', method='POST')
    def save_settings():
        try:
            b = request.forms.get('brightness', type=int)
            p = request.forms.get('show_progress') == 'on'
            idle_mode = request.forms.get('idle_mode') or app_state.get('idle_mode', 'clock')
            if idle_mode not in ('off', 'clock', 'clock_date'):
                idle_mode = 'clock'
            idle_color = request.forms.get('idle_color') or app_state.get('idle_color', '#1ED760')
            idle_block_start = request.forms.get('idle_block_start') or app_state.get('idle_block_start', '00:00')
            idle_block_end = request.forms.get('idle_block_end') or app_state.get('idle_block_end', '00:00')
            matrix_rows = request.forms.get('matrix_rows', type=int) or app_state.get('matrix_rows', 64)
            matrix_cols = request.forms.get('matrix_cols', type=int) or app_state.get('matrix_cols', 64)
            gpio_slowdown = request.forms.get('gpio_slowdown', type=int) or app_state.get('gpio_slowdown', 1)
            limit_refresh_rate_hz = request.forms.get('limit_refresh_rate_hz', type=int) or app_state.get('limit_refresh_rate_hz', 165)
            pwm_lsb_nanoseconds = request.forms.get('pwm_lsb_nanoseconds', type=int) or app_state.get('pwm_lsb_nanoseconds', 75)
            chain_length = request.forms.get('chain_length', type=int) or app_state.get('chain_length', 1)
            parallel = request.forms.get('parallel', type=int) or app_state.get('parallel', 1)
            show_refresh_rate = request.forms.get('show_refresh_rate') == 'on'

            matrix_rows = max(1, matrix_rows)
            matrix_cols = max(1, matrix_cols)
            gpio_slowdown = max(0, gpio_slowdown)
            limit_refresh_rate_hz = max(1, limit_refresh_rate_hz)
            pwm_lsb_nanoseconds = max(0, pwm_lsb_nanoseconds)
            chain_length = max(1, chain_length)
            parallel = max(1, parallel)

            matrix_config_changed = any(app_state.get(key) != value for key, value in (
                ('matrix_rows', matrix_rows),
                ('matrix_cols', matrix_cols),
                ('gpio_slowdown', gpio_slowdown),
                ('limit_refresh_rate_hz', limit_refresh_rate_hz),
                ('pwm_lsb_nanoseconds', pwm_lsb_nanoseconds),
                ('chain_length', chain_length),
                ('parallel', parallel),
                ('show_refresh_rate', show_refresh_rate),
            ))
            
            if request.forms.get('action') == 'reset_color':
                c = '#1ED760'
                app_state['progress_color'] = c
            else:
                c = request.forms.get('progress_color')
                if c:
                    app_state['progress_color'] = c

            if b is None:
                b = app_state.get('brightness', 100)

            app_state['brightness'] = b
            app_state['show_progress'] = p
            app_state['idle_mode'] = idle_mode
            app_state['idle_color'] = idle_color
            app_state['idle_block_start'] = idle_block_start
            app_state['idle_block_end'] = idle_block_end
            app_state['matrix_rows'] = matrix_rows
            app_state['matrix_cols'] = matrix_cols
            app_state['gpio_slowdown'] = gpio_slowdown
            app_state['limit_refresh_rate_hz'] = limit_refresh_rate_hz
            app_state['pwm_lsb_nanoseconds'] = pwm_lsb_nanoseconds
            app_state['chain_length'] = chain_length
            app_state['parallel'] = parallel
            app_state['show_refresh_rate'] = show_refresh_rate

            # Save settings persistently to a JSON file
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
            with open(settings_path, 'w') as f:
                json.dump({
                    'brightness': b,
                    'show_progress': p,
                    'progress_color': app_state.get('progress_color', '#1ED760'),
                    'idle_mode': idle_mode,
                    'idle_color': idle_color,
                    'idle_block_start': idle_block_start,
                    'idle_block_end': idle_block_end,
                    'matrix_rows': matrix_rows,
                    'matrix_cols': matrix_cols,
                    'gpio_slowdown': gpio_slowdown,
                    'limit_refresh_rate_hz': limit_refresh_rate_hz,
                    'pwm_lsb_nanoseconds': pwm_lsb_nanoseconds,
                    'chain_length': chain_length,
                    'parallel': parallel,
                    'show_refresh_rate': show_refresh_rate
                }, f)

            if matrix_config_changed:
                app_state['restart'] = True
        except Exception as e:
            return f"Fehler beim Speichern der Einstellungen: {str(e)}"
        redirect('/')

    @app.route('/logout')
    def logout():
        if os.path.exists(".cache"):
            os.remove(".cache")
        app_state['reload_spotify'] = True
        redirect('/')

    @app.route('/system_wifi', method='POST')
    def system_wifi():
        import subprocess
        ssid = request.forms.get('ssid')
        password = request.forms.get('password')
        
        if ssid:
            # WPA_Supplicant template for DietPi/Debian
            if password:
                wpa_block = f'\\nnetwork={{\\n    ssid="{ssid}"\\n    psk="{password}"\\n    key_mgmt=WPA-PSK\\n}}\\n'
            else:
                wpa_block = f'\\nnetwork={{\\n    ssid="{ssid}"\\n    key_mgmt=NONE\\n}}\\n'
            try:
                # Write to the end of wpa_supplicant.conf
                cmd = f"echo '{wpa_block}' | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null"
                subprocess.check_call(cmd, shell=True)

                # We also trigger a system reboot so it connects properly
                subprocess.Popen(['sudo', 'reboot'])
                msg = "WLAN erfolgreich gespeichert!<br><br>Die Matrix startet neu, um die Verbindung herzustellen."
            except Exception as e:
                msg = f"Fehler beim Speichern von WLAN: {e}"
        else:
            msg = "Fehler: SSID darf nicht leer sein."

        return f"""
        <html>
        <head>
            <style>
                body {{ background-color:#121212; color:white; font-family:sans-serif; text-align:center; padding:50px; }}
                p {{ color:#b3b3b3; line-height: 1.5; }}
            </style>
            <meta http-equiv="refresh" content="20;url=/" />
        </head>
        <body>
            <h2>Netzwerkkonfiguration</h2>
            <p>{msg}</p>
            <p>Wenn die Verbindung erfolgreich ist, verschwindet dieser Hotspot.<br>Bitte verbinde dich wieder mit deinem normalen WLAN.</p>
        </body>
        </html>
        """

    @app.route('/system_power', method='POST')
    def system_power():
        import subprocess
        command = request.forms.get('command')
        if command == 'reboot':
            subprocess.Popen(['sudo', 'reboot'])
            msg = "Gerät wird neu gestartet..."
        elif command == 'shutdown':
            subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
            msg = "Gerät wird heruntergefahren... Du kannst den Strom in 15 Sekunden sicher trennen."
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

            result = subprocess.run(
                ['git', 'pull'],
                env=env,
                cwd=cwd_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                error_output = (result.stderr or result.stdout or 'Unknown error').strip()
                error_output = error_output[-1200:]
                return f"""
                <html>
                <head>
                    <style>
                        body {{ background-color:#121212; color:white; font-family:sans-serif; text-align:center; padding:40px; }}
                        p {{ color:#b3b3b3; line-height: 1.5; }}
                        pre {{ text-align: left; margin: 20px auto 0 auto; max-width: 720px; white-space: pre-wrap; word-break: break-word; background:#181818; border:1px solid #333; border-radius:8px; padding:12px; color:#ff8080; }}
                        a {{ color:#1DB954; }}
                    </style>
                </head>
                <body>
                    <h2>Update fehlgeschlagen</h2>
                    <p>Die Matrix konnte das neueste Update nicht laden. Bitte behebe das Git-Problem und versuche es erneut.</p>
                    <pre>{error_output}</pre>
                    <p><a href=\"/\">Zurück zu den Einstellungen</a></p>
                </body>
                </html>
                """
        except Exception as e:
            print(f"Error pulling updates: {e}")
            return f"""
            <html>
            <head>
                <style>
                    body {{ background-color:#121212; color:white; font-family:sans-serif; text-align:center; padding:40px; }}
                    p {{ color:#b3b3b3; line-height: 1.5; }}
                    a {{ color:#1DB954; }}
                </style>
            </head>
            <body>
                <h2>Update fehlgeschlagen</h2>
                <p>Beim Prüfen auf Updates ist ein unerwarteter Fehler aufgetreten.</p>
                <p>{str(e)}</p>
                <p><a href=\"/\">Zurück zu den Einstellungen</a></p>
            </body>
            </html>
            """
        
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
            <h2>Update & Neustart...</h2>
            <div class="spinner"></div>
            <p style="margin-top: 30px;">Die Matrix lädt neuen Code herunter und startet neu.</p>
            <p>Diese Seite aktualisiert sich in 15 Sekunden automatisch.</p>
        </body>
        </html>
        """

    @app.route('/api/now_playing', method='GET')
    def api_now_playing():
        return {
            'is_playing': app_state.get('is_playing', False),
            'track_name': app_state.get('track_name', ''),
            'artist_name': app_state.get('artist_name', ''),
            'album_art': app_state.get('album_art', ''),
            'progress_ms': app_state.get('progress_ms', 0),
            'duration_ms': app_state.get('duration_ms', 0)
        }

    @app.route('/api/playback', method='POST')
    def api_playback():
        command = request.forms.get('command')
        if not sp_oauth.get_cached_token():
            return {'status': 'error', 'message': 'Nicht angemeldet'}
        
        try:
            sp = get_spotify_client()
            
            if command == 'play_pause':
                playback = sp.current_playback()
                if playback and playback.get('is_playing'):
                    sp.pause_playback()
                    app_state['is_playing'] = False
                else:
                    sp.start_playback()
                    app_state['is_playing'] = True
            elif command == 'next':
                sp.next_track()
            elif command == 'previous':
                sp.previous_track()
                
            return {'status': 'success'}
        except Exception as e:
            print("Spotify API Error during playback control:", str(e))
            return {'status': 'error', 'message': str(e)}

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
                target = 'https://matrix.local' + self.path
                self.send_response(301)
                self.send_header('Location', target)
                self.end_headers()

            def do_POST(self):
                self.do_GET()

            def log_message(self, format, *args):
                return

        HTTPServer(('0.0.0.0', 80), RedirectHandler).serve_forever()

    # Start HTTPS web interface in the background
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Redirect plain HTTP to HTTPS so browsers never get a connection refused on port 80
    http_thread = threading.Thread(target=run_http_redirect_server, daemon=True)
    http_thread.start()