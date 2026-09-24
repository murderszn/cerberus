/* Account connections for the hosted Worker and browser-only Pollinations login. */
(function () {
    'use strict';
    var HOSTED_ORIGIN = 'https://cerberus-github-auth.jjohnso75.workers.dev';
    var POLLINATIONS_AUTH = 'https://enter.pollinations.ai';
    var POLLINATIONS_API = 'https://gen.pollinations.ai';
    var CLIENT_ID = 'pk_mKBcJlqmSkTExVm4'; // Public Cerberus BYOP app identifier.
    var KEY = 'cerberus:ai-key-v5';
    var AUTH = 'cerberus:pollinations-auth';
    var hosted = location.origin === HOSTED_ORIGIN;
    var $ = function (id) { return document.getElementById(id); };
    var githubUser = null;
    var loginTimer = null;
    function status(id, message) { if ($(id)) $(id).textContent = message; }
    function readKey() { try { return sessionStorage.getItem(KEY) || ''; } catch (e) { return ''; } }
    function saveKey(value, approved) {
        try {
            if (value) sessionStorage.setItem(KEY, value);
            else sessionStorage.removeItem(KEY);
            if (approved) sessionStorage.setItem(AUTH, '1');
            else sessionStorage.removeItem(AUTH);
        } catch (e) { /* private browsing may block storage */ }
        updatePollinations();
    }
    function updatePollinations() {
        var connected = !!readKey();
        var ollama = $('ai-provider').value === 'ollama';
        $('pollinations-login-btn').hidden = ollama || connected;
        $('pollinations-logout-btn').hidden = ollama || !connected;
        if (connected) status('pollinations-status', 'Connected for this tab. Report findings are sent only when you generate a brief.');
    }
    function updateGithub() {
        $('github-login-btn').hidden = !!githubUser;
        $('github-logout-btn').hidden = !githubUser;
        $('github-app-panel').hidden = !githubUser;
        if (githubUser) status('github-status', 'Signed in as ' + githubUser.login + '.');
    }
    function githubRequest(path, options) {
        return fetch('/auth/github/' + path, Object.assign({credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}}, options || {})).then(function (response) {
            if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json')) throw new Error('GitHub sign-in is unavailable.');
            return response.json();
        });
    }
    function openHostedGithub() { window.open(HOSTED_ORIGIN + '/auth/github/start', '_blank', 'noopener,noreferrer'); }
    $('github-login-btn').addEventListener('click', function () {
        if (hosted) location.assign('/auth/github/start');
        else openHostedGithub();
    });
    $('github-logout-btn').addEventListener('click', function () {
        if (!hosted) return;
        var button = this;
        button.disabled = true;
        githubRequest('logout', {method:'POST',headers:{Accept:'application/json','X-Cerberus-CSRF':'1'}}).then(function () {
            githubUser = null; updateGithub(); status('github-status', 'Signed out of Cerberus.');
        }).catch(function (error) { status('github-status', error.message); }).finally(function () { button.disabled = false; });
    });
    $('github-install-btn').addEventListener('click', function () {
        if (!hosted) { openHostedGithub(); return; }
        var button = this;
        button.disabled = true;
        fetch('/github/install/start', {method:'POST',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json','X-Cerberus-CSRF':'1'}}).then(function (response) {
            return response.json().then(function (data) { if (!response.ok || !data.url) throw new Error(data.error || 'GitHub installation unavailable.'); return data; });
        }).then(function (data) { location.assign(data.url); }).catch(function (error) {
            status('github-app-status', error.message); button.disabled = false;
        });
    });
    if (hosted) {
        githubRequest('session').then(function (data) {
            githubUser = data.user || null;
            var params = new URL(location.href).searchParams;
            var callback = params.get('github_auth');
            var install = params.get('github_install');
            updateGithub();
            if (!githubUser) status('github-status', callback === 'denied' ? 'GitHub sign-in was cancelled.' : callback === 'failed' ? 'Sign-in failed. A verified primary GitHub email is required.' : 'Sign in to your Cerberus account with GitHub.');
            if (install) status('github-app-status', install === 'connected' ? 'Repository access connected.' : 'Repository installation was not completed.');
            if (callback || install) { var clean = new URL(location.href); clean.searchParams.delete('github_auth'); clean.searchParams.delete('github_install'); history.replaceState(null, '', clean.href); }
        }).catch(function () { status('github-status', 'GitHub sign-in is unavailable right now. Token scans still work.'); });
    } else {
        $('github-login-btn').textContent = 'Open hosted sign-in ↗';
        status('github-status', 'Account sign-in runs on the hosted agent. Use a token here for local private scans.');
    }

    function startPollinationsLogin() {
        var button = $('pollinations-login-btn');
        button.disabled = true;
        var popup = null;
        try { popup = window.open('about:blank', 'cerberus-pollinations-login'); } catch (e) { /* popup blocked */ }
        status('pollinations-status', 'Starting Pollinations sign-in…');
        fetch(POLLINATIONS_AUTH + '/api/device/code', {method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({client_id:CLIENT_ID})}).then(function (response) {
            return response.json().then(function (data) { if (!response.ok) throw new Error(data.error || 'Device sign-in unavailable.'); return data; });
        }).then(function (device) {
            if (!device.device_code || !device.user_code) throw new Error('Pollinations returned an incomplete sign-in response.');
            var verify = device.verification_uri || POLLINATIONS_AUTH + '/device';
            if (verify.charAt(0) === '/') verify = POLLINATIONS_AUTH + verify;
            if (!verify.startsWith(POLLINATIONS_AUTH + '/')) throw new Error('Unexpected Pollinations approval URL.');
            if (popup && !popup.closed) popup.location.href = verify;
            else window.open(verify, '_blank', 'noopener,noreferrer');
            var interval = Math.max(2000, Number(device.interval || 5) * 1000);
            var deadline = Date.now() + Math.min(600000, Number(device.expires_in || 600) * 1000);
            status('pollinations-status', 'Enter code ' + device.user_code + ' on the Pollinations approval page. Waiting for approval…');
            function poll() {
                if (Date.now() > deadline) { button.disabled = false; status('pollinations-status', 'Sign-in expired. Try connecting again.'); return; }
                fetch(POLLINATIONS_AUTH + '/api/device/token', {method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({device_code:device.device_code})}).then(function (response) {
                    return response.json().then(function (data) { return {data:data,status:response.status}; });
                }).then(function (result) {
                    var data = result.data || {};
                    if (data.access_token) { saveKey(data.access_token, true); button.disabled = false; return; }
                    if (data.error === 'authorization_pending') { loginTimer = setTimeout(poll, interval); return; }
                    if (data.error === 'slow_down') { loginTimer = setTimeout(poll, Math.max(interval, Number(data.retry_after || 10) * 1000)); return; }
                    throw new Error(data.error || 'Pollinations sign-in was not completed.');
                }).catch(function (error) { button.disabled = false; status('pollinations-status', 'Sign-in failed: ' + error.message); });
            }
            loginTimer = setTimeout(poll, interval);
        }).catch(function (error) {
            if (popup && !popup.closed) popup.close();
            button.disabled = false; status('pollinations-status', 'Sign-in failed: ' + error.message);
        });
    }
    $('pollinations-login-btn').addEventListener('click', startPollinationsLogin);
    $('pollinations-logout-btn').addEventListener('click', function () {
        if (loginTimer) clearTimeout(loginTimer);
        saveKey('', false); $('pollinations-key').value = '';
        status('pollinations-status', 'Disconnected from Pollinations in this tab.');
    });
    $('pollinations-save-btn').addEventListener('click', function () {
        var key = $('pollinations-key').value.trim();
        if (!key) { status('pollinations-status', 'Enter an API key first.'); return; }
        saveKey(key, false); $('pollinations-key').value = '';
        status('pollinations-status', 'API key ready for this tab. Use Test connection to verify it.');
    });
    $('pollinations-model').addEventListener('change', function () {
        try { localStorage.setItem('cerberus:pollinations-model', this.value); } catch (e) { /* ignore */ }
    });
    try { $('pollinations-model').value = localStorage.getItem('cerberus:pollinations-model') || 'gpt-5.6-sol'; } catch (e) { /* ignore */ }
    function testPollinations() {
        var key = readKey();
        if (!key) { status('pollinations-status', 'Connect Pollinations or enter an API key first.'); return; }
        status('pollinations-status', 'Checking Pollinations access…');
        fetch(POLLINATIONS_API + '/v1/models', {headers:{Authorization:'Bearer ' + key,Accept:'application/json'}}).then(function (response) {
            if (response.status === 401) throw new Error('The saved key was rejected. Reconnect or use another key.');
            if (!response.ok) throw new Error('Pollinations returned HTTP ' + response.status);
            status('pollinations-status', 'Connected. Ready to generate a report.');
        }).catch(function (error) { status('pollinations-status', error.message); });
    }
    function syncProvider() {
        var ollama = $('ai-provider').value === 'ollama';
        $('pollinations-settings').hidden = ollama;
        $('ollama-settings').hidden = !ollama;
        $('pollinations-login-btn').hidden = ollama || !!readKey();
        $('pollinations-logout-btn').hidden = ollama || !readKey();
        $('ai-test-btn').textContent = ollama ? 'Test Ollama' : 'Test Pollinations';
    }
    $('ai-provider').addEventListener('change', syncProvider);
    updateGithub(); updatePollinations(); syncProvider();
    window.CerberusConnections = {
        pollinations: function () { return {key:readKey(),model:$('pollinations-model').value}; },
        startPollinationsLogin:startPollinationsLogin,
        testPollinations:testPollinations
    };
})();
