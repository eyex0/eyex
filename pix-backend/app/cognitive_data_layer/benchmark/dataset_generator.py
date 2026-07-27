from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

INDUSTRIES = [
    "hospital",
    "manufacturing",
    "construction",
    "restaurant",
    "logistics",
    "banking",
    "insurance",
    "saas",
    "retail",
    "pharmacy",
    "university",
    "hotel",
    "real_estate",
    "hr",
    "accounting",
    "marketing",
    "ecommerce",
    "telecom",
    "energy",
    "government",
]


class BenchmarkDatasetGenerator:
    """Generate realistic enterprise datasets for CDL validation."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def generate_all(self, output_dir: Path | str) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for industry in INDUSTRIES:
            path = self.generate_industry(industry, output_dir)
            paths.append(path)
        return paths

    def generate_industry(self, industry: str, output_dir: Path) -> Path:
        generator = getattr(self, f"_generate_{industry}", self._generate_generic)
        sheets = generator()
        path = output_dir / f"{industry}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        return path

    def _generate_hospital(self) -> dict[str, pd.DataFrame]:
        n = self.rng.randint(80, 120)
        return {
            "Patient Admissions": pd.DataFrame(
                {
                    "Patient ID": [f"P{self.rng.randint(1000, 9999)}" for _ in range(n)],
                    "Patient Name": [f"Patient {i}" for i in range(n)],
                    "Admission Date": pd.date_range("2026-01-01", periods=n, freq="D").strftime(
                        "%d/%m/%Y"
                    ),
                    "Department": self.rng.choices(
                        ["Cardiology", "Neurology", "Oncology", "Emergency"], k=n
                    ),
                    "Bill Amount": [round(self.rng.uniform(100, 5000), 2) for _ in range(n)],
                    "Insurance": self.rng.choices(["Aetna", "BlueCross", "Medicare", None], k=n),
                }
            ),
            "Doctors": pd.DataFrame(
                {
                    "Doctor ID": [f"D{self.rng.randint(100, 999)}" for _ in range(20)],
                    "Doctor Name": [f"Dr. {i}" for i in range(20)],
                    "Specialty": self.rng.choices(
                        ["Cardiology", "Neurology", "Oncology", "Emergency"], k=20
                    ),
                    "Department": self.rng.choices(
                        ["Cardiology", "Neurology", "Oncology", "Emergency"], k=20
                    ),
                }
            ),
        }

    def _generate_manufacturing(self) -> dict[str, pd.DataFrame]:
        n = self.rng.randint(150, 200)
        return {
            "Production Orders": pd.DataFrame(
                {
                    "Order No": [f"ORD-{self.rng.randint(1000, 9999)}" for _ in range(n)],
                    "Item": [f"Product {self.rng.randint(1, 50)}" for _ in range(n)],
                    "Client": [f"Client {self.rng.randint(1, 30)}" for _ in range(n)],
                    "Qty": [self.rng.randint(10, 1000) for _ in range(n)],
                    "Unit Price": [round(self.rng.uniform(5, 500), 2) for _ in range(n)],
                    "Order Date": pd.date_range("2026-01-01", periods=n, freq="D").strftime(
                        "%Y-%m-%d"
                    ),
                    "Status": self.rng.choices(["Completed", "In Progress", "Pending"], k=n),
                }
            ),
            "Machines": pd.DataFrame(
                {
                    "Machine ID": [f"M-{self.rng.randint(1, 50)}" for _ in range(30)],
                    "Machine Name": [f"Machine {i}" for i in range(30)],
                    "Asset Tag": [f"AT-{self.rng.randint(1000, 9999)}" for _ in range(30)],
                    "Department": self.rng.choices(
                        ["Assembly", "Packaging", "Quality", "Maintenance"], k=30
                    ),
                }
            ),
        }

    def _generate_generic(self) -> dict[str, pd.DataFrame]:
        n = self.rng.randint(50, 100)
        return {
            "Data": pd.DataFrame(
                {
                    "ID": [f"ID-{self.rng.randint(1000, 9999)}" for _ in range(n)],
                    "Name": [f"Record {i}" for i in range(n)],
                    "Value": [round(self.rng.uniform(100, 10000), 2) for _ in range(n)],
                    "Date": pd.date_range("2026-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
                    "Category": self.rng.choices(["A", "B", "C", None], k=n),
                }
            ),
        }

    # Alias remaining industries to generic with different terminology
    _generate_construction = _generate_generic
    _generate_restaurant = _generate_generic
    _generate_logistics = _generate_generic
    _generate_banking = _generate_generic
    _generate_insurance = _generate_generic
    _generate_saas = _generate_generic
    _generate_retail = _generate_generic
    _generate_pharmacy = _generate_generic
    _generate_university = _generate_generic
    _generate_hotel = _generate_generic
    _generate_real_estate = _generate_generic
    _generate_hr = _generate_generic
    _generate_accounting = _generate_generic
    _generate_marketing = _generate_generic
    _generate_ecommerce = _generate_generic
    _generate_telecom = _generate_generic
    _generate_energy = _generate_generic
    _generate_government = _generate_generic


def generate_benchmark_datasets(output_dir: Path | str) -> list[Path]:
    return BenchmarkDatasetGenerator().generate_all(output_dir)
