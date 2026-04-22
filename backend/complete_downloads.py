"""complete_downloads.py — Descarga archivos faltantes de la bateria."""
import requests, json, os, sys

BASE = "http://127.0.0.1:8000"
EMAIL = "backend.apisperu.verify.20260411_140659@printflow.pe"
PASS = "test123456"
OUT = "pruebas qwen"

def login():
    r = requests.post(f"{BASE}/token", data={"username":EMAIL,"password":PASS,"grant_type":"password"}, timeout=10)
    return r.json()["access_token"]

def save(folder, name, content, binary=False):
    os.makedirs(folder, exist_ok=True)
    if binary:
        with open(os.path.join(folder, name), "wb") as f: f.write(content)
    else:
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False))

def main():
    hdr = {"Authorization": f"Bearer {login()}"}

    # Leer responses de cada carpeta para obtener document_id
    folders = {
        "01_boleta": None, "02_factura": None,
        "03_nota_credito": None, "04_nota_debito": None,
        "05_baja": None
    }

    for folder in folders:
        resp_file = os.path.join(OUT, folder, "response.json")
        if os.path.exists(resp_file):
            with open(resp_file, encoding="utf-8") as f:
                data = json.load(f)
            doc_id = data.get("document_id")
            serie = data.get("serie")
            correlativo = data.get("correlativo")
            folders[folder] = (doc_id, serie, correlativo)
            print(f"{folder}: doc_id={doc_id} serie={serie}-{correlativo}")

    # Descargar XML y PDF ApisPeru para nota_credito, nota_debito, baja
    for folder, info in folders.items():
        if not info: continue
        doc_id, serie, correlativo = info
        if not doc_id: continue

        prefix = folder.split("_")[1] if "_" in folder else folder
        # XML
        r = requests.post(f"{BASE}/facturacion/xml", headers=hdr, json={"comprobante_id":doc_id}, timeout=15)
        if r.status_code == 200:
            save(os.path.join(OUT, folder), f"{prefix}.xml", r.content, binary=True)
            print(f"  ✅ {folder}/{prefix}.xml descargado")
        else:
            print(f"  ⚠️  {folder}/{prefix}.xml -> {r.status_code}")

        # PDF ApisPeru
        r = requests.post(f"{BASE}/facturacion/pdf", headers=hdr, json={"comprobante_id":doc_id}, timeout=15)
        if r.status_code == 200:
            save(os.path.join(OUT, folder), f"{prefix}_apisperu.pdf", r.content, binary=True)
            print(f"  ✅ {folder}/{prefix}_apisperu.pdf descargado")
        else:
            print(f"  ⚠️  {folder}/{prefix}_apisperu.pdf -> {r.status_code}")

        # PDF Interno (nuestro diseño)
        r = requests.get(f"{BASE}/cotizaciones/{doc_id}/pdf", headers=hdr, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and data.get("url"):
                r2 = requests.get(data["url"], timeout=15)
                if r2.status_code == 200:
                    save(os.path.join(OUT, folder), f"{prefix}_interno.pdf", r2.content, binary=True)
                    print(f"  ✅ {folder}/{prefix}_interno.pdf descargado")
                else:
                    print(f"  ⚠️  {folder}/{prefix}_interno.pdf URL fetch -> {r2.status_code}")
            else:
                print(f"  ⚠️  {folder}/{prefix}_interno.pdf no URL en response")
        else:
            print(f"  ⚠️  {folder}/{prefix}_interno.pdf -> {r.status_code}")

    print("\nListo!")

if __name__ == "__main__":
    main()
