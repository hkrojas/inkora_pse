"""get_internal_pdfs.py — Intenta descargar los PDFs internos (nuestro diseño)."""
import requests, json, os

BASE = "http://127.0.0.1:8000"
EMAIL = "backend.apisperu.verify.20260411_140659@printflow.pe"
PASS = "test123456"
OUT = "pruebas qwen"

def login():
    r = requests.post(f"{BASE}/token", data={"username":EMAIL,"password":PASS,"grant_type":"password"}, timeout=10)
    return r.json()["access_token"]

def main():
    hdr = {"Authorization": f"Bearer {login()}"}

    # Boleta y Factura tienen document_id
    docs = {
        "01_boleta": {"prefix":"boleta", "doc_id": None},
        "02_factura": {"prefix":"factura", "doc_id": None},
    }

    # Obtener document_ids de los response.json
    for folder in docs:
        resp_file = os.path.join(OUT, folder, "response.json")
        if os.path.exists(resp_file):
            with open(resp_file, encoding="utf-8") as f:
                data = json.load(f)
            docs[folder]["doc_id"] = data.get("document_id")

    for folder, cfg in docs.items():
        p = cfg["prefix"]
        doc_id = cfg["doc_id"]
        if not doc_id:
            print(f"⚠️  {folder}: sin document_id")
            continue

        # Intentar PDF interno varias veces (puede estar generando en background)
        for intento in range(3):
            r = requests.get(f"{BASE}/cotizaciones/{doc_id}/pdf", headers=hdr, timeout=15)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, dict) and d.get("url"):
                    r2 = requests.get(d["url"], timeout=15)
                    if r2.status_code == 200:
                        folder_path = os.path.join(OUT, folder)
                        os.makedirs(folder_path, exist_ok=True)
                        with open(os.path.join(folder_path, f"{p}_interno.pdf"), "wb") as f:
                            f.write(r2.content)
                        print(f"✅ {folder}/{p}_interno.pdf (intento {intento+1})")
                        break
                    else:
                        print(f"⚠️  {folder}/{p}_interno.pdf URL fetch {r2.status_code} (intento {intento+1})")
                else:
                    print(f"⚠️  {folder}/{p}_interno.pdf sin URL (intento {intento+1})")
            elif r.status_code == 202:
                print(f"⏳ {folder}/{p}_interno.pdf generando... (intento {intento+1})")
                import time; time.sleep(5)
            else:
                print(f"❌ {folder}/{p}_interno.pdf HTTP {r.status_code} (intento {intento+1})")
                break

if __name__ == "__main__":
    main()
