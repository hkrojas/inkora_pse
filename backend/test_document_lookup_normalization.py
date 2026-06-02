from routers.clientes import _build_dni_result, _build_ruc_result


def test_build_ruc_result_accepts_snake_case_lookup_payload():
    result = _build_ruc_result(
        {
            "ruc": "20606751509",
            "razon_social": "PAPELERIA GRAFICA Y PUBLICITARIA SAC.",
            "nombre_comercial": "PAPELERIA GRAFICA",
            "direccion_fiscal": "AV. ALFONSO UGARTE 252",
            "ubigeo_sunat": "150101",
            "estado_contribuyente": "ACTIVO",
            "condicion_domicilio": "HABIDO",
        },
        "20606751509",
    )

    assert result["tipo"] == "RUC"
    assert result["documento"] == "20606751509"
    assert result["razon_social"] == "PAPELERIA GRAFICA Y PUBLICITARIA SAC."
    assert result["nombre_comercial"] == "PAPELERIA GRAFICA"
    assert result["direccion"] == "AV. ALFONSO UGARTE 252"
    assert result["ubigeo"] == "150101"
    assert result["estado"] == "ACTIVO"
    assert result["condicion"] == "HABIDO"


def test_build_ruc_result_accepts_nested_lookup_payload():
    result = _build_ruc_result(
        {
            "success": True,
            "data": {
                "numeroDocumento": "20606751509",
                "nombreORazonSocial": "INKORA DEMO SAC",
                "direccionFiscal": "JR. DEMO 123",
            },
        },
        "20606751509",
    )

    assert result["documento"] == "20606751509"
    assert result["razon_social"] == "INKORA DEMO SAC"
    assert result["direccion"] == "JR. DEMO 123"


def test_build_dni_result_accepts_snake_case_lookup_payload():
    result = _build_dni_result(
        {
            "dni": "12345678",
            "nombres": "JUAN",
            "apellido_paterno": "PEREZ",
            "apellido_materno": "ROJAS",
            "cod_verifica": "7",
        },
        "12345678",
    )

    assert result["tipo"] == "DNI"
    assert result["documento"] == "12345678"
    assert result["razon_social"] == "JUAN PEREZ ROJAS"
    assert result["apellido_paterno"] == "PEREZ"
    assert result["apellido_materno"] == "ROJAS"
    assert result["cod_verifica"] == "7"
