// Secret competitor-analysis page. Self-contained — depends on no other script.
// Fetches the lean /api/inspect endpoint and renders the competitor dashboard.

const inputEl = document.getElementById("channel-input");
const buttonEl = document.getElementById("inspect-btn");
const statusEl = document.getElementById("status-text");
const resultsEl = document.getElementById("results");
const saveChannelBtn = document.getElementById("save-channel-btn");
const saveStatusEl = document.getElementById("save-status");
const savedChannelsListEl = document.getElementById("saved-channels-list");
const savedPaginationEl = document.getElementById("saved-pagination");
const savedPrevBtn = document.getElementById("saved-prev");
const savedNextBtn = document.getElementById("saved-next");
const savedPageInfoEl = document.getElementById("saved-page-info");

let latestPayload = null;
let savedChannels = [];
let savedPage = 0;
const SAVED_PER_PAGE = 6;

// --- Formatting helpers (kept local so this page stays isolated from app.js) ---
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
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function trimText(text, max = 220) {
  if (!text) return "";
  return text.length <= max ? text : `${text.slice(0, max)}…`;
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b14f45" : "#6a7076";
}

function makeStat(label, value, badgeClass) {
  const wrap = document.createElement("div");
  wrap.className = "stat";
  const span = document.createElement("span");
  span.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;
  if (badgeClass) strong.classList.add("badge", badgeClass);
  wrap.appendChild(span);
  wrap.appendChild(strong);
  return wrap;
}

function clear(el) {
  el.innerHTML = "";
}

// --- Section renderers --------------------------------------------------------
function renderOverview(channel, profile) {
  document.getElementById("channel-name").textContent = channel.name || "Unknown channel";
  const meta = [
    channel.customUrl ? `@${channel.customUrl.replace("@", "")}` : null,
    channel.country || null,
    profile.ageText && profile.ageText !== "-" ? `Age ${profile.ageText}` : null,
    channel.publishedAt ? `Started ${formatDate(channel.publishedAt)}` : null,
  ].filter(Boolean).join(" • ");
  document.getElementById("channel-meta").textContent = meta;
  document.getElementById("channel-description").textContent =
    channel.description || "No description.";

  const stats = channel.statistics || {};
  const grid = document.getElementById("channel-stats");
  clear(grid);
  grid.appendChild(makeStat("Subscribers", formatNumber(stats.subscriberCount)));
  grid.appendChild(makeStat("Total Views", formatNumber(stats.viewCount)));
  grid.appendChild(makeStat("Total Videos", formatNumber(stats.videoCount)));
  grid.appendChild(makeStat("Avg Views / Video", formatNumber(profile.avgViewsLifetime)));
  const badge = { engaged: "badge-good", average: "badge-warn", low: "badge-bad" }[
    profile.viewsToSubLabel
  ];
  grid.appendChild(makeStat("Views-to-Sub Ratio", `${profile.viewsToSubRatio}%`, badge));

  const tagsEl = document.getElementById("channel-tags");
  clear(tagsEl);
  const topicTags = (channel.topics || []).map((t) => {
    const slug = t.split("/").pop() || t;
    return `Topic: ${slug.replace(/_/g, " ")}`;
  });
  const tags = [...(channel.keywords || []), ...topicTags];
  if (!tags.length) tags.push("No keywords");
  tags.forEach((tag) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag;
    tagsEl.appendChild(span);
  });
}

function renderCadence(cadence) {
  const grid = document.getElementById("cadence-stats");
  clear(grid);
  grid.appendChild(makeStat("Avg Days Between", `${cadence.avgDaysBetween} d`));
  grid.appendChild(makeStat("Consistency", cadence.consistencyLabel));
  grid.appendChild(makeStat("Peak Day", cadence.peakDayLabel));

  const bars = document.getElementById("peak-hours");
  clear(bars);
  const hours = cadence.peakHoursKST || [];
  if (!hours.length) {
    bars.innerHTML = '<span class="muted">No data.</span>';
    return;
  }
  const max = Math.max(...hours.map((h) => h.count));
  hours.forEach((h) => {
    const row = document.createElement("div");
    row.className = "mini-bar";
    const label = document.createElement("span");
    label.className = "mini-bar__label";
    label.textContent = `${String(h.hour).padStart(2, "0")}:00`;
    const track = document.createElement("div");
    track.className = "mini-bar__track";
    const fill = document.createElement("div");
    fill.className = "mini-bar__fill";
    fill.style.width = `${max ? (h.count / max) * 100 : 0}%`;
    const count = document.createElement("span");
    count.className = "mini-bar__count";
    count.textContent = `${h.count}`;
    track.appendChild(fill);
    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(count);
    bars.appendChild(row);
  });
}

function renderFormat(fmt) {
  const ratio = document.getElementById("format-ratio");
  clear(ratio);
  // Ratio is over classified videos only (0-duration live/premiere excluded).
  const shortCount = fmt.shortsCount || 0;
  const longCount = fmt.longformCount || 0;
  const classified = shortCount + longCount;
  const shortPct = classified ? (shortCount / classified) * 100 : 0;
  const longPct = classified ? (longCount / classified) * 100 : 0;
  [
    { cls: "ratio-bar__fill--short", pct: shortPct, label: `Shorts ${shortPct.toFixed(0)}%` },
    { cls: "ratio-bar__fill--long", pct: longPct, label: `Long ${longPct.toFixed(0)}%` },
  ].forEach((seg) => {
    if (seg.pct <= 0) return;
    const div = document.createElement("div");
    div.className = `ratio-bar__fill ${seg.cls}`;
    div.style.width = `${seg.pct}%`;
    div.textContent = seg.label;
    ratio.appendChild(div);
  });
  if (!classified) ratio.innerHTML = '<span class="muted">No classified videos.</span>';

  const grid = document.getElementById("format-stats");
  clear(grid);
  grid.appendChild(makeStat("Avg Duration (long)", `${fmt.avgDurationMin} min`));
  const trend = fmt.durationTrendMin || 0;
  const trendText = trend > 0 ? `↑ +${trend} min` : trend < 0 ? `↓ ${trend} min` : "→ flat";
  grid.appendChild(makeStat("Duration Trend", trendText));
  grid.appendChild(makeStat("Avg Title Length", `${fmt.avgTitleLength} chars`));
  grid.appendChild(makeStat("Listicle Ratio", `${fmt.listicleRatio}%`));

  const chips = document.getElementById("title-formulas");
  clear(chips);
  const labels = { howTo: "How-to", why: "Why", listicle: "Listicle", numberStart: "Number-led" };
  Object.entries(fmt.titleFormulas || {}).forEach(([key, count]) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = `${labels[key] || key}: ${count}`;
    chips.appendChild(chip);
  });
}

function renderVideoList(container, videos, emptyText) {
  clear(container);
  if (!videos || !videos.length) {
    container.innerHTML = `<span class="muted">${emptyText}</span>`;
    return;
  }
  videos.forEach((v) => {
    const row = document.createElement("div");
    row.className = "video-row";
    const title = document.createElement("span");
    title.className = "video-row__title";
    title.textContent = v.title || "Untitled";
    const views = document.createElement("span");
    views.className = "video-row__views";
    views.textContent = `${formatNumber(v.views)} views`;
    row.appendChild(title);
    row.appendChild(views);
    if (v.url) {
      const link = document.createElement("a");
      link.href = v.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.className = "video-row__link";
      link.textContent = "Open";
      row.appendChild(link);
    }
    container.appendChild(row);
  });
}

function renderEngagement(eng) {
  const grid = document.getElementById("engagement-stats");
  clear(grid);
  grid.appendChild(makeStat("Avg Views (latest 10)", formatNumber(eng.avgViewsLatest)));
  grid.appendChild(makeStat("Avg Views (top 10)", formatNumber(eng.avgViewsTop)));
  grid.appendChild(makeStat("Like Rate", `${eng.likeRate}%`));
  grid.appendChild(makeStat("Comment Rate", `${eng.commentRate}%`));
  grid.appendChild(makeStat("Engagement Rate", `${eng.engagementRate}%`));
  renderVideoList(
    document.getElementById("breakout-list"),
    eng.breakoutVideos,
    "No breakout videos in the sample."
  );
  renderVideoList(
    document.getElementById("underperform-list"),
    eng.underperformVideos,
    "No underperforming videos."
  );
}

function renderSeo(seo) {
  const cloud = document.getElementById("tag-cloud");
  clear(cloud);
  const tags = seo.topTags || [];
  if (!tags.length) {
    cloud.innerHTML = '<span class="muted">No tags found.</span>';
  } else {
    const max = Math.max(...tags.map((t) => t.count));
    tags.forEach((t) => {
      const span = document.createElement("span");
      span.className = "tag-cloud__item";
      const size = 0.8 + (max ? (t.count / max) * 0.9 : 0);
      span.style.fontSize = `${size.toFixed(2)}rem`;
      span.textContent = t.tag;
      span.title = `${t.count} videos`;
      cloud.appendChild(span);
    });
  }

  const grid = document.getElementById("seo-stats");
  clear(grid);
  grid.appendChild(makeStat("Avg Tags / Video", seo.avgTagsPerVideo));
  grid.appendChild(makeStat("Sponsor Rate", `${seo.sponsorRate}%`));
  grid.appendChild(makeStat("Paid Placements", formatNumber(seo.paidPlacementCount)));

  const streams = document.getElementById("revenue-streams");
  clear(streams);
  const labels = {
    merch: "Merch", course: "Course", discord: "Discord",
    newsletter: "Newsletter", membership: "Membership", affiliate: "Affiliate",
  };
  Object.entries(seo.revenueStreams || {}).forEach(([key, active]) => {
    const chip = document.createElement("span");
    chip.className = `revenue-badge ${active ? "is-active" : ""}`;
    chip.textContent = labels[key] || key;
    streams.appendChild(chip);
  });
}

function normalizeList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value === "string") {
    return value.split(/\n|\r|•|-/).map((v) => v.trim()).filter(Boolean);
  }
  return [];
}

function renderAnalysisList(container, items) {
  clear(container);
  const list = items && items.length ? items : ["No insights available."];
  list.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    container.appendChild(li);
  });
}

// Structured 5-dimension thumbnail design breakdown.
function renderThumbDesign(design) {
  const grid = document.getElementById("analysis-thumb-design");
  clear(grid);
  const labels = {
    characters: "Characters / Subjects",
    colorPalette: "Color Palette",
    artStyle: "Art Style",
    typography: "Typography",
    branding: "Logo / Branding",
  };
  const d = design || {};
  if (!Object.keys(labels).some((k) => d[k])) {
    grid.innerHTML = '<span class="muted">No thumbnail design data.</span>';
    return;
  }
  Object.keys(labels).forEach((key) => {
    const row = document.createElement("div");
    row.className = "detail-item";
    const label = document.createElement("span");
    label.textContent = labels[key];
    const text = document.createElement("p");
    text.textContent = d[key] || "-";
    row.appendChild(label);
    row.appendChild(text);
    grid.appendChild(row);
  });
}

function renderChips(container, items) {
  clear(container);
  if (!items || !items.length) {
    container.innerHTML = '<span class="muted">None.</span>';
    return;
  }
  items.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = item;
    container.appendChild(chip);
  });
}

function renderAnalysis(analysis) {
  const card = document.getElementById("analysis-card");
  const statusNode = document.getElementById("analysis-status");
  const caveats = document.getElementById("analysis-caveats");
  const titleFormula = document.getElementById("analysis-title-formula");
  const thumbFormula = document.getElementById("analysis-thumb-formula");
  const strategyEl = document.getElementById("analysis-strategy");
  const recTagsEl = document.getElementById("analysis-rec-tags");
  if (!analysis) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  if (analysis.enabled === false) {
    statusNode.textContent = "Analysis unavailable";
    statusNode.style.color = "#b14f45";
    caveats.textContent = analysis.error || analysis.reason || "";
    renderAnalysisList(document.getElementById("analysis-titles"), []);
    renderAnalysisList(document.getElementById("analysis-thumbnails"), []);
    titleFormula.textContent = "-";
    thumbFormula.textContent = "-";
    renderThumbDesign({});
    renderAnalysisList(strategyEl, []);
    renderChips(recTagsEl, []);
    return;
  }
  statusNode.textContent = "Generated by Vertex AI";
  statusNode.style.color = "#6a7076";
  renderAnalysisList(document.getElementById("analysis-titles"), normalizeList(analysis.titleTrends));
  renderAnalysisList(
    document.getElementById("analysis-thumbnails"),
    normalizeList(analysis.thumbnailTrends)
  );
  titleFormula.textContent = analysis.titleFormula || "-";
  thumbFormula.textContent = analysis.thumbnailFormula || "-";
  renderThumbDesign(analysis.thumbnailDesign);
  renderAnalysisList(strategyEl, normalizeList(analysis.strategyTips));
  renderChips(recTagsEl, normalizeList(analysis.recommendedTags));
  caveats.textContent = trimText(analysis.caveats || analysis.raw || "", 400);
}

// --- Orchestration -----------------------------------------------------------
function renderPayload(payload) {
  const channel = payload.channel || {};
  const metrics = payload.competitorAnalysis || {};
  renderOverview(channel, metrics.profile || {});
  renderCadence(metrics.cadence || {});
  renderFormat(metrics.format || {});
  renderEngagement(metrics.engagement || {});
  renderSeo(metrics.seo || {});
  renderAnalysis(payload.analysis);
  resultsEl.classList.remove("hidden");
}

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
    const response = await fetch(`/api/inspect?lean=1&url=${encodeURIComponent(url)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Failed to fetch data.");

    latestPayload = payload;
    renderPayload(payload);
    saveChannelBtn.disabled = false;
    saveStatusEl.classList.add("hidden");
    setStatus("Done.");
  } catch (err) {
    setStatus(err.message || "Something went wrong.", true);
  } finally {
    buttonEl.disabled = false;
  }
}

// --- Save & saved channels ---------------------------------------------------
async function saveChannel() {
  if (!latestPayload || !latestPayload.channel) return;
  try {
    const response = await fetch("/api/channels/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(latestPayload),
    });
    if (!response.ok) throw new Error("save failed");
    saveStatusEl.textContent = "Saved!";
    saveStatusEl.classList.remove("hidden");
    setTimeout(() => saveStatusEl.classList.add("hidden"), 2000);
  } catch (err) {
    setStatus("Failed to save channel.", true);
  }
}

function viewSavedChannel(payload) {
  if (!payload) return;
  latestPayload = payload;
  renderPayload(payload);
  saveChannelBtn.disabled = false;
  saveStatusEl.classList.add("hidden");
  window.scrollTo({ top: resultsEl.offsetTop - 20, behavior: "smooth" });
}

function buildSavedItem(channel) {
  const item = document.createElement("div");
  item.className = "saved-channel-item";

  const info = document.createElement("div");
  info.className = "saved-channel-info";
  const name = document.createElement("h4");
  name.textContent = channel.name || "Unknown";
  const meta = document.createElement("p");
  const handle = channel.custom_url ? `@${channel.custom_url.replace("@", "")}` : "";
  const subs = channel.subscriber_count ? `${formatNumber(channel.subscriber_count)} subs` : "";
  meta.textContent = [handle, subs].filter(Boolean).join(" • ");
  info.appendChild(name);
  info.appendChild(meta);

  const actions = document.createElement("div");
  actions.className = "saved-channel-actions";
  const viewBtn = document.createElement("button");
  viewBtn.className = "saved-channel-view";
  viewBtn.textContent = "View Stats";
  viewBtn.addEventListener("click", () => viewSavedChannel(channel.full_payload));
  const delBtn = document.createElement("button");
  delBtn.className = "saved-channel-delete";
  delBtn.textContent = "Delete";
  delBtn.addEventListener("click", () => deleteSavedChannel(channel.channel_id));
  actions.appendChild(viewBtn);
  actions.appendChild(delBtn);

  item.appendChild(info);
  item.appendChild(actions);
  return item;
}

// Render the current page of saved channels; paginate to avoid breaking layout.
function renderSavedPage() {
  savedChannelsListEl.innerHTML = "";
  if (!savedChannels.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No saved channels yet.";
    savedChannelsListEl.appendChild(p);
    savedPaginationEl.classList.add("hidden");
    return;
  }
  const totalPages = Math.ceil(savedChannels.length / SAVED_PER_PAGE);
  savedPage = Math.min(Math.max(savedPage, 0), totalPages - 1);
  const start = savedPage * SAVED_PER_PAGE;
  savedChannels
    .slice(start, start + SAVED_PER_PAGE)
    .forEach((channel) => savedChannelsListEl.appendChild(buildSavedItem(channel)));

  if (totalPages > 1) {
    savedPaginationEl.classList.remove("hidden");
    savedPageInfoEl.textContent = `Page ${savedPage + 1} / ${totalPages}`;
    savedPrevBtn.disabled = savedPage === 0;
    savedNextBtn.disabled = savedPage >= totalPages - 1;
  } else {
    savedPaginationEl.classList.add("hidden");
  }
}

async function loadSavedChannels() {
  try {
    const response = await fetch("/api/channels/saved");
    savedChannels = await response.json();
    savedPage = 0;
    renderSavedPage();
  } catch (err) {
    savedChannels = [];
    savedChannelsListEl.innerHTML = '<p class="muted">Failed to load saved channels.</p>';
    savedPaginationEl.classList.add("hidden");
  }
}

async function deleteSavedChannel(channelId) {
  try {
    const response = await fetch(`/api/channels/saved/${channelId}`, { method: "DELETE" });
    if (!response.ok) throw new Error("delete failed");
    loadSavedChannels();
  } catch (err) {
    setStatus("Failed to delete channel.", true);
  }
}

function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.tab === target));
      document.querySelectorAll(".tab-content").forEach((panel) => {
        panel.classList.toggle("hidden", panel.dataset.tab !== target);
      });
      if (target === "saved") loadSavedChannels();
    });
  });
}

// --- Event wiring ------------------------------------------------------------
buttonEl.addEventListener("click", inspectChannel);
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") inspectChannel();
});
saveChannelBtn.addEventListener("click", saveChannel);
savedPrevBtn.addEventListener("click", () => {
  savedPage -= 1;
  renderSavedPage();
});
savedNextBtn.addEventListener("click", () => {
  savedPage += 1;
  renderSavedPage();
});
initTabs();
