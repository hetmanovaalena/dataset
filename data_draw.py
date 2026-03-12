import tkinter as tk
from tkinter import ttk, colorchooser
from datetime import datetime
from io import BytesIO

import dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageTk, ImageDraw


STUDENT_ID = "70172833"
DEFAULT_CMAP = "magma"

CMAP_LIST = [
    "viridis", "plasma", "inferno", "magma", "cividis",
    "Greys", "Purples", "Blues", "Greens", "Oranges",
    "Reds", "YlOrBr", "YlOrRd", "OrRd", "PuRd",
    "RdPu", "BuPu", "GnBu", "PuBu", "YlGnBu",
    "PuBuGn", "BuGn", "YlGn", "binary", "gist_yarg",
    "spring", "summer", "autumn", "winter"
]


def digital_root(value: str) -> int:
    total = sum(int(ch) for ch in value if ch.isdigit())
    while total >= 10:
        total = sum(int(ch) for ch in str(total))
    return total


def default_line_width(student_id: str) -> int:
    return digital_root(student_id) // 2 + 5


def default_brush_color(student_id: str) -> str:
    last_six = student_id[-6:]
    r = int(last_six[0:2])
    g = int(last_six[2:4])
    b = int(last_six[4:6])
    return f"#{r:02X}{g:02X}{b:02X}"


def get_countable_columns():
    if hasattr(dataset, "COUNTABLE_COLUMNS"):
        return [col for col in dataset.COUNTABLE_COLUMNS if col in dataset.df.columns]

    numeric_cols = dataset.df.select_dtypes(include=["number"]).columns.tolist()
    if "Unnamed: 0" in numeric_cols:
        numeric_cols.remove("Unnamed: 0")
    return numeric_cols


def get_categorical_columns():
    if hasattr(dataset, "CATEGORICAL_COLUMNS"):
        return [col for col in dataset.CATEGORICAL_COLUMNS if col in dataset.df.columns]

    all_cols = dataset.df.columns.tolist()
    countable = get_countable_columns()
    return [col for col in all_cols if col not in countable and col != "Unnamed: 0"]


def get_all_plot_columns():
    countable = get_countable_columns()
    categorical = get_categorical_columns()
    result = []
    for col in countable + categorical:
        if col not in result:
            result.append(col)
    return result


class DataDrawApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("data_draw")
        self.root.geometry("1080x760")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.df = dataset.df
        self.countable_columns = get_countable_columns()
        self.categorical_columns = get_categorical_columns()
        self.all_columns = get_all_plot_columns()

        if len(self.all_columns) < 2:
            raise ValueError("Для построения графиков требуется минимум две колонки.")

        self.x_column = self.all_columns[0]
        self.y_column = self.all_columns[1]
        self.current_cmap = tk.StringVar(value=DEFAULT_CMAP)

        self.draw_mode = False
        self.is_drawing = False
        self.current_line_points = []
        self.current_line_canvas_id = None
        self.finished_lines = []

        self.brush_color = default_brush_color(STUDENT_ID)
        self.line_width = tk.IntVar(value=default_line_width(STUDENT_ID))

        self.base_image_pil = None
        self.base_photo = None

        self.build_interface()
        self.bind_events()
        self.update_plot()

    def build_interface(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.top_frame = tk.Frame(self.root, padx=5, pady=5)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.left_frame = tk.Frame(self.root, padx=5, pady=5)
        self.left_frame.grid(row=1, column=0, sticky="ns")

        self.center_frame = tk.Frame(self.root, padx=5, pady=5)
        self.center_frame.grid(row=1, column=1, sticky="nsew")

        self.bottom_frame = tk.Frame(self.root, padx=5, pady=5)
        self.bottom_frame.grid(row=2, column=1, sticky="ew")

        self.save_frame = tk.Frame(self.root, padx=5, pady=5)
        self.save_frame.grid(row=2, column=0, sticky="sw")

        tk.Label(self.top_frame, text="cmap:").pack(side="left", padx=(0, 6))

        self.cmap_box = ttk.Combobox(
            self.top_frame,
            textvariable=self.current_cmap,
            values=CMAP_LIST,
            state="readonly",
            width=16
        )
        self.cmap_box.pack(side="left", padx=(0, 14))
        self.cmap_box.bind("<<ComboboxSelected>>", lambda event: self.update_plot())

        self.draw_button = tk.Button(
            self.top_frame,
            text="Рисование",
            width=14,
            command=self.toggle_draw_mode
        )
        self.draw_button.pack(side="left", padx=(0, 10))

        tk.Label(self.top_frame, text="Толщина:").pack(side="left")
        self.width_spinbox = tk.Spinbox(
            self.top_frame,
            from_=1,
            to=50,
            width=5,
            textvariable=self.line_width
        )
        self.width_spinbox.pack(side="left", padx=(4, 14))

        tk.Label(self.top_frame, text="Цвет:").pack(side="left")
        self.color_button = tk.Button(
            self.top_frame,
            width=3,
            bg=self.brush_color,
            command=self.choose_color
        )
        self.color_button.pack(side="left")

        self.graph_canvas = tk.Canvas(
            self.center_frame,
            width=760,
            height=560,
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        self.graph_canvas.pack(fill="both", expand=True)

        for col in self.all_columns:
            btn = tk.Button(
                self.left_frame,
                text=col,
                width=20,
                command=lambda c=col: self.set_y_column(c)
            )
            btn.pack(pady=2, fill="x")

        for col in self.all_columns:
            btn = tk.Button(
                self.bottom_frame,
                text=col,
                width=18,
                command=lambda c=col: self.set_x_column(c)
            )
            btn.pack(side="left", padx=2)

        save_btn = tk.Button(
            self.save_frame,
            text="Сохранить",
            width=14,
            command=self.save_graph
        )
        save_btn.pack(anchor="w")

    def bind_events(self):
        self.graph_canvas.bind("<Button-1>", self.on_left_press)
        self.graph_canvas.bind("<B1-Motion>", self.on_left_motion)
        self.graph_canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.graph_canvas.bind("<Button-3>", self.on_right_click)

        self.root.bind("<Control-z>", self.undo_last_line)
        self.root.bind("<Control-Z>", self.undo_last_line)

    def is_countable(self, column_name: str) -> bool:
        return column_name in self.countable_columns

    def is_categorical(self, column_name: str) -> bool:
        return column_name in self.categorical_columns

    def get_colors(self, n: int):
        cmap = plt.get_cmap(self.current_cmap.get())
        if n <= 1:
            return [cmap(0.6)]
        return [cmap(i / max(n - 1, 1)) for i in range(n)]

    def choose_color(self):
        selected = colorchooser.askcolor(color=self.brush_color, title="Выберите цвет кисти")
        if selected[1]:
            self.brush_color = selected[1]
            self.color_button.configure(bg=self.brush_color)

    def toggle_draw_mode(self):
        if self.draw_mode:
            self.disable_draw_mode()
        else:
            self.enable_draw_mode()

    def enable_draw_mode(self):
        self.draw_mode = True
        self.draw_button.configure(relief="sunken")
        try:
            self.graph_canvas.configure(cursor="pencil")
        except tk.TclError:
            self.graph_canvas.configure(cursor="crosshair")

    def disable_draw_mode(self):
        self.draw_mode = False
        self.is_drawing = False
        self.current_line_points = []
        self.current_line_canvas_id = None
        self.draw_button.configure(relief="raised")
        self.graph_canvas.configure(cursor="")

    def set_x_column(self, column_name: str):
        self.disable_draw_mode()
        self.x_column = column_name
        self.update_plot()

    def set_y_column(self, column_name: str):
        self.disable_draw_mode()
        self.y_column = column_name
        self.update_plot()

    def create_figure(self):
        fig, ax = plt.subplots(figsize=(7.6, 5.6), dpi=100)

        x_col = self.x_column
        y_col = self.y_column

        x_is_num = self.is_countable(x_col)
        y_is_num = self.is_countable(y_col)
        x_is_cat = self.is_categorical(x_col)
        y_is_cat = self.is_categorical(y_col)

        if x_col == y_col and x_is_num:
            series = self.df[x_col].dropna()
            counts, bins, patches = ax.hist(series, bins=10, edgecolor="black")
            colors = self.get_colors(len(patches))
            for patch, color in zip(patches, colors):
                patch.set_facecolor(color)

            ax.set_xlabel(x_col)
            ax.set_ylabel("Частота")
            ax.set_title(f"Гистограмма: {x_col}")
            ax.grid(True, alpha=0.3)

        elif x_col == y_col and x_is_cat:
            counts = self.df[x_col].astype(str).value_counts(dropna=False)
            colors = self.get_colors(len(counts))
            ax.pie(
                counts.values,
                labels=counts.index.tolist(),
                colors=colors,
                autopct="%1.1f%%"
            )
            ax.set_title(f"Круговая диаграмма: {x_col}")

        elif x_is_cat:
            counts = self.df[x_col].astype(str).value_counts(dropna=False)
            colors = self.get_colors(len(counts))
            ax.bar(counts.index.tolist(), counts.values, color=colors)
            ax.set_xlabel(x_col)
            ax.set_ylabel("Количество")
            ax.set_title(f"Столбчатая диаграмма: {x_col}")
            ax.tick_params(axis="x", rotation=25)
            ax.grid(True, alpha=0.3, axis="y")

        elif x_is_num and y_is_cat:
            temp_df = self.df[[x_col, y_col]].dropna().copy()
            temp_df[y_col] = temp_df[y_col].astype(str)

            grouped_values = []
            labels = []
            for category, group in temp_df.groupby(y_col):
                labels.append(str(category))
                grouped_values.append(group[x_col].values)

            bp = ax.boxplot(grouped_values, labels=labels, patch_artist=True)
            colors = self.get_colors(len(bp["boxes"]))
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)

            ax.set_xlabel(y_col)
            ax.set_ylabel(x_col)
            ax.set_title(f"Коробочная диаграмма: {x_col} / {y_col}")
            ax.tick_params(axis="x", rotation=25)
            ax.grid(True, alpha=0.3)

        else:
            temp_df = self.df[[x_col, y_col]].dropna()
            color = self.get_colors(1)[0]
            ax.scatter(temp_df[x_col], temp_df[y_col], color=color)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(f"{x_col} / {y_col}")
            ax.grid(True, alpha=0.3)

        fig.tight_layout()
        return fig

    def update_plot(self):
        fig = self.create_figure()

        buffer = BytesIO()
        fig.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)

        self.base_image_pil = Image.open(buffer).convert("RGBA")
        self.base_photo = ImageTk.PhotoImage(self.base_image_pil)

        self.graph_canvas.delete("all")
        self.graph_canvas.config(
            width=self.base_photo.width(),
            height=self.base_photo.height()
        )
        self.graph_canvas.create_image(0, 0, anchor="nw", image=self.base_photo)

        self.finished_lines.clear()
        self.current_line_points = []
        self.current_line_canvas_id = None

    def on_left_press(self, event):
        if not self.draw_mode:
            return

        if not self.point_on_graph(event.x, event.y):
            return

        self.is_drawing = True
        self.current_line_points = [(event.x, event.y)]

        size = self.line_width.get()
        self.current_line_canvas_id = self.graph_canvas.create_rectangle(
            event.x,
            event.y,
            event.x + size,
            event.y + size,
            outline=self.brush_color,
            fill=self.brush_color
        )

    def on_left_motion(self, event):
        if not self.draw_mode or not self.is_drawing:
            return

        if not self.point_on_graph(event.x, event.y):
            return

        self.current_line_points.append((event.x, event.y))

        size = self.line_width.get()
        self.graph_canvas.create_rectangle(
            event.x,
            event.y,
            event.x + size,
            event.y + size,
            outline=self.brush_color,
            fill=self.brush_color
        )

    def on_left_release(self, event):
        if not self.draw_mode or not self.is_drawing:
            return

        self.is_drawing = False

        if self.current_line_points:
            line_record = {
                "points": self.current_line_points.copy(),
                "color": self.brush_color,
                "width": self.line_width.get()
            }
            self.finished_lines.append(line_record)

        self.current_line_points = []
        self.current_line_canvas_id = None

    def on_right_click(self, event):
        if self.draw_mode:
            self.disable_draw_mode()

    def point_on_graph(self, x: int, y: int) -> bool:
        width = self.graph_canvas.winfo_width()
        height = self.graph_canvas.winfo_height()
        return 0 <= x < width and 0 <= y < height

    def undo_last_line(self, event=None):
        if self.is_drawing:
            return

        if not self.finished_lines:
            return

        self.finished_lines.pop()
        self.redraw_canvas_with_lines()

    def redraw_canvas_with_lines(self):
        if self.base_photo is None:
            return

        self.graph_canvas.delete("all")
        self.graph_canvas.create_image(0, 0, anchor="nw", image=self.base_photo)

        for line in self.finished_lines:
            self.draw_line_on_canvas(
                line["points"],
                line["color"],
                line["width"]
            )

    def draw_line_on_canvas(self, points, color, width):
        for x, y in points:
            self.graph_canvas.create_rectangle(
                x,
                y,
                x + width,
                y + width,
                outline=color,
                fill=color
            )

    def save_graph(self):
        if self.base_image_pil is None:
            return

        image_to_save = self.base_image_pil.copy()
        draw = ImageDraw.Draw(image_to_save)

        for line in self.finished_lines:
            color = line["color"]
            width = line["width"]

            for x, y in line["points"]:
                draw.rectangle(
                    [x, y, x + width, y + width],
                    fill=color,
                    outline=color
                )

        filename = datetime.now().strftime("graph%H_%M_%S.png")
        image_to_save.save(filename, format="PNG")

    def on_close(self):
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DataDrawApp(root)
    root.mainloop()
