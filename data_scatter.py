import tkinter as tk
from datetime import datetime
from io import BytesIO

import dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageTk


STUDENT_ID = "70172833"


def digital_root(value: str) -> int:
    total = sum(int(ch) for ch in value if ch.isdigit())
    while total >= 10:
        total = sum(int(ch) for ch in str(total))
    return total


# Соответствие маркеров по таблице из методички
MARKER_MAP = {
    1: "^",
    2: ">",
    3: "o",
    4: "s",
    5: "P",
    6: "h",
    7: "*",
    8: "p",
    9: "<",
}

MARKER_STYLE = MARKER_MAP[digital_root(STUDENT_ID)]


def get_numeric_columns():
    # Если в dataset.py уже есть явный список счётных колонок — используем его
    if hasattr(dataset, "COUNTABLE_COLUMNS"):
        return [col for col in dataset.COUNTABLE_COLUMNS if col in dataset.df.columns]

    # Иначе определяем автоматически
    numeric_cols = dataset.df.select_dtypes(include=["number"]).columns.tolist()

    # Исключаем технический индекс, если он есть
    if "Unnamed: 0" in numeric_cols:
        numeric_cols.remove("Unnamed: 0")

    return numeric_cols


class DataScatterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("data_scatter")
        self.root.geometry("900x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.df = dataset.df
        self.numeric_columns = get_numeric_columns()

        if len(self.numeric_columns) < 2:
            raise ValueError("Для построения диаграммы требуется минимум две числовые колонки.")

        self.x_column = self.numeric_columns[0]
        self.y_column = self.numeric_columns[1]

        self.graph_photo = None

        self.build_interface()
        self.update_plot()

    def build_interface(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.left_frame = tk.Frame(self.root, padx=5, pady=5)
        self.left_frame.grid(row=0, column=0, sticky="ns")

        self.center_frame = tk.Frame(self.root, padx=5, pady=5)
        self.center_frame.grid(row=0, column=1, sticky="nsew")

        self.bottom_frame = tk.Frame(self.root, padx=5, pady=5)
        self.bottom_frame.grid(row=1, column=1, sticky="ew")

        self.save_frame = tk.Frame(self.root, padx=5, pady=5)
        self.save_frame.grid(row=1, column=0, sticky="sw")

        # Canvas для отображения изображения графика
        self.graph_canvas = tk.Canvas(
            self.center_frame,
            width=650,
            height=500,
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        self.graph_canvas.pack(fill="both", expand=True)

        # Кнопки выбора Y
        for col in self.numeric_columns:
            btn = tk.Button(
                self.left_frame,
                text=col,
                width=18,
                command=lambda c=col: self.set_y_column(c)
            )
            btn.pack(pady=2, fill="x")

        # Кнопки выбора X
        for col in self.numeric_columns:
            btn = tk.Button(
                self.bottom_frame,
                text=col,
                width=18,
                command=lambda c=col: self.set_x_column(c)
            )
            btn.pack(side="left", padx=2)

        # Кнопка сохранения
        save_btn = tk.Button(
            self.save_frame,
            text="Сохранить",
            width=14,
            command=self.save_graph
        )
        save_btn.pack(anchor="w")

    def set_x_column(self, column_name: str):
        self.x_column = column_name
        self.update_plot()

    def set_y_column(self, column_name: str):
        self.y_column = column_name
        self.update_plot()

    def create_figure(self):
        fig, ax = plt.subplots(figsize=(6.5, 5), dpi=100)

        plot_df = self.df[[self.x_column, self.y_column]].dropna()

        ax.scatter(
            plot_df[self.x_column],
            plot_df[self.y_column],
            marker=MARKER_STYLE
        )

        ax.set_xlabel(self.x_column)
        ax.set_ylabel(self.y_column)
        ax.set_title(f"{self.x_column} / {self.y_column}")
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
    app = DataScatterApp(root)
    root.mainloop()
