---
name: demo
description: "Fixture skill with only valid and allow-listed names."
---

# Demo

Build with `Invoke-DemoBuild -repo octo-demo -config DebugL -noTests -Verbose`.

```powershell
Start-DemoStack -nonInteractive $true -profile default
Stop-DemoStack
Get-ChildItem . | Select-Object Name
Invoke-DemoBuild -repo x -extra '-notAParameter'
```

Prose that mentions Invoke-Nothing outside code is not checked.

```bash
octo-cli -c ImportDemo -f data.json --wait --replace
octo-cli --context local -c ListDemos
octo-cli -c <Command> --whatever
echo admin@example.com
```

Pipeline nodes: `FromDemoTrigger@1`, `TransformDemo@1` and `TransformDemo@2`.
The retired `RetiredDemo@1` is named on purpose (allow-listed).

Read `octo-mesh-demo/AGENTS.md`, `octo-mesh-demo/docs/guide.md`, the folder `octo-mesh-demo/docs/nodes/`
and `octo-legacy-demo/CLAUDE.md`. `customer-app/AGENTS.md` is outside the repository patterns.
