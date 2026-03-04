import argparse

import pandas as pd


def analizar_modularidad(csv_path: str, top_n: int = 10) -> None:
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: El archivo '{csv_path}' no se encontro.")
        return
    except pd.errors.EmptyDataError:
        print(f"Error: El archivo '{csv_path}' esta vacio.")
        return
    except pd.errors.ParserError:
        print(f"Error: El archivo '{csv_path}' no esta bien formateado.")
        return

    columnas_necesarias = {"modularity_class", "degree", "Id", "Label"}
    if not columnas_necesarias.issubset(df.columns):
        print(f"Error: El archivo CSV debe contener las columnas: {columnas_necesarias}")
        return

    total_nodos = len(df)
    if total_nodos == 0:
        print("El archivo CSV no contiene nodos.")
        return

    grupos = df.groupby("modularity_class").size().reset_index(name="size")
    grupos = grupos.sort_values(by="size", ascending=False)
    grupos_top = grupos.head(top_n)

    print(f"\nMostrando las top {min(top_n, len(grupos_top))} comunidades mas relevantes:\n")

    for display_index, (_, row) in enumerate(grupos_top.iterrows(), start=1):
        clase = row["modularity_class"]
        size = row["size"]
        grupo = df[df["modularity_class"] == clase]
        porcentaje = (size / total_nodos) * 100

        print(f"=== Comunidad {display_index} ===")
        print(f"Clase de modularidad: {clase}")
        print(f"Cantidad de nodos: {size}")
        print(f"Porcentaje de la clase: {porcentaje:.2f}%")

        top_nodos = grupo.sort_values(by="degree", ascending=False).head(10)
        print("\nTop 10 nodos con mayor grado:")
        print(top_nodos[["Id", "Label", "degree"]].to_string(index=False))
        print("\n" + "-" * 50 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resume las comunidades principales a partir de un CSV con metricas."
    )
    parser.add_argument("--csv", default="data/words/words_metrics_nodes.csv")
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analizar_modularidad(args.csv, top_n=args.top_n)
