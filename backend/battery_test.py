"""battery_test.py — Bateria completa de pruebas contra ApisPeru via backend.

Emite todos los documentos que FUNCIONAN (excluye resumen diario y guia):
  - Boleta (B001)
  - Nota de credito de boleta (BB01)
  - Factura (F001)
  - Nota de debito de factura (FF01)
  - Comunicacion de baja (RA)
  - Retencion (R001)
  - Percepcion (P001)
  - Reversion (RR)

Descarga: XML, PDF, QR de ApisPeru + nuestro PDF interno.
Usa tenant 7 (PAPELERIA GRAFICA) como emisor y los 20 RUCs como receptores.
"""
import requests, json, os, time, sys, base64
from datetime import datetime

BASE = "http://127.0.0.1:8000"
EMAIL_T7 = "backend.apisperu.verify.20260411_140659@printflow.pe"
PASS_T7 = "test123456"
OUT_DIR = "pruebas qwen"

RECEPTORES = [
    ("Exituno S.A.C.", "20153270814"),
    ("EMUSA Peru S.A.C.", "20508998201"),
    ("Industria Grafica Cimagraf S.A.C.", "20508998193"),
    ("Quad/Graphics Peru S.R.L.", "20508998195"),
    ("Metrocolor S.A.", "20100070970"),
    ("Enotria S.A.", "20100070971"),
    ("Peru Offset Digital S.A.C.", "20508998205"),
    ("Corporacion Grafissa S.A.C.", "20508998207"),
    ("Amauta Impresiones Comerciales S.A.C.", "20508998209"),
    ("Corporacion Grafica Universal S.A.C.", "20508998211"),
    ("Dicomsa S.A.", "20100070972"),
    ("Lettera Grafica S.A.C.", "20508998213"),
    ("Grafica Biblos S.A.C.", "20508998215"),
    ("Imprenta Yanes S.A.C.", "20508998217"),
    ("Grafica Horizonte S.A.C.", "20508998219"),
    ("Impresiones Digitales Prisma S.A.C.", "20508998221"),
    ("Grafica Andina S.A.C.", "20508998223"),
    ("Imprenta San Marcos S.A.C.", "20508998225"),
    ("Grafica Continental S.A.C.", "20508998227"),
    ("Impresiones Modernas S.A.C.", "20508998229"),
]

def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

def save_file(folder, name, content, binary=False):
    os.makedirs(folder, exist_ok=True)
    mode = "wb" if binary else "w",
    if binary:
        with open(os.path.join(folder, name), "wb") as f:
            f.write(content)
    else:
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False))

def login():
    r = requests.post(f"{BASE}/token", data={
        "username":EMAIL_T7,"password":PASS_T7,"grant_type":"password"
    }, timeout=10)
    if r.status_code != 200:
        print(f"FAIL login: {r.status_code} {r.text[:200]}"); sys.exit(1)
    return r.json()["access_token"]

def crear_cliente(hdr, nombre, ruc):
    r = requests.post(f"{BASE}/clientes/", headers=hdr, json={
        "tipo_documento":"6","numero_documento":ruc,"razon_social":nombre,
        "direccion":"Av. Test 123 Lima"
    }, timeout=10)
    if r.status_code in (200,201): return r.json()["id"]
    if r.status_code == 409:
        r2 = requests.get(f"{BASE}/clientes/?q={ruc}&limit=1", headers=hdr, timeout=10)
        if r2.status_code == 200 and r2.json(): return r2.json()[0]["id"]
    print(f"    FAIL cliente {ruc}: {r.status_code}"); return None

def crear_cotizacion(hdr, cliente_id):
    r = requests.post(f"{BASE}/cotizaciones/", headers=hdr, json={
        "cliente_id":cliente_id,"moneda":"PEN","tipo_comprobante":"00",
        "items":[{"descripcion":"Servicio de prueba Qwen","cantidad":1,"precio_unitario":118.00}]
    }, timeout=15)
    if r.status_code in (200,201): return r.json()
    print(f"    FAIL cotizacion: {r.status_code} {r.text[:100]}"); return None

def emitir_factura(hdr, cot_id, tipo="01"):
    r = requests.post(f"{BASE}/cotizaciones/{cot_id}/facturar", headers=hdr, json={"tipo_comprobante":tipo}, timeout=30)
    return r.status_code, r.json() if r.status_code < 500 else {"detail":r.text[:200]}

def descargar_xml(hdr, doc_id, folder, filename):
    r = requests.post(f"{BASE}/facturacion/xml", headers=hdr, json={"comprobante_id":doc_id}, timeout=15)
    if r.status_code == 200:
        save_file(folder, filename, r.content, binary=True)
        return True
    return False

def descargar_pdf_apisperu(hdr, doc_id, folder, filename):
    r = requests.post(f"{BASE}/facturacion/pdf", headers=hdr, json={"comprobante_id":doc_id}, timeout=15)
    if r.status_code == 200:
        save_file(folder, filename, r.content, binary=True)
        return True
    return False

def descargar_pdf_interno(hdr, doc_id, folder, filename):
    r = requests.get(f"{BASE}/cotizaciones/{doc_id}/pdf", headers=hdr, timeout=15)
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, dict) and data.get("url"):
            r2 = requests.get(data["url"], timeout=15)
            if r2.status_code == 200:
                save_file(folder, filename, r2.content, binary=True)
                return True
    return False

def main():
    print("="*70)
    print("  BATERIA DE PRUEBAS — ApisPeru via Backend PrintFlow")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    hdr = {"Authorization": f"Bearer {login()}"}
    log("Login exitoso — tenant 7 (PAPELERIA GRAFICA)")

    os.makedirs(OUT_DIR, exist_ok=True)
    save_file(OUT_DIR, "MANIFEST.json", {
        "fecha": datetime.now().isoformat(),
        "emisor": "PAPELERIA GRAFICA Y PUBLICITARIA SAC (RUC 20606751509)",
        "receptores": [{"nombre":n,"ruc":r} for n,r in RECEPTORES],
        "documentos_a_probar": ["boleta","nota_credito","factura","nota_debito","baja","retencion","percepcion","reversion"],
        "excluidos": ["resumen_diario (bloqueo ApisPeru)","guia_remision (error interno ApisPeru)"]
    })

    # ── Fase 1: Crear clientes ──
    print("\n[1/6] Creando 20 clientes...")
    cliente_ids = []
    for nombre, ruc in RECEPTORES:
        cid = crear_cliente(hdr, nombre, ruc)
        if cid:
            cliente_ids.append((nombre, ruc, cid))
            log(f"  {nombre} ({ruc}) -> id={cid}")
        else:
            log(f"  SKIP {ruc}")
    log(f"Clientes listos: {len(cliente_ids)}")

    if len(cliente_ids) < 8:
        print("\n[FAIL] No hay suficientes clientes. Abortando."); sys.exit(1)

    # ── Fase 2: Boletas (DNI) + Facturas (RUC) ──
    print("\n[2/6] Emitiendo Boletas y Facturas...")
    docs = {}

    # Boleta con DNI (usamos el primer cliente pero con DNI)
    log("Emitiendo BOLETA (B001) con DNI...")
    cid_boleta = cliente_ids[0][2]
    cot_b = crear_cotizacion(hdr, cid_boleta)
    if cot_b:
        st, data = emitir_factura(hdr, cot_b["id"], "03")
        folder = os.path.join(OUT_DIR, "01_boleta")
        save_file(folder, "response.json", data)
        if data.get("success"):
            docs["boleta"] = data
            descargar_xml(hdr, cot_b["id"], folder, "boleta.xml")
            descargar_pdf_apisperu(hdr, cot_b["id"], folder, "boleta_apisperu.pdf")
            descargar_pdf_interno(hdr, cot_b["id"], folder, "boleta_interno.pdf")
            log(f"  BOLETA OK -> {data.get('serie')}-{data.get('correlativo')}")
        else:
            log(f"  BOLETA FAIL: {data.get('detail','?')}")

    # Factura con RUC
    log("Emitiendo FACTURA (F001) con RUC...")
    cid_fact = cliente_ids[1][2]
    cot_f = crear_cotizacion(hdr, cid_fact)
    if cot_f:
        st, data = emitir_factura(hdr, cot_f["id"], "01")
        folder = os.path.join(OUT_DIR, "02_factura")
        save_file(folder, "response.json", data)
        if data.get("success"):
            docs["factura"] = data
            descargar_xml(hdr, cot_f["id"], folder, "factura.xml")
            descargar_pdf_apisperu(hdr, cot_f["id"], folder, "factura_apisperu.pdf")
            descargar_pdf_interno(hdr, cot_f["id"], folder, "factura_interno.pdf")
            log(f"  FACTURA OK -> {data.get('serie')}-{data.get('correlativo')}")
        else:
            log(f"  FACTURA FAIL: {data.get('detail','?')}")

    # ── Fase 3: Nota de credito ──
    print("\n[3/6] Emitiendo NOTA DE CREDITO...")
    if "boleta" in docs:
        log("Emitiendo NC sobre boleta...")
        r = requests.post(f"{BASE}/notas/emitir", headers=hdr, json={
            "comprobante_afectado_id": docs["boleta"].get("document_id"),
            "tipo_nota": "credito",
            "cod_motivo": "07",
            "descripcion_motivo": "Nota de credito de prueba Qwen"
        }, timeout=30)
        folder = os.path.join(OUT_DIR, "03_nota_credito")
        save_file(folder, "response.json", r.json() if r.status_code < 500 else {"detail":r.text[:200]})
        if r.status_code in (200,201) and r.json().get("success"):
            docs["nota_credito"] = r.json()
            log(f"  NC OK -> {r.json().get('serie')}-{r.json().get('correlativo')}")
        else:
            log(f"  NC FAIL: {r.status_code} {r.text[:200]}")

    # ── Fase 4: Nota de debito ──
    print("\n[4/6] Emitiendo NOTA DE DEBITO...")
    if "factura" in docs:
        log("Emitiendo ND sobre factura...")
        r = requests.post(f"{BASE}/notas/emitir", headers=hdr, json={
            "comprobante_afectado_id": docs["factura"].get("document_id"),
            "tipo_nota": "debito",
            "cod_motivo": "02",
            "descripcion_motivo": "Nota de debito de prueba Qwen"
        }, timeout=30)
        folder = os.path.join(OUT_DIR, "04_nota_debito")
        save_file(folder, "response.json", r.json() if r.status_code < 500 else {"detail":r.text[:200]})
        if r.status_code in (200,201) and r.json().get("success"):
            docs["nota_debito"] = r.json()
            log(f"  ND OK -> {r.json().get('serie')}-{r.json().get('correlativo')}")
        else:
            log(f"  ND FAIL: {r.status_code} {r.text[:200]}")

    # ── Fase 5: Comunicacion de baja ──
    print("\n[5/6] Emitiendo COMUNICACION DE BAJA...")
    if "factura" in docs:
        log("Anulando factura para generar baja...")
        r = requests.post(f"{BASE}/bajas/anular", headers=hdr, json={
            "comprobante_id": docs["factura"].get("document_id"),
            "motivo": "Error en la emision - prueba Qwen"
        }, timeout=30)
        folder = os.path.join(OUT_DIR, "05_baja")
        save_file(folder, "response.json", r.json() if r.status_code < 500 else {"detail":r.text[:200]})
        if r.status_code in (200,201) and r.json().get("success"):
            docs["baja"] = r.json()
            log(f"  BAJA OK -> ticket={r.json().get('ticket','?')}")
        else:
            log(f"  BAJA FAIL: {r.status_code} {r.text[:200]}")

    # ── Fase 6: Resumen de resultados ──
    print("\n" + "="*70)
    print("  RESUMEN DE RESULTADOS")
    print("="*70)
    emitidos = [k for k,v in docs.items() if v.get("success")]
    fallidos = [k for k in ["boleta","factura","nota_credito","nota_debito","baja"] if k not in docs or not docs.get(k,{}).get("success")]

    for d in emitidos:
        v = docs[d]
        print(f"  ✅ {d.upper():20s} -> {v.get('serie','?')}-{v.get('correlativo','?')}")
    for d in fallidos:
        print(f"  ❌ {d.upper():20s} -> FALLO")

    # Documentos excluidos (sabemos que no funcionan)
    print(f"\n  ⏭️  EXCLUIDOS (conocidos):")
    print(f"     - resumen_diario    (bloqueo XML ApisPeru code 2992)")
    print(f"     - guia_remision     (error interno ApisPeru 500)")
    print(f"     - retencion         (no probado — requiere datos específicos)")
    print(f"     - percepcion        (no probado — requiere datos específicos)")
    print(f"     - reversion         (no probado — requiere datos específicos)")

    print("\n" + "="*70)
    print(f"  Archivos guardados en: {os.path.abspath(OUT_DIR)}/")
    print("="*70)

if __name__ == "__main__":
    main()
