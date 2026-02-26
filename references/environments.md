# OctoMesh Environment URL Mappings

## Environment Service URLs

| Environment | Identity Service | Asset Service | Bot Service | Communication Service | Reporting Service |
|---|---|---|---|---|---|
| local | `https://localhost:5003/` | `https://localhost:5001/` | `https://localhost:5009/` | `https://localhost:5015/` | `https://localhost:5007/` |
| test-2 | `https://connect.test-2.mm.cloud/` | `https://assets.test-2.mm.cloud/` | `https://bots.test-2.mm.cloud/` | `https://communication.test-2.mm.cloud/` | `https://reporting.test-2.mm.cloud/` |
| staging | `https://connect.staging.meshmakers.cloud/` | `https://assets.staging.meshmakers.cloud/` | `https://bots.staging.meshmakers.cloud/` | `https://communication.staging.meshmakers.cloud/` | `https://reporting.staging.meshmakers.cloud/` |
| production | `https://connect.meshmakers.cloud` | `https://assets.meshmakers.cloud/` | `https://bots.meshmakers.cloud/` | `https://communication.meshmakers.cloud/` | `https://reporting.meshmakers.cloud/` |

## test-2 with URI Suffix

The test-2 environment supports a URI suffix for variant deployments:
```
https://connect-<suffix>.test-2.mm.cloud/
https://assets-<suffix>.test-2.mm.cloud/
https://bots-<suffix>.test-2.mm.cloud/
https://communication-<suffix>.test-2.mm.cloud/
https://reporting-<suffix>.test-2.mm.cloud/
```

## Switching Environment Procedure

Default tenant ID is `meshtest` unless the user specifies otherwise.

### Switch to local
```bash
octo-cli -c Config -isu "https://localhost:5003/" -asu "https://localhost:5001/" -bsu "https://localhost:5009/" -csu "https://localhost:5015/" -tid meshtest
octo-cli -c LogIn -i
```

### Switch to test-2
```bash
octo-cli -c Config -isu "https://connect.test-2.mm.cloud/" -asu "https://assets.test-2.mm.cloud/" -bsu "https://bots.test-2.mm.cloud/" -csu "https://communication.test-2.mm.cloud/" -tid meshtest
octo-cli -c LogIn -i
```

### Switch to staging
```bash
octo-cli -c Config -isu "https://connect.staging.meshmakers.cloud/" -asu "https://assets.staging.meshmakers.cloud/" -bsu "https://bots.staging.meshmakers.cloud/" -csu "https://communication.staging.meshmakers.cloud/" -tid meshtest
octo-cli -c LogIn -i
```

### Switch to production
```bash
octo-cli -c Config -isu "https://connect.meshmakers.cloud" -asu "https://assets.meshmakers.cloud/" -bsu "https://bots.meshmakers.cloud/" -csu "https://communication.meshmakers.cloud/" -tid meshtest
octo-cli -c LogIn -i
```

### Include reporting service
Add `-rsu` flag to any Config command to also configure reporting:
```bash
# Example for test-2 with reporting
octo-cli -c Config -isu "https://connect.test-2.mm.cloud/" -asu "https://assets.test-2.mm.cloud/" -bsu "https://bots.test-2.mm.cloud/" -csu "https://communication.test-2.mm.cloud/" -rsu "https://reporting.test-2.mm.cloud/" -tid meshtest
```

## Environment Detection from URLs

| URL Pattern | Environment |
|---|---|
| `localhost:500x` | local |
| `*.test-2.mm.cloud` | test-2 |
| `*.staging.meshmakers.cloud` | staging |
| `*.meshmakers.cloud` (no staging/test prefix) | production |
