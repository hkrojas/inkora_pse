import { d as attr_class, m as clsx, f as escape_html } from "../../../chunks/index2.js";
import { e as pageEyebrowClass, f as pageTitleClass, h as pageSubtitleClass, b as glassPanelClass, g as glassPanelStrongClass, m as mutedGlassPanelClass } from "../../../chunks/uiClasses.js";
import { L as Loader_circle } from "../../../chunks/loader-circle.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let activeGuide;
    const conductorOptions = [
      {
        id: "cond-1",
        label: "Carlos Mejia",
        nombres: "Carlos",
        apellidos: "Mejia Soto",
        nro_doc: "45678912",
        licencia: "Q12345678"
      },
      {
        id: "cond-2",
        label: "Lucia Paredes",
        nombres: "Lucia",
        apellidos: "Paredes Leon",
        nro_doc: "40781234",
        licencia: "Q22345679"
      },
      {
        id: "cond-3",
        label: "Miguel Ramos",
        nombres: "Miguel",
        apellidos: "Ramos Diaz",
        nro_doc: "47890123",
        licencia: "Q32345670"
      }
    ];
    const vehicleOptions = [
      { id: "veh-1", label: "Sprinter - F1A221", placa: "F1A221" },
      { id: "veh-2", label: "Kia K2500 - B7R912", placa: "B7R912" },
      { id: "veh-3", label: "Hyundai H100 - C3T447", placa: "C3T447" }
    ];
    let cotizaciones = [];
    let guias = [];
    let activeGuideId = null;
    let lastEmissionLinks = { xml: null, pdf: null, cdr: null };
    getInitialForm();
    function getInitialForm() {
      return {
        cotizacion_id: "",
        fecha_traslado: getDefaultDateTime(),
        peso_bruto_total: "",
        numero_bultos: "",
        motivo_traslado: "01",
        descripcion_motivo: "Venta",
        selectedConductorId: conductorOptions[0].id,
        conductor_nombres: conductorOptions[0].nombres,
        conductor_apellidos: conductorOptions[0].apellidos,
        conductor_nro_doc: conductorOptions[0].nro_doc,
        conductor_licencia: conductorOptions[0].licencia,
        selectedVehicleId: vehicleOptions[0].id,
        vehiculo_placa: vehicleOptions[0].placa,
        partida_ubigeo: "150101",
        partida_direccion: "Av. Industrial 456, Lima",
        llegada_ubigeo: "150101",
        llegada_direccion: ""
      };
    }
    function getDefaultDateTime() {
      const current = /* @__PURE__ */ new Date();
      current.setMinutes(0, 0, 0);
      const offset = current.getTimezoneOffset() * 6e4;
      return new Date(current.getTime() - offset).toISOString().slice(0, 16);
    }
    function getQuoteMeta(cotizacionId) {
      return cotizaciones.find((cotizacion) => cotizacion.id === cotizacionId) || null;
    }
    activeGuide = guias.find((guia) => guia.id === activeGuideId) || null;
    activeGuide ? getQuoteMeta(activeGuide.cotizacion_id) : null;
    ({
      xml: activeGuide?.sunat_xml_url || lastEmissionLinks.xml,
      pdf: activeGuide?.sunat_pdf_url || lastEmissionLinks.pdf,
      cdr: activeGuide?.sunat_cdr_url || lastEmissionLinks.cdr
    });
    $$renderer2.push(`<div class="space-y-6"><section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between"><div class="space-y-2"><p${attr_class(clsx(pageEyebrowClass))}>Logistica fiscal</p> <div class="space-y-1"><h1${attr_class(clsx(pageTitleClass))}>Despachos</h1> <p${attr_class(`max-w-3xl ${pageSubtitleClass}`)}>Genera guias de remision desde cotizaciones vigentes y controla la emision final hacia SUNAT.</p></div></div> <div${attr_class(`rounded-2xl px-4 py-3 ${glassPanelClass}`)}><p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Estado operativo</p> <p class="mt-1 text-sm font-semibold text-slate-900">${escape_html(guias.length)} guia${escape_html(guias.length === 1 ? "" : "s")} registradas</p></div></section> `);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div${attr_class(`flex min-h-[420px] items-center justify-center rounded-[30px] ${glassPanelStrongClass}`)}><div${attr_class(`flex items-center gap-3 rounded-2xl px-5 py-4 text-sm text-slate-600 ${mutedGlassPanelClass}`)}>`);
      Loader_circle($$renderer2, {
        class: "h-5 w-5 animate-spin text-emerald-600",
        strokeWidth: 1.9
      });
      $$renderer2.push(`<!----> <span>Cargando centro de despachos...</span></div></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
