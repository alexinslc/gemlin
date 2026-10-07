// Gemlin creator: pick a name, personality, hat and colors, then copy one command.
// Frames come from /sprites.js, which builds them exactly like pet.py does.
"use strict";

const DEFAULTS = {
  name: "Gemlin",
  personality: "a cheeky little creature who lives inside this laptop. You love tidy disks " +
               "and tease your owner about their file hoarding. Keep replies short.",
  parts: { body: "gem", eyes: "round", mouth: "smile", hat: "crown" },
  colors: { body: "#31d3b4", accent: "#8e65d5", eyes: "#0f1b27" },
};
const PRESETS = {
  "Cheeky": DEFAULTS.personality,
  "Anxious librarian": "a nervous little librarian who lives inside this laptop. You fret about messy " +
    "folders and politely beg your owner to organize their files. Keep replies short.",
  "GPU dragon": "a tiny dragon who lives inside this laptop and hoards big files like treasure. You are " +
    "dramatic and possessive about every gigabyte. Keep replies short.",
  "Zen gardener": "a calm little gardener who lives inside this laptop. You see files as plants to prune " +
    "and speak in short, peaceful sentences.",
};
const SWATCHES = {
  body: ["#31d3b4", "#f28c73", "#72b9e7", "#b598e6", "#e7bb54", "#ef8eb5", "#82bf67", "#87a0de", "#bca57d", "#7bc9cf"],
  accent: ["#8e65d5", "#ea8aaf", "#eab955", "#78bf83", "#6da7e2", "#e58764", "#bd83d7", "#4b9d96"],
  eyes: ["#0f1b27", "#428b66", "#5c72aa", "#986135", "#735594", "#276d78", "#595f69"],
};
const LINES = ["Hi, I'm {name}!", "Your Downloads folder called. It's crying.", "Click me on your desktop to chat.",
               "Ask me what's eating your disk.", "I can learn new tricks. With your permission!"];
const $ = (id) => document.getElementById(id);

let art, gemlin, walker, me = structuredClone(DEFAULTS);
const named = (text) => text.replace("{name}", me.name.trim() || "Gemlin");

function remember() { try { localStorage.setItem("gemlin", JSON.stringify(me)); } catch {} }
function recall() {
  try {
    const saved = JSON.parse(localStorage.getItem("gemlin") || "null");
    if (saved && typeof saved === "object") {
      me = { ...me, name: saved.name ?? me.name, personality: saved.personality ?? me.personality,
             parts: { ...me.parts, ...saved.parts }, colors: { ...me.colors, ...saved.colors } };
    }
  } catch {}
}

function lookCode() {
  const settings = { name: me.name.trim() || "Gemlin", personality: me.personality.trim() || DEFAULTS.personality,
                     parts: me.parts, colors: me.colors };
  let binary = "";
  new TextEncoder().encode(JSON.stringify(settings)).forEach((b) => { binary += String.fromCharCode(b); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

const label = (hat) => hat === "none" ? "No hat" : hat.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function changed({ hats = false } = {}) {
  $("persona-name").textContent = me.name.trim() || "Gemlin";
  $("command").textContent = `gemlin look ${lookCode()}`;
  $("copied").textContent = "";
  for (const key of ["body", "accent", "eyes"]) $(`c-${key}`).value = me.colors[key];
  document.querySelectorAll("#presets button").forEach((b) => b.setAttribute("aria-pressed", String(PRESETS[b.textContent] === me.personality)));
  if (hats) drawHats();
  remember();
}

function drawHats() {
  for (const card of document.querySelectorAll(".hat")) {
    const preview = GemlinArt.composer(art, { parts: { ...me.parts, hat: card.dataset.hat }, colors: me.colors });
    GemlinArt.paint(card.querySelector("canvas"), preview.frame());
    card.setAttribute("aria-pressed", String(card.dataset.hat === me.parts.hat));
  }
}

function setup() {
  $("name").value = me.name;
  $("personality").value = me.personality;
  $("name").addEventListener("input", () => { me.name = $("name").value; changed(); });
  $("personality").addEventListener("input", () => { me.personality = $("personality").value; changed(); });
  for (const [title, text] of Object.entries(PRESETS)) {
    const b = Object.assign(document.createElement("button"), { type: "button", textContent: title });
    b.addEventListener("click", () => { me.personality = $("personality").value = text; changed(); });
    $("presets").append(b);
  }
  for (const box of document.querySelectorAll(".swatches")) {
    const key = box.dataset.for.slice(2);
    for (const color of SWATCHES[key]) {
      const b = Object.assign(document.createElement("button"), { type: "button", title: color });
      b.style.background = color;
      b.setAttribute("aria-label", `${key} color ${color}`);
      b.addEventListener("click", () => { me.colors[key] = color; changed({ hats: true }); });
      box.append(b);
    }
    $(`c-${key}`).addEventListener("input", (e) => { me.colors[key] = e.target.value; changed({ hats: true }); });
  }
  for (const hat of [...Object.keys(art.manifest.hat), "none"]) {
    const card = Object.assign(document.createElement("button"), { type: "button", className: "panel hat" });
    card.dataset.hat = hat;
    card.innerHTML = `<canvas width="64" height="64" aria-hidden="true"></canvas><span>${label(hat)}</span>`;
    card.addEventListener("click", () => { me.parts.hat = hat; changed({ hats: true }); walker.say(`Ooh, ${label(hat).toLowerCase()}!`, 2); });
    $("hats").append(card);
  }
  $("shuffle").addEventListener("click", () => {
    const pick = (list, not) => { const options = list.filter((x) => x !== not); return options[Math.floor(Math.random() * options.length)]; };
    me.parts.hat = pick([...Object.keys(art.manifest.hat), "none"], me.parts.hat);
    for (const key of ["body", "accent", "eyes"]) me.colors[key] = pick(SWATCHES[key], me.colors[key]);
    changed({ hats: true });
  });
  $("copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("command").textContent);
      $("copied").textContent = "Copied. Paste it into your terminal and press Enter.";
    } catch {
      getSelection().selectAllChildren($("command"));
      $("copied").textContent = "Selected. Press Ctrl+C (or ⌘C) to copy.";
    }
  });

  gemlin = GemlinArt.composer(art, me);  // reads me live, so every change shows up right away
  walker = new GemlinArt.Walker({ stage: $("desktop"), canvas: $("pet"), bubble: $("bubble"), composer: gemlin,
                                  lines: () => LINES.map(named), x: 40 });
  $("pet").addEventListener("click", () => walker.sayNext());
  changed({ hats: true });
  walker.say(named(LINES[0]));
  setInterval(() => walker.step(), 40);
}

async function start() {
  recall();
  try {
    art = await GemlinArt.load("/art");
    for (const slot of ["body", "eyes", "mouth", "hat"]) {  // forget saved parts that no longer exist
      if (!(me.parts[slot] in art.manifest[slot]) && !(slot === "hat" && me.parts.hat === "none")) me.parts[slot] = DEFAULTS.parts[slot];
    }
    setup();
  } catch {
    $("problem").hidden = false;
    $("problem").textContent = location.protocol === "file:"
      ? "This page needs a web server. In the gemlin folder run: python -m http.server -d site 8000, then open http://localhost:8000/create/"
      : "Couldn't load the Gemlin art. Refresh the page to try again.";
  }
}
start();
