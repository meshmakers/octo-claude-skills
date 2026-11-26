# Own Angular app from the template repository

How a developer and their coding agent start an **own Angular app** for a tenant from the public template repository
`meshmakers/template-repo` (template-repo): initialise it, register the OIDC client of the dev server, scaffold pages
with the MCP tools, generate the typed GraphQL client and see tenant data in the browser. The agent works MCP-first:
knowledge pages, then MCP tools; local tools only where the work happens in the developer's own checkout. The
template's `README.md` and `CLAUDE.md` hold the exact local commands; read them in the checkout.

## Own template app or operator-deployed workload

| You need | Path |
|---|---|
| Your own UI code: Angular pages, Kendo UI components, the Meshmakers app design, typed GraphQL queries against the tenant, developed and tested in your own repository | **own template app** (this page) |
| The platform to run and update a web app in the cluster from a blueprint (`DeployWorkload`), with an HTTP API of Mesh Adapter pipelines behind it | **operator-deployed Application workload**, see [app-workload.md](app-workload.md) |

The two differ in how they reach the tenant: the template app signs the user in with its own OIDC client and calls
the tenant's GraphQL API directly (`<apiUrl>/tenants/<tenantId>/graphQL`); the workload pattern serves a static SPA
through a proxy to the Mesh Adapter routes. The template ships its own `Dockerfile` (nginx, port 80, configured at
start through `CONFIG_*` variables) and Helm chart; it does not follow the chart contract of the workload page, so
running it in the cluster is a separate step and not part of this path.

The builder's mandate ([draft-and-validate.md](draft-and-validate.md)) still holds for drafts on the tenant: the
builder writes CK models, pipelines and blueprints, not app code. This path is the developer's own code in the
developer's own repository; the MCP tools below only plan and render files, the developer's coding agent writes them
with its own file tools, because the MCP server cannot write to the developer's machine.

## Steps and tools

| Step | MCP tool | Stays local, and why |
|---|---|---|
| 1. Find the path | `knowledge_search`, `knowledge_get` | - |
| 2. Check model and data of the tenant | `search_types`, `get_type_schema`, `query_entities` | - |
| 3. Create the app | - | `git clone` and `./init.sh`: the code lives in the developer's repository |
| 4. Register the OIDC client of the dev server | `add_authorization_code_client`, `add_scope_to_client`, check with `get_client` | - |
| 5. Configure `config.json` | - | a file of the checkout |
| 6. Dev certificate and licence | - | a certificate file of the developer's machine; the Telerik licence is the developer's own |
| 7. Scaffold pages | `get_custom_app_template_manifest`, `plan_custom_app_scaffold`, `apply_custom_app_scaffold`, `list_kendo_components` | writing the returned files |
| 8. Generate the GraphQL client | `export_runtime_graphql_sdl` | the download, `npm install`, `npm run codegen`: the code generator runs where the code is |
| 9. Check and start | `query_entities` to compare the rows | `npm run lint`, `npm run test:ci`, `npm run build:prod`, `npm start` |

**3. Create the app.** `./init.sh` renames the template (`custom-app`, `CustomApp`) to the app name, writes the
tenant id and the client id into `src/<app>/src/assets/config.json`, the Helm values and the template's tenant
scripts, renames the app folder from `src/custom-app/` to `src/<app>/` (kebab-case app name) and removes itself. An
agent runs it without prompts:
`./init.sh --app-name <App> --tenant-id <tenant> --lang en-GB --yes` (`--client-id <id>` when the client is not
`<app>-frontend-debug`; `--extra-langs de-AT` for more languages). Without a terminal `--app-name` and `--yes` are
required; invalid input stops it with exit code 2 before it changes a file.

**4. OIDC client.** The app signs in with authorization code and PKCE, so the client has no secret. In the tenant of
the app: `add_authorization_code_client` with `clientId` `<app>-frontend-debug` (the default of `init.sh`), a
`clientName`, and `clientUri` = the dev server address: https on port 4300 of the developer's machine with a trailing
slash, exactly as the template's README names it (section "Create the dev certificates"). Redirect, post-logout and
CORS addresses default to the client URI. Then `add_scope_to_client` twice, with `octo_api` and `offline_access`.
`Forbidden` means the user may not manage clients in this tenant: ask the tenant administrator to register the client
(same redirect URI and scopes) and pass its id to `init.sh --client-id`. A client id the tenant does not know ends the
sign-in with an "invalid_client" or "unknown client" page.

**5. Configure.** `config.json` holds `tenantId`, `apiUrl` and `assetServicesUrl` (the asset service), `authorityUrl`
(the identity service, with a trailing slash), `clientId` and `scope` (`openid profile octo_api offline_access`). The
app sends the tenant with the sign-in (`acr_values=tenant:<tenant>`), so the login page of that tenant opens directly.

**6. Certificate and licence.** `npm start` serves https on port 4300 and stops at once without the certificate
files in `src/<app>/`; the template's certificate script creates them (README, "Create the dev certificates"). The
app uses Kendo UI: `npm start` and `npm run build:prod` stop without the developer's own Telerik licence in the
environment variable `TELERIK_LICENSE`. Never commit either.

**7. Scaffold.** `get_custom_app_template_manifest` lists the files the agent may edit and the generated ones it
leaves alone. `plan_custom_app_scaffold` takes `appSlug` (kebab-case) and `drawerItems` (comma- or newline-separated
page names) and returns the pages, routes and drawer items. `apply_custom_app_scaffold` takes that plan and per page
a type binding keyed by its route slug: `TypeId` (the CK type), `GraphqlOperationName` (the camelCase field under
`runtime`, for example `basicAsset` for `Basic/Asset`) and `Attributes` (`Name` in camelCase, `TsType`,
`IsOptional`). It returns `WriteOps` (page component, template, style, a service with a unit test, a DTO and the
query `get<Page>.graphql`), `EditOps` for `app.routes.ts` and the drawer items, and `NextSteps` (grid columns, drawer
icon). A page without a binding gets stubs with TODO markers.

**8. GraphQL client.** `export_runtime_graphql_sdl` returns no schema but a download (the introspection JSON is several
megabytes): a GET on `/file-transfer/download` at the host of the MCP server the agent is connected to (without the
tenant path), with the headers `X-Transfer-Id` (the `TransferId`) and `X-Transfer-Key` (the one-time `transferKey`,
valid a few minutes; or the bearer token of the connection). Save the body as `src/<app>/schema.json`, then run
`npm install` and `npm run codegen` in `src/<app>/`. `codegen.yml` reads `schema.json` by default; for an SDL file set
`OCTO_GRAPHQL_SCHEMA=schema.graphql`. Both files are tenant specific and gitignored. Generated names carry the suffix
`Dto`: a query `GetAssets` gives `GetAssetsQueryDto` and the service `GetAssetsDtoGQL`. `npm run codegen:check`
validates the queries against the schema without writing files. On a fresh tenant this already works: the template's
own query uses only System types, and its sample items table stays off until the sample model is imported.

## Current limitations

These gaps of the tools are known; work around them as described until the tools are fixed (AB#9355, AB#9356,
AB#9789, AB#9406).

- **Scaffold paths after `init.sh`.** `apply_custom_app_scaffold` writes every file below `src/custom-app/`, the folder
  name before `init.sh`. Replace `src/custom-app/` with `src/<app>/` in every path it returns, and pass the three edit
  paths `appRoutesPath`, `commandSettingsPath` and `customSvgIconsPath` with `src/<app>/`. The `NextSteps` text also
  says to run codegen in `src/custom-app/`: run it in `src/<app>/`.
- **Codegen command of the schema export.** `export_runtime_graphql_sdl` tells you to run `graphql-codegen` with
  `--schema schema.json` and to save the file below `src/custom-app/`. Ignore both: save it as `src/<app>/schema.json`
  and run `npm run codegen`, which reads the schema from `codegen.yml`.
- **Names of the generated client.** The service `apply_custom_app_scaffold` renders imports `Get<Page>GQL` and
  `Get<Page>Query`, but the template's codegen generates `Get<Page>DtoGQL` and `Get<Page>QueryDto`. After
  `npm run codegen`, rename the import and the injected type in `services/<page>.service.ts`, then lint and build.
- **Service addresses of a hosted installation.** No MCP tool returns the identity and asset service URLs of a hosted
  OctoMesh. Ask the developer for the URLs they log in to with octo-cli, or the operator of the installation; never
  write a guessed host or a placeholder into `config.json`.

## Check the result

1. `get_client` shows the client with the dev server address as redirect URI and the scopes `octo_api` and
   `offline_access`.
2. `npm run codegen:check`, `npm run lint`, `npm run test:ci` and `npm run build:prod` pass in `src/<app>/`.
3. `npm start`, sign in on the login page of the tenant, open the scaffolded page: its table shows the entities that
   `query_entities` lists for the same type. A sign-in error page means a wrong client id or redirect URI (step 4); a
   certificate error means the browser does not trust the dev certificate (step 6).
