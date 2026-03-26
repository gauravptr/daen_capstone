import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def detect_delimiter(file_path: Path) -> str:
    with file_path.open("r", newline="") as f:
        sample = f.read(2048)
    try:
        return csv.Sniffer().sniff(sample).delimiter
    except Exception:
        return ";"


def main() -> None:
    csv_path = Path("./output/combined_full_scan.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing file: {csv_path}")

    delim = detect_delimiter(csv_path)
    data = np.genfromtxt(
        csv_path,
        delimiter=delim,
        names=True,
        dtype=None,
        encoding="utf-8",
    )

    names = data.dtype.names or ()
    x_col = "X" if "X" in names else "x"
    y_col = "Y" if "Y" in names else "y"
    z_col = "Z" if "Z" in names else "z"
    if not all(col in names for col in [x_col, y_col, z_col]):
        raise ValueError(f"Could not find x/y/z columns in {names}")

    x = np.asarray(data[x_col], dtype=float)
    y = np.asarray(data[y_col], dtype=float)
    z = np.asarray(data[z_col], dtype=float)

    fig = plt.figure(figsize=(11, 8), dpi=130)
    ax = fig.add_subplot(111, projection="3d")

    if "categoryID" in names:
        c = np.asarray(data["categoryID"], dtype=float)
        scatter = ax.scatter(x, y, z, c=c, s=0.7, cmap="tab20", alpha=0.8)
        fig.colorbar(scatter, ax=ax, label="categoryID")
    else:
        ax.scatter(x, y, z, c=z, s=0.7, cmap="viridis", alpha=0.8)

    ax.set_title("Combined Point Cloud (CSV)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
