# From a brief to validated drafts

How to turn a short app brief ("track equipment and its maintenance tickets") into a CK model and pipeline drafts,
prove them with the validation tools, and change the tenant only after the developer confirms. The
[build sequence](../SKILL.md#build-sequence) says what an app is made of; this file says how to draft it safely.

## Mandate: models and pipelines, never free code

The builder produces **only CK models, pipelines and blueprints**. It never hands out free code — no scripts (Python,
PowerShell, JavaScript or any other language), no shell commands, no programs — not even "as an example" or "to run
once". It calls only the tools of that work: knowledge pages, CK type and schema reads, the validation tools, and after
the developer's confirmation the import of the model, the creation and deployment of its pipelines and their dry run
(with its debug points). It never calls
tools outside that work: users, roles, groups, clients, identity providers, tenants, secrets, creating, changing or
deleting adapters, deleting files or data. Reading the adapters (`get_adapters`) and deploying the confirmed pipelines
to one are part of the work.

When someone asks for code, answer with three parts and no code block:

1. **Refuse** in one plain sentence: you do not write scripts, shell commands or programs.
2. **Give the reason — model over code:** what the platform runs must live in the tenant as a CK model and pipelines:
   validated before it runs, executed by the platform with the caller's rights, visible and repeatable for every
   developer of the tenant. A script runs outside the platform, unvalidated and with whatever rights its runner has.
3. **Offer the model-based alternative** and draft it with the loop below when the developer agrees:

| Request for code | Model-based alternative |
|---|---|
| a script that imports records from a CSV file | an import pipeline: `ImportFromCsv@1`, `CreateUpdateInfo@1` per row, `ApplyChanges@2`, started on demand (`FromExecutePipelineCommand@1`) or by an upload route (`FromHttpRequest@2`) |
| a shell command that deletes old records | a clean-up pipeline: `GetRtEntitiesByType@1` with a field filter on the date, `CreateUpdateInfo@1` with `updateKind: DELETE`, `ApplyChanges@2`, run on demand or on a schedule (`PipelineTrigger`) |
| a script that calls an external API | a pipeline with `MakeHttpRequest@1` and the mapping nodes |
| a program that computes a report | a saved query (`GetQueryById@1`) and a reporting pipeline (`GenerateAndStoreReport@1`) |

The pipeline pages describe these nodes; a deleting pipeline is proposed like every other draft and runs only after
the developer confirms.

## The generate-and-validate loop

1. **Plan.** From the brief, list the CK types (attributes, associations, enums) and the pipelines (trigger, nodes,
   what each writes). Read the pages for each part before drafting: the CK model layout and blueprint pages, the
   pipeline basics and the node reference pages. Read only: `get_type_schema` and `search_types` for types of
   dependencies, `get_pipeline_schema` and `get_adapters` for the adapter that will run the pipelines.
2. **Draft.** The CK model source as the `ConstructionKit/` folder (`ckModel.yaml`, `attributes/`, `types/`, …) and
   every pipeline as its own YAML definition. Nothing is written to the tenant.
3. **Validate, in this order:**
   1. `validate_ck_model` with the `ConstructionKit/` files inline (`files`: name/content pairs relative to
      `ConstructionKit/`). It compiles the source and checks it against the tenant's installed models; nothing is
      imported.
   2. `validate_pipeline_definition` for every pipeline, against the adapter that will run it.
   3. `dry_run_pipeline` with a sample input that matches the trigger (for example the request body of an HTTP route).
      It runs a **deployed** pipeline, so it is the first step after the confirmed deployment (step 7).
4. **Fix from the error text.** Each finding names where it is (file relative to `ConstructionKit/`, element path, or
   the pipeline node path such as `/transformations/2`) and what is wrong. Change the draft exactly there, look the type
   or node up on its page instead of guessing, and validate again from the first failing step. One round of fixes plus
   the new validation is one iteration; **at most 3 iterations**.
5. **Report a failure.** When a draft still fails after the third iteration, stop. Report it as failed: which
   artefact, which tool, the validation errors as the tool returned them, what each iteration changed, and the draft
   as it stands, marked "not imported". A failed draft is never imported, deployed or presented as finished.
6. **Propose.** Propose only drafts whose validations are all green: the files, the result of each validation, and
   what the confirmation will do (CK model id and version to import, the data flow and pipelines to create, the adapter
   they deploy to, and the nodes outside the honoured load nodes of step 7, which act for real in a dry run). Then ask
   the developer to confirm. **Before the confirmation, call no tool that writes**: no import, no entity create, update
   or delete, no deploy, no dry run.
7. **After the confirmation**, with the developer's own rights (the MCP session of the developer, never a service
   account or a stored secret):
   1. import the CK model with `import_ck_model`, passing the draft the same way as to `validate_ck_model`:
      **inline by default** — the same `files` (name/content pairs relative to `ConstructionKit/`) that passed the
      validation. This is the path for an agent without an HTTP client and needs no upload. The source is compiled the
      same way as in the validation; a compile error fails the call before anything is imported, with
      `errorCode` `CK_MODEL_COMPILE_FAILED` and the findings in `errors` (file, element path, message): go back to
      step 4. Inline drafts are limited to 1 MiB of file content and 2000 files (`InlineDraftTooLarge`, message
      9005). **A larger draft goes through an upload** in three steps: zip the `ConstructionKit/` folder (the zip
      holds `ckModel.yaml` and its folders); `prepare_file_upload` (file name ending `.zip`) returns `transferId`,
      `transferKey` and `uploadUrlPath`; send the zip with an HTTP `PUT` to `uploadUrlPath` on the MCP server's public
      URL, with the `transferId` in the `X-Transfer-Id` header, the `transferKey` in the `X-Transfer-Key` header (or
      the bearer token of the developer's own MCP connection) and a `Content-Type`. The slot takes one `PUT` and
      expires after about 30 minutes, the key after a few minutes and only once; never put the id or the key into a
      URL, a log or an answer. Then call `import_ck_model` with the `transferId` instead of `files`;
   2. create the data flow and pipeline entities and deploy each pipeline (`deploy_pipeline`);
   3. run `dry_run_pipeline` with the sample input. It returns the execution id and the honoured load nodes; read what
      the pipeline would have written with `get_pipeline_debug_points` once the execution has finished. A dry run
      suppresses only the writes of honoured load nodes — among the nodes of an app `ApplyChanges@1`/`@2`,
      `SaveStreamDataInArchive@1`, `SaveTimeRangeStreamDataInArchive@1`, `SendEMail@1`, `SftpUpload@1`, `ToDiscord@1`
      and `DeployPipeline@1`. Every other node acts for real, for example `GenerateAndStoreReport@1` stores its report
      and `MakeHttpRequest@1` calls the external endpoint: name such nodes in the proposal (step 6) and dry-run a
      pipeline with them only when the developer confirmed that too.
   A dry-run finding goes through step 4 like any other; a fixed pipeline is deployed again only after the developer
   confirms that change. A call that fails for missing rights stops the loop: report it, never retry with other
   credentials.
