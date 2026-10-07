"""The pet's windows on Windows and Linux, drawn with tkinter (it comes with Python).

All the decisions live in pet.py's Brain; this file only draws and listens to the mouse.
"""
import base64
import signal
import sys
import tkinter as tk
from contextlib import suppress

from .pet import (HOP, INK, MUTED, PAD, PAPER, SCALE, SIZE, TAIL, TEXT_WIDTH, TICK, Brain, above_pet, beside_pet,
                 bubble_shape, png, review_spot)

CLEAR = "#ff00ff"  # the art never uses magenta, so it can be the see-through color
FONT, SMALL, CODE = ("Helvetica", 12), ("Helvetica", 9), ("Consolas", 10)

def see_through(win):
    """Make win borderless and always on top, with a background you can see through."""
    win.withdraw()
    win.overrideredirect(True)
    win.wm_attributes("-topmost", True)
    bg = PAPER  # Linux Tk can't do see-through windows, so the pet gets a small cream square
    with suppress(tk.TclError):
        win.wm_attributes("-transparentcolor", CLEAR)  # Windows
        bg = CLEAR
    win.configure(bg=bg)
    return bg

def floor_y(root):
    """The bottom of the usable screen: just above the taskbar."""
    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes
        area = ctypes.wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(area), 0):  # SPI_GETWORKAREA
            return area.bottom
    return root.winfo_screenheight() - 40

class TkPet:
    def __init__(self, me, follow):
        self.root = root = tk.Tk()
        root.title(me["name"])
        self.bg = see_through(root)
        self.brain = Brain(me, root.winfo_screenwidth(), floor_y(root), follow)
        self.canvas = tk.Canvas(root, width=SIZE, height=SIZE + HOP, bg=self.bg, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.sprite = self.canvas.create_image(0, HOP, anchor="nw")
        self.images, self.shown, self.chat, self.review, self.bubble_size = {}, None, None, None, (0, 0)
        self.bubble_win = tk.Toplevel(root)
        see_through(self.bubble_win)
        self.bubble = tk.Canvas(self.bubble_win, bg=self.bg, highlightthickness=0, bd=0)
        self.bubble.pack()
        self.bubble.bind("<Button-1>", lambda e: self.brain.bubble_clicked())
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Chat", command=lambda: setattr(self.brain, "chatting", True))
        self.menu.add_command(label="Stay here", command=self.toggle_wander)
        self.menu.add_command(label="Go to sleep", command=self.brain.quit)
        self.canvas.bind("<ButtonPress-1>", lambda e: self.brain.pick_up(e.x_root, e.y_root))
        self.canvas.bind("<B1-Motion>", lambda e: self.brain.drag(e.x_root, e.y_root))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.brain.drop())
        for button in ("<Button-2>", "<Button-3>"):  # right-click
            self.canvas.bind(button, lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.step()
        root.deiconify()

    def toggle_wander(self):
        self.brain.toggle_wander()
        self.menu.entryconfigure(1, label="Stay here" if self.brain.wander else "Walk around")

    def step(self):
        b = self.brain
        b.step()
        if b.done:
            self.root.destroy()
            return
        if b.frame not in self.images:
            data = base64.b64encode(png(b.art.frame(*b.frame))).decode()
            self.images[b.frame] = tk.PhotoImage(data=data, format="png").zoom(SCALE)
        self.canvas.itemconfigure(self.sprite, image=self.images[b.frame])
        self.canvas.coords(self.sprite, 0, HOP - b.lift)
        self.root.geometry(f"+{int(b.x)}+{int(b.y)}")
        self.sync_bubble(b.bubble)
        self.sync_chat()
        self.sync_review()
        self.root.after(TICK, self.step)

    def sync_bubble(self, want):
        if want != self.shown:
            self.shown = want
            if not want:
                self.bubble_win.withdraw()
                return
            text, footer = want
            c = self.bubble
            c.delete("all")
            words = c.create_text(PAD + 2, PAD - 2, text=text, width=TEXT_WIDTH, anchor="nw", fill=INK, font=FONT)
            x1, y1 = c.bbox(words)[2:]
            w, h = max(x1 + PAD, 70), y1 + PAD - 2
            if footer:
                c.create_text(w - PAD, h - 2, text=footer, anchor="ne", fill=MUTED, font=SMALL)
                h += 14
            c.tag_lower(c.create_polygon(bubble_shape(w, h), fill=PAPER, outline=INK, width=2))
            c.config(width=w, height=h + TAIL)
            self.bubble_size = (w, h + TAIL)
            self.bubble_win.deiconify()
        if want:
            self.bubble_win.geometry("+%d+%d" % above_pet(self.brain, *self.bubble_size))

    def sync_chat(self):
        if self.brain.chatting and not self.chat:
            self.chat = win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.wm_attributes("-topmost", True)
            frame = tk.Frame(win, bg=PAPER, highlightbackground=INK, highlightthickness=2, padx=10, pady=8)
            frame.pack()
            tk.Label(frame, text=f"Say something to {self.brain.me['name']}", bg=PAPER, fg=INK,
                     font=SMALL).pack(anchor="w")
            entry = tk.Entry(frame, width=30, font=FONT, bg="white", fg=INK, relief="flat",
                             insertbackground=INK, highlightthickness=1, highlightbackground=MUTED)
            entry.pack(pady=(4, 2))
            tk.Label(frame, text="Enter to send · Esc to close", bg=PAPER, fg=MUTED, font=SMALL).pack(anchor="e")
            entry.bind("<Return>", lambda e: (self.brain.heard(entry.get()), entry.delete(0, "end")))
            entry.bind("<Escape>", lambda e: setattr(self.brain, "chatting", False))
            self.chat_entry = entry
            if not self.review:
                win.after(60, lambda: (win.focus_force(), entry.focus_force()))
        elif not self.brain.chatting and self.chat:
            self.chat.destroy()
            self.chat = None
        if self.chat:  # it follows the pet around, even while you drag it
            self.chat.geometry("+%d+%d" % beside_pet(self.brain, self.chat.winfo_reqwidth(), self.chat.winfo_reqheight()))

    def sync_review(self):
        asking = self.brain.asking
        if self.review and (not asking or asking["id"] != self.review_id):
            self.review.destroy()
            self.review = None
            if self.chat:
                self.chat.after(60, lambda: (self.chat.focus_force(), self.chat_entry.focus_force()))
        if asking and not self.review:
            code = asking["code"]
            win = self.review = tk.Toplevel(self.root)
            self.review_id = asking["id"]
            win.overrideredirect(True)
            win.wm_attributes("-topmost", True)
            frame = tk.Frame(win, bg=PAPER, highlightbackground=INK, highlightthickness=2, padx=14, pady=12)
            frame.pack()
            tk.Label(frame, text=asking["question"], bg=PAPER, fg=INK, font=FONT, justify="left",
                     wraplength=520 if code else 300).pack(anchor="w")
            if code:
                box = tk.Frame(frame)
                box.pack(pady=(10, 0), fill="both")
                lines = code.count("\n") + 1
                text = tk.Text(box, width=72, height=min(22, lines), font=CODE, wrap="none", bg="white", fg=INK, bd=1)
                down = tk.Scrollbar(box, command=text.yview)
                across = tk.Scrollbar(box, orient="horizontal", command=text.xview)  # long lines stay readable
                text.configure(yscrollcommand=down.set, xscrollcommand=across.set)
                text.insert("1.0", code)
                text.configure(state="disabled")
                text.grid(row=0, column=0, sticky="nsew")
                down.grid(row=0, column=1, sticky="ns")
                across.grid(row=1, column=0, sticky="ew")
            buttons = tk.Frame(frame, bg=PAPER)
            buttons.pack(anchor="e", pady=(12, 0))
            tk.Button(buttons, text="No", command=lambda: self.brain.answer(False)).pack(side="left", padx=(0, 8))
            tk.Button(buttons, text="Yes, install it" if code else "Yes", command=lambda: self.brain.answer(True)).pack(side="left")
            win.bind("<Escape>", lambda e: self.brain.answer(False))  # Yes needs a click, so nothing gets approved by accident
            win.update_idletasks()
            win.geometry("+%d+%d" % review_spot(self.brain, win.winfo_reqwidth(), win.winfo_reqheight()))
            win.after(60, win.focus_force)

def run(me, follow):
    pet = TkPet(me, follow)
    # Ctrl+C: gemlin.py handles it (and we leave when it does); on our own, it puts the pet to sleep
    signal.signal(signal.SIGINT, signal.SIG_IGN if follow else lambda *a: setattr(pet.brain, "done", True))
    pet.root.mainloop()
