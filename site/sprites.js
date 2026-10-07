// Builds Gemlin frames from the layered art in /art, exactly like pet.py does, and walks
// them around a stage the way the desktop pet does. Used by the home page and the creator.
"use strict";

const GemlinArt = (() => {
  const FIRST = { body: "stand", eyes: "open", mouth: "closed", hat: "still" };
  const FALLBACK = { walk_2: "walk_1", walk_1: "stand", blink: "open", talk_1: "closed" };
  const KEYS = {  // the artist paints recolorable areas in these exact colors
    "255,128,128": ["body", "light"], "255,0,0": ["body", "base"], "128,0,0": ["body", "dark"],
    "128,128,255": ["accent", "light"], "0,0,255": ["accent", "base"], "0,0,128": ["accent", "dark"],
    "0,255,0": ["eyes", "base"],
  };
  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  function shade(c, tone) {
    if (tone === "light") return c.map((v) => Math.round(v + (255 - v) * 0.55));
    if (tone === "dark") return c.map((v) => Math.round(v * 0.5));
    return c;
  }

  async function load(base = "/art") {
    const manifest = await (await fetch(`${base}/manifest.json`)).json();
    const images = {};
    const files = Object.entries(manifest).flatMap(([slot, options]) =>
      Object.entries(options).flatMap(([option, names]) => names.map((n) => `${slot}/${option}/${n}`)));
    await Promise.all(files.map((path) => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => { images[path] = img; resolve(); };
      img.onerror = reject;
      img.src = `${base}/${path}.png`;
    })));
    return { manifest, images };
  }

  // look = { parts: {body, eyes, mouth, hat}, colors: {body, accent, eyes} }; read fresh on every call
  function composer(art, look) {
    const cache = new Map();
    const slots = () => Object.keys(FIRST).filter((s) => !(s === "hat" && look.parts.hat === "none"));
    function find(slot, frame, prefix = "") {
      const have = art.manifest[slot]?.[look.parts[slot]] || [];
      while (frame) {
        if (have.includes(prefix + frame)) return `${slot}/${look.parts[slot]}/${prefix}${frame}`;
        frame = FALLBACK[frame];
      }
      return null;
    }
    const prefix = (view) => view === "side" && slots().every((s) => find(s, FIRST[s], "side_")) ? "side_" : "";
    function steps(view) {
      const found = find("body", "walk_2", prefix(view));
      return found && found.endsWith("walk_2") ? ["walk_1", "walk_2"] : ["stand", "walk_1"];
    }
    function frame(view = "front", body = "stand", eyes = "open", mouth = "closed", left = false) {
      const key = JSON.stringify([look.parts, look.colors, view, body, eyes, mouth, left]);
      if (cache.has(key)) return cache.get(key);
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 64;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (left) { ctx.translate(64, 0); ctx.scale(-1, 1); }  // walking left = the whole sprite mirrored
      slots().forEach((slot, i) => {
        const path = find(slot, [body, eyes, mouth, "still"][i], prefix(view));
        if (path) ctx.drawImage(art.images[path], 0, 0);
      });
      const data = ctx.getImageData(0, 0, 64, 64);
      const palette = {};
      for (const [k, [slot, tone]] of Object.entries(KEYS)) palette[k] = shade(rgb(look.colors[slot]), tone);
      for (let i = 0; i < data.data.length; i += 4) {
        if (!data.data[i + 3]) continue;
        const swap = palette[`${data.data[i]},${data.data[i + 1]},${data.data[i + 2]}`];
        if (swap) data.data.set(swap, i);
      }
      ctx.putImageData(data, 0, 0);
      cache.set(key, canvas);
      return canvas;
    }
    const tops = new Map();
    function top() {  // first row with pixels (head or hat), like Sprites.top in pet.py
      const key = JSON.stringify(look.parts);
      if (!tops.has(key)) {
        const px = frame().getContext("2d").getImageData(0, 0, 64, 64).data;
        let y = 0;
        while (y < 63 && ![...Array(64).keys()].some((x) => px[(y * 64 + x) * 4 + 3])) y++;
        tops.set(key, y);
      }
      return tops.get(key);
    }
    return { frame, steps, top };
  }

  function paint(canvas, src) {
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(src, 0, 0, canvas.width, canvas.height);
  }

  // A Gemlin wandering a stage: walks sideways, stops, turns to face you, sometimes talks.
  class Walker {
    constructor({ stage, canvas, bubble, composer, lines = [], chatty = 0.35, x }) {
      Object.assign(this, { stage, canvas, bubble, composer, lines, chatty });
      this.x = x ?? 10 + Math.random() * Math.max(10, stage.clientWidth - 148);
      this.target = null; this.rest = 20 + Math.random() * 80; this.left = false;
      this.tick = 0; this.blinkAt = 60 + Math.random() * 60; this.talkUntil = 0; this.hideAt = 0;
      this.line = 0;
      this.still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
    sayNext() {  // lines can be a list, or a function that returns one (so they can use a changing name)
      const lines = typeof this.lines === "function" ? this.lines() : this.lines;
      if (!lines.length) return false;
      this.say(lines[this.line++ % lines.length]);
      return true;
    }
    say(text, seconds = 3.5) {
      this.bubble.textContent = text;
      this.bubble.hidden = false;
      this.hideAt = this.tick + seconds * 25;
      this.talkUntil = this.tick + Math.min(text.length / 15, 3) * 25;
      this.target = null;
    }
    step() {
      this.tick++;
      const width = this.stage.clientWidth, talking = !this.bubble.hidden;
      if (talking && this.tick >= this.hideAt) this.bubble.hidden = true;
      let walking = false;
      if (!talking && !this.still) {
        if (this.target === null) {
          if (--this.rest <= 0) {
            const spoke = Math.random() < this.chatty && this.sayNext();
            if (!spoke) this.target = 10 + Math.random() * Math.max(10, width - 148);
          }
        } else if (Math.abs(this.target - this.x) <= 1.5) {
          this.x = this.target; this.target = null; this.rest = 40 + Math.random() * 140;
        } else {
          this.left = this.target < this.x;
          this.x += this.left ? -1.5 : 1.5;
          walking = true;
        }
      }
      this.x = Math.min(this.x, Math.max(0, width - 128));
      const anim = Math.floor(this.tick / 3);
      if (this.tick >= this.blinkAt + 4) this.blinkAt = this.tick + 60 + Math.random() * 90;
      const eyes = this.tick >= this.blinkAt ? "blink" : "open";
      let src, lift = 0;
      if (walking) {  // sideways, facing where it's going
        src = this.composer.frame("side", this.composer.steps("side")[anim % 2], eyes, "closed", this.left);
        lift = 4 * (anim % 2);
      } else {  // standing still: turn to face you
        const mouth = talking && this.tick < this.talkUntil && anim % 2 ? "talk_1" : "closed";
        src = this.composer.frame("front", "stand", eyes, mouth, false);
      }
      paint(this.canvas, src);
      this.canvas.style.transform = `translate(${this.x}px, ${-lift}px)`;
      if (!this.bubble.hidden) {
        const feet = parseFloat(getComputedStyle(this.canvas).bottom);  // keep the bubble just above the head or hat
        this.bubble.style.bottom = `${feet + 128 - this.composer.top() * 2 + 12}px`;
        const left = Math.min(Math.max(8, this.x + 24), width - this.bubble.offsetWidth - 8);
        this.bubble.style.transform = `translateX(${left}px)`;
      }
    }
  }

  return { load, composer, paint, Walker };
})();
