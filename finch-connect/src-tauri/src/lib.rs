//! Finch Connect — on-device sign-in + Robinhood Agentic OAuth.
//!
//! TWO loopback OAuth flows, both run entirely on YOUR machine:
//!
//!   A) Sign in to Finch (Google via Supabase):
//!      open Supabase/Google consent in your browser → catch the code on a local
//!      127.0.0.1 listener → exchange it for a Finch session. No password typed here.
//!
//!   B) Connect Robinhood (agent OAuth):
//!      register Robinhood's agent client → PKCE → open robinhood.com consent in your
//!      browser → catch the one-time code on the same local listener → hand it to YOUR
//!      Finch backend, which exchanges + stores the tokens server-side.
//!
//! No secrets are ever written to disk. Every server contacted is a named constant
//! below — there are no hidden network calls.

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use rand::RngCore;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, Manager};

// --- Finch's Supabase project (anon key is a public, publishable key) ----------
const SUPABASE_URL: &str = "https://iokwxwcvxhfqgiglfdbi.supabase.co";
const SUPABASE_ANON_KEY: &str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlva3d4d2N2eGhmcWdpZ2xmZGJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE1MjAzMDIsImV4cCI6MjA3NzA5NjMwMn0.XEGry8Koo_pzjGcsKYiK1VqXRmnpDLnMqLhKRNaENzw";

// --- Robinhood agent OAuth (the only Robinhood servers we touch) ----------------
const RH_REGISTER_URL: &str = "https://agent.robinhood.com/oauth/trading/register";
const RH_AUTHORIZE_URL: &str = "https://robinhood.com/oauth";
const RH_RESOURCE: &str = "https://agent.robinhood.com/mcp/trading"; // RFC 8707 resource indicator
const RH_SCOPE: &str = "internal";

// --- Shared loopback (RFC 8252) -------------------------------------------------
const LOOPBACK_PORT: u16 = 8765;
const FINCH_REDIRECT: &str = "http://127.0.0.1:8765/finch-callback";
const RH_REDIRECT: &str = "http://127.0.0.1:8765/robinhood-callback";
const CONSENT_TIMEOUT: Duration = Duration::from_secs(180);

/// Branded page shown in the user's browser after they approve, so the redirect
/// doesn't dump a blank/raw screen. Matches Finch's look (DM Sans, emerald, logo).
const DONE_PAGE: &str = r##"<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  html,body{height:100%;margin:0}
  body{font-family:'DM Sans',-apple-system,system-ui,sans-serif;color:#111827;
    display:flex;align-items:center;justify-content:center;
    background:radial-gradient(900px 460px at 50% -10%,#d1fae5 0%,rgba(209,250,229,0) 60%),linear-gradient(180deg,#f0fdf9 0%,#fff 45%)}
  .card{background:#fff;border:1px solid #e8eaed;border-radius:22px;padding:40px 44px;text-align:center;
    box-shadow:0 12px 40px rgba(16,24,40,.10);max-width:380px}
  .logo{filter:drop-shadow(0 6px 14px rgba(16,185,129,.35));border-radius:11px}
  .check{width:52px;height:52px;border-radius:50%;background:#ecfdf5;display:flex;align-items:center;
    justify-content:center;margin:18px auto 14px}
  h1{font-size:21px;font-weight:700;letter-spacing:-.5px;margin:0 0 6px}
  p{color:#6b7280;font-size:14.5px;margin:0}
</style></head>
<body><div class="card">
  <svg class="logo" width="44" height="44" viewBox="0 0 36 36" fill="none">
    <rect width="36" height="36" rx="9" fill="#10b981"/>
    <rect x="8" y="8" width="5" height="20" rx="1.5" fill="#fff"/>
    <rect x="15" y="8" width="5" height="12" rx="1.5" fill="#fff"/>
    <rect x="22" y="14" width="5" height="6" rx="1.5" fill="#fff"/>
  </svg>
  <div class="check">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
  </div>
  <h1>You're approved</h1>
  <p>Return to <b>Finch Connect</b> — you can close this tab.</p>
</div></body></html>"##;

#[derive(Clone, Serialize)]
struct Progress {
    event: String,
    message: String,
}

fn emit(app: &AppHandle, event: &str, message: &str) {
    let _ = app.emit(
        "progress",
        Progress { event: event.to_string(), message: message.to_string() },
    );
}

#[derive(Clone, Serialize)]
struct FinchSession {
    access_token: String,
    user_id: String,
    email: String,
}

fn b64url(bytes: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(bytes)
}

/// PKCE (RFC 7636) S256: returns (verifier, challenge).
fn make_pkce() -> (String, String) {
    let mut raw = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut raw);
    let verifier = b64url(&raw);
    let challenge = b64url(&Sha256::digest(verifier.as_bytes()));
    (verifier, challenge)
}

fn random_state() -> String {
    let mut raw = [0u8; 12];
    rand::thread_rng().fill_bytes(&mut raw);
    b64url(&raw)
}

/// Minimal percent-encoding for values we embed in URLs (no extra deps).
fn urlencode(s: &str) -> String {
    let mut out = String::with_capacity(s.len() * 3);
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{:02X}", b)),
        }
    }
    out
}

fn open_in_browser(url: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    let (cmd, args): (&str, Vec<&str>) = ("open", vec![url]);
    #[cfg(target_os = "windows")]
    let (cmd, args): (&str, Vec<&str>) = ("cmd", vec!["/C", "start", "", url]);
    #[cfg(target_os = "linux")]
    let (cmd, args): (&str, Vec<&str>) = ("xdg-open", vec![url]);
    std::process::Command::new(cmd)
        .args(args)
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("couldn't open browser: {e}"))
}

/// Block until the browser redirects to our loopback, then return the parsed query
/// params. Responds to the browser with a friendly confirmation page either way.
fn wait_for_redirect(listener: TcpListener) -> Result<HashMap<String, String>, String> {
    listener.set_nonblocking(true).map_err(|e| e.to_string())?;
    let deadline = Instant::now() + CONSENT_TIMEOUT;
    loop {
        if Instant::now() > deadline {
            return Err("timed_out".into());
        }
        match listener.accept() {
            Ok((mut stream, _)) => {
                let mut buf = [0u8; 8192];
                let n = stream.read(&mut buf).unwrap_or(0);
                let req = String::from_utf8_lossy(&buf[..n]);
                let first_line = req.lines().next().unwrap_or("");
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n{}",
                    DONE_PAGE
                );
                let _ = stream.write_all(resp.as_bytes());
                let query = first_line
                    .split_whitespace()
                    .nth(1)
                    .and_then(|p| p.split_once('?').map(|(_, q)| q.to_string()))
                    .unwrap_or_default();
                let mut params = HashMap::new();
                for pair in query.split('&') {
                    if let Some((k, v)) = pair.split_once('=') {
                        params.insert(k.to_string(), v.to_string());
                    }
                }
                if let Some(err) = params.get("error") {
                    return Err(format!("provider returned error: {err}"));
                }
                return Ok(params);
            }
            Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(200));
            }
            Err(e) => return Err(format!("loopback accept failed: {e}")),
        }
    }
}

// ============================ A) Sign in to Finch ==============================

fn run_sign_in(app: AppHandle) -> Result<FinchSession, String> {
    let (verifier, challenge) = make_pkce();

    let listener = TcpListener::bind(("127.0.0.1", LOOPBACK_PORT))
        .map_err(|e| format!("couldn't open local listener on {LOOPBACK_PORT}: {e}"))?;

    // Supabase OAuth (PKCE) → Google. Redirect comes back to our loopback as ?code=.
    let authorize = format!(
        "{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={redirect}\
         &code_challenge={challenge}&code_challenge_method=s256",
        redirect = urlencode(FINCH_REDIRECT),
    );

    emit(&app, "finch", "Opening Google sign-in in your browser…");
    open_in_browser(&authorize)?;

    emit(&app, "finch", "Waiting for you to sign in…");
    let params = wait_for_redirect(listener)?;
    let code = params
        .get("code")
        .ok_or("sign-in redirect had no code (is the loopback URL allow-listed in Supabase?)")?;

    emit(&app, "finch", "Completing sign-in…");
    let resp = reqwest::blocking::Client::new()
        .post(format!("{SUPABASE_URL}/auth/v1/token?grant_type=pkce"))
        .header("apikey", SUPABASE_ANON_KEY)
        .json(&serde_json::json!({ "auth_code": code, "code_verifier": verifier }))
        .send()
        .map_err(|e| format!("token exchange failed: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("Finch sign-in failed: {}", resp.text().unwrap_or_default()));
    }
    let json: serde_json::Value = resp.json().map_err(|e| e.to_string())?;
    let access_token = json["access_token"].as_str().unwrap_or("").to_string();
    let user_id = json["user"]["id"].as_str().unwrap_or("").to_string();
    let email = json["user"]["email"].as_str().unwrap_or("").to_string();
    if access_token.is_empty() || user_id.is_empty() {
        return Err("sign-in succeeded but no session was returned".into());
    }
    emit(&app, "finch", &format!("Signed in as {email}"));
    Ok(FinchSession { access_token, user_id, email })
}

// ========================== B) Connect Robinhood ===============================

fn register_rh_client() -> Result<String, String> {
    let body = serde_json::json!({
        "client_name": "Finch Connect",
        "redirect_uris": [RH_REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    });
    let json: serde_json::Value = reqwest::blocking::Client::new()
        .post(RH_REGISTER_URL)
        .json(&body)
        .send()
        .map_err(|e| format!("registration failed: {e}"))?
        .json()
        .map_err(|e| format!("registration response not JSON: {e}"))?;
    json["client_id"]
        .as_str()
        .map(|s| s.to_string())
        .ok_or_else(|| "registration returned no client_id".into())
}

fn handoff_to_finch(
    backend_url: &str,
    finch_token: &str,
    user_id: &str,
    code: &str,
    verifier: &str,
    client_id: &str,
) -> Result<(), String> {
    let url = format!("{}/robinhood/native/exchange", backend_url.trim_end_matches('/'));
    let resp = reqwest::blocking::Client::new()
        .post(&url)
        .bearer_auth(finch_token)
        .json(&serde_json::json!({
            "user_id": user_id,
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "redirect_uri": RH_REDIRECT,
        }))
        .send()
        .map_err(|e| format!("couldn't reach Finch backend: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!(
            "Finch backend rejected the connection ({}): {}",
            resp.status(),
            resp.text().unwrap_or_default()
        ));
    }
    Ok(())
}

fn run_connect(
    app: AppHandle,
    backend_url: String,
    finch_token: String,
    user_id: String,
) -> Result<String, String> {
    emit(&app, "rh", "Registering with Robinhood…");
    let client_id = register_rh_client()?;
    let (verifier, challenge) = make_pkce();
    let state = random_state();

    let listener = TcpListener::bind(("127.0.0.1", LOOPBACK_PORT))
        .map_err(|e| format!("couldn't open local listener on {LOOPBACK_PORT}: {e}"))?;

    let authorize_url = format!(
        "{RH_AUTHORIZE_URL}?response_type=code&client_id={client_id}&redirect_uri={redirect}\
         &code_challenge={challenge}&code_challenge_method=S256&scope={RH_SCOPE}&state={state}&resource={resource}",
        redirect = urlencode(RH_REDIRECT),
        resource = urlencode(RH_RESOURCE),
    );

    emit(&app, "rh", "Opening Robinhood — log in and approve there.");
    let _ = app.emit("authorize-url", &authorize_url);
    open_in_browser(&authorize_url)?;

    emit(&app, "rh", "Waiting for you to approve on robinhood.com…");
    let params = wait_for_redirect(listener)?;
    if params.get("state").map(String::as_str) != Some(state.as_str()) {
        return Err("state mismatch — aborting for safety".into());
    }
    let code = params.get("code").ok_or("redirect arrived without an auth code")?;

    emit(&app, "rh", "Linking the connection to your Finch account…");
    handoff_to_finch(&backend_url, &finch_token, &user_id, code, &verifier, &client_id)?;

    emit(&app, "rh", "Connected ✓");
    Ok("connected".into())
}

// ================================ commands =====================================

#[tauri::command]
async fn sign_in_finch(app: AppHandle) -> Result<FinchSession, String> {
    tauri::async_runtime::spawn_blocking(move || run_sign_in(app))
        .await
        .map_err(|e| format!("internal error: {e}"))?
}

#[tauri::command]
async fn connect_robinhood(
    app: AppHandle,
    backend_url: String,
    finch_token: String,
    user_id: String,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        run_connect(app, backend_url, finch_token, user_id)
    })
    .await
    .map_err(|e| format!("internal error: {e}"))?
}

/// Is this user's Robinhood already connected? Lets the UI reflect a prior connect.
#[tauri::command]
async fn check_robinhood(backend_url: String, finch_token: String, user_id: String) -> Result<bool, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let url = format!("{}/robinhood/status/{}", backend_url.trim_end_matches('/'), user_id);
        let resp = reqwest::blocking::Client::new()
            .get(&url)
            .bearer_auth(&finch_token)
            .send()
            .map_err(|e| format!("status check failed: {e}"))?;
        let json: serde_json::Value = resp.json().map_err(|e| e.to_string())?;
        Ok(json.get("is_connected").and_then(|v| v.as_bool()).unwrap_or(false))
    })
    .await
    .map_err(|e| format!("internal error: {e}"))?
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_deep_link::init())
        .setup(|app| {
            // A finch-connect:// link (from the Finch web app) just brings this app
            // to the front — no auth data is passed through the URL.
            use tauri_plugin_deep_link::DeepLinkExt;
            let handle = app.handle().clone();
            app.deep_link().on_open_url(move |_event| {
                if let Some(win) = handle.get_webview_window("main") {
                    let _ = win.unminimize();
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![sign_in_finch, connect_robinhood, check_robinhood])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
