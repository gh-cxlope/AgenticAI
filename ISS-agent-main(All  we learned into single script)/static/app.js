const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const statusEl = document.querySelector("#connectionStatus");
const traceLink = document.querySelector("#traceLink");
const sessionId = crypto.randomUUID();

function setStatus(text) {
  statusEl.innerHTML = `<span class="pulse"></span>${text}`;
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(role, text = "") {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "◇" : "★";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  article.append(avatar, bubble);
  messages.append(article);
  scrollToBottom();
  return bubble;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function markdownLinksToHtml(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, (_match, label, url) => {
    const safeUrl = url.replaceAll("&amp;", "&");
    return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${label}</a>`;
  });
}

function extractMapCoordinates(text) {
  const osmMatch = text.match(/openstreetmap\.org\/\?mlat=(-?\d+(?:\.\d+)?)&amp;mlon=(-?\d+(?:\.\d+)?)/i)
    || text.match(/openstreetmap\.org\/\?mlat=(-?\d+(?:\.\d+)?)&mlon=(-?\d+(?:\.\d+)?)/i);
  if (osmMatch) return { lat: Number(osmMatch[1]), lon: Number(osmMatch[2]) };

  const googleMatch = text.match(/google\.com\/maps\?q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/i);
  if (googleMatch) return { lat: Number(googleMatch[1]), lon: Number(googleMatch[2]) };

  const plainMatch = text.match(/latitude[^-\d]*(-?\d+(?:\.\d+)?)[\s\S]{0,80}longitude[^-\d]*(-?\d+(?:\.\d+)?)/i);
  if (plainMatch) return { lat: Number(plainMatch[1]), lon: Number(plainMatch[2]) };

  return null;
}

function mapEmbedHtml(coords) {
  const lat = Math.max(-90, Math.min(90, coords.lat));
  const lon = Math.max(-180, Math.min(180, coords.lon));
  const delta = 8;
  const bbox = [
    Math.max(-180, lon - delta),
    Math.max(-90, lat - delta),
    Math.min(180, lon + delta),
    Math.min(90, lat + delta),
  ].join(",");
  const embedUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lon}`;
  const openUrl = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=4/${lat}/${lon}`;

  return `
    <div class="map-card">
      <div class="map-card-header">
        <span>ISS map view</span>
        <a href="${openUrl}" target="_blank" rel="noreferrer">Open map</a>
      </div>
      <iframe title="Map showing the requested location" src="${embedUrl}" loading="lazy"></iframe>
    </div>
  `;
}

function renderRichAgentBubble(bubble) {
  const rawText = bubble.textContent;
  const coords = extractMapCoordinates(rawText);
  const linkified = markdownLinksToHtml(rawText).replace(/\n/g, "<br>");
  bubble.innerHTML = coords ? `${linkified}${mapEmbedHtml(coords)}` : linkified;
}

window.renderRichAgentBubbleForTest = renderRichAgentBubble;

function addStatus(text) {
  const item = document.createElement("div");
  item.className = "status-line";
  item.textContent = text;
  messages.append(item);
  scrollToBottom();
}

function parseSse(buffer, onEvent) {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";

  for (const part of parts) {
    const eventLine = part.split("\n").find((line) => line.startsWith("event: "));
    const dataLine = part.split("\n").find((line) => line.startsWith("data: "));
    if (!eventLine || !dataLine) continue;
    onEvent(eventLine.slice(7), JSON.parse(dataLine.slice(6)));
  }

  return rest;
}

async function sendMessage(text) {
  addMessage("user", text);
  const agentBubble = addMessage("agent", "");
  setStatus("Thinking");
  form.querySelector("button").disabled = true;
  input.disabled = true;

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text, session_id: sessionId }),
  });

  if (!response.ok || !response.body) {
    agentBubble.textContent = "The space radio crackled. Please try again.";
    setStatus("Ready");
    form.querySelector("button").disabled = false;
    input.disabled = false;
    input.focus();
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleEvent = (event, data) => {
    if (event === "trace") {
      traceLink.href = data.url;
      traceLink.classList.add("active");
    }
    if (event === "status") addStatus(data.text);
    if (event === "delta") {
      agentBubble.textContent += data.text;
      scrollToBottom();
    }
    if (event === "error") {
      agentBubble.textContent = data.text;
      if (data.debug) addStatus(data.debug);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseSse(buffer, handleEvent);
  }

  renderRichAgentBubble(agentBubble);
  setStatus("Ready");
  form.querySelector("button").disabled = false;
  input.disabled = false;
  input.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  await sendMessage(text);
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
  });
});
