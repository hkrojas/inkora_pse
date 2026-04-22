"""extract_all.py — Extrae XML, CDR, QR y PDFs de los responses de la bateria."""
import json, os, base64, requests, sys
from datetime import datetime

OUT = "pruebas qwen"
BASE = "http://127.0.0.1:8000"
EMAIL = "backend.apisperu.verify.20260411_140659@printflow.pe"
PASS = "test123456"

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

    # Documentos con document_id (boleta, factura)
    docs_con_id = {
        "01_boleta": {"prefix":"boleta", "needs_pdf":True},
        "02_factura": {"prefix":"factura", "needs_pdf":True},
    }

    # Documentos sin document_id pero con XML inline (nota credito, nota debito, baja)
    docs_sin_id = {
        "03_nota_credito": {"prefix":"nota_credito", "tipo":"note"},
        "04_nota_debito": {"prefix":"nota_debito", "tipo":"note"},
        "05_baja": {"prefix":"baja", "tipo":"voided"},
    }

    # ── Extraer de documentos con ID ──
    for folder, cfg in docs_con_id.items():
        p = cfg["prefix"]
        resp_file = os.path.join(OUT, folder, "response.json")
        if not os.path.exists(resp_file): continue
        with open(resp_file, encoding="utf-8") as f:
            data = json.load(f)

        doc_id = data.get("document_id")
        if not doc_id: continue

        # XML desde ApisPeru
        r = requests.post(f"{BASE}/facturacion/xml", headers=hdr, json={"comprobante_id":doc_id}, timeout=15)
        if r.status_code == 200:
            save(os.path.join(OUT, folder), f"{p}.xml", r.content, binary=True)
            print(f"✅ {folder}/{p}.xml")

        # PDF ApisPeru
        r = requests.post(f"{BASE}/facturacion/pdf", headers=hdr, json={"comprobante_id":doc_id}, timeout=15)
        if r.status_code == 200:
            save(os.path.join(OUT, folder), f"{p}_apisperu.pdf", r.content, binary=True)
            print(f"✅ {folder}/{p}_apisperu.pdf")

        # PDF interno (nuestro diseño)
        r = requests.get(f"{BASE}/cotizaciones/{doc_id}/pdf", headers=hdr, timeout=15)
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, dict) and d.get("url"):
                r2 = requests.get(d["url"], timeout=15)
                if r2.status_code == 200:
                    save(os.path.join(OUT, folder), f"{p}_interno.pdf", r2.content, binary=True)
                    print(f"✅ {folder}/{p}_interno.pdf (nuestro diseño)")

        # QR payload
        if data.get("qr_payload"):
            save(os.path.join(OUT, folder), f"{p}_qr.json", data["qr_payload"])
            print(f"✅ {folder}/{p}_qr.json")

        # CDR zip (base64)
        if data.get("cdr_zip_base64"):
            cdr = base64.b64decode(data["cdr_zip_base64"])
            save(os.path.join(OUT, folder), f"{p}_cdr.zip", cdr, binary=True)
            print(f"✅ {folder}/{p}_cdr.zip")

    # ── Extraer de documentos sin ID (XML inline en response) ──
    for folder, cfg in docs_sin_id.items():
        p = cfg["prefix"]
        resp_file = os.path.join(OUT, folder, "response.json")
        if not os.path.exists(resp_file): continue
        with open(resp_file, encoding="utf-8") as f:
            data = json.load(f)

        # XML directo del response
        if data.get("xml"):
            save(os.path.join(OUT, folder), f"{p}.xml", data["xml"])
            print(f"✅ {folder}/{p}.xml (extraído del response)")

        # CDR zip
        if data.get("cdr_zip_base64"):
            cdr = base64.b64decode(data["cdr_zip_base64"])
            save(os.path.join(OUT, folder), f"{p}_cdr.zip", cdr, binary=True)
            print(f"✅ {folder}/{p}_cdr.zip")

        # QR payload
        if data.get("qr_payload"):
            save(os.path.join(OUT, folder), f"{p}_qr.json", data["qr_payload"])
            print(f"✅ {folder}/{p}_qr.json")

        # Intentar PDF ApisPeru via endpoint directo
        tipo = cfg["tipo"]
        endpoint_map = {"note": "/note/pdf", "voided": "/voided/pdf"}
        endpoint = endpoint_map.get(tipo)
        if endpoint:
            # Necesitamos el payload completo para regenerar el PDF
            # ApisPeru requiere el XML firmado o los datos del documento
            # Por ahora guardamos metadata
            save(os.path.join(OUT, folder), f"{p}_metadata.json", {
                "serie": data.get("serie"),
                "correlativo": data.get("correlativo"),
                "hash": data.get("hash"),
                "ticket": data.get("ticket"),
                "sunat_response": data.get("sunat_response", {}),
            })
            print(f"✅ {folder}/{p}_metadata.json")

    print("\nListo!")

if __name__ == "__main__":
    main()
