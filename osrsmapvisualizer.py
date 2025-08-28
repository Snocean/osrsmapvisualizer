import tkinter as tk
from tkinter import ttk
import tkinter.colorchooser as colorchooser
import json
import os
from PIL import Image, ImageTk

STATE_FILE = "state.json"

class PinMapperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OSRS Farming Points")
        self.root.geometry("1920x1080")
        self.root.minsize(800, 600)

        self.pins = {}  # store pin widgets by label
        self.lines = []  # list of lines

        self.setup_ui()
        self.load_state()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # Main PanedWindow (resizable columns)
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left column (controls)
        self.left_frame = ttk.Frame(self.paned, width=600)
        self.left_frame.pack(fill=tk.Y, side=tk.LEFT)

        self.entry = ttk.Entry(self.left_frame)
        self.entry.pack(fill=tk.X, padx=5, pady=5)
        self.add_button = ttk.Button(self.left_frame, text="Add", command=self.add_line)
        self.add_button.pack(fill=tk.X, padx=5, pady=5)

        self.line_container = ttk.Frame(self.left_frame)
        self.line_container.pack(fill=tk.BOTH, expand=True)

        # Right side (canvas with world map)
        self.canvas = tk.Canvas(self.paned, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Load world map image
        self.original_img = Image.open("worldmap.png")
        self.world_img = ImageTk.PhotoImage(self.original_img)
        self.bg_image_id = self.canvas.create_image(0, 0, image=self.world_img, anchor="nw")
        self.canvas.tag_lower(self.bg_image_id)

        # Bind resize event
        self.canvas.bind("<Configure>", self.resize_background)

        self.paned.add(self.left_frame, weight=0)
        self.paned.add(self.canvas, weight=1)

    def resize_background(self, event=None):
        if not hasattr(self, "original_img"):
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 10 or canvas_height < 10:
            return

        resized = self.original_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        self.world_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.bg_image_id, image=self.world_img)

        # Reposition all pins according to their relative positions
        for line in self.lines:
            if line["pin"] and "rel_pos" in line:
                rel_x, rel_y = line["rel_pos"]
                x = rel_x * canvas_width
                y = rel_y * canvas_height
                theight = 15
                twidth = 7
                points = [
                    x, y + theight,
                    x - twidth, y - theight,
                    x + twidth, y - theight
                ]
                self.canvas.coords(line["pin"], *points)
                line["last_pos"] = (x, y)

    def add_line(self, text=None, checked=True, color="#FFFF00", pin_pos=None):
        if not text:
            text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)

        frame = ttk.Frame(self.line_container)
        frame.pack(fill=tk.X, pady=2)

        var = tk.BooleanVar(value=checked)
        chk = ttk.Checkbutton(frame, variable=var)
        chk.pack(side=tk.LEFT)

        color_box = tk.Label(frame, background=color, width=2)
        color_box.pack(side=tk.LEFT, padx=2)

        lbl = ttk.Label(frame, text=text)
        lbl.pack(side=tk.LEFT)

        line_data = {"text": text, "var": var, "color": color, "pin": None}
        self.lines.append(line_data)

        # Context menu for removing
        menu = tk.Menu(self.root, tearoff=0)
        def remove_line():
            if line_data["pin"]:
                self.canvas.delete(line_data["pin"])
            self.lines.remove(line_data)
            frame.destroy()
            self.save_state()
        menu.add_command(label="Remove", command=remove_line)

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        for w in [frame, chk, color_box, lbl]:
            w.bind("<Button-3>", show_menu)

        # Color change
        def change_color(event):
            new_color = colorchooser.askcolor(title="Choose pin color", color=line_data["color"])
            if new_color and new_color[1]:
                line_data["color"] = new_color[1]
                color_box.config(background=new_color[1])
                if line_data["pin"]:
                    self.canvas.itemconfig(line_data["pin"], fill=new_color[1])
        color_box.bind("<Button-1>", change_color)

        # Toggle pin visibility
        var.trace_add("write", lambda *_, l=line_data: self.toggle_pin(l))

        # Schedule initial creation if checked
        if checked:
            self.schedule_pin_creation(line_data)

    def schedule_pin_creation(self, line_data):
        def attempt_creation():
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 10 and ch > 10:
                if line_data["var"].get() and not line_data["pin"]:
                    self.create_pin(line_data, pos=line_data.get("last_pos"))
            else:
                self.root.after(50, attempt_creation)
        self.root.after(0, attempt_creation)

    def create_pin(self, line_data, pos=None):
        if line_data["pin"]:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if pos:
            x, y = pos
        elif line_data.get("last_pos"):
            x, y = line_data["last_pos"]
        elif line_data.get("rel_pos"):
            x = line_data["rel_pos"][0] * canvas_width
            y = line_data["rel_pos"][1] * canvas_height
        else:
            x, y = 200, 200

        theight = 15
        twidth = 7
        points = [x, y + theight, x - twidth, y - theight, x + twidth, y - theight]

        pin = self.canvas.create_polygon(points, fill=line_data["color"], outline="black")
        self.pins[line_data["text"]] = pin
        line_data["pin"] = pin

        if "last_pos" not in line_data:
            line_data["last_pos"] = (x, y)
        if "rel_pos" not in line_data:
            line_data["rel_pos"] = (x / canvas_width, y / canvas_height)

        self.make_draggable(pin, line_data)

    def make_draggable(self, pin, line_data):
        def start_drag(event):
            self.drag_data = {"x": event.x, "y": event.y}

        def do_drag(event):
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.canvas.move(pin, dx, dy)
            self.drag_data = {"x": event.x, "y": event.y}

            coords = self.canvas.coords(pin)
            x = sum(coords[0::2]) / 3
            y = sum(coords[1::2]) / 3
            line_data["last_pos"] = (x, y)
            line_data["rel_pos"] = (x / self.canvas.winfo_width(), y / self.canvas.winfo_height())

        self.canvas.tag_bind(pin, "<ButtonPress-1>", start_drag)
        self.canvas.tag_bind(pin, "<B1-Motion>", do_drag)

    def toggle_pin(self, line_data):
        if line_data["var"].get():
            self.schedule_pin_creation(line_data)
        else:
            if line_data["pin"]:
                self.canvas.delete(line_data["pin"])
                line_data["pin"] = None

    def save_state(self):
        state = []
        for line in self.lines:
            state.append({
                "text": line["text"],
                "checked": line["var"].get(),
                "color": line["color"],
                "rel_pos": line.get("rel_pos", (0.5, 0.5)),
                "last_pos": line.get("last_pos", (0.5, 0.5))
            })
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

    def load_state(self):
        if not os.path.exists(STATE_FILE):
            return
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        for item in state:
            self.add_line(item["text"], item["checked"], item["color"])
            line_data = self.lines[-1]
            if item.get("rel_pos"):
                line_data["rel_pos"] = tuple(item["rel_pos"])
            if item.get("last_pos"):
                line_data["last_pos"] = tuple(item["last_pos"])

    def on_close(self):
        self.save_state()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PinMapperApp(root)
    root.mainloop()
