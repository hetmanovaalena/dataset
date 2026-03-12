import io
from contextlib import redirect_stdout

import pandas as pd

# Глобальная переменная, доступная при импорте модуля
df = pd.read_csv("dataset.csv")

# Явное разделение колонок по смыслу данных
COUNTABLE_COLUMNS = [
    "Screen Size (inches)",
    "RAM (GB)",
    "Storage (GB)",
    "Price (USD)",
    "Rating",
]

CATEGORICAL_COLUMNS = [
    "Processor",
    "Camera Setup",
    "Unnamed: 0",
]


def build_report() -> str:
    buffer = io.StringIO()

    with redirect_stdout(buffer):
        # 1. Размер набора данных
        print(df.shape)
        print()

        # 2. Информация о типах данных в колонках
        df.info()
        print()

        # 3. Количество незаполненных ячеек
        print(df.isna().sum())
        print()

        # 4. Статистическая информация по счётным колонкам
        print("Колонка>\tсреднее\tмедиана\tотклонение")
        for column in COUNTABLE_COLUMNS:
            mean_value = df[column].mean()
            median_value = df[column].median()
            std_value = df[column].std()

            print(
                f"{column}>\t"
                f"{mean_value:.2f};\t"
                f"{median_value:.2f};\t"
                f"{std_value:.2f}"
            )
        print()

        # 5. Частотные распределения категориальных колонок
        for column in CATEGORICAL_COLUMNS:
            print(column)
            print(df[column].value_counts(dropna=False))
            print()

    return buffer.getvalue()


if __name__ == "__main__":
    report_text = build_report()

    # Вывод в консоль
    print(report_text, end="")

    # Дублирование в report.txt
    with open("report.txt", "w", encoding="utf-8") as file:
        file.write(report_text)
