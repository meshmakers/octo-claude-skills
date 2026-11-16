# HTTP-API pipelines on the Mesh Adapter — verified patterns

JSON HTTP APIs built purely from `FromHttpRequest@2` pipelines — no service code.
The transformations below ran verbatim in production-shape on 2026-06-09 (one-time-ticket
demo, System.Communication 3.22.0, then with the deprecated `FromHttpRequest@1`
trigger); the triggers now use `FromHttpRequest@2`, which takes the same `method` and
`path` and adds the route security. Node property details → pipeline-expert skill.

## Route security (authenticated by default)

`FromHttpRequest@2` authorizes every call before the pipeline runs:

1. a bearer token issued by the tenant's identity service (signature, issuer, audience,
   lifetime) — otherwise `401`;
2. the token's tenant must be the tenant the adapter serves — otherwise `403` (also for
   client-credentials tokens);
3. with `requiredRoles`, the caller must hold at least one of them — otherwise `403`;
   without it any valid token of the tenant is enough.

Use the defaults (`allowAnonymous` omitted = `false`) for every route of an app, and
add `requiredRoles` with the app's roles for routes that change data. The caller's
`Authorization` header never reaches the DataContext. A web app calls the routes with
the signed-in user's access token; another service calls them with a client-credentials
token of the same tenant.

### Public routes (only on purpose)

> **Warning — a public route can be called by anyone who knows the URL.** No token, no
> tenant check, no role check, no caller identity: the pipeline runs with the adapter's
> rights, and whatever it reads or returns is open to the internet. The adapter records
> only that the route exists (one event per deployment); single calls are not audited by
> default. Unintended public routes have been found on production tenants before.

Make a route public only when its callers cannot have an account of the tenant, for
example a webhook of an external service, a public form, or a one-time link sent to a
person outside the tenant (Pattern 3). Then:

- set `allowAnonymous: true` on `FromHttpRequest@2` explicitly and say why in a comment;
- return only what an anonymous caller may see (`Project@1 clear: true`), never list or
  search endpoints over tenant data, and verify the caller in the pipeline where possible
  (a secret in the link, a signature of the webhook, a CAPTCHA with `VerifyCaptcha@1`);
- never use `FromHttpRequest@1` for it: it is deprecated and always public, without a
  visible marker in the YAML.

## Route + request/response semantics

- Routes register per `(METHOD, path)` tuple as `/{tenantId}{path}`, lowercase.
  GET and POST on the same path are two routes (e.g. `GET /tickets` + `POST /tickets`).
- If a path matches but the method has no route, the adapter answers
  **200 with empty body in ~0.1 ms** — treat that symptom as "route missing".
- Request context: `$.body` (parsed JSON body — POST/PUT only), `$.query.<param>`,
  `$.path`, `$.method`, `$.files[]`, `$.formData`.
- **Response = the entire final DataContext serialized as JSON.** Always 200,
  always `application/json` — no status-code or content-type control, and
  `SetPipelineExecutionResult@1` does NOT shape the HTTP response. The ONLY
  shaping tool is `Project@1` with `clear: true` as the last node. Without it the
  response leaks `$.body` (the raw request!) and every lookup result.
- Errors: return `{ "error": "<code>" }` fields and let clients check for them.

## Pattern 1 — create an entity (`POST /tickets` → `{ ticketId }`)

```yaml
triggers:
  - type: FromHttpRequest@2
    method: Post
    path: /tickets
    requiredRoles: [TicketIssuer]          # any valid token of the tenant without it

transformations:
  - type: CreateUpdateInfo@1
    updateKind: Insert
    ckTypeId: Demo.Tickets/Ticket          # unversioned in pipeline YAML
    rtIdPath: $.newTicketRtId              # empty path + generateRtId → new ObjectId
    generateRtId: true
    targetPath: $.updates
    targetValueWriteMode: Append
    targetValueKind: Array
    attributeUpdates:
      - attributeName: Name                # CK attribute name as declared in the type
        attributeValueType: String
        valuePath: $.body.name
      - attributeName: Secret
        attributeValueType: String
        valuePath: $.body.secret
      - attributeName: Redeemed
        attributeValueType: Boolean
        value: false                       # constant value (no valuePath)

  - type: ApplyChanges@2
    entityUpdatesPath: $.updates

  - type: SetPrimitiveValue@1              # generated id is at $.updates[0].RtId
    valuePath: $.updates[0].RtId
    valueType: String
    targetPath: $.ticketId

  - type: Project@1                        # response = { ticketId } and NOTHING else
    clear: true
    fields:
      - path: $.ticketId
        inclusion: true
```

## Pattern 2 — list entities, omitting sensitive fields (`GET /tickets`)

`GetRtEntitiesByType@1` returns `{ TotalCount, Items: [ { RtId, CkTypeId,
RtCreationDateTime, Attributes: { <Name>: <value> } } ] }` — **PascalCase**.
Rebuild a clean array with `ForEach@1` (`keyPath`/`mergePath`) instead of
returning raw items:

```yaml
transformations:
  - type: GetRtEntitiesByType@1
    ckTypeId: Demo.Tickets/Ticket
    take: 200
    targetPath: $.lookup

  - type: ForEach@1
    iterationPath: $.lookup.Items
    keyPath: $.key                          # current item visible as $.key.* inside
    mergePath: $.key.out                    # ONLY $.key.out lands in the result array
    targetPath: $.tickets
    transformations:
      - type: SetPrimitiveValue@1
        valuePath: $.key.RtId
        valueType: String
        targetPath: $.key.out.id
      - type: SetPrimitiveValue@1
        valuePath: $.key.Attributes.Name
        valueType: String
        targetPath: $.key.out.name
      - type: SetPrimitiveValue@1
        valuePath: $.key.Attributes.Redeemed
        valueType: Boolean
        targetPath: $.key.out.redeemed
      - type: If@1                          # OPTIONAL attribute: guard the copy or the
        path: $.key.Attributes.Redeemed     # pipeline 500s on entities where it is unset
        operator: Equal
        value: true
        valueType: Boolean
        transformations:
          - type: SetPrimitiveValue@1
            valuePath: $.key.Attributes.RedeemedAt
            valueType: DateTime
            targetPath: $.key.out.redeemedAt

  - type: Project@1
    clear: true
    fields:
      - path: $.tickets
        inclusion: true
```

## Pattern 3 — conditional read-and-update (`GET /redeem?id=` — reveal once)

The recipient of a one-time link has no account of the tenant, so this is one of the
few routes that is public on purpose (see §Public routes). The ticket id is the only
check here, and an rtId is not a secret (ObjectIds are partly predictable): a production
design puts a random token into the link and compares it in the pipeline. The response
holds the secret once and nothing else.

Branching: `If@1` has no else — use complementary conditions. Look up by rtId via
fieldFilters (`attributePath` is PascalCase; system fields like `RtId` work):

```yaml
triggers:
  - type: FromHttpRequest@2
    method: Get
    path: /redeem
    allowAnonymous: true                   # public on purpose: link recipients have no account

transformations:
  - type: GetRtEntitiesByType@1
    ckTypeId: Demo.Tickets/Ticket
    targetPath: $.lookup
    fieldFilters:
      - attributePath: RtId
        operator: Equals
        comparisonValuePath: $.query.id

  - type: If@1                              # not found
    path: $.lookup.TotalCount
    operator: Equal
    value: 0
    valueType: Int
    transformations:
      - type: SetPrimitiveValue@1
        value: not_found
        valueType: String
        targetPath: $.error

  - type: If@1                              # found
    path: $.lookup.TotalCount
    operator: GreaterThan
    value: 0
    valueType: Int
    transformations:
      - type: If@1                          # already consumed
        path: $.lookup.Items[0].Attributes.Redeemed
        operator: Equal
        value: true
        valueType: Boolean
        transformations:
          - type: SetPrimitiveValue@1
            value: already_redeemed
            valueType: String
            targetPath: $.error
      - type: If@1                          # open → reveal, then burn
        path: $.lookup.Items[0].Attributes.Redeemed
        operator: Equal
        value: false
        valueType: Boolean
        transformations:
          - type: SetPrimitiveValue@1
            valuePath: $.lookup.Items[0].Attributes.Secret
            valueType: String
            targetPath: $.secret
          - type: DateTime@1
            operation: Now
            targetPath: $.now
          - type: CreateUpdateInfo@1
            updateKind: Update
            ckTypeId: Demo.Tickets/Ticket
            rtIdPath: $.lookup.Items[0].RtId
            targetPath: $.updates
            targetValueWriteMode: Append
            targetValueKind: Array
            attributeUpdates:
              - attributeName: Redeemed
                attributeValueType: Boolean
                value: true
              - attributeName: RedeemedAt
                attributeValueType: DateTime
                valuePath: $.now
              - attributeName: Secret      # clear the stored value, don't just flag it
                attributeValueType: String
                value: ""
          - type: ApplyChanges@2
            entityUpdatesPath: $.updates

  - type: Project@1
    clear: true
    fields:
      - path: $.secret
        inclusion: true
      - path: $.error
        inclusion: true
```

Note: read-check-write is **not atomic**; perfectly concurrent requests can race.
Acceptable for demos — say so explicitly when the use case is production-like.

## Iteration loop (scratch dataflow)

1. Throwaway ImportRt file: temp rtIds + temp paths (`/myapp-test-*`) + Pipeline
   entities with `ParentChild` → scratch DataFlow, `Executes` → Mesh Adapter.
2. `octo-cli -c ImportRt -f <file> -w` (use `-r` on re-runs) +
   `octo-cli -c DeployDataFlow --identifier <scratchDataflowRtId>`.
3. Call the route on the Mesh Adapter<!-- developer-machine --> (curl via port-forward: `kubectl port-forward -n octo svc/<tenant>-<adapterRtId> 5020:80`,
   then `http://localhost:5020/{tenant}{path}`)<!-- /developer-machine -->.
4. **Deploy-rotation quirk**: after a `-r` re-import, a `DeployDataFlow` may
   REMOVE an unchanged pipeline while re-registering a changed one (adapter log:
   `Removing pipeline …` / `Re-registering changed pipeline …`). Re-run
   `DeployDataFlow` and re-test every route after each deploy. The fresh
   blueprint-install path (new entities, single deploy) does not hit this.
5. Done → copy YAML into the blueprint seed, `UndeployDataFlow`, delete scratch
   entities via GraphQL `runtime.runtimeEntities.delete` (unversioned ckTypeIds),
   verify routes answer 404.

## Debugging

- Adapter log is the source of truth:
  `kubectl logs -n octo deploy/<tenant>-<adapterRtId> --since=5m` — full pipeline
  exceptions with failing node, request traces, route registrations.
- `No value found at ValuePath '$...'` → pattern-2 optional-attribute guard missing.
- `GetLatestPipelineExecution --identifier <pipelineRtId> --json` may show
  `Status: null` for HTTP-triggered runs — verify against data/log instead.
- Empty 200 in ~0.1 ms → route/method not registered (see rotation quirk).
