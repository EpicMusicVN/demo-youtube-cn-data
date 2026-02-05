const inputEl = document.getElementById("channel-input");
const buttonEl = document.getElementById("inspect-btn");
const statusEl = document.getElementById("status-text");
const resultsEl = document.getElementById("results");

const channelNameEl = document.getElementById("channel-name");
const channelMetaEl = document.getElementById("channel-meta");
const channelDescriptionEl = document.getElementById("channel-description");
const channelStatsEl = document.getElementById("channel-stats");
const channelTagsEl = document.getElementById("channel-tags");
const quickMetricsEl = document.getElementById("quick-metrics");
const topVideosEl = document.getElementById("top-videos");
const latestVideosEl = document.getElementById("latest-videos");
const analysisCardEl = document.getElementById("analysis-card");
const analysisStatusEl = document.getElementById("analysis-status");
const analysisTitlesEl = document.getElementById("analysis-titles");
const analysisThumbsEl = document.getElementById("analysis-thumbnails");
const analysisTitleFormulaEl = document.getElementById("analysis-title-formula");
const analysisThumbFormulaEl = document.getElementById("analysis-thumb-formula");
const analysisCaveatsEl = document.getElementById("analysis-caveats");
const avgView5ValueEl = document.getElementById("avg-view-5-value");
const saveChannelBtn = document.getElementById("save-channel-btn");
const saveStatusEl = document.getElementById("save-status");
const savedChannelsListEl = document.getElementById("saved-channels-list");

let latestPayload = null;
let topData = { all: [], long: [], short: [] };
let latestData = { all: [], long: [], short: [] };

function formatNumber(value) {
  if (value === null || value === undefined) return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString();
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function trimText(text, max = 140) {
  if (!text) return "";
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function secondsToReadable(totalSeconds) {
  if (!totalSeconds && totalSeconds !== 0) return "-";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes || hours) parts.push(`${minutes}m`);
  parts.push(`${seconds}s`);
  return parts.join(" ");
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b14f45" : "#6a7076";
}

function makeStat(label, value) {
  const wrap = document.createElement("div");
  wrap.className = "stat";
  wrap.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
  return wrap;
}

function renderChannel(channel) {
  channelNameEl.textContent = channel.name || "Unknown channel";
  const meta = [
    channel.customUrl ? `@${channel.customUrl.replace("@", "")}` : null,
    channel.country || null,
    channel.publishedAt ? `Started ${formatDate(channel.publishedAt)}` : null,
  ]
    .filter(Boolean)
    .join(" • ");
  channelMetaEl.textContent = meta;
  channelDescriptionEl.textContent = channel.description || "No description.";

  channelStatsEl.innerHTML = "";
  const stats = channel.statistics || {};
  channelStatsEl.appendChild(makeStat("Subscribers", formatNumber(stats.subscriberCount)));
  channelStatsEl.appendChild(makeStat("Total Views", formatNumber(stats.viewCount)));
  channelStatsEl.appendChild(makeStat("Total Videos", formatNumber(stats.videoCount)));

  channelTagsEl.innerHTML = "";
  const keywords = channel.keywords || [];
  const topics = channel.topics || [];
  const topicTags = topics.map((t) => {
    const slug = t.split("/").pop() || t;
    return `Topic: ${slug.replace(/_/g, " ")}`;
  });
  const tags = [...keywords, ...topicTags];
  if (!tags.length) {
    const emptyTag = document.createElement("span");
    emptyTag.className = "tag";
    emptyTag.textContent = "No keywords";
    channelTagsEl.appendChild(emptyTag);
  } else {
    tags.forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = tag;
      channelTagsEl.appendChild(span);
    });
  }
}

function renderMetrics(latest, topViewed) {
  quickMetricsEl.innerHTML = "";
  const latestViews = latest.map((v) => Number(v.views || 0));
  const topViews = topViewed.map((v) => Number(v.views || 0));
  const latestLikes = latest.map((v) => Number(v.likes || 0));
  const likeRate = latestViews.length
    ? (latestLikes.reduce((a, b) => a + b, 0) / Math.max(latestViews.reduce((a, b) => a + b, 0), 1)) * 100
    : 0;

  const avgLatestViews = latestViews.length
    ? Math.round(latestViews.reduce((a, b) => a + b, 0) / latestViews.length)
    : 0;
  const avgTopViews = topViews.length
    ? Math.round(topViews.reduce((a, b) => a + b, 0) / topViews.length)
    : 0;

  quickMetricsEl.appendChild(makeStat("Avg Views (Latest)", formatNumber(avgLatestViews)));
  quickMetricsEl.appendChild(makeStat("Avg Views (Top)", formatNumber(avgTopViews)));
  quickMetricsEl.appendChild(makeStat("Like Rate (Latest)", `${likeRate.toFixed(2)}%`));
}

function renderAvgView5(latest) {
  const slice = latest.slice(0, 5);
  if (!slice.length) {
    avgView5ValueEl.textContent = "-";
    return;
  }
  const sum = slice.reduce((acc, v) => acc + Number(v.views || 0), 0);
  avgView5ValueEl.textContent = formatNumber(Math.round(sum / slice.length));
}

function renderVideos(container, videos) {
  container.innerHTML = "";
  if (!videos.length) {
    const empty = document.createElement("div");
    empty.className = "muted";
    empty.textContent = "No videos found.";
    container.appendChild(empty);
    return;
  }

  videos.forEach((video) => {
    const card = document.createElement("div");
    card.className = "video-card";

    const img = document.createElement("img");
    img.className = "video-thumb";
    img.src = video.thumbnail || "";
    img.alt = video.title || "Video thumbnail";

    const body = document.createElement("div");
    body.className = "video-body";

    const title = document.createElement("div");
    title.className = "video-title";
    title.textContent = video.title || "Untitled";

    const meta = document.createElement("div");
    meta.className = "video-meta";
    meta.textContent = `${formatNumber(video.views)} views • ${formatDate(video.publishedAt)} • ${secondsToReadable(video.durationSeconds)}`;

    const desc = document.createElement("div");
    desc.className = "video-desc";
    desc.textContent = trimText(video.description || "");

    const link = document.createElement("a");
    link.className = "video-link";
    link.href = video.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Open on YouTube";

    body.appendChild(title);
    body.appendChild(meta);
    body.appendChild(desc);
    body.appendChild(link);

    card.appendChild(img);
    card.appendChild(body);
    container.appendChild(card);
  });
}

function renderList(container, items) {
  container.innerHTML = "";
  if (!items || !items.length) {
    const li = document.createElement("li");
    li.textContent = "No insights available.";
    container.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    container.appendChild(li);
  });
}

function normalizeList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value === "string") {
    return value
      .split(/\\n|\\r|\\u2022|\\-/)
      .map((v) => v.trim())
      .filter(Boolean);
  }
  return [];
}

function renderAnalysis(analysis) {
  if (!analysis) {
    analysisCardEl.classList.add("hidden");
    return;
  }
  analysisCardEl.classList.remove("hidden");

  if (analysis.enabled === false) {
    analysisStatusEl.textContent = "Analysis unavailable";
    analysisStatusEl.style.color = "#b14f45";
    analysisCaveatsEl.textContent = analysis.error || analysis.reason || "";
    renderList(analysisTitlesEl, []);
    renderList(analysisThumbsEl, []);
    analysisTitleFormulaEl.textContent = "-";
    analysisThumbFormulaEl.textContent = "-";
    return;
  }

  analysisStatusEl.textContent = "Generated by Vertex AI";
  analysisStatusEl.style.color = "#6a7076";

  const titleTrends = normalizeList(analysis.titleTrends);
  const thumbTrends = normalizeList(analysis.thumbnailTrends);

  renderList(analysisTitlesEl, titleTrends);
  renderList(analysisThumbsEl, thumbTrends);

  analysisTitleFormulaEl.textContent = analysis.titleFormula || "-";
  analysisThumbFormulaEl.textContent = analysis.thumbnailFormula || "-";
  analysisCaveatsEl.textContent = analysis.caveats || analysis.raw || "";
}

function setActiveFilter(groupEl, filter) {
  const buttons = groupEl.querySelectorAll(".filter-btn");
  buttons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.filter === filter);
  });
}

function applyFilter(section, filter) {
  if (section === "top") {
    renderVideos(topVideosEl, topData[filter] || []);
  } else if (section === "latest") {
    renderVideos(latestVideosEl, latestData[filter] || []);
  }
}

function initFilters() {
  const groups = document.querySelectorAll(".filter-group");
  groups.forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest(".filter-btn");
      if (!button) return;
      const section = group.dataset.section;
      const filter = button.dataset.filter;
      setActiveFilter(group, filter);
      applyFilter(section, filter);
    });
  });
}

initFilters();

async function inspectChannel() {
  const url = inputEl.value.trim();
  if (!url) {
    setStatus("Please paste a channel link.", true);
    return;
  }

  setStatus("Fetching data…");
  buttonEl.disabled = true;
  saveChannelBtn.disabled = true;
  resultsEl.classList.add("hidden");

  try {
    const response = await fetch(`/api/inspect?url=${encodeURIComponent(url)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Failed to fetch data.");
    }

    latestPayload = payload;
    renderChannel(payload.channel || {});
    renderMetrics(payload.latest || [], payload.topViewed || []);
    renderAvgView5(payload.latest || []);
    topData = {
      all: payload.topViewed || [],
      long: payload.topViewedLong || [],
      short: payload.topViewedShort || [],
    };
    latestData = {
      all: payload.latest || [],
      long: payload.latestLong || [],
      short: payload.latestShort || [],
    };
    applyFilter("top", "all");
    applyFilter("latest", "all");
    renderAnalysis(payload.analysis);
    resultsEl.classList.remove("hidden");
    saveChannelBtn.disabled = false;
    saveStatusEl.classList.add("hidden");
    setStatus("Done.");
  } catch (err) {
    setStatus(err.message || "Something went wrong.", true);
  } finally {
    buttonEl.disabled = false;
  }
}

buttonEl.addEventListener("click", inspectChannel);
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    inspectChannel();
  }
});

function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.tab === target));
      document.querySelectorAll(".tab-content").forEach((panel) => {
        panel.classList.toggle("hidden", panel.dataset.tab !== target);
      });
      if (target === "saved") {
        loadSavedChannels();
      }
    });
  });
}

async function saveChannel() {
  if (!latestPayload || !latestPayload.channel) return;
  try {
    await fetch("/api/channels/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(latestPayload),
    });
    saveStatusEl.textContent = "Saved!";
    saveStatusEl.classList.remove("hidden");
    setTimeout(() => {
      saveStatusEl.classList.add("hidden");
    }, 2000);
  } catch (err) {
    setStatus("Failed to save channel.", true);
  }
}

async function loadSavedChannels() {
  try {
    const response = await fetch("/api/channels/saved");
    const channels = await response.json();
    renderSavedList(channels);
  } catch (err) {
    savedChannelsListEl.innerHTML = "";
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Failed to load saved channels.";
    savedChannelsListEl.appendChild(p);
  }
}

function renderSavedList(channels) {
  savedChannelsListEl.innerHTML = "";
  if (!channels || !channels.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No saved channels yet.";
    savedChannelsListEl.appendChild(p);
    return;
  }
  channels.forEach((ch) => {
    const item = document.createElement("div");
    item.className = "saved-channel-item";

    const info = document.createElement("div");
    info.className = "saved-channel-info";

    const name = document.createElement("h4");
    name.textContent = ch.name || "Unknown";
    info.appendChild(name);

    const meta = document.createElement("p");
    const handle = ch.custom_url ? `@${ch.custom_url.replace("@", "")}` : "";
    const subs = ch.subscriber_count ? `${formatNumber(ch.subscriber_count)} subs` : "";
    meta.textContent = [handle, subs].filter(Boolean).join(" • ");
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "saved-channel-actions";

    const viewBtn = document.createElement("button");
    viewBtn.className = "saved-channel-view";
    viewBtn.textContent = "View Stats";
    viewBtn.addEventListener("click", () => viewSavedChannel(ch.full_payload));
    actions.appendChild(viewBtn);

    const delBtn = document.createElement("button");
    delBtn.className = "saved-channel-delete";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => deleteSavedChannel(ch.channel_id));
    actions.appendChild(delBtn);

    item.appendChild(info);
    item.appendChild(actions);
    savedChannelsListEl.appendChild(item);
  });
}

async function deleteSavedChannel(channelId) {
  try {
    await fetch(`/api/channels/saved/${channelId}`, { method: "DELETE" });
    loadSavedChannels();
  } catch (err) {
    setStatus("Failed to delete channel.", true);
  }
}

function viewSavedChannel(payload) {
  if (!payload) return;
  latestPayload = payload;
  renderChannel(payload.channel || {});
  renderMetrics(payload.latest || [], payload.topViewed || []);
  renderAvgView5(payload.latest || []);
  topData = {
    all: payload.topViewed || [],
    long: payload.topViewedLong || [],
    short: payload.topViewedShort || [],
  };
  latestData = {
    all: payload.latest || [],
    long: payload.latestLong || [],
    short: payload.latestShort || [],
  };
  applyFilter("top", "all");
  applyFilter("latest", "all");
  renderAnalysis(payload.analysis);
  resultsEl.classList.remove("hidden");
  saveChannelBtn.disabled = false;
  saveStatusEl.classList.add("hidden");
}

saveChannelBtn.addEventListener("click", saveChannel);
initTabs();
