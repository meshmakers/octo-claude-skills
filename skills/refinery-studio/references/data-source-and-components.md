# Data Sources, List Views & Components — Reference

All paths are relative to the app package
`src/octo-mesh-refinery-studio/` unless noted.

## Component organization

- **Routed components**: `*-details.component.ts` (page with header, back button)
- **Inline components**: `*-details-inline.component.ts` (embeddable, `@Input()`
  driven, no routing)
- **Container components**: orchestrate inline components based on selection

Naming/lint: selector prefix `app-` (enforced by ESLint); SCSS for styles;
templates inline (`template:`) or external (`templateUrl:`). Unused imports are
errors; unused vars must be `_`-prefixed; generated GraphQL under
`src/app/graphQL/**` is excluded from linting.

## mm-list-view (ListViewComponent)

`ListViewComponent` from `@meshmakers/shared-ui` is the primary list/grid. Wire
it to a data-source directive via the directive's selector + `exportAs`. Common
inputs:

```html
<mm-list-view
  appMyDataSource
  #dir="appMyDataSource"
  [sortable]="true"
  [rowFilterEnabled]="true"
  [searchTextBoxEnabled]="true"
  [selectable]="{mode: 'single', enabled: true}"
  [pageable]="{buttonCount: 3, pageSizes: [10, 20, 50, 100]}"
  [pageSize]="20"
  [columns]="[
    {field: 'fieldName', displayName: 'Display Name', dataType: 'text'},
    {field: 'dateField', displayName: 'Date', dataType: 'date'},
    {field: 'numField', displayName: 'Number', dataType: 'numeric'}
  ]"
  [actionCommandItems]="[
    {id: 'edit', type:'link', text: 'Edit', svgIcon: editIcon, link: 'path/to/{{rtId}}'}
  ]"
  [contextMenuCommandItems]="[copyIdMenuItem, {id:'sep', type:'separator'},
    {id: 'delete', type:'link', text: 'Delete', onClick: onDeleteClick, svgIcon: deleteIcon}]"
  [leftToolbarActions]="[
    {id: 'add', type:'link', text: 'New Item', svgIcon: plusIcon, link: 'path/to/new'}
  ]"
  (rowClicked)="onRowClicked($event)">
</mm-list-view>
```

**Sorting priority**: when a data source has a predefined sort, interactive
column-header sorting should win:

```typescript
const kendoSort = this.getSortDefinitions(queryOptions.state);
const sortToUse = (kendoSort && kendoSort.length > 0) ? kendoSort : this._predefinedSort;
```

## OctoGraphQlDataSource directive

Extend `OctoGraphQlDataSource<T>` (from `@meshmakers/octo-ui`) and implement
`fetchData`. The base class provides `getSortDefinitions`,
`getFieldFilterDefinitions`, `getSearchFilterDefinitions`.

Required imports for a new directive:

```typescript
import { Directive, forwardRef, inject } from "@angular/core";
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { OctoGraphQlDataSource } from '@meshmakers/octo-ui';
import { DataSourceBase, FetchDataOptions, FetchResultTyped, ListViewComponent } from '@meshmakers/shared-ui';
import { GraphQL } from '@meshmakers/octo-services';
```

Pattern (verified against
`tenants/communication/adapters/data-sources/adapters-data-source.directive.ts`):

```typescript
@Directive({
  selector: "[appMyDataSource]",
  exportAs: 'appMyDataSource',
  providers: [{ provide: DataSourceBase, useExisting: forwardRef(() => MyDataSourceDirective) }]
})
export class MyDataSourceDirective extends OctoGraphQlDataSource<MyType> {
  private readonly gql = inject(GetMyDataDtoGQL);

  constructor() {
    super(inject(ListViewComponent));
    this.searchFilterAttributePaths = ['fieldName'];
  }

  public override fetchData(options: FetchDataOptions): Observable<FetchResultTyped<MyType> | null> {
    const variables = {
      first: options.state.take,
      after: GraphQL.offsetToCursor(options.state.skip ?? 0),
      sortOrder: this.getSortDefinitions(options.state),
      fieldFilter: this.getFieldFilterDefinitions(options.state),
      searchFilter: this.getSearchFilterDefinitions(options.textSearch)
    };
    return this.gql.fetch({ variables, fetchPolicy: "network-only" }).pipe(map(result =>
      new FetchResultTyped<MyType>(
        result.data?.runtime?.myData?.items?.filter(i => i !== null) as MyType[] || [],
        result.data?.runtime?.myData?.totalCount ?? 0
      )));
  }
}
```

Derive the item type from the generated query type rather than hand-writing it:

```typescript
type Item = NonNullable<NonNullable<NonNullable<GetMyDataQueryDto['runtime']>['myData']>['items']>[number];
export type MyType = NonNullable<Item>;
```

Auto-generated services are injected the same way for one-off fetches:

```typescript
private readonly getEntityGQL = inject(GetRuntimeEntityByIdDtoGQL);
const result = await firstValueFrom(this.getEntityGQL.fetch({ variables: {...} }));
```

## New list-component checklist

### 1. GraphQL query (`src/app/graphQL/getMyItems.graphql`)

```graphql
query GetMyItems($first: Int, $after: String, $sortOrder: [Sort], $fieldFilter: [FieldFilter], $searchFilter: SearchFilter) {
  runtime {
    myItems(first: $first, after: $after, sortOrder: $sortOrder, fieldFilter: $fieldFilter, searchFilter: $searchFilter) {
      totalCount
      pageInfo { hasNextPage endCursor }
      items {
        rtId
        ckTypeId
        # ... fields ...
        constructionKitType { ckTypeId { fullName } }   # needed for Copy ID
      }
    }
  }
}
```

Then run `npm run codegen`.

### 2. Folder structure

```
repository/my-feature/
├── data-sources/
│   └── my-feature-data-source.directive.ts
├── my-feature-list.component.ts
├── my-feature-list.component.html
├── my-feature-list.component.scss
└── my-feature.routes.ts
```

### 3. Component

```typescript
@Component({
  selector: 'app-my-feature-list',
  standalone: true,
  imports: [MyFeatureDataSourceDirective, ListViewComponent],
  templateUrl: './my-feature-list.component.html',
  styleUrl: './my-feature-list.component.scss'
})
export class MyFeatureListComponent { }
```

### 4. Routes (`my-feature.routes.ts`)

```typescript
import { Routes } from '@angular/router';
import { MyFeatureListComponent } from './my-feature-list.component';

export const routes: Routes = [{
  path: '',
  component: MyFeatureListComponent,
  data: { breadcrumb: [{ label: 'My Feature', url: 'repository/my-feature' }] }
}];
```

### 5. Register in parent (`repository.routes.ts`)

```typescript
{
  path: 'my-feature',
  loadChildren: () => import('./my-feature/my-feature.routes').then(m => m.routes),
  data: { breadcrumb: [{ label: 'Repository', svgIcon: storage, url: 'repository' }] }
}
```

## Copy ID context menu (REQUIRED for Rt entities)

Every list view and detail view showing Runtime (Rt) entities MUST include a
"Copy ID" context menu with these submenu items:

- **RtId** — runtime instance id (e.g. `65d5c447b420da3fb12381bc`)
- **CkTypeId** — full CK type name (e.g. `System.Communication/MeshAdapter`)
- **RtCkTypeId** — same, from the entity's `ckTypeId` field
- **RtEntityId** — combined `{ckTypeId}@{rtId}`

Imports: `copyIcon` from `@progress/kendo-svg-icons`,
`NotificationDisplayService` from `@meshmakers/shared-ui`,
`CommandItem`/`CommandItemExecuteEventArgs` from `@meshmakers/shared-services`.

```typescript
private readonly notificationDisplayService = inject(NotificationDisplayService);
protected readonly copyIcon = copyIcon;

protected readonly copyIdMenuItem: CommandItem = {
  id: 'copyId', type: 'link', text: 'Copy ID', svgIcon: copyIcon,
  children: [
    { id: 'copyRtId', type: 'link', text: 'RtId', onClick: this.onCopyRtId.bind(this) },
    { id: 'copyCkTypeId', type: 'link', text: 'CkTypeId', onClick: this.onCopyCkTypeId.bind(this) },
    { id: 'copyRtCkTypeId', type: 'link', text: 'RtCkTypeId', onClick: this.onCopyRtCkTypeId.bind(this) },
    { id: 'copyRtEntityId', type: 'link', text: 'RtEntityId', onClick: this.onCopyRtEntityId.bind(this) }
  ]
};

private async copyToClipboard(value: string, label: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value);
    this.notificationDisplayService.showSuccess(`${label} copied`, 2000);
  } catch (error) {
    this.notificationDisplayService.showError('Failed to copy to clipboard');
  }
}
// onCopyRtId → entity.rtId; onCopyCkTypeId → entity.constructionKitType?.ckTypeId?.fullName || entity.ckTypeId;
// onCopyRtCkTypeId → entity.ckTypeId; onCopyRtEntityId → `${entity.ckTypeId}@${entity.rtId}`
```

Add `copyIdMenuItem` to `[contextMenuCommandItems]`, and ensure the GraphQL
query selects `constructionKitType { ckTypeId { fullName } }`.

## CK detail-inline components

For `ck-*-details-inline.component.ts`:

- **Semantic versioned names**: show `semanticVersionedFullName` in parentheses
  when it differs from `fullName`.
- **Modifier badges**: use colored badges, not parenthesized text —
  `.badge.abstract` (cyan), `.badge.final` (violet), `.badge.normal` (subtle).
- Shared CK styles live in the `_ck-details-common.scss` mixin; key classes:
  `.info-row`, `.hierarchy-row`, `.type-info`, `.semantic-name`.

## Query Builder

`repository/query-builder/` — orchestrator
(`query-builder.component.ts`, saved-queries sidebar), config panel
(`query-config-panel.component.ts`: CK type selection, columns, filters, sort),
results panel (`query-results-panel.component.ts`, uses `mm-list-view`), and a
transient `query-results-data-source.directive.ts`. Supports transient queries
without saving, save/load configs, navigation to entity details, and per-column
filter/sort. Stream-data queries use `stream-data-query-results-data-source.directive.ts`.

## Runtime Browser messages

`RuntimeBrowserComponent` (from `@meshmakers/octo-ui`) takes a
`RuntimeBrowserMessages` object via its `messages` input; the app supplies
English defaults from `shared/runtime-browser-messages.ts`.
