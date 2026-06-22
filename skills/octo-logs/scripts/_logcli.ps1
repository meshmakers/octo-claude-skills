# Loads the octo-tools profile (which dot-sources the private profile that sets
# LOKI_USERNAME / LOKI_PASSWORD), resolves the cluster's Loki datasource-proxy
# URL via the Grafana API, then runs logcli. Credentials never leave this
# PowerShell session and are never written to stdout.
#
# Invoked by run_logcli.sh as:
#   pwsh -NoProfile -File _logcli.ps1 <profile-path> <cluster> <logcli args...>

if ($args.Count -lt 3) {
    Write-Error "usage: _logcli.ps1 <profile-path> <cluster> <logcli args...>"
    exit 1
}

$profilePath = $args[0]
$cluster     = $args[1]
$logcliArgs  = @($args[2..($args.Count - 1)])

# Cluster -> monitoring Grafana base URL. This is the Prometheus-stack Grafana
# (internal, carries the Loki datasource) — NOT the customer-facing grafana.* host.
$baseMap = @{
    'test-2'    = 'https://monitoring.test-2.mm.cloud'
    'staging-1' = 'https://monitoring.staging.octo-mesh.com'
    'prod-1'    = 'https://monitoring.prod-1.octo-mesh.com'
    'prod-2'    = 'https://monitoring.prod-2.octo-mesh.com'
}
if (-not $baseMap.ContainsKey($cluster)) {
    Write-Error "Unknown cluster '$cluster'. Known clusters: $($baseMap.Keys -join ', ')"
    exit 1
}
$base = $baseMap[$cluster]

# Load the profile. It is the user's working profile and may emit host chatter
# and benign non-terminating errors (path resolves, etc.); suppress all of its
# streams so only logcli output reaches stdout. If credentials end up unset we
# report a clear error below.
$prev = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
. $profilePath *> $null
$ErrorActionPreference = $prev

# Per-cluster credential override (e.g. LOKI_USERNAME_PROD1 / LOKI_PASSWORD_PROD1)
# falls back to the generic LOKI_USERNAME / LOKI_PASSWORD. Use a generic pair if
# the same admin login works across the clusters you access.
$suffix = $cluster.ToUpper().Replace('-', '')
$user = [Environment]::GetEnvironmentVariable("LOKI_USERNAME_$suffix")
if (-not $user) { $user = $env:LOKI_USERNAME }
$pass = [Environment]::GetEnvironmentVariable("LOKI_PASSWORD_$suffix")
if (-not $pass) { $pass = $env:LOKI_PASSWORD }

if (-not $user -or -not $pass) {
    Write-Error "LOKI_USERNAME / LOKI_PASSWORD are not set after loading the profile. Run /octo-logs-setup to configure credentials safely."
    exit 2
}

# Resolve the Loki datasource UID (stable per Grafana, but discovered at runtime
# so no UID is hard-coded and the skill works across clusters unchanged).
$sec  = ConvertTo-SecureString $pass -AsPlainText -Force
$cred = [System.Management.Automation.PSCredential]::new($user, $sec)
try {
    $ds = Invoke-RestMethod -Uri "$base/api/datasources" -Authentication Basic -Credential $cred -TimeoutSec 20
} catch {
    Write-Error "Could not reach $base/api/datasources : $($_.Exception.Message). Check VPN/Tailscale reachability and that the credentials are valid."
    exit 3
}
$uid = ($ds | Where-Object { $_.type -eq 'loki' } | Select-Object -First 1).uid
if (-not $uid) {
    Write-Error "No Loki datasource found on $base."
    exit 3
}

# logcli reads these from the environment; LOKI_ADDR points at the Grafana
# datasource proxy (Loki is not exposed directly on the monitoring host).
$env:LOKI_ADDR     = "$base/api/datasources/proxy/uid/$uid"
$env:LOKI_USERNAME = $user
$env:LOKI_PASSWORD = $pass

& logcli @logcliArgs
exit $LASTEXITCODE
