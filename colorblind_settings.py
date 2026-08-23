import os
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont

import numpy as np

import build_colorblind_mod as builder
import colorfilters as cf

WHY_NOT_IN_GAME = (
    "Deadlock bakes its color lookup table into a resource file that is read "
    "when the game starts, and exposes no production console command that "
    "selects or weights one. Fully close Deadlock, apply the setting here, then "
    "start the game. This window does not need to remain open."
)

BG = "#16161a"
PANEL = "#1e1e24"
FG = "#e2e2e8"
MUTED = "#9a9aa6"
ACCENT = "#c8a24a"

MODE_ORDER = ["deutan", "protan", "tritan", "gray", "invert", "off"]
MODE_HELP = {
    "deutan": "Green-cone deficiency. The most common form of red-green colorblindness.",
    "protan": "Red-cone deficiency. The other red-green form; reds look darker.",
    "tritan": "Blue-cone deficiency. Rare; affects blue/yellow separation.",
    "gray": "Removes all color. Useful as a test that the mod is loading.",
    "invert": "Photo-negative of the whole scene.",
    "off": "Restores Deadlock's original colors, filter disabled.",
}


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        root.title("Deadlock Color Filter")
        root.configure(bg=BG)
        root.resizable(False, False)

        state = builder.load_state()
        self.mode = tk.StringVar(value=state["mode"])
        self.severity = tk.DoubleVar(value=state["severity"])
        self.gain = tk.DoubleVar(value=state["gain"])

        self.h1 = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        self.lbl = tkfont.Font(family="Segoe UI", size=9)
        self.small = tkfont.Font(family="Segoe UI", size=8)

        wrap = tk.Frame(root, bg=BG, padx=18, pady=16)
        wrap.pack()

        tk.Label(wrap, text="Deadlock Color Filter", font=self.h1,
                 bg=BG, fg=FG).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(wrap, text=WHY_NOT_IN_GAME, font=self.small, bg=BG, fg=MUTED,
                 wraplength=620, justify="left").grid(row=1, column=0, columnspan=2,
                                                      sticky="w", pady=(2, 12))

        left = tk.Frame(wrap, bg=BG)
        left.grid(row=2, column=0, sticky="nw", padx=(0, 18))
        self._build_controls(left)

        right = tk.Frame(wrap, bg=BG)
        right.grid(row=2, column=1, sticky="nw")
        self._build_preview(right)

        self.status = tk.Label(wrap, text="", font=self.small, bg=BG, fg=MUTED,
                               wraplength=620, justify="left", anchor="w")
        self.status.grid(row=3, column=0, columnspan=2, sticky="we", pady=(12, 0))

        self.refresh()

    def _build_controls(self, parent):
        tk.Label(parent, text="FILTER", font=self.small, bg=BG, fg=MUTED).pack(anchor="w")
        for m in MODE_ORDER:
            tk.Radiobutton(
                parent, text=cf.MODE_LABELS[m], value=m, variable=self.mode,
                command=self.refresh, font=self.lbl, bg=BG, fg=FG,
                selectcolor=PANEL, activebackground=BG, activeforeground=ACCENT,
                highlightthickness=0, bd=0, anchor="w",
            ).pack(anchor="w", fill="x")

        self.mode_help = tk.Label(parent, text="", font=self.small, bg=BG, fg=MUTED,
                                  wraplength=260, justify="left")
        self.mode_help.pack(anchor="w", pady=(4, 12))

        self.sev_box = tk.Frame(parent, bg=BG)
        self.sev_label = tk.Label(self.sev_box, text="", font=self.small, bg=BG, fg=MUTED)
        self.sev_label.pack(anchor="w")
        tk.Scale(self.sev_box, from_=0.1, to=1.0, resolution=0.05,
                 orient="horizontal", variable=self.severity, command=lambda _: self.refresh(),
                 length=260, bg=BG, fg=FG, troughcolor=PANEL, highlightthickness=0,
                 bd=0, showvalue=False, activebackground=ACCENT).pack(anchor="w")
        tk.Label(self.sev_box, text="How strong your color deficiency is.",
                 font=self.small, bg=BG, fg=MUTED).pack(anchor="w")
        self.sev_box.pack(anchor="w", fill="x", pady=(0, 10))

        self.gain_box = tk.Frame(parent, bg=BG)
        self.gain_label = tk.Label(self.gain_box, text="", font=self.small, bg=BG, fg=MUTED)
        self.gain_label.pack(anchor="w")
        tk.Scale(self.gain_box, from_=0.0, to=1.0, resolution=0.05,
                 orient="horizontal", variable=self.gain, command=lambda _: self.refresh(),
                 length=260, bg=BG, fg=FG, troughcolor=PANEL, highlightthickness=0,
                 bd=0, showvalue=False, activebackground=ACCENT).pack(anchor="w")
        tk.Label(self.gain_box, text="How hard the filter pushes. Lower is subtler.",
                 font=self.small, bg=BG, fg=MUTED).pack(anchor="w")
        self.gain_box.pack(anchor="w", fill="x", pady=(0, 14))

        self.apply_btn = tk.Button(parent, text="Apply to Deadlock", command=self.apply,
                                   font=self.lbl, bg=ACCENT, fg="#1a1a1a",
                                   activebackground="#e0bb5e", bd=0, padx=12, pady=7,
                                   cursor="hand2")
        self.apply_btn.pack(anchor="w", fill="x")
        tk.Button(parent, text="Remove filter from game", command=self.remove,
                  font=self.small, bg=PANEL, fg=FG, activebackground="#2a2a32",
                  bd=0, padx=12, pady=5, cursor="hand2").pack(anchor="w", fill="x", pady=(6, 0))

    def _build_preview(self, parent):
        self.sw, self.sh, self.pad, self.top, self.lw = 74, 30, 5, 40, 96
        cols = 4
        w = self.lw + cols * (self.sw + self.pad)
        h = self.top + len(builder.SWATCHES) * (self.sh + self.pad) + 46
        self.canvas = tk.Canvas(parent, width=w, height=h, bg=BG,
                                highlightthickness=0, bd=0)
        self.canvas.pack()

    def draw_preview(self):
        c = self.canvas
        c.delete("all")
        mode = self.mode.get()
        sev, gain = self.severity.get(), self.gain.get()
        sim_type = mode if mode in cf.CVD_TYPES else "deutan"
        simulating = mode in cf.CVD_TYPES

        heads = ["Original", "You see", "Filtered", "You see"] if simulating \
            else ["Original", "", "Filtered", ""]
        for i, head in enumerate(heads):
            if head:
                c.create_text(self.lw + i * (self.sw + self.pad) + 2, 22,
                              text=head, anchor="w", fill=MUTED, font=self.small)

        for row, (name, hexv) in enumerate(builder.SWATCHES):
            y = self.top + row * (self.sh + self.pad)
            base = builder.hex_to_rgb(hexv)
            filtered = cf.apply_mode(base, mode, sev, gain)
            cells = [base,
                     cf.simulate(base, sim_type, sev) if simulating else None,
                     filtered,
                     cf.simulate(filtered, sim_type, sev) if simulating else None]
            c.create_text(0, y + self.sh / 2, text=name, anchor="w",
                          fill=FG, font=self.small)
            for i, col in enumerate(cells):
                if col is None:
                    continue
                x = self.lw + i * (self.sw + self.pad)
                c.create_rectangle(x, y, x + self.sw, y + self.sh,
                                   fill=builder.rgb_to_hex(col), outline="")

        rows = builder.separation_scores(mode, sev, gain)
        y = self.top + len(builder.SWATCHES) * (self.sh + self.pad) + 6
        if rows:
            c.create_text(0, y, text="Separation for you (higher = easier to tell apart)",
                          anchor="w", fill=MUTED, font=self.small)
            for i, (label, before, after, pct) in enumerate(rows):
                color = "#6fcf7f" if pct > 0 else "#d97b7b"
                c.create_text(0, y + 14 + i * 12, anchor="w", font=self.small, fill=FG,
                              text="%-22s %.2f -> %.2f" % (label, before, after))
                c.create_text(240, y + 14 + i * 12, anchor="w", font=self.small,
                              fill=color, text="%+.0f%%" % pct)

    def refresh(self):
        mode = self.mode.get()
        self.mode_help.config(text=MODE_HELP[mode])
        is_cvd = mode in cf.CVD_TYPES
        self.sev_label.config(text="Deficiency severity   %.2f" % self.severity.get())
        self.gain_label.config(text="Filter intensity   %.2f" % self.gain.get())
        for w in self.sev_box.winfo_children():
            try:
                w.configure(state="normal" if is_cvd else "disabled")
            except tk.TclError:
                pass
        enabled = mode != "off"
        for w in self.gain_box.winfo_children():
            try:
                w.configure(state="normal" if enabled else "disabled")
            except tk.TclError:
                pass
        self.draw_preview()

    def set_status(self, text, good=None):
        color = MUTED if good is None else ("#6fcf7f" if good else "#d97b7b")
        self.status.config(text=text, fg=color)
        self.root.update_idletasks()

    def apply(self):
        if self.busy:
            return
        self.busy = True
        self.apply_btn.config(state="disabled", text="Building...")
        mode, sev, gain = self.mode.get(), self.severity.get(), self.gain.get()
        lines = []

        def work():
            try:
                old_state = builder.load_state()
                last_mode = mode if mode != "off" else old_state["last_mode"]
                payload = builder.build(mode, sev, gain, log=lines.append)
                builder.install(payload, log=lines.append)
                builder.save_state(mode, sev, gain, last_mode=last_mode)
                self.root.after(0, done, True, None)
            except Exception as exc:
                self.root.after(0, done, False, exc)

        def done(ok, exc):
            self.busy = False
            self.apply_btn.config(state="normal", text="Apply to Deadlock")
            if ok:
                self.set_status(
                    "Applied: %s. %s  Fully restart Deadlock to see it."
                    % (cf.MODE_LABELS[mode], " ".join(l.strip() for l in lines[:1])),
                    good=True)
            else:
                self.set_status("Failed: %s" % exc, good=False)

        threading.Thread(target=work, daemon=True).start()

    def remove(self):
        lines = []
        try:
            builder.uninstall(log=lines.append)
            self.set_status("Filter removed. Deadlock is back to its original colors "
                            "after a full restart.", good=True)
        except Exception as exc:
            self.set_status("Failed to remove: %s" % exc, good=False)


def main():
    if not os.path.exists(builder.GAME_PAK):
        print("ERROR: Deadlock not found at %s" % builder.GAME, file=sys.stderr)
        return 1
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
