param(
  [switch]$RequirePostgres,
  [string]$PythonPath,
  [ValidateSet('Auto', 'Full')][string]$Mode = 'Auto',
  [string]$BaseRef = 'inkora_pse/main'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$localPythonPath = Join-Path $repoRoot 'backend/venv/Scripts/python.exe'
if (-not $PythonPath) { $PythonPath = $localPythonPath }
if (-not (Test-Path -LiteralPath $PythonPath)) {
  throw 'Falta el entorno de pruebas backend. Use -PythonPath con un intérprete existente.'
}
Push-Location $repoRoot
try {
  & $PythonPath -m unittest discover -s scripts -p 'test_release_*.py'
  if ($LASTEXITCODE -ne 0) { throw 'Controles de selección/evidencia/versiones fallaron.' }
  & $PythonPath -m unittest discover -s scripts -p 'test_run_e2e_selection.py'
  if ($LASTEXITCODE -ne 0) { throw 'Aislamiento del runner falló.' }
  $planArguments = @('scripts/release_ci_evidence.py', 'plan', '--base', $BaseRef, '--output', 'tmp/local-release-plan.json')
  if ($Mode -eq 'Full') { $planArguments += '--full' }
  & $PythonPath @planArguments
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo determinar el alcance de validación.' }
  $releasePlan = Get-Content tmp/local-release-plan.json -Raw | ConvertFrom-Json
} finally { Pop-Location }
if ($releasePlan.profile -eq 'full') {
Push-Location (Join-Path $repoRoot 'backend')
try {
  & $PythonPath -m pytest -q --ignore=test_sale_dispatch_postgres.py --ignore=test_internal_transfer_postgres.py --ignore=test_internal_transfer_migration.py --ignore=test_cotizaciones_postgres.py --ignore=test_inventory_recovery_postgres.py --ignore=test_emission_worker_postgres.py --ignore=test_panel_retry_postgres.py --ignore=test_panel_retry_sequence_postgres.py --ignore=test_resumen_confirmation_postgres.py
  if ($LASTEXITCODE -ne 0) { throw 'Regresión backend falló: publicación bloqueada.' }
  if ($RequirePostgres) {
    if (-not $env:INKORA_GRE_POSTGRES_URL -or -not $env:INKORA_QUOTE_POSTGRES_URL -or -not $env:INKORA_WORKER_POSTGRES_URL -or -not $env:INKORA_SUMMARY_POSTGRES_URL) { throw 'Se requieren cuatro bases PostgreSQL locales desechables: GRE, cotizaciones, worker y resumen diario.' }
    $previousPostgresUrl = $env:INKORA_TEST_POSTGRES_URL
    $previousRequired = $env:INKORA_REQUIRE_POSTGRES_TESTS
    try {
      $env:INKORA_REQUIRE_POSTGRES_TESTS = '1'
      $env:INKORA_TEST_POSTGRES_URL = $env:INKORA_GRE_POSTGRES_URL
      & $PythonPath -m pytest test_sale_dispatch_postgres.py test_internal_transfer_postgres.py test_internal_transfer_migration.py -q
      if ($LASTEXITCODE -ne 0) { throw 'Concurrencia o migración GRE falló.' }
      $env:INKORA_TEST_POSTGRES_URL = $env:INKORA_QUOTE_POSTGRES_URL
      & $PythonPath -m pytest test_cotizaciones_postgres.py test_inventory_recovery_postgres.py -q
      if ($LASTEXITCODE -ne 0) { throw 'Concurrencia cotizaciones falló.' }
      $env:INKORA_TEST_POSTGRES_URL = $env:INKORA_WORKER_POSTGRES_URL
      & $PythonPath -m pytest test_emission_worker_postgres.py test_panel_retry_postgres.py test_panel_retry_sequence_postgres.py test_fiscal_pdf_delivery_postgres.py -q
      if ($LASTEXITCODE -ne 0) { throw 'Concurrencia, leases, avisos o migración del worker fallaron.' }
      & $PythonPath -m pytest test_resumen_confirmation_postgres.py -q
      if ($LASTEXITCODE -ne 0) { throw 'Concurrencia y confirmación del resumen diario fallaron.' }
    } finally {
      $env:INKORA_TEST_POSTGRES_URL = $previousPostgresUrl
      $env:INKORA_REQUIRE_POSTGRES_TESTS = $previousRequired
    }
  }
} finally { Pop-Location }
}
if ($releasePlan.profile -ne 'docs') {
Push-Location (Join-Path $repoRoot 'frontend')
try {
  npm test
  if ($LASTEXITCODE -ne 0) { throw 'Pruebas frontend fallaron.' }
  npm run lint
  if ($LASTEXITCODE -ne 0) { throw 'Lint falló.' }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Build falló.' }
  npm run check:bundle
  if ($LASTEXITCODE -ne 0) { throw 'Presupuesto de bundle falló.' }
} finally { Pop-Location }
& $PythonPath (Join-Path $PSScriptRoot 'release_ci_evidence.py') e2e --plan (Join-Path $repoRoot 'tmp/local-release-plan.json')
if ($LASTEXITCODE -ne 0) { throw 'Pruebas E2E locales aisladas fallaron.' }
}
& $PythonPath (Join-Path $PSScriptRoot 'release_guard.py') check
if ($LASTEXITCODE -ne 0) { throw 'Manifiesto o contratos inválidos.' }
Write-Output "Validación local concluida: $($releasePlan.profile). No publica ni migra. Conserva revisión visual, esquema remoto cuando cambia backend y aprobación del paquete."
