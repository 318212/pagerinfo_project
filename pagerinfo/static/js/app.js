const VAPID_PUBLIC_KEY = "YOUR_VAPID_PUBLIC_KEY_HERE";

let currentSource = "";
let allPosts      = [];
let deferredInstallPrompt = null;

const feed          = document.getElementById("feed");
const loadingState  = document.getElementById("loadingState");
const emptyState    = document.getElementById("emptyState");
const statusText    = document.getElementById("statusText");
const lastScrape    = document.getElementById("lastScrape");
const unreadBadge   = document.getElementById("unreadBadge");
const sourceNav     = document.getElementById("sourceNav");
const installBanner = document.getElementById("installBanner");
const postTemplate  = document.getElementById("postTemplate");

function relativeTime(isoStr) {
  if (!isoStr) return "";
  const diff = (Date.now() - new Date(isoStr + "Z").getTime()) / 1000;
  if (diff < 60)   return "just now";
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  return `${Math.floor(diff/86400)}d ago`;
}

function urlB64ToUint8Array(b64) {
  const pad = "=".repeat((4 - b64.length % 4) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

async function loadPosts(source = "") {
  loadingState.hidden = false;
  emptyState.hidden   = true;

  feed.querySelectorAll(".post-card").forEach(el => el.remove());

  const params = new URLSearchParams({ limit: 80 });
  if (source) params.set("source", source);

  const res   = await fetch(`/api/posts?${params}`);
  const data  = await res.json();
  allPosts    = data.posts;

  loadingState.hidden = true;

  if (allPosts.length === 0) {
    emptyState.hidden = false;
    return;
  }

  allPosts.forEach(post => feed.appendChild(buildCard(post)));
  updateStatusBar();
}

function buildCard(post) {
  const tpl  = postTemplate.content.cloneNode(true);
  const card = tpl.querySelector(".post-card");

  card.dataset.id = post.id;
  if (post.read) card.classList.add("is-read");

  const authorEl = card.querySelector(".post-author");
  authorEl.textContent = post.author || "Unknown";
  if (!post.author || post.author === "Unknown") {
    authorEl.style.opacity = "0.35";
  }

  const displayTime = post.post_timestamp || relativeTime(post.scraped_at);
  card.querySelector(".post-time").textContent = displayTime;

  const tag = card.querySelector(".post-source-tag");
  tag.textContent  = post.source_label || "";
  tag.dataset.type = post.source_type  || "";

  card.querySelector(".post-body").textContent = post.text;

  card.querySelector(".read-btn").addEventListener("click", () => markRead(post.id, card));

  return card;
}

async function updateStatusBar() {
  const res  = await fetch("/api/stats");
  const data = await res.json();

  statusText.textContent = `${data.unread} unread · ${data.total} total`;
  lastScrape.textContent = data.last_scraped
    ? `last scraped ${relativeTime(data.last_scraped)}`
    : "not yet scraped";

  if (data.unread > 0) {
    unreadBadge.textContent = data.unread;
    unreadBadge.classList.add("visible");
  } else {
    unreadBadge.classList.remove("visible");
  }
}

async function loadSources() {
  const res   = await fetch("/api/sources");
  const data  = await res.json();
  const pills = sourceNav.querySelectorAll(".pill:not([data-source=''])");
  pills.forEach(p => p.remove());

  data.sources.forEach(src => {
    const btn = document.createElement("button");
    btn.className       = "pill";
    btn.dataset.source  = src.source_label;
    btn.textContent     = `${src.source_label} (${src.count})`;
    btn.addEventListener("click", () => filterBySource(src.source_label, btn));
    sourceNav.appendChild(btn);
  });
}

function filterBySource(source, clickedBtn) {
  currentSource = source;
  sourceNav.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
  clickedBtn.classList.add("active");
  loadPosts(source);
}

async function markRead(postId, cardEl) {
  await fetch(`/api/posts/${postId}/read`, { method: "POST" });
  cardEl.classList.add("is-read");
  updateStatusBar();
}

async function markAllRead() {
  await fetch("/api/posts/mark-all-read", { method: "POST" });
  feed.querySelectorAll(".post-card").forEach(c => c.classList.add("is-read"));
  updateStatusBar();
}

async function subscribeToPush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
  if (VAPID_PUBLIC_KEY === "YOUR_VAPID_PUBLIC_KEY_HERE") return; // not configured yet

  try {
    const reg  = await navigator.serviceWorker.ready;
    const sub  = await reg.pushManager.subscribe({
      userVisibleOnly:      true,
      applicationServerKey: urlB64ToUint8Array(VAPID_PUBLIC_KEY),
    });
    await fetch("/api/push/subscribe", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(sub),
    });
    console.log("✅ Push notifications subscribed");
  } catch (e) {
    console.warn("Push subscription failed:", e);
  }
}

async function registerSW() {
  if (!("serviceWorker" in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register("/sw.js");
    console.log("SW registered:", reg.scope);
    await subscribeToPush();
  } catch (e) {
    console.warn("SW registration failed:", e);
  }
}

window.addEventListener("beforeinstallprompt", e => {
  e.preventDefault();
  deferredInstallPrompt = e;
  installBanner.hidden  = false;
});

document.getElementById("installBtn").addEventListener("click", async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  const { outcome } = await deferredInstallPrompt.userChoice;
  deferredInstallPrompt  = null;
  installBanner.hidden   = true;
});

document.getElementById("installDismiss").addEventListener("click", () => {
  installBanner.hidden = true;
});

document.getElementById("refreshBtn").addEventListener("click", () => {
  loadPosts(currentSource);
  loadSources();
});

document.getElementById("markAllBtn").addEventListener("click", markAllRead);

document.getElementById("filterBtn").addEventListener("click", () => {
  sourceNav.hidden = !sourceNav.hidden;
});

sourceNav.querySelector('[data-source=""]').addEventListener("click", function() {
  currentSource = "";
  sourceNav.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
  this.classList.add("active");
  loadPosts("");
});

setInterval(() => {
  loadPosts(currentSource);
  updateStatusBar();
}, 5 * 60 * 1000);

(async () => {
  await registerSW();
  await loadSources();
  await loadPosts();
})();