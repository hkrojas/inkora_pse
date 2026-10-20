import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import {
  attachApiOriginGuard,
  attachCriticalErrorCollector,
} from "./helpers/assertions";
import { chooseInkoraOption } from "./helpers/inkora-controls";
import { expectInlineGuideQueries } from './helpers/guide-queries';

const API = process.env.E2E_API_URL || "http://localhost:8000";
const ORIGIN = new URL(API).origin;
const departureDate = () => {
  const date = new Date(Date.now() + 86400000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};
const source = {
  id: 1,
  name: "Depósito de papel",
  is_active: true,
  establishment_id: 1,
  establishment: {
    id: 1,
    name: "Depósito",
    is_active: true,
    verified_at: "2026-10-16",
    sunat_code: "0001",
    address: "Av. de Prueba 100, Lima",
    ubigeo: "150101",
  },
};
const destination = {
  ...source,
  id: 2,
  name: "Tienda principal",
  establishment_id: 2,
  establishment: {
    ...source.establishment,
    id: 2,
    name: "Tienda",
    sunat_code: "0000",
    address: "Av. de Prueba 200, Lima",
  },
};
const product = {
  id: 20,
  nombre: "Papel couché A4",
  codigo_interno: "PAPEL-QA",
  unidad_medida: "NIU",
  item_type: "inventory",
};
async function captureWizard(page, width, path) {
  await page.setViewportSize({ width, height: width > 760 ? 1300 : 1800 });
  await page
    .locator(".transfer-wizard")
    .evaluate((element) => element.scrollIntoView({ block: "start" }));
  await page.screenshot({ path, animations: "disabled" });
  await page.setViewportSize({ width, height: 1000 });
}

async function mockWizard(
  browser,
  baseURL,
  {
    width = 1440,
    theme = "light",
    failStage,
    sameEstablishment = false,
    enabled = true,
  } = {},
) {
  const context = await browser.newContext({
    baseURL,
    viewport: { width, height: 1000 },
    reducedMotion: "reduce",
    storageState: { cookies: [], origins: [] },
  });
  await context.addInitScript((value) => {
    localStorage.setItem("token", "wizard-qa");
    localStorage.setItem("inkora-theme", value);
  }, theme);
  const page = await context.newPage();
  const writes = [];
  const unexpected = [];
  const objects = {
    transfer: new Map(),
    dispatch: new Map(),
    guide: new Map(),
  };
  let failed = false;
  let transfer;
  const target = sameEstablishment
    ? {
        ...destination,
        establishment_id: 1,
        establishment: source.establishment,
      }
    : destination;
  await page.route(`${ORIGIN}/**`, async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.replace(/\/$/, "");
    let payload;
    let stage;
    if (req.method() === "GET") {
      if (path === "/users/me")
        payload = {
          id: 73,
          tenant_id: 73,
          rol: "admin",
          nombre_completo: "Asistente QA",
          email: "wizard@inkora.test",
          is_superadmin: false,
          must_change_password: false,
        };
      else if (path === "/tenant/subscription-status")
        payload = {
          fiscal_feature_flags: { guides: true, internal_transfers: enabled },
        };
      else if (path === "/tenant")
        payload = { id: 73, business_name: "Pruebas QA", is_active: true };
      else if (path === "/sunat/exchange-rate")
        payload = { buy: 3.7, sell: 3.72 };
      else if (path === "/inventario/almacenes")
        payload = [
          source,
          target,
          {
            ...destination,
            id: 3,
            name: "Sin verificar",
            establishment: { ...destination.establishment, verified_at: null },
          },
        ];
      else if (path === "/productos/search") payload = [product];
      else if (path === "/productos/20") payload = product;
      else if (path === "/traslados-internos/60") payload = transfer;
      else if (path === "/guias-remision/90")
        payload = {
          id: 90,
          serie: "T001",
          correlativo: 1,
          estado: "pendiente",
          tipo_documento: "09",
          motivo_traslado: "04",
          modalidad_traslado: "02",
          internal_transfer_id: 60,
          internal_order_number: "TI-60",
          items: [],
          actions: {},
        };
    } else if (
      req.method() === "POST" &&
      path === "/inventario/disponibilidad"
    ) {
      payload = [
        { product_id: 20, available: 8.5, requested: 1, sufficient: true },
      ];
    } else if (req.method() === "POST") {
      const body = req.postDataJSON();
      writes.push({ path, body });
      if (path === "/traslados-internos") {
        stage = "transfer";
        if (!objects.transfer.has(body.idempotency_key)) {
          transfer = {
            id: 60,
            version: 1,
            status: "pending",
            reason: body.reason,
            source_establishment: source.establishment,
            destination_establishment: target.establishment,
            requires_gre: !sameEstablishment,
            lines: body.lines.map((line, index) => ({
              ...line,
              id: index + 100,
              inventory_controlled: Boolean(line.product_id),
              pending_assignment: line.quantity,
              available_stock: line.product_id ? 8.5 : null,
              assigned: 0,
              departed: 0,
              received: 0,
              in_transit: 0,
              cancelled: 0,
            })),
            dispatches: [],
          };
          objects.transfer.set(body.idempotency_key, transfer);
        }
        payload = objects.transfer.get(body.idempotency_key);
      } else if (path === "/traslados-internos/60/despachos") {
        stage = "dispatch";
        if (!objects.dispatch.has(body.idempotency_key))
          objects.dispatch.set(body.idempotency_key, {
            dispatch_id: 80,
            context: transfer,
          });
        payload = objects.dispatch.get(body.idempotency_key);
      } else if (path === "/guias-remision/desde-traslado-interno") {
        stage = "guide";
        if (!objects.guide.has(body.idempotency_key))
          objects.guide.set(body.idempotency_key, { id: 90 });
        payload = objects.guide.get(body.idempotency_key);
      }
      if (stage && stage === failStage && !failed) {
        failed = true;
        await route.abort("connectionreset");
        return;
      }
    }
    if (payload === undefined) unexpected.push(`${req.method()} ${path}`);
    await route.fulfill({
      status: payload === undefined ? 500 : 200,
      json: payload ?? { detail: "Solicitud no prevista" },
    });
  });
  const errors = attachCriticalErrorCollector(page);
  const origin = attachApiOriginGuard(page);
  await page.goto("/traslados-internos/nuevo");
  return { context, page, writes, objects, unexpected, errors, origin };
}

async function goods(
  page,
  {
    catalog = false,
    sourceName = source.name,
    destinationName = destination.name,
  } = {},
) {
  await chooseInkoraOption(page, "Almacén de salida", sourceName);
  await chooseInkoraOption(page, "Almacén de llegada", destinationName);
  await page
    .getByLabel("¿Para qué haces el traslado?", { exact: true })
    .fill("Reponer papel en la tienda");
  if (catalog) {
    await page
      .getByRole("textbox", { name: "Buscar producto", exact: true })
      .fill("Papel");
    await page
      .locator(".internal-transfer-search-results")
      .getByRole("button")
      .first()
      .click();
    await expect(
      page.getByText("Disponible en origen: 8.5", { exact: true }),
    ).toBeVisible();
  } else {
    await page
      .getByRole("button", { name: "Agregar otro bien", exact: true })
      .click();
    await page
      .getByRole("textbox", { name: "Descripción del bien 1", exact: true })
      .fill("Muestrarios impresos");
  }
  await page
    .getByRole("spinbutton", { name: "Cantidad total del bien 1", exact: true })
    .fill("5");
}

async function selectTransportDate(page, dateLabel, timeLabel) {
  const value = departureDate();
  const date = new Date(`${value.slice(0, 10)}T12:00:00`);
  await page.getByRole("button", { name: dateLabel, exact: true }).click();
  const calendar = page.getByRole("dialog", { name: "Seleccionar fecha", exact: true });
  const day = date.toLocaleDateString("es-PE", { day: "numeric", month: "long", year: "numeric" });
  if (!(await calendar.getByRole("button", { name: day, exact: true }).count()))
    await calendar.getByRole("button", { name: "Mes siguiente", exact: true }).click();
  await calendar.getByRole("button", { name: day, exact: true }).click();
  await page.getByLabel(timeLabel, { exact: true }).fill(value.slice(11));
}

for (const width of [1440, 390]) {
  test(`calendario Inkora y DNI: éxito, error y respuesta atrasada a ${width}px`, async ({ browser, baseURL }) => {
    const qa = await mockWizard(browser, baseURL, { width, theme: width === 390 ? "dark" : "light" });
    const { page } = qa;
    let releaseLookup;
    const delayedLookup = new Promise((resolve) => { releaseLookup = resolve; });
    let requestStarted;
    const started = new Promise((resolve) => { requestStarted = resolve; });
    await page.route(`${ORIGIN}/consultar-documento/*`, async (route) => {
      const number = new URL(route.request().url()).pathname.split("/").pop();
      if (number === "11112222") { requestStarted(); await delayedLookup; }
      await route.fulfill(number === "87654321"
        ? { status: 503, json: { detail: "Consulta temporalmente no disponible. Completa los datos manualmente." } }
        : { json: { documento: number, nombres: "Ana María", apellido_paterno: "Rojas", apellido_materno: "Pérez" } });
    });
    try {
      await goods(page);
      await page.getByRole("button", { name: "Continuar", exact: true }).click();
      await expect(page.locator('input[type="datetime-local"]')).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Consultar DNI", exact: true })).toBeDisabled();
      await privateTransport(page);
      await expectInlineGuideQueries(page);
      await page.getByRole("button", { name: "Consultar DNI", exact: true }).click();
      await expect(page.getByLabel("Nombres del conductor", { exact: true })).toHaveValue("Ana María");
      await expect(page.getByLabel("Apellidos del conductor", { exact: true })).toHaveValue("Rojas Pérez");
      await expect(page.getByLabel("Licencia de conducir", { exact: true })).toHaveValue("Q123456789");
      await expect(page.getByLabel("Placa del vehículo", { exact: true })).toHaveValue("ABC123");
      const accessibility = await new AxeBuilder({ page }).include(".transfer-wizard__transport").analyze();
      expect(accessibility.violations.filter((violation) => ["serious", "critical"].includes(violation.impact))).toEqual([]);
      await page.getByLabel("Número de documento", { exact: true }).fill("87654321");
      await page.getByRole("button", { name: "Consultar DNI", exact: true }).click();
      await expect(page.getByRole("alert")).toContainText("Completa los datos manualmente");
      await expect(page.getByLabel("Nombres del conductor", { exact: true })).toHaveValue("Ana María");
      await page.getByLabel("Número de documento", { exact: true }).fill("11112222");
      await page.getByRole("button", { name: "Consultar DNI", exact: true }).click();
      await started;
      await page.getByLabel("Número de documento", { exact: true }).fill("33334444");
      await page.getByLabel("Nombres del conductor", { exact: true }).fill("Nombre manual");
      releaseLookup();
      await expect(page.getByLabel("Nombres del conductor", { exact: true })).toHaveValue("Nombre manual");
      await chooseInkoraOption(page, "Documento del conductor", "Carné de extranjería");
      await expect(page.getByRole("button", { name: "Consultar DNI", exact: true })).toHaveCount(0);
      await expect(page.locator(".transfer-wizard")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(qa.writes).toHaveLength(0);
    } finally { releaseLookup(); await qa.context.close(); }
  });
}

async function privateTransport(page) {
  await expect(
    page.getByRole("button", { name: "Fecha de salida", exact: true }),
  ).toHaveText("dd/mm/aaaa");
  await expect(page.getByLabel("Peso total (kg)", { exact: true })).toHaveValue(
    "",
  );
  await selectTransportDate(page, "Fecha de salida", "Hora de salida");
  await page.getByLabel("Peso total (kg)", { exact: true }).fill("25.5");
  await page
    .getByLabel("Número de documento", { exact: true })
    .fill("12345678");
  await page.getByLabel("Nombres del conductor", { exact: true }).fill("Ana");
  await page
    .getByLabel("Apellidos del conductor", { exact: true })
    .fill("Rojas");
  await page
    .getByLabel("Licencia de conducir", { exact: true })
    .fill("Q123456789");
  await page.getByLabel("Placa del vehículo", { exact: true }).fill("ABC123");
}

for (const [width, theme] of [
  [1440, "light"],
  [390, "dark"],
]) {
  test(`asistente completo, edición y viaje parcial a ${width}px ${theme}`, async ({
    browser,
    baseURL,
  }, testInfo) => {
    const qa = await mockWizard(browser, baseURL, { width, theme });
    const { page, writes } = qa;
    try {
      await goods(page, { catalog: true });
      await expect(
        page.locator("aside").getByRole("link", { name: "Guías", exact: true }),
      ).toHaveAttribute("aria-current", "page");
      const quantity = page.getByRole("spinbutton", {
        name: "Cantidad total del bien 1",
        exact: true,
      });
      await quantity.fill("20");
      await expect(
        page.getByRole("button", { name: "Continuar", exact: true }),
      ).toBeDisabled();
      await page
        .getByRole("checkbox", { name: /Lo llevaré en varios viajes/ })
        .check();
      await page
        .getByRole("spinbutton", {
          name: "Cantidad de este viaje del bien 1",
          exact: true,
        })
        .fill("8.5");
      expect(writes).toEqual([]);
      await captureWizard(
        page,
        width,
        testInfo.outputPath(`asistente-bienes-${width}.png`),
      );
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      await privateTransport(page);
      await captureWizard(
        page,
        width,
        testInfo.outputPath(`asistente-transporte-${width}.png`),
      );
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      await expect(
        page.getByRole("heading", {
          name: "Revisa antes de crear",
          exact: true,
        }),
      ).toBeFocused();
      await page
        .getByRole("button", { name: "Editar bienes", exact: true })
        .click();
      await expect(quantity).toHaveValue("20");
      await expect(
        page.getByRole("spinbutton", {
          name: "Cantidad de este viaje del bien 1",
          exact: true,
        }),
      ).toHaveValue("8.5");
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      await expect(
        page.getByLabel("Peso total (kg)", { exact: true }),
      ).toHaveValue("25.5");
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      expect(writes).toEqual([]);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.setViewportSize({ width, height: width > 760 ? 1300 : 1800 });
      const accessibility = await new AxeBuilder({ page })
        .include(".transfer-wizard")
        .withTags(["wcag2a", "wcag2aa"])
        .analyze();
      expect(accessibility.violations).toEqual([]);
      await captureWizard(
        page,
        width,
        testInfo.outputPath(`asistente-revision-${width}.png`),
      );
      await page
        .getByRole("button", { name: "Crear guía en borrador", exact: true })
        .click();
      await expect(page).toHaveURL(/\/guias\/90$/);
      await expect(
        page.getByRole("link", { name: "Volver al traslado", exact: true }),
      ).toHaveAttribute("href", "/traslados-internos/60");
      expect(writes.map((write) => write.path)).toEqual([
        "/traslados-internos",
        "/traslados-internos/60/despachos",
        "/guias-remision/desde-traslado-interno",
      ]);
      expect(writes[0].body).toMatchObject({
        source_warehouse_id: 1,
        destination_warehouse_id: 2,
        lines: [{ product_id: 20, quantity: 20 }],
      });
      expect(writes[0].body).not.toHaveProperty("tenant_id");
      expect(writes[1].body.lines).toEqual([
        { transfer_line_id: 100, quantity: 8.5 },
      ]);
      expect(writes[2].body).toMatchObject({
        dispatch_id: 80,
        modalidad_traslado: "02",
        peso_bruto_total: 25.5,
        conductor_nro_doc: "12345678",
        vehiculo_placa: "ABC123",
      });
      expect(
        await page.evaluate(() =>
          Object.keys(sessionStorage).filter((key) =>
            key.startsWith("inkora-transfer-wizard:"),
          ),
        ),
      ).toEqual([]);
      expect(qa.unexpected).toEqual([]);
      qa.errors.assertClean();
      qa.origin.assertClean();
    } finally {
      await qa.context.close();
    }
  });
}

for (const scenario of ["public", "registered", "m1-private", "m1-public"]) {
  test(`transporte ${scenario} conserva requisitos y elimina datos ocultos`, async ({
    browser,
    baseURL,
  }) => {
    const qa = await mockWizard(browser, baseURL);
    const { page } = qa;
    try {
      await goods(page);
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      await privateTransport(page);
      if (scenario !== "m1-private")
        await page
          .getByRole("radio", { name: /Una empresa de transporte/ })
          .check();
      if (scenario !== "public")
        await page
          .getByText("Opciones del transporte", { exact: true })
          .click();
      if (scenario.startsWith("m1-"))
        await page.getByRole("checkbox", { name: /Usar la excepción/ }).check();
      if (scenario === "registered")
        await page
          .getByRole("checkbox", { name: /Registrar también el vehículo/ })
          .check();
      if (scenario !== "m1-private")
        await selectTransportDate(page, "Fecha de entrega al transportista", "Hora de entrega al transportista");
      if (["public", "registered"].includes(scenario)) {
        await page
          .getByLabel("RUC del transportista", { exact: true })
          .fill("20100047218");
        await page
          .getByLabel("Registro MTC del transportista", { exact: true })
          .fill("MTC-QA-123");
        await page
          .getByLabel("Nombre o razón social del transportista", {
            exact: true,
          })
          .fill("Transporte de prueba SAC");
      }
      if (scenario === "registered") {
        await page
          .getByLabel("Número de circulación del vehículo", { exact: true })
          .fill("CIR-QA-123");
        await page
          .getByRole("button", { name: "Continuar", exact: true })
          .click();
        await expect(
          page.getByRole("heading", {
            name: "¿Cómo se transportará?",
            exact: true,
          }),
        ).toBeVisible();
        await page
          .getByRole("checkbox", { name: /Confirmo el acuerdo/ })
          .check();
      }
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      if (scenario === "public")
        await expect(
          page.getByText(
            "El transportista deberá proporcionar su guía (GRE 31) antes de registrar la salida física.",
            { exact: true },
          ),
        ).toBeVisible();
      await page
        .getByRole("button", { name: "Crear guía en borrador", exact: true })
        .click();
      await expect(page).toHaveURL(/\/guias\/90$/);
      const payload = qa.writes.at(-1).body;
      expect(payload.modalidad_traslado).toBe(
        scenario === "m1-private" ? "02" : "01",
      );
      expect(payload.indicador_m1_l).toBe(scenario.startsWith("m1-"));
      expect(payload.conductor_nro_doc).toBe(
        scenario === "registered" ? "12345678" : null,
      );
      expect(payload.vehiculo_placa).toBe(
        scenario === "public" ? null : "ABC123",
      );
      expect(payload.transportista_acuerdo_confirmado).toBe(
        scenario === "registered",
      );
      expect(qa.unexpected).toEqual([]);
      qa.errors.assertClean();
    } finally {
      await qa.context.close();
    }
  });
}

for (const stage of ["transfer", "dispatch", "guide"]) {
  test(`recupera respuesta perdida de ${stage} tras recargar sin duplicar`, async ({
    browser,
    baseURL,
  }) => {
    const qa = await mockWizard(browser, baseURL, { failStage: stage });
    const { page } = qa;
    try {
      await goods(page);
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      await privateTransport(page);
      await page
        .getByRole("button", { name: "Continuar", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Crear guía en borrador", exact: true })
        .click();
      await expect(
        page.getByRole("button", { name: "Retomar creación", exact: true }),
      ).toBeEnabled();
      await page.reload();
      await expect(
        page.getByRole("heading", {
          name: "Revisa antes de crear",
          exact: true,
        }),
      ).toBeVisible();
      await page
        .getByRole("button", { name: "Retomar creación", exact: true })
        .click();
      await expect(page).toHaveURL(/\/guias\/90$/);
      for (const records of Object.values(qa.objects))
        expect(records.size).toBe(1);
      const path = {
        transfer: "/traslados-internos",
        dispatch: "/traslados-internos/60/despachos",
        guide: "/guias-remision/desde-traslado-interno",
      }[stage];
      const attempts = qa.writes.filter((write) => write.path === path);
      expect(attempts).toHaveLength(2);
      expect(attempts[0].body).toEqual(attempts[1].body);
      expect(qa.unexpected).toEqual([]);
      expect(
        qa.errors.errors.filter((error) => !/ERR_CONNECTION_RESET/.test(error)),
      ).toEqual([]);
      qa.origin.assertClean();
    } finally {
      await qa.context.close();
    }
  });
}

test("permite continuar un guardado incompleto desde el traslado sin dejar bloqueado otro asistente", async ({
  browser,
  baseURL,
}) => {
  const qa = await mockWizard(browser, baseURL, { failStage: "guide" });
  try {
    await goods(qa.page);
    await qa.page
      .getByRole("button", { name: "Continuar", exact: true })
      .click();
    await privateTransport(qa.page);
    await qa.page
      .getByRole("button", { name: "Continuar", exact: true })
      .click();
    await qa.page
      .getByRole("button", { name: "Crear guía en borrador", exact: true })
      .click();
    const resume = qa.page.getByRole("link", {
      name: "Continuar desde el traslado",
      exact: true,
    });
    await expect(resume).toBeVisible();
    await resume.click();
    await expect(qa.page).toHaveURL(/\/traslados-internos\/60$/);
    expect(
      await qa.page.evaluate(() =>
        Object.keys(sessionStorage).filter((key) =>
          key.startsWith("inkora-transfer-wizard:"),
        ),
      ),
    ).toEqual([]);
    expect(qa.objects.transfer.size).toBe(1);
    expect(qa.objects.dispatch.size).toBe(1);
    expect(qa.objects.guide.size).toBe(1);
    expect(qa.unexpected).toEqual([]);
  } finally {
    await qa.context.close();
  }
});

test("movimiento del mismo establecimiento prepara viaje sin crear una guía fiscal", async ({
  browser,
  baseURL,
}) => {
  const qa = await mockWizard(browser, baseURL, { sameEstablishment: true });
  try {
    await goods(qa.page);
    await qa.page
      .getByRole("button", { name: "Continuar", exact: true })
      .click();
    await expect(
      qa.page.getByText(
        /Prepararemos el viaje interno sin una guía de remisión/,
      ),
    ).toBeVisible();
    await qa.page
      .getByRole("button", { name: "Continuar", exact: true })
      .click();
    await qa.page
      .getByRole("button", { name: "Preparar viaje interno", exact: true })
      .click();
    await expect(qa.page).toHaveURL(/\/traslados-internos\/60$/);
    expect(qa.writes).toHaveLength(2);
    expect(qa.objects.guide.size).toBe(0);
    expect(qa.unexpected).toEqual([]);
    qa.errors.assertClean();
  } finally {
    await qa.context.close();
  }
});

test("respeta la habilitación por empresa y no muestra el asistente si está desactivado", async ({
  browser,
  baseURL,
}) => {
  const qa = await mockWizard(browser, baseURL, { enabled: false });
  try {
    await expect(
      qa.page.getByText(
        "Los traslados internos no están habilitados para esta empresa.",
        { exact: true },
      ),
    ).toBeVisible();
    await expect(
      qa.page.getByRole("button", { name: "Continuar", exact: true }),
    ).toHaveCount(0);
    expect(qa.writes).toEqual([]);
    qa.errors.assertClean();
  } finally {
    await qa.context.close();
  }
});

for (const width of [1440, 390]) {
  test(`API y SQLite reales: crea borrador, reserva stock y mantiene saldos físicos a ${width}px`, async ({
    page,
  }) => {
    test.setTimeout(60_000);
    expect(process.env.ENVIRONMENT).toBe("test");
    expect(process.env.DATABASE_URL).toMatch(/^sqlite:\/\//);
    execFileSync(
      process.env.E2E_PYTHON || "python",
      [
        "-c",
        `
import os
assert os.environ['ENVIRONMENT'] == 'test' and os.environ['DATABASE_URL'].startswith('sqlite:///')
from database import SessionLocal
import models
with SessionLocal() as db:
    user = db.query(models.User).filter(models.User.email == os.environ['E2E_TENANT_EMAIL']).one()
    tenant = db.query(models.Tenant).filter(models.Tenant.id == user.tenant_id).one()
    tenant.smartpse_environment = 'demo'
    subscription = db.query(models.Subscription).filter(models.Subscription.tenant_id == tenant.id).first()
    if not subscription:
        subscription = models.Subscription(tenant_id=tenant.id, status='active')
        db.add(subscription)
    subscription.status = 'active'
    subscription.beta_feature_flags = {'guides': True, 'internal_transfers': True}
    db.commit()
`,
      ],
      { cwd: resolve(process.cwd(), "../backend"), env: process.env },
    );
    const storage = await page.context().storageState();
    const token = storage.origins
      .flatMap((origin) => origin.localStorage)
      .find((entry) => entry.name === "token")?.value;
    const api = async (method, path, data) => {
      const response = await page.request[method](`${API}${path}`, {
        headers: { Authorization: `Bearer ${token}` },
        data,
      });
      expect(response.ok(), `${method} ${path}: ${await response.text()}`).toBe(
        true,
      );
      return response.json();
    };
    const suffix = randomUUID().slice(0, 6);
    await api("post", "/inventario/activar", {});
    const mainEstablishment = (await api("get", "/establecimientos")).find(
      (row) => row.sunat_code === "0000",
    );
    const originWarehouse = await api("post", "/inventario/almacenes", {
      code: `SRC-${suffix}`,
      name: `Depósito QA ${suffix}`,
      establishment_id: mainEstablishment.id,
    });
    const establishment = await api("post", "/establecimientos", {
      sunat_code: width === 1440 ? "0101" : "0102",
      name: `Destino QA ${suffix}`,
      ubigeo: "150101",
      address: "Av. QA 200, Lima",
    });
    await api("post", `/establecimientos/${establishment.id}/verificar`, {
      note: "Verificación sintética exclusiva de las pruebas locales.",
    });
    const arrivalWarehouse = await api("post", "/inventario/almacenes", {
      code: `W-${suffix}`,
      name: `Tienda QA ${suffix}`,
      establishment_id: establishment.id,
    });
    const item = await api("post", "/productos/", {
      nombre: `Papel QA ${suffix}`,
      codigo_interno: `WIZ-${suffix}`,
      precio_unitario: "1.18",
    });
    await api("put", `/inventario/productos/${item.id}`, {
      item_type: "inventory",
      inventory_enabled: true,
      warehouse_id: originWarehouse.id,
      opening_stock: 100,
      minimum_stock: 0,
    });
    await page.setViewportSize({ width, height: 1000 });
    const errors = attachCriticalErrorCollector(page);
    const originGuard = attachApiOriginGuard(page);
    await page.goto("/traslados-internos/nuevo");
    await chooseInkoraOption(page, "Almacén de salida", originWarehouse.name);
    await chooseInkoraOption(page, "Almacén de llegada", arrivalWarehouse.name);
    await page
      .getByLabel("¿Para qué haces el traslado?", { exact: true })
      .fill(`Reposición QA ${suffix}`);
    await page
      .getByRole("textbox", { name: "Buscar producto", exact: true })
      .fill(item.nombre);
    await page
      .locator(".internal-transfer-search-results")
      .getByRole("button")
      .first()
      .click();
    await expect(
      page.getByText("Disponible en origen: 100", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("spinbutton", {
        name: "Cantidad total del bien 1",
        exact: true,
      })
      .fill("25.5");
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await privateTransport(page);
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await page
      .getByRole("button", { name: "Crear guía en borrador", exact: true })
      .click();
    await expect(page).toHaveURL(/\/guias\/\d+$/);
    const savedGuide = await api(
      "get",
      `/guias-remision/${page.url().split("/").at(-1)}`,
    );
    expect(savedGuide.estado).toBe("pendiente");
    expect(savedGuide.motivo_traslado).toBe("04");
    expect(savedGuide.internal_transfer_id).toBeTruthy();
    const transfer = await api(
      "get",
      `/traslados-internos/${savedGuide.internal_transfer_id}`,
    );
    expect(Number(transfer.lines[0].assigned)).toBe(25.5);
    expect(transfer.dispatches).toHaveLength(1);
    expect(transfer.dispatches[0].departure_confirmed_at).toBeNull();
    expect(Number(transfer.lines[0].received)).toBe(0);
    const balances = (await api("get", "/inventario/existencias")).filter(
      (row) => row.product_id === item.id,
    );
    expect(
      Number(
        balances.find((row) => row.warehouse_id === originWarehouse.id).on_hand,
      ),
    ).toBe(100);
    expect(
      Number(
        balances.find((row) => row.warehouse_id === originWarehouse.id)
          .committed,
      ),
    ).toBe(25.5);
    expect(
      balances.some(
        (row) =>
          row.warehouse_id === arrivalWarehouse.id && Number(row.on_hand) > 0,
      ),
    ).toBe(false);
    await expect(
      page.getByRole("link", { name: "Volver al traslado", exact: true }),
    ).toHaveAttribute(
      "href",
      `/traslados-internos/${savedGuide.internal_transfer_id}`,
    );
    errors.assertClean();
    originGuard.assertClean();
  });
}
