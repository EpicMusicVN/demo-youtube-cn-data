// Comment fetcher page. Self-contained — fetches /api/comments and renders the
// thread into a fixed-height scrollable box with a copy-to-clipboard action.

const inputEl = document.getElementById("video-input");
const fetchBtn = document.getElementById("fetch-btn");
const countSelect = document.getElementById("count-select");
const orderSelect = document.getElementById("order-select");
const statusEl = document.getElementById("status-text");
const resultsEl = document.getElementById("results");
const commentBox = document.getElementById("comment-box");
const commentCountEl = document.getElementById("comment-count");
const copyBtn = document.getElementById("copy-btn");

let lastResult = null;

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b14f45" : "#6a7076";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function formatLikes(n) {
  const num = Number(n) || 0;
  return num === 1 ? "1 like" : `${num.toLocaleString()} likes`;
}

// --- Rendering ---------------------------------------------------------------
function buildMeta(comment) {
  const meta = document.createElement("span");
  meta.className = "comment-meta";
  const parts = [formatLikes(comment.likes)];
  const date = formatDate(comment.publishedAt);
  if (date) parts.push(date);
  meta.textContent = parts.join(" · ");
  return meta;
}

function buildComment(comment, index) {
  const item = document.createElement("div");
  item.className = "comment-item";

  const head = document.createElement("div");
  head.className = "comment-head";
  const author = document.createElement("span");
  author.className = "comment-author";
  author.textContent = `${index}. ${comment.author || "Unknown"}`;
  head.appendChild(author);
  head.appendChild(buildMeta(comment));

  const text = document.createElement("p");
  text.className = "comment-text";
  text.textContent = comment.text || "";

  item.appendChild(head);
  item.appendChild(text);

  (comment.replies || []).forEach((reply) => {
    const replyEl = document.createElement("div");
    replyEl.className = "comment-reply";
    const rhead = document.createElement("div");
    rhead.className = "comment-head";
    const rauthor = document.createElement("span");
    rauthor.className = "comment-author";
    rauthor.textContent = `↳ ${reply.author || "Unknown"}`;
    rhead.appendChild(rauthor);
    rhead.appendChild(buildMeta(reply));
    const rtext = document.createElement("p");
    rtext.className = "comment-text";
    rtext.textContent = reply.text || "";
    replyEl.appendChild(rhead);
    replyEl.appendChild(rtext);
    item.appendChild(replyEl);
  });

  const hidden = (comment.replyCount || 0) - (comment.replies || []).length;
  if (hidden > 0) {
    const note = document.createElement("p");
    note.className = "comment-reply-note";
    note.textContent = `+ ${hidden} more ${hidden === 1 ? "reply" : "replies"}`;
    item.appendChild(note);
  }
  return item;
}

function renderComments(result) {
  commentBox.innerHTML = "";
  const comments = result.comments || [];
  const moreNote = result.truncated ? " · more available" : "";
  commentCountEl.textContent =
    `${comments.length} comments · video ${result.videoId}${moreNote}`;
  if (!comments.length) {
    commentBox.innerHTML = '<p class="muted">No comments found.</p>';
    return;
  }
  comments.forEach((comment, idx) => {
    commentBox.appendChild(buildComment(comment, idx + 1));
  });
}

// --- Clipboard ---------------------------------------------------------------
// Plain-text export — clean and structured for pasting into an AI prompt.
function buildPlainText(result) {
  const comments = result.comments || [];
  const header =
    `YouTube Comments — ${comments.length} comments — video ${result.videoId}` +
    (result.truncated ? " (more available, not all fetched)" : "");
  const lines = [header, ""];
  comments.forEach((comment, idx) => {
    const date = formatDate(comment.publishedAt);
    lines.push(
      `[${idx + 1}] ${comment.author || "Unknown"} · ${formatLikes(comment.likes)}` +
        (date ? ` · ${date}` : "")
    );
    lines.push(comment.text || "");
    (comment.replies || []).forEach((reply) => {
      lines.push(`   ↳ ${reply.author || "Unknown"} · ${formatLikes(reply.likes)}: ${reply.text || ""}`);
    });
    lines.push("");
  });
  return lines.join("\n");
}

async function copyToClipboard() {
  if (!lastResult) return;
  const text = buildPlainText(lastResult);
  try {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy to clipboard"), 2000);
  } catch (err) {
    // Fallback for browsers / contexts without the async clipboard API.
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.left = "-9999px";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand("copy");
      copyBtn.textContent = "Copied!";
      setTimeout(() => (copyBtn.textContent = "Copy to clipboard"), 2000);
    } catch (e) {
      setStatus("Could not copy — select the text manually.", true);
    }
    document.body.removeChild(area);
  }
}

// --- Orchestration -----------------------------------------------------------
async function fetchComments() {
  if (fetchBtn.disabled) return; // guard against repeated Enter while in-flight
  const url = inputEl.value.trim();
  if (!url) {
    setStatus("Please paste a video link.", true);
    return;
  }
  setStatus("Fetching comments…");
  fetchBtn.disabled = true;
  resultsEl.classList.add("hidden");
  try {
    const params = new URLSearchParams({
      url,
      max: countSelect.value,
      order: orderSelect.value,
    });
    const response = await fetch(`/api/comments?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Failed to fetch comments.");

    lastResult = payload;
    renderComments(payload);
    resultsEl.classList.remove("hidden");
    setStatus(`Done — ${payload.count} comments fetched.`);
  } catch (err) {
    setStatus(err.message || "Something went wrong.", true);
  } finally {
    fetchBtn.disabled = false;
  }
}

fetchBtn.addEventListener("click", fetchComments);
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") fetchComments();
});
copyBtn.addEventListener("click", copyToClipboard);
