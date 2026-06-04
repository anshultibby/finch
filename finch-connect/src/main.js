const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;

const $ = (id) => document.getElementById(id);
let session = null; // { access_token, user_id, email }

function showResult(ok, title, detail) {
  const el = $("result");
  el.className = "result " + (ok ? "ok" : "err");
  el.innerHTML = `<b>${title}</b>${detail ? `<span>${detail}</span>` : ""}`;
  el.classList.remove("hidden");
}

function setStatus(msg) {
  $("progress").classList.remove("hidden");
  $("status").textContent = msg;
}

async function signIn() {
  $("result").classList.add("hidden");
  $("signin").disabled = true;
  setStatus("Starting sign-in…");
  try {
    session = await invoke("sign_in_finch");
    const sub = $("signin-sub");
    sub.textContent = `Signed in as ${session.email} ✓`;
    sub.classList.remove("hidden");
    $("signin").textContent = "Signed in ✓";
    $("connect-card").classList.remove("disabled");
    $("connect").disabled = false;
    $("status").textContent = "";
    $("progress").classList.add("hidden");
  } catch (err) {
    $("signin").disabled = false;
    const msg = String(err);
    showResult(
      false,
      "Sign-in failed",
      msg.includes("allow-list")
        ? "The desktop loopback URL isn't allow-listed in Supabase yet (see setup notes)."
        : msg
    );
  }
}

async function connect() {
  if (!session) return showResult(false, "Sign in to Finch first.");
  $("result").classList.add("hidden");
  $("connect").disabled = true;
  setStatus("Starting…");
  try {
    await invoke("connect_robinhood", {
      backendUrl: $("backend").value.trim(),
      finchToken: session.access_token,
      userId: session.user_id,
    });
    showResult(true, "Robinhood connected ✓", "Your agent can now trade in your Agentic account. You can close this app.");
  } catch (err) {
    const msg = String(err);
    showResult(
      false,
      "Connection failed",
      msg.includes("timed_out")
        ? "Timed out waiting for approval. Click Connect to try again."
        : msg
    );
  } finally {
    $("connect").disabled = false;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  $("signin").addEventListener("click", signIn);
  $("connect").addEventListener("click", connect);

  listen("progress", (e) => setStatus(e.payload.message));
  listen("authorize-url", (e) => {
    $("authurl").textContent = e.payload;
    $("urlbox").classList.remove("hidden");
  });
});
