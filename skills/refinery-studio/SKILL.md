---
name: refinery-studio
description: >-
  Guides Angular development on the OctoMesh Data Refinery Studio
  (octo-frontend-refinery-studio) — the main web app for CK model design,
  dashboards, queries, pipelines, and visualizations (distinct from the older
  admin panel). Covers the tech stack, multi-tenant /:tenantId/ routing, the
  OctoGraphQlDataSource list-view pattern, the GraphQL codegen workflow, the
  LCARS theme token system, the link to octo-frontend-libraries, and the
  lint/test/build commands.
  Trigger on: refinery studio, data refinery, OctoMesh frontend, Angular
  component work, mm-list-view, OctoGraphQlDataSource, data source directive,
  GraphQL codegen frontend, npm run codegen, LCARS theme, theme tokens,
  Kendo UI, Apollo Angular, tenant routing, octo-frontend-libraries.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/refinery-studio/references/*)"
---

# OctoMesh Data Refinery Studio (Angular)

## Purpose

Developer guide for working in **`octo-frontend-refinery-studio`** — the main
Angular web application for OctoMesh. The Studio is a unified workspace for
three audiences:

- **Developers** — design Construction Kits (CK), configure data models,
  build integrations
- **Data owners** — build dashboards (MeshBoards), define queries, manage
  data pipelines
- **End users** — interactive dashboards, real-time visualizations, KPIs

**This is NOT the old admin panel.** `octo-frontend-admin-panel` is the
legacy interface. New frontend feature work belongs in Refinery Studio.

## CRITICAL: where the app actually lives

The git repo root (`C:\dev\meshmakers\octo-frontend-refinery-studio`) is **not**
the npm project. The app package is one level down:

```
octo-frontend-refinery-studio/
└── src/
    └── octo-mesh-refinery-studio/   ← the Angular app (package.json, codegen.yml, src/)
```

**Run all npm/ng commands from `src/octo-mesh-refinery-studio/`.** There is no
root-level `package.json`.

## Tech Stack (verified from package.json)

| Piece | Version | Notes |
|-------|---------|-------|
| Angular | `^21.2.4` | Standalone components + signals; `app-` selector prefix |
| Apollo Angular | `^13.0.0` | GraphQL client (`@apollo/client ^4.1.6`) |
| Kendo UI Angular | `23.2.0` | `@progress/kendo-angular-*` component suite |
| RxJS | `~7.8.2` | Reactive streams |
| TypeScript | `~5.9.3` | Strict; ESLint via `angular-eslint 21` |
| angular-oauth2-oidc | `^20.0.2` | Auth, wrapped by `@meshmakers/shared-auth` |

Other notable deps: `monaco-editor` (YAML/code editing), `dockview-angular`
(dock layouts), `cytoscape` + `dagre` (graph views), `cron-parser`/`cronstrue`
(schedule UIs), `tus-js-client` (resumable uploads), `@microsoft/signalr`.

CK construction-kit terms: **CK** = schema (`CkTypeDto`, `CkEnumDto`,
`CkRecordDto`, `CkAttributeDto`); **Rt** = data instances (`RtEntityDto` with
`rtId`, `ckTypeId`, associations). Use `rtCkTypeId` (e.g.
`OctoSdkDemo/Customer`) for runtime queries, **not** `fullName`.

## Commands (verified in package.json — run from `src/octo-mesh-refinery-studio/`)

| Command | What it does | Label |
|---------|--------------|-------|
| `npm install` | Install deps (resolves `@meshmakers/*` from local `file:` dist) | Mutating (writes node_modules) |
| `npm start` / `ng serve` | Dev server at `https://localhost:4200` | Read-only |
| `npm run build` | `ng lint && ng build` (lint gate is built in) | Read-only (build output) |
| `npm run build:skip-lint` | `ng build` without lint | Read-only |
| `npm run watch` | `ng build --watch --configuration development` | Read-only |
| `npm run lint` / `ng lint` | ESLint over the project | Read-only |
| `ng lint --fix` | Auto-fix unused imports etc. | Mutating (rewrites source) |
| `npm test` | `ng test --watch=false --browsers=ChromeHeadlessCI` | Read-only |
| `npm run codegen` | Regenerate GraphQL types/services | Mutating (rewrites generated `.ts`) |

`npm start`/`npm run build` are prefixed by a `setup-license` step
(`scripts/setup-license.js`) for the Kendo license — do not bypass it.

### Lint/test discipline (from the repo CLAUDE.md — REQUIRED)

> **Always run the linter after every code change.** CI fails on any lint
> error. Common fixes: unused imports → `ng lint --fix`; intentionally unused
> vars → prefix with `_`; missing types → add explicit annotations.

Pre-commit gate (run from `src/octo-mesh-refinery-studio/`):

```bash
ng lint && npm test -- --watch=false --browsers=ChromeHeadless && ng build --configuration development
```

If `package.json` changed (incl. via `npm install`), regenerate the lock file
before committing: `rm -f package-lock.json && npm install` (CI runs
`npm install` and needs them in sync).

## Multi-Tenant Routing

Routes follow the **`/:tenantId/...`** pattern. Each tenant gets an isolated
Apollo client pointing at that tenant's GraphQL endpoint. Feature areas are
lazy-loaded via `*.routes.ts`:

- `repository/` — Runtime Browser, CK Browser, Auto-Increment, Fixup Scripts,
  Events, Query Builder, Archives
- `reporting/` — Report Explorer (folder/file tree)
- `identity/` — users, roles, groups, OAuth clients, identity providers
- `communication/` — adapters, pools, applications, data flows
- `general/`, `bot/`, `development/`, `ui-management/`

When adding a feature, register its routes under the relevant parent
`*.routes.ts` with a `loadChildren` import and a `breadcrumb` data entry.

## OctoGraphQlDataSource Pattern (list views)

The primary list/grid is `ListViewComponent` (`mm-list-view`) from
`@meshmakers/shared-ui`. Back it with a **directive** that extends
`OctoGraphQlDataSource<T>` (from `@meshmakers/octo-ui`). Verified sketch,
condensed from `tenants/communication/adapters/data-sources/adapters-data-source.directive.ts`:

```typescript
import { Directive, forwardRef, inject } from "@angular/core";
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { OctoGraphQlDataSource } from '@meshmakers/octo-ui';
import { DataSourceBase, FetchDataOptions, FetchResultTyped, ListViewComponent } from '@meshmakers/shared-ui';
import { GraphQL } from '@meshmakers/octo-services';
import { GetSystemCommunicationAdaptersDtoGQL, GetSystemCommunicationAdaptersQueryDto } from '../../../../graphQL/getSystemCommunicationAdapters';

// Derive the item type from the generated query type (no hand-written DTOs)
type Item = NonNullable<NonNullable<NonNullable<GetSystemCommunicationAdaptersQueryDto['runtime']>['systemCommunicationAdapter']>['items']>[number];
export type AdapterDto = NonNullable<Item>;

@Directive({
  selector: "[appAdaptersDataSource]",
  exportAs: 'appAdaptersDataSource',
  providers: [{ provide: DataSourceBase, useExisting: forwardRef(() => AdaptersDataSourceDirective) }]
})
export class AdaptersDataSourceDirective extends OctoGraphQlDataSource<AdapterDto> {
  private readonly gql = inject(GetSystemCommunicationAdaptersDtoGQL);

  constructor() {
    super(inject(ListViewComponent));
    this.searchFilterAttributePaths = ['name'];   // fields the text box searches
  }

  public override fetchData(options: FetchDataOptions): Observable<FetchResultTyped<AdapterDto> | null> {
    const variables = {
      first: options.state.take,
      after: GraphQL.offsetToCursor(options.state.skip ?? 0),
      sortOrder: this.getSortDefinitions(options.state),
      fieldFilter: this.getFieldFilterDefinitions(options.state),
      searchFilter: this.getSearchFilterDefinitions(options.textSearch)
    };
    return this.gql.fetch({ variables, fetchPolicy: "network-only" }).pipe(map(result =>
      new FetchResultTyped<AdapterDto>(
        result.data?.runtime?.systemCommunicationAdapter?.items?.filter(i => i !== null) as AdapterDto[] || [],
        result.data?.runtime?.systemCommunicationAdapter?.totalCount ?? 0
      )));
  }
}
```

Key points:
- The base class supplies `getSortDefinitions`, `getFieldFilterDefinitions`,
  `getSearchFilterDefinitions` — use them; do not hand-roll Kendo state parsing.
- Always `fetchPolicy: "network-only"` for live list data.
- Derive DTO types from the **generated** query type; never duplicate the shape.
- Wire it on the template via the directive selector and `exportAs`:
  `<mm-list-view appAdaptersDataSource #dir="appAdaptersDataSource" ...>`.
- **Copy ID context menu** is REQUIRED on every list/detail view showing Rt
  entities (submenu: RtId, CkTypeId, RtCkTypeId, RtEntityId). The GraphQL query
  must select `constructionKitType { ckTypeId { fullName } }`.

For the full new-list-component checklist (folder layout, routes, `mm-list-view`
inputs, Copy-ID implementation), read
`references/data-source-and-components.md`.

## GraphQL Code Generation Workflow

GraphQL operations live in `src/app/graphQL/*.graphql`. After editing or adding
one, run `npm run codegen`. Config is `codegen.yml` (verified):

- Generated types get the **`Dto`** suffix (`typesSuffix: Dto`) →
  `RtEntityDto`, `CkTypeDto`, `GetSystemCommunicationAdaptersQueryDto`, etc.
- `near-operation-file` preset → one generated `.ts` per `.graphql` operation,
  with shared base types in `globalTypes.ts`.
- An injectable Apollo Angular service is generated per operation
  (`...DtoGQL`, e.g. `GetSystemCommunicationAdaptersDtoGQL`) — inject it with
  `inject(...)`.
- `possibleTypes.ts` (fragment matcher) and `scalars: { DateTime: Date }` are
  emitted too.

**Never edit generated `.ts` by hand** — edit the `.graphql`, regenerate. The
generated GraphQL folder is excluded from ESLint. Ensure `schema.graphql` is
current before generating.

## LCARS Theme System

The Studio uses a Star-Trek-LCARS-inspired theme built from the Octo Brand
Manual. **`src/styles.scss` is the single source of truth** for theme tokens,
global LCARS layout classes, and Kendo overrides.

Two token tiers:

- **Brand tokens (theme-invariant)** — `--octo-mint` `#64ceb9`, `--neo-cyan`
  `#00a8dc`, `--royal-violet` `#6c4da8`, `--toffee` `#da9162`, `--bubblegum`
  `#ec658f`, etc. Use these for decorative accents (header bar, footer ribbon).
- **Semantic theme tokens (`--theme-*`)** — `--theme-bg-app`,
  `--theme-bg-surface`, `--theme-text-primary`, `--theme-text-secondary`,
  `--theme-text-accent`, `--theme-border-subtle`, `--theme-glow-primary`,
  `--theme-status-success/warning/error/info`, `--theme-chart-1..8`. These have
  dark defaults and light overrides; use them for anything that must adapt to
  dark/light mode.

Dark is default; light auto-applies on `prefers-color-scheme: light` unless the
user forces a theme via the AppBar toggle (`ThemeService` writes
`<html data-theme="…">`, persisted in localStorage key
`octo-theme-preference`).

### Do / Do-not (from repo CLAUDE.md)

- **Do** use `var(--theme-bg-*)`, `var(--theme-text-*)`, `var(--theme-border-*)`
  for theme-dependent values, and `var(--octo-mint)` etc. for brand accents.
- **Do** use `color-mix(in srgb, var(--brand) X%, transparent)` for alpha
  derivations.
- **Do NOT** redeclare brand color SCSS vars at the top of a component's SCSS —
  `styles.scss` owns them.
- **Do NOT** duplicate the global LCARS layout classes
  (`.lcars-page-header`, `.lcars-content-panel`, `.lcars-footer`, `.footer-bar`,
  etc.) in component SCSS — they are global. Component SCSS should hold only the
  container class (background gradient), responsive padding, and component
  `::ng-deep` overrides.
- **Do NOT** use pure black — the darkest background is Deep Sea `#07172b`.
- Every page-level component MUST use the standard LCARS layout (header /
  content panel / footer). Library components stay theme-agnostic; LCARS styling
  is the host app's job.

For the full token catalog, page-layout HTML/SCSS template, and component-author
conventions, read `references/lcars-theme.md`.

## Shared Libraries — `octo-frontend-libraries`

The `@meshmakers/*` packages are developed in the **separate**
`octo-frontend-libraries` repo and consumed here, **not** via an npm-link
script. In `package.json` they are `file:` references into the sibling repo's
built dist:

```
"@meshmakers/octo-ui": "file:../../../octo-frontend-libraries/src/frontend-libraries/dist/meshmakers/octo-ui"
```

(CI/Docker swaps these `file:` refs for registry versions before install.)

| Library | Provides |
|---------|----------|
| `@meshmakers/shared-auth` | OAuth2/OIDC (`AuthorizeGuard`, `AuthorizeService`) |
| `@meshmakers/shared-services` | messages, breadcrumbs, `CommandItem`, `TreeItemDataTyped` |
| `@meshmakers/shared-ui` | `ListViewComponent`, `DataSourceBase`, `FetchResultTyped`, dialogs |
| `@meshmakers/octo-services` | `GraphQL` utilities, `OctoErrorLink` |
| `@meshmakers/octo-ui` | `PropertyGridComponent`, `OctoGraphQlDataSource`, Runtime Browser |
| `@meshmakers/octo-process-diagrams` | process diagram / symbol editor |
| `@meshmakers/octo-meshboard` | dashboard widgets (KPI, Gauge, Chart, …) |

**To change a shared library**, edit and build it in `octo-frontend-libraries`
(per-library script, e.g. `npm run build:octo-ui`, which runs `ng lint && ng
build`), then re-run `npm install` here to pick up the updated `dist/`. Clear
the Angular cache if stale: `npx ng cache clean`. Keep `@angular/*` versions
aligned across both repos or `npm install` hits `ERESOLVE` peer conflicts.

## Backend for local UI dev

The Studio needs running OctoMesh services. To stand up a `meshtest` tenant
with sample data (commands run via octo-cli, which must be on PATH):

```powershell
octo-cli -c Create -tid meshtest -db meshtest        # create tenant (Mutating)
./om_importck.ps1 -configuration Debug               # import sample CKs
./om_importrt_sample_general.ps1                      # optional runtime data
./om_importrt_sample_simulation.ps1                   # optional simulation feed
```

For building/starting the backend services and infrastructure, defer to the
`octo-devtools` skill.

## Common Pitfalls (from the repo CLAUDE.md)

- Running npm/ng from the repo root — there is no package.json there; use
  `src/octo-mesh-refinery-studio/`.
- Editing generated GraphQL `.ts` files by hand instead of the `.graphql`
  source + `npm run codegen`.
- Forgetting `npm run codegen` after touching a `.graphql` file (build then
  references a missing/old `...DtoGQL`).
- Skipping `ng lint` — CI fails on any lint error; unused imports and untyped
  vars are the usual culprits.
- Hand-writing DTO interfaces instead of deriving from generated query types.
- Duplicating global LCARS classes or brand color vars in component SCSS.
- Mismatched `@angular/*` versions between this repo and
  `octo-frontend-libraries` → `ERESOLVE` on install.
- Omitting the Copy-ID context menu (and its `constructionKitType` query field)
  on Rt entity list/detail views.

## References

- `references/data-source-and-components.md` — new list-component checklist,
  `mm-list-view` inputs, OctoGraphQlDataSource details, Copy-ID context menu,
  CK detail-inline conventions.
- `references/lcars-theme.md` — brand + semantic token catalog, page-layout
  HTML/SCSS template, light-theme tokens, Kendo overrides, component-author
  conventions.
