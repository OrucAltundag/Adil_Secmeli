r"""AHP kriter agirliklarini hesaplayan ornek calistirilabilir script.

Calistir:
    env\Scripts\python.exe app\scripts\ahp_weights_demo.py
"""

from __future__ import annotations

import numpy as np

from app.services.calculation import KararMotoru


def main() -> None:
    motor = KararMotoru()

    # 1. Saaty kurallarina gore 4x4 ikili karsilastirma matrisi.
    # Satir/sutun sirasi: Basari, Trend, Populerlik, Anket
    matrix = motor.ahp_matrisi()

    # 2. Ana ozvektor tabanli agirliklar.
    weights = np.array(motor.ahp_calistir(), dtype=float)

    # 3. Tutarlilik hesabi.
    cr, valid, lambda_max = motor.ahp_tutarlilik_kontrolu(matris=matrix, agirliklar=weights)

    criteria = ["Basari", "Trend", "Populerlik", "Anket"]

    print("AHP Ikili Karsilastirma Matrisi")
    print("=" * 36)
    print(matrix)
    print()

    print("Kriter Agirliklari")
    print("=" * 36)
    for name, weight in zip(criteria, weights):
        print(f"{name:12}: {weight:.6f}  (%{weight * 100:.2f})")
    print()

    print("Tutarlilik Analizi")
    print("=" * 36)
    print(f"lambda_max : {lambda_max:.6f}")
    print(f"CR         : {cr:.6f}")
    print(f"Gecerli mi : {'Evet' if valid else 'Hayir'}")


if __name__ == "__main__":
    main()
