// Gemlin creator: builds your Gemlin from the art in art/ and turns your choices into one
// command. Frames are assembled exactly like pet.py does, so what you see is what walks.
"use strict";

const DEFAULTS = {
  name: "Gemlin",
  personality: "a cheeky little creature who lives inside this laptop. You love tidy disks " +
               "and tease your owner about their file hoarding. Keep replies short.",
  parts: { body: "gem", eyes: "round", mouth: "smile", hat: "crown" },
  colors: { body: "#31d3b4", accent: "#8e65d5", eyes: "#0f1b27" },
  walk: "side",
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
const SWATCHES = {  // from the art pack's palette
  body: ["#31d3b4", "#f28c73", "#72b9e7", "#b598e6", "#e7bb54", "#ef8eb5", "#82bf67", "#87a0de", "#bca57d", "#7bc9cf"],
  accent: ["#8e65d5", "#ea8aaf", "#eab955", "#78bf83", "#6da7e2", "#e58764", "#bd83d7", "#4b9d96"],
  eyes: ["#0f1b27", "#428b66", "#5c72aa", "#986135", "#735594", "#276d78", "#595f69"],
};
const FIRST = { body: "stand", eyes: "open", mouth: "closed", hat: "still" };
const FALLBACK = { walk_2: "walk_1", walk_1: "stand", blink: "open", talk_1: "closed" };
const KEYS = {  // the artist paints recolorable areas in these exact colors
  "255,128,128": ["body", "light"], "255,0,0": ["body", "base"], "128,0,0": ["body", "dark"],
  "128,128,255": ["accent", "light"], "0,0,255": ["accent", "base"], "0,0,128": ["accent", "dark"],
  "0,255,0": ["eyes", "base"],
};
const LINES = ["Hi, I'm {name}!", "Your Downloads folder called. It's crying.", "Click me on your desktop to chat.",
               "Ask me what's eating your disk.", "I can learn new tricks. With your permission!"];
const $ = (id) => document.getElementById(id);

let manifest = {}, me = structuredClone(DEFAULTS), os = /Win/.test(navigator.platform) ? "windows" : "mac";
const images = {}, frames = new Map();

// ---------- saving your choices in this browser ----------
function remember() { try { localStorage.setItem("gemlin", JSON.stringify(me)); } catch {} }
function recall() {
  try {
    const saved = JSON.parse(localStorage.getItem("gemlin") || "null");
    if (saved && typeof saved === "object") me = { ...me, ...saved, parts: { ...me.parts, ...saved.parts }, colors: { ...me.colors, ...saved.colors } };
  } catch {}
}

// ---------- building frames (same steps as pet.py) ----------
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
function shade(c, tone) {
  if (tone === "light") return c.map((v) => Math.round(v + (255 - v) * 0.55));
  if (tone === "dark") return c.map((v) => Math.round(v * 0.5));
  return c;
}
function palette() {
  const out = {};
  for (const [key, [slot, tone]] of Object.entries(KEYS)) out[key] = shade(rgb(me.colors[slot]), tone);
  return out;
}
function slots() { return Object.keys(FIRST).filter((s) => !(s === "hat" && me.parts.hat === "none")); }
function find(slot, frame, prefix = "") {
  const have = manifest[slot]?.[me.parts[slot]] || [];
  while (frame) {
    if (have.includes(prefix + frame)) return `${slot}/${me.parts[slot]}/${prefix}${frame}`;
    frame = FALLBACK[frame];
  }
  return null;
}
function hasSide() { return slots().every((s) => find(s, FIRST[s], "side_")); }
function steps(view) {
  const prefix = view === "side" && hasSide() ? "side_" : "";
  const found = find("body", "walk_2", prefix);
  return found && found.endsWith("walk_2") ? ["walk_1", "walk_2"] : ["stand", "walk_1"];
}
function frame(view, body, eyes, mouth, left) {
  const key = [me.parts.hat, view, body, eyes, mouth, left].join("|");
  if (frames.has(key)) return frames.get(key);
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const prefix = view === "side" && hasSide() ? "side_" : "";
  slots().forEach((slot, i) => {
    const path = find(slot, [body, eyes, mouth, "still"][i], prefix);
    if (path && images[path]) ctx.drawImage(images[path], 0, 0);
  });
  const data = ctx.getImageData(0, 0, 64, 64), p = palette();
  for (let i = 0; i < data.data.length; i += 4) {
    if (!data.data[i + 3]) continue;
    const swap = p[`${data.data[i]},${data.data[i + 1]},${data.data[i + 2]}`];
    if (swap) data.data.set(swap, i);
  }
  ctx.putImageData(data, 0, 0);
  if (left) {  // walking left = the whole sprite mirrored
    const flipped = document.createElement("canvas");
    flipped.width = flipped.height = 64;
    const f = flipped.getContext("2d");
    f.translate(64, 0); f.scale(-1, 1); f.drawImage(canvas, 0, 0);
    frames.set(key, flipped);
    return flipped;
  }
  frames.set(key, canvas);
  return canvas;
}
const tops = {};
function headTop() {  // first row with any pixels, like Sprites.top in pet.py
  if (!(me.parts.hat in tops)) {
    const px = frame("front", "stand", "open", "closed", false).getContext("2d").getImageData(0, 0, 64, 64).data;
    let top = 0;
    while (top < 63 && ![...Array(64).keys()].some((x) => px[(top * 64 + x) * 4 + 3])) top++;
    tops[me.parts.hat] = top;
  }
  return tops[me.parts.hat];
}
function paint(canvas, src) {
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(src, 0, 0, canvas.width, canvas.height);
}

// ---------- the walking preview (a small copy of pet.py's Brain) ----------
const pet = { x: 40, target: null, rest: 30, left: false, tick: 0, blinkAt: 60, talkUntil: 0, hideAt: 0, line: 0 };
function say(text, seconds = 3.5) {
  $("bubble").textContent = text.replace("{name}", me.name || "Gemlin");
  $("bubble").hidden = false;
  pet.hideAt = pet.tick + seconds * 25;
  pet.talkUntil = pet.tick + Math.min(text.length / 15, 3) * 25;
}
function step() {
  pet.tick++;
  const width = $("desktop").clientWidth, talking = !$("bubble").hidden;
  if (talking && pet.tick >= pet.hideAt) $("bubble").hidden = true;
  let walking = false;
  if (!talking) {
    if (pet.target === null) {
      if (--pet.rest <= 0) {
        if (Math.random() < 0.35) say(LINES[pet.line++ % LINES.length]);
        else pet.target = 10 + Math.random() * Math.max(10, width - 148);
      }
    } else if (Math.abs(pet.target - pet.x) <= 1.5) {
      pet.x = pet.target; pet.target = null; pet.rest = 40 + Math.random() * 120;
    } else {
      pet.left = pet.target < pet.x;
      pet.x += pet.left ? -1.5 : 1.5;
      walking = true;
    }
  }
  const anim = Math.floor(pet.tick / 3);
  if (pet.tick >= pet.blinkAt + 4) pet.blinkAt = pet.tick + 60 + Math.random() * 90;
  const eyes = pet.tick >= pet.blinkAt ? "blink" : "open";
  let src, lift = 0;
  if (walking) {
    src = frame(me.walk, steps(me.walk)[anim % 2], eyes, "closed", pet.left);
    lift = 4 * (anim % 2);
  } else {
    const mouth = talking && pet.tick < pet.talkUntil && anim % 2 ? "talk_1" : "closed";
    src = frame("front", "stand", eyes, mouth, false);
  }
  paint($("pet"), src);
  $("bubble").style.bottom = `${56 + 128 - headTop() * 2 + 12}px`;  // just above the head or hat
  $("pet").style.transform = `translate(${pet.x}px, ${-lift}px)`;
  const bubble = $("bubble");
  if (!bubble.hidden) bubble.style.transform = `translateX(${Math.min(Math.max(8, pet.x + 24), width - bubble.offsetWidth - 8)}px)`;
}

// ---------- your choices ----------
function lookCode() {
  const settings = { name: me.name.trim() || "Gemlin", personality: me.personality.trim() || DEFAULTS.personality,
                     parts: me.parts, colors: me.colors, walk: me.walk };
  const bytes = new TextEncoder().encode(JSON.stringify(settings));
  let binary = "";
  bytes.forEach((b) => { binary += String.fromCharCode(b); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function changed({ art = false } = {}) {
  if (art) frames.clear();
  $("persona-name").textContent = me.name.trim() || "Gemlin";
  $("command").textContent = `${os === "mac" ? "python3" : "python"} gemlin.py --look ${lookCode()}`;
  $("copied").textContent = "";
  for (const key of ["body", "accent", "eyes"]) $(`c-${key}`).value = me.colors[key];
  document.querySelectorAll("[data-walk]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.walk === me.walk)));
  document.querySelectorAll("[data-os]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.os === os)));
  document.querySelectorAll("#presets button").forEach((b) => b.setAttribute("aria-pressed", String(PRESETS[b.textContent] === me.personality)));
  if (art) drawHats();
  remember();
}
function drawHats() {
  const wearing = me.parts.hat;
  document.querySelectorAll(".hat").forEach((card) => {
    me.parts.hat = card.dataset.hat;
    paint(card.querySelector("canvas"), frame("front", "stand", "open", "closed", false));
    card.setAttribute("aria-pressed", String(card.dataset.hat === wearing));
  });
  me.parts.hat = wearing;
}
const label = (name) => name === "none" ? "No hat" : name.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

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
      b.addEventListener("click", () => { me.colors[key] = color; changed({ art: true }); });
      box.append(b);
    }
    $(`c-${key}`).addEventListener("input", (e) => { me.colors[key] = e.target.value; changed({ art: true }); });
  }
  document.querySelectorAll("[data-walk]").forEach((b) => b.addEventListener("click", () => { me.walk = b.dataset.walk; changed(); }));
  document.querySelectorAll("[data-os]").forEach((b) => b.addEventListener("click", () => { os = b.dataset.os; changed(); }));
  for (const hat of [...Object.keys(manifest.hat), "none"]) {
    const card = Object.assign(document.createElement("button"), { type: "button", className: "panel hat" });
    card.dataset.hat = hat;
    card.innerHTML = `<canvas width="64" height="64" aria-hidden="true"></canvas><span>${label(hat)}</span>`;
    card.addEventListener("click", () => { me.parts.hat = hat; changed({ art: true }); say(`Ooh, ${label(hat).toLowerCase()}!`, 2); });
    $("hats").append(card);
  }
  $("shuffle").addEventListener("click", () => {
    const pick = (list, not) => { const options = list.filter((x) => x !== not); return options[Math.floor(Math.random() * options.length)]; };
    me.parts.hat = pick([...Object.keys(manifest.hat), "none"], me.parts.hat);
    for (const key of ["body", "accent", "eyes"]) me.colors[key] = pick(SWATCHES[key], me.colors[key]);
    changed({ art: true });
  });
  $("pet").addEventListener("click", () => say(LINES[pet.line++ % LINES.length]));
  $("copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("command").textContent);
      $("copied").textContent = "Copied. Paste it into your terminal in the gemlin folder.";
    } catch {
      getSelection().selectAllChildren($("command"));
      $("copied").textContent = "Selected. Press Ctrl+C (or ⌘C) to copy.";
    }
  });
  changed({ art: true });
  say("Hi, I'm {name}!");
  setInterval(step, 40);
}

async function start() {
  recall();
  try {
    manifest = await (await fetch("art/manifest.json")).json();
    const files = Object.entries(manifest).flatMap(([slot, options]) =>
      Object.entries(options).flatMap(([option, names]) => names.map((n) => `${slot}/${option}/${n}`)));
    await Promise.all(files.map((path) => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => { images[path] = img; resolve(); };
      img.onerror = reject;
      img.src = `art/${path}.png`;
    })));
    for (const slot of Object.keys(FIRST)) {  // forget saved parts that no longer exist
      if (!(me.parts[slot] in manifest[slot]) && !(slot === "hat" && me.parts.hat === "none")) me.parts[slot] = DEFAULTS.parts[slot];
    }
    setup();
  } catch (error) {
    $("problem").hidden = false;
    $("problem").textContent = location.protocol === "file:"
      ? "This page needs to be opened from a web server. In the gemlin folder run: python -m http.server -d creator 8000, then open http://localhost:8000"
      : "Couldn't load the Gemlin art. Refresh the page to try again.";
  }
}
start();
