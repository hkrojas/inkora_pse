from services.quote_observation_service import build_default_observation_lines


def test_build_default_observation_lines_soporta_config_en_pdf_note_2():
    lines = build_default_observation_lines(
        note_1_text="Linea 1",
        note_1_color="#112233",
        note_2_text='{"version":1,"line_1":{"bold":false},"line_2":{"text":"Linea 2","color":"#445566","bold":true}}',
    )

    assert lines == [
        {"text": "Linea 1", "color": "#112233", "bold": False},
        {"text": "Linea 2", "color": "#445566", "bold": True},
    ]


def test_build_default_observation_lines_mantiene_compatibilidad_legacy():
    lines = build_default_observation_lines(
        note_1_text="Linea 1",
        note_1_color="#FF0000",
        note_2_text="Linea 2 legacy",
    )

    assert lines == [
        {"text": "Linea 1", "color": "#FF0000", "bold": True},
        {"text": "Linea 2 legacy", "color": "#111111", "bold": False},
    ]
