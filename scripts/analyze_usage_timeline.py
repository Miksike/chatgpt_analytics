import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main():
    root = find_workspace_root()
    in_path = root / "working_data" / "messages.csv"
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)

    df = pd.read_csv(in_path)

    # Tüüpide korrastus
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Hoiame ainult sisulised kasutaja + assistendi read
    df = df[df["role"].isin(["user", "assistant"])].copy()
    df = df[df["timestamp"].notna()].copy()

    # Teeme timestampist indeksiga ajatelje
    df = df.sort_values("timestamp").set_index("timestamp")

    # Resample
    daily = df.resample("D").size()
    weekly = df.resample("W-MON").size()
    monthly = df.resample("MS").size()
    yearly = df.resample("YS").size()

    # Salvesta tabelid CSV-na
    daily.to_csv(reports_dir / "usage_daily.csv", header=["message_count"])
    weekly.to_csv(reports_dir / "usage_weekly.csv", header=["message_count"])
    monthly.to_csv(reports_dir / "usage_monthly.csv", header=["message_count"])
    yearly.to_csv(reports_dir / "usage_yearly.csv", header=["message_count"])

    # Päevane graafik
    plt.figure(figsize=(14, 6))
    plt.plot(daily.index, daily.values)
    plt.title("ChatGPT kasutus ajas – päevane sõnumite arv")
    plt.xlabel("Kuupäev")
    plt.ylabel("Sõnumite arv")
    plt.tight_layout()
    plt.savefig(reports_dir / "usage_daily.png", dpi=150)
    plt.close()

    # Nädalane graafik
    plt.figure(figsize=(14, 6))
    plt.plot(weekly.index, weekly.values)
    plt.title("ChatGPT kasutus ajas – nädalane sõnumite arv")
    plt.xlabel("Nädal")
    plt.ylabel("Sõnumite arv")
    plt.tight_layout()
    plt.savefig(reports_dir / "usage_weekly.png", dpi=150)
    plt.close()

    # Kuine graafik
    plt.figure(figsize=(14, 6))
    plt.plot(monthly.index, monthly.values)
    plt.title("ChatGPT kasutus ajas – kuine sõnumite arv")
    plt.xlabel("Kuu")
    plt.ylabel("Sõnumite arv")
    plt.tight_layout()
    plt.savefig(reports_dir / "usage_monthly.png", dpi=150)
    plt.close()

    # Aastane graafik
    plt.figure(figsize=(14, 6))
    plt.plot(yearly.index, yearly.values)
    plt.title("ChatGPT kasutus ajas – aastane sõnumite arv")
    plt.xlabel("Aasta")
    plt.ylabel("Sõnumite arv")
    plt.tight_layout()
    plt.savefig(reports_dir / "usage_yearly.png", dpi=150)
    plt.close()

    print("Valmis. Loodi failid:")
    print(f" - {reports_dir / 'usage_daily.csv'}")
    print(f" - {reports_dir / 'usage_weekly.csv'}")
    print(f" - {reports_dir / 'usage_monthly.csv'}")
    print(f" - {reports_dir / 'usage_yearly.csv'}")
    print(f" - {reports_dir / 'usage_daily.png'}")
    print(f" - {reports_dir / 'usage_weekly.png'}")
    print(f" - {reports_dir / 'usage_monthly.png'}")
    print(f" - {reports_dir / 'usage_yearly.png'}")


if __name__ == "__main__":
    main()