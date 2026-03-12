import tkinter as tk
from tkinter import ttk
from datetime import datetime
from io import BytesIO

import dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageTk


DEFAULT_CMAP = "magma"  # для фамилии на букву Г

CMAP_LIST = [
    "viridis", "plasma", "inferno", "magma", "cividis",
    "Greys", "Purples", "Blues", "Greens", "Oranges",
    "Reds", "YlOrBr", "YlOrRd", "OrRd", "PuRd",
    "RdPu", "BuPu", "GnBu", "PuBu", "YlGnBu",
    "PuBuGn", "BuGn", "YlGn", "binary", "gist_yarg",
    "spring", "summer", "autumn", "winter"
]


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
    categorical = [col for col in all_cols if col not in countable]

    # если технический индекс попадёт сюда, оставим только если он реально нужен
    return categorical


def get_all_plot_columns():
    countable = get_countable_columns()
    categorical = get_categorical_columns()

    # порядок: сначала счётные, затем категориальные
    result = []
    for col in countable + categorical:
        if col not in result:
            result.append(col)
    return result


class DataVisualApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("data_visual")
        self.root.geometry("1000x720")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.df = dataset.df
        self.countable_columns = get_countable_columns()
        self.categorical_columns = get_categorical_columns()
        self.all_columns = get_all_plot_columns()

        if len(self.all_columns) < 2:
            raise ValueError("Для построения графиков требуется минимум две колонки.")

        self.x_column = self.all_columns[0]
        self.y_column = self.all_columns[1] if len(self.all_columns) > 1 else self.all_columns[0]

        self.current_cmap = tk.StringVar(value=DEFAULT_CMAP)
        self.graph_photo = None

        self.build_interface()
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
        self.cmap_box.pack(side="left")
        self.cmap_box.bind("<<ComboboxSelected>>", lambda event: self.update_plot())

        self.graph_canvas = tk.Canvas(
            self.center_frame,
            width=700,
            height=550,
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        self.graph_canvas.pack(fill="both", expand=True)

        # Кнопки выбора Y
        for col in self.all_columns:
            btn = tk.Button(
                self.left_frame,
                text=col,
                width=18,
                command=lambda c=col: self.set_y_column(c)
            )
            btn.pack(pady=2, fill="x")

        # Кнопки выбора X
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

    def is_countable(self, column_name: str) -> bool:
        return column_name in self.countable_columns

    def is_categorical(self, column_name: str) -> bool:
        return column_name in self.categorical_columns

    def set_x_column(self, column_name: str):
        self.x_column = column_name
        self.update_plot()

    def set_y_column(self, column_name: str):
        self.y_column = column_name
        self.update_plot()

    def get_colors(self, n: int):
        cmap = plt.get_cmap(self.current_cmap.get())
        if n <= 1:
            return [cmap(0.6)]
        return [cmap(i / max(n - 1, 1)) for i in range(n)]

    def create_figure(self):
        fig, ax = plt.subplots(figsize=(7.0, 5.5), dpi=100)

        x_col = self.x_column
        y_col = self.y_column

        x_is_num = self.is_countable(x_col)
        y_is_num = self.is_countable(y_col)
        x_is_cat = self.is_categorical(x_col)
        y_is_cat = self.is_categorical(y_col)

        # 1. Одинаковая числовая колонка -> гистограмма
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

        # 2. Одинаковая категориальная колонка -> круговая диаграмма
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

        # 3. X категориальная, Y любая другая -> столбчатая диаграмма
        elif x_is_cat:
            counts = self.df[x_col].astype(str).value_counts(dropna=False)
            colors = self.get_colors(len(counts))

            ax.bar(counts.index.tolist(), counts.values, color=colors)
            ax.set_xlabel(x_col)
            ax.set_ylabel("Количество")
            ax.set_title(f"Столбчатая диаграмма: {x_col}")
            ax.tick_params(axis="x", rotation=25)
            ax.grid(True, alpha=0.3, axis="y")

        # 4. X числовая, Y категориальная -> коробочная диаграмма
        elif x_is_num and y_is_cat:
            temp_df = self.df[[x_col, y_col]].dropna().copy()
            temp_df[y_col] = temp_df[y_col].astype(str)

            grouped_values = []
            labels = []

            for category, group in temp_df.groupby(y_col):
                labels.append(str(category))
                grouped_values.append(group[x_col].values)

            bp = ax.boxplot(
                grouped_values,
                labels=labels,
                patch_artist=True
            )

            colors = self.get_colors(len(bp["boxes"]))
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)

            ax.set_xlabel(y_col)
            ax.set_ylabel(x_col)
            ax.set_title(f"Коробочная диаграмма: {x_col} / {y_col}")
            ax.tick_params(axis="x", rotation=25)
            ax.grid(True, alpha=0.3)

        # 5. Иначе -> точечная диаграмма
        else:
            temp_df = self.df[[x_col, y_col]].dropna()
            color = self.get_colors(1)[0]

            ax.scatter(
                temp_df[x_col],
                temp_df[y_col],
                color=color
            )

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

        image = Image.open(buffer)
        self.graph_photo = ImageTk.PhotoImage(image)

        self.graph_canvas.delete("all")
        self.graph_canvas.config(
            width=self.graph_photo.width(),
            height=self.graph_photo.height()
        )
        self.graph_canvas.create_image(0, 0, anchor="nw", image=self.graph_photo)

    def save_graph(self):
        fig = self.create_figure()
        filename = datetime.now().strftime("graph%H_%M_%S.png")
        fig.savefig(filename, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)

    def on_close(self):
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DataVisualApp(root)
    root.mainloop()
