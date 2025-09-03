import requests
import pandas as pd
import time
from datetime import datetime

BASE_URL = "https://tienda.mercadona.es/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9"
}

def get_category_products(cat_id: int) -> dict:
    r = requests.get(f"{BASE_URL}/categories/{cat_id}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def get_product_details(prod_id: str | int) -> dict:
    r = requests.get(f"{BASE_URL}/products/{prod_id}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    all_rows = []
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Categoria 77 = Huevos
    cat_data = get_category_products(77)

    for sub in cat_data.get("categories", []):
        for prod in sub.get("products", []):
            prod_id = prod["id"]
            try:
                details = get_product_details(prod_id)
                suppliers = [s["name"] for s in details.get("details", {}).get("suppliers", [])]
                suppliers_str = ", ".join(suppliers) if suppliers else None

                price = details.get("price_instructions", {}) or {}
                all_rows.append({
                    "date": today,
                    "product_id": prod_id,
                    "name": details.get("display_name"),
                    "origin": details.get("details", {}).get("origin"),
                    "suppliers": suppliers_str,
                    "packaging": details.get("packaging"),
                    "price_total": price.get("unit_price"),
                    "price_unit": price.get("bulk_price"),
                    "price_ref": price.get("reference_price"),
                    "ref_format": price.get("reference_format"),
                    "iva": price.get("iva"),
                    "url": details.get("share_url")
                })

                time.sleep(0.2)
            except Exception as e:
                print(f"[AVISO] Falha no produto {prod_id}: {e}")

    df = pd.DataFrame(all_rows)
    csv_name = f"mercadona_huevos_{today}.csv"
    xlsx_name = f"mercadona_huevos_{today}.xlsx"

    df.to_csv(csv_name, index=False, encoding="utf-8-sig")
    try:
        df.to_excel(xlsx_name, index=False)
    except Exception as e:
        print(f"[AVISO] Não foi possível salvar XLSX: {e}")

if __name__ == "__main__":
    main()
