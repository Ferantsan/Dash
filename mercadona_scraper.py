import os
import time
import requests
import pandas as pd
from datetime import datetime

BASE_URL = "https://tienda.mercadona.es/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
}

def get_category_products(cat_id: int) -> dict:
    """Busca os produtos de uma categoria específica."""
    r = requests.get(f"{BASE_URL}/categories/{cat_id}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def get_product_details(prod_id: str | int) -> dict:
    """Busca detalhes completos de um produto (inclui fornecedores, origem, preços)."""
    r = requests.get(f"{BASE_URL}/products/{prod_id}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def main() -> None:
    rows = []
    today = datetime.utcnow().strftime("%Y-%m-%d")  # data na coluna e no nome do arquivo

    # Categoria 77 = Huevos
    cat_data = get_category_products(77)

    for sub in cat_data.get("categories", []):
        for prod in sub.get("products", []):
            prod_id = prod.get("id")
            try:
                details = get_product_details(prod_id)
                suppliers_list = details.get("details", {}).get("suppliers", []) or []
                suppliers = ", ".join([s.get("name", "") for s in suppliers_list]) or None

                price = details.get("price_instructions", {}) or {}

                rows.append({
                    "date": today,
                    "product_id": prod_id,
                    "name": details.get("display_name"),
                    "origin": details.get("details", {}).get("origin"),
                    "suppliers": suppliers,
                    "packaging": details.get("packaging"),
                    "price_total": price.get("unit_price"),
                    "price_unit": price.get("bulk_price"),
                    "price_ref": price.get("reference_price"),
                    "ref_format": price.get("reference_format"),
                    "iva": price.get("iva"),
                    "url": details.get("share_url"),
                })

                time.sleep(0.2)  # evita bater muito rápido na API

            except Exception as e:
                print(f"[AVISO] Falha no produto {prod_id}: {e}")

    df = pd.DataFrame(rows)

    # ----- salvar em SUBPASTA data/mercadona -----
    out_dir = "data/mercadona"
    os.makedirs(out_dir, exist_ok=True)

    csv_name = os.path.join(out_dir, f"mercadona_huevos_{today}.csv")
    xlsx_name = os.path.join(out_dir, f"mercadona_huevos_{today}.xlsx")

    df.to_csv(csv_name, index=False, encoding="utf-8-sig")
    try:
        # requer openpyxl (listado no requirements.txt)
        df.to_excel(xlsx_name, index=False)
    except Exception as e:
        print(f"[AVISO] Não foi possível salvar XLSX: {e}")

if __name__ == "__main__":
    main()

