import argparse

import pandas as pd


def clean_labels(input_path: str, output_path: str, base_url: str) -> None:
    df = pd.read_csv(input_path)
    normalized_base = f"{base_url.rstrip('/')}/wiki/"
    df["Label"] = df["Label"].str.replace('"', "", regex=False)
    df["Label"] = df["Label"].str.replace(normalized_base, "", regex=False)
    df.to_csv(output_path, index=False)
    print(f"Archivo procesado guardado en '{output_path}'.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Limpia las labels del CSV de enlaces generado por el pipeline."
    )
    parser.add_argument("--input", default="data/links/links_nodes.csv")
    parser.add_argument("--output", default="data/links/links_nodes_clean.csv")
    parser.add_argument("--base-url", default="https://en.wikipedia.org")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    clean_labels(args.input, args.output, args.base_url)
