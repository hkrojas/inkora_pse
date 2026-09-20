param(
  [switch]$RequirePostgres,
  [string]$PythonPath
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$localPythonPath = Join-Path $repoRoot 'backend/venv/Scripts/python.exe'
if (-not $PythonPath) { $PythonPath = $localPythonPath }
if (-not (Test-Path -LiteralPath $PythonPath)) {
  throw 'Falta el entorno de pruebas backend. Use -PythonPath con un intérprete existente.'
}
Push-Location (Join-Path $repoRoot 'backend')
try {
  & $PythonPath -m pytest -q --ignore=test_sale_dispatch_postgres.py --ignore=test_cotizaciones_postgres.py --ignore=test_inventory_recovery_postgres.py
  if ($LASTEXITCODE -ne 0) { throw 'Regresión backend falló: publicación bloqueada.' }
  if ($RequirePostgres) {
    if (-not $env:INKORA_GRE_POSTGRES_URL -or -not $env:INKORA_QUOTE_POSTGRES_URL) { throw 'Se requieren dos bases PostgreSQL locales desechables, GRE y cotizaciones.' }
    $previousPostgresUrl = $env:INKORA_TEST_POSTGRES_URL
    $previousRequired = $env:INKORA_REQUIRE_POSTGRES_TESTS
    try {
      $env:INKORA_REQUIRE_POSTGRES_TESTS = '1'
      $env:INKORA_TEST_POSTGRES_URL = $env:INKORA_GRE_POSTGRES_URL
      & $PythonPath -m pytest test_sale_dispatch_postgres.py -q
      if ($LASTEXITCODE -ne 0) { throw 'Concurrencia GRE falló.' }
      $env:INKORA_TEST_POSTGRES_URL = $env:INKORA_QUOTE_POSTGRES_URL
      & $PythonPath -m pytest test_cotizaciones_postgres.py test_inventory_recovery_postgres.py -q
      if ($LASTEXITCODE -ne 0) { throw 'Concurrencia cotizaciones falló.' }
    } finally {
      $env:INKORA_TEST_POSTGRES_URL = $previousPostgresUrl
      $env:INKORA_REQUIRE_POSTGRES_TESTS = $previousRequired
    }
  }
} finally { Pop-Location }
Push-Location (Join-Path $repoRoot 'frontend')
try {
  npm test
  if ($LASTEXITCODE -ne 0) { throw 'Pruebas frontend fallaron.' }
  npm run lint
  if ($LASTEXITCODE -ne 0) { throw 'Lint falló.' }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Build falló.' }
} finally { Pop-Location }
& $PythonPath (Join-Path $PSScriptRoot 'run_e2e_local.py')
if ($LASTEXITCODE -ne 0) { throw 'Pruebas E2E locales aisladas fallaron.' }
& $PythonPath (Join-Path $PSScriptRoot 'release_guard.py') check
if ($LASTEXITCODE -ne 0) { throw 'Manifiesto o contratos inválidos.' }
Write-Output 'Validación local concluida. No publica ni migra. Exige además revisión visual, esquema remoto y aprobación del paquete.'
