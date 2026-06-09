# LCARS Theme System — Reference

Star-Trek-LCARS-inspired theme for OctoMesh Data Refinery Studio, derived from
the Octo Brand Manual. **`src/styles.scss` is the single source of truth** for
tokens, global layout classes, and Kendo overrides.

## Brand Colors (theme-invariant tokens)

Defined in `:root` in `styles.scss`; available as both SCSS-style hex and CSS
custom properties. These keep the same value in dark and light mode.

| Category | Name | Hex | CSS var | Usage |
|----------|------|-----|---------|-------|
| Primary | Octo Mint | `#64ceb9` | `--octo-mint` | Main accent, glow, primary buttons |
| Primary | Neo Cyan | `#00a8dc` | `--neo-cyan` | Secondary highlights |
| Secondary | Indigogo | `#546fbd` | — | Panel accents, info states |
| Tertiary | Toffee | `#da9162` | `--toffee` | Warm accent, warnings |
| Tertiary | Bubblegum | `#ec658f` | `--bubblegum` | Alerts, errors |
| Tertiary | Lilac Glow | `#c861d6` | — | Hover states |
| Tertiary | Royal Violet | `#6c4da8` | `--royal-violet` | LCARS accents |
| Neutral | Ash Blue | `#9292a6` | — | Inactive elements, secondary text |
| Neutral | Iron Navy | `#394555` | `--iron-navy` | Surface, panels |
| Neutral | Deep Sea | `#07172b` | `--deep-sea` | Background (NEVER use black) |

Other root vars: `--lcars-font-primary: 'Montserrat', 'Roboto', sans-serif`,
`--lcars-glow-primary: 0 0 10px rgba(100,206,185,0.4)`,
`--lcars-radius-sm/md/lg/xl: 4px/8px/16px/24px`.

### Typography

- Primary: **Montserrat** (Google Fonts, imported in `index.html`)
- Fallback: Roboto
- Mono: Roboto Mono (code, version numbers)

## Semantic Theme Tokens (`--theme-*`) — adapt to dark/light

Dark defaults live in `:root`; light values come from a
`@mixin light-theme-tokens` applied via:
1. `@media (prefers-color-scheme: light) :root:not([data-theme="dark"])`
   — auto-light when OS pref is light AND no force-dark override
2. `:root[data-theme="light"]` — explicit force

| Token | Dark | Light | Purpose |
|---|---|---|---|
| `--theme-bg-app` | `#07172b` | `#f3f6fa` | Page background |
| `--theme-bg-surface` | `#394555` | `#ffffff` | Panels |
| `--theme-bg-elevated` | `#1f2e40` | `#eef2f7` | AppBar, toolbars |
| `--theme-text-primary` | `#ffffff` | `#07172b` | Body text |
| `--theme-text-secondary` | `#9292a6` | `#4b576b` | Labels |
| `--theme-text-accent` | `#64ceb9` | `#2e8473` | Mint text (darkened in light) |
| `--theme-border-subtle` | `rgba(100,206,185,0.20)` | `rgba(46,132,115,0.30)` | Default borders |
| `--theme-glow-primary` | `0 0 10px rgba(100,206,185,0.40)` | `0 1px 3px rgba(7,23,43,0.10)` | Accent shadow |
| `--theme-status-success` | `#37b400` | `#2e8b00` | Status |
| `--theme-status-error` | `#ec658f` | `#c63d6a` | Status |
| `--theme-chart-1..8` | brand colors | darkened variants | 8-series chart palette |

See `src/styles.scss` for the complete catalog (`--theme-status-warning/info`,
`--theme-glow-accent`, etc.).

### Theme switching

- `ThemeService` (`src/app/services/theme.service.ts`) holds a signal
  `preference: 'system' | 'dark' | 'light'`, persists explicit choices to
  localStorage key `octo-theme-preference`, writes `<html data-theme="…">`, and
  exposes a `resolved: 'dark' | 'light'` signal.
- `ThemeToggleComponent` (`src/app/shared/theme-toggle/`) in the AppBar cycles
  `system → light → dark → system`.
- `ChartColorsService` (`src/app/services/chart-colors.service.ts`) exposes a
  `palette()` signal (8 theme-aware colors) for inline Kendo charts.
- An inline `<script>` in `index.html` reads localStorage before stylesheets
  load to suppress FOUC.

## Component-author conventions (Do / Do-not)

- **Do** use `var(--theme-bg-*)`, `var(--theme-text-*)`, `var(--theme-border-*)`
  for theme-dependent values; `var(--theme-glow-primary/accent)` for glow;
  `var(--theme-status-*)` for status.
- **Do** use `var(--octo-mint)`, `var(--neo-cyan)`, etc. for decorative LCARS
  accent elements that keep brand colors in both themes (header accent bar,
  footer ribbon, panel rule).
- **Do** use `color-mix(in srgb, var(--brand) X%, transparent)` for alpha
  derivations instead of `rgba($scss-var, 0.X)`.
- **Do NOT** redeclare brand SCSS color vars at the top of component SCSS —
  `styles.scss` is the single source of truth.
- **Do NOT** duplicate global LCARS layout classes in component SCSS (see
  below); they are global.
- **Do NOT** use pure black — Deep Sea `#07172b` is the floor.

### Global utility / layout classes (in styles.scss — do not redefine)

`.lcars-panel`, `.lcars-panel-asymmetric`, `.lcars-header-bar`, `.lcars-divider`,
`.lcars-glow-mint/cyan/violet/pink`, `.lcars-text-mint/cyan/violet`,
`.lcars-scanline`, `.lcars-pulse`, plus the page-layout classes
`.lcars-page-header`, `.lcars-header-accent`, `.header-content`, `.page-title`,
`.lcars-content-panel`, `.panel-accent-top/bottom`, `.lcars-footer`,
`.footer-bar`, `.footer-indicator`, `.k-command-cell`, `.list-view-toolbar`.

### Design patterns

1. Asymmetric border radius (one side rounded, one square)
2. Subtle brand-color glow on active/hover
3. Linear gradient backgrounds (Iron Navy → Deep Sea)
4. Mint/Cyan accent lines (left border or top bar)
5. Uppercase labels with letter-spacing
6. Pulsing status indicators (`@keyframes pulse-glow`)

### Kendo overrides

All Kendo components are themed in `styles.scss`: `.k-appbar`, `.k-button`,
`.k-grid`, `.k-dialog`, `.k-drawer` (inherited from octo-ui `octo.styles()`),
`.k-popup`. Override there, not per-component.

### Process Designer canvas theming

The `@meshmakers/octo-process-diagrams` library ships neutral defaults. Refinery
Studio overrides them in `styles.scss`:

```scss
mm-process-designer, mm-symbol-editor, mm-symbol-editor-page {
  --designer-canvas-color: #394555 !important;          // Iron Navy
  --designer-grid-color: rgba(100, 206, 185, 0.15) !important;
}
```

Fallback via `::ng-deep` on `.canvas-background { fill: … }` /
`.designer-grid-line { stroke: … }`. After changing the library, rebuild it in
`octo-frontend-libraries` (`npm run build:octo-process-diagrams`), `npm install`
here, then `npx ng cache clean` and restart `npm start`.

## Required LCARS Page Layout

Every page-level component MUST use this structure: header, content panel,
footer. The classes are global — copy the HTML, keep component SCSS minimal.

### HTML template

```html
<div class="[component-name]-container">
  <div class="lcars-page-header">
    <div class="lcars-header-accent"></div>
    <div class="header-content">
      <h1 class="page-title">
        <span class="title-prefix">SECTION</span>   <!-- REPOSITORY / SYSTEM / IDENTITY -->
        <span class="title-main">Page Title</span>
      </h1>
      <div class="header-stats">
        <div class="stat-badge">
          <span class="badge-icon">&#9632;</span>
          <span class="badge-label">Context Label</span>
        </div>
      </div>
    </div>
    <div class="lcars-header-line"></div>
  </div>

  <div class="lcars-content-panel">
    <div class="panel-accent-top"></div>
    <!-- main content -->
    <div class="panel-accent-bottom"></div>
  </div>

  <div class="lcars-footer">
    <div class="footer-bar bar-1"></div>
    <div class="footer-bar bar-2"></div>
    <div class="footer-bar bar-3"></div>
    <div class="footer-spacer"></div>
    <div class="footer-indicator">
      <span class="indicator-dot"></span>
      <span class="indicator-text">READY</span>
    </div>
  </div>
</div>
```

### Component SCSS (minimal — only the container)

The header/panel/footer classes are global in `styles.scss`; do NOT redeclare
them. Component SCSS holds only the container, responsive padding, and any
component-specific `::ng-deep`:

```scss
.my-component-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  background: linear-gradient(180deg, rgba(7, 23, 43, 0.95), rgba(7, 23, 43, 1));
  gap: 16px;
}
```

Add responsive padding overrides at the 1024px and 768px breakpoints. Prefer
`var(--deep-sea)` / `color-mix(...)` over hard-coded hex where the value should
track the theme.

### Responsive breakpoints

| Width | Layout |
|-------|--------|
| < 480px | Mobile small |
| < 768px | Mobile |
| < 1024px | Tablet |
| < 1440px | Desktop small |
| ≥ 1440px | Desktop large |

### Components already using the pattern (title prefix / main)

`tenants` (SYSTEM / Tenant Management), `ck-models-browser` (REPOSITORY / CK
Browser), `runtime-browser` (REPOSITORY / Runtime Browser), `auto-increment-list`,
`fixup-scripts-list`, `events-list`, `query-builder`, `tenant-provisioning`
(SYSTEM / Admin Provisioning: {tenantId}).
