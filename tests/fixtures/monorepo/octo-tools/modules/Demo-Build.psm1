function Invoke-DemoBuild {
    <#
    .SYNOPSIS
    Fixture: a function with comment help, CmdletBinding and a param block.
    .EXAMPLE
    Invoke-DemoBuild -repo "a (b)" -configuration DebugL
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true, Position = 0)] [string]$repo,
        [ValidateSet('DebugL', 'Release')] [string]$configuration = "DebugL", # comment with (parens)
        [switch]$noTests,
        [string[]]$extra = @('-x', '$notAParam')
    )
    Write-Host "$repo $configuration"
}

function Global:Start-DemoStack([string]$profile = "default", [Boolean]$nonInteractive = $false) {
    Write-Host $profile
}

function Stop-DemoStack {
    Write-Host "no parameters"
}

Export-ModuleMember -Function @('Invoke-DemoBuild', 'Start-DemoStack', 'Stop-DemoStack')
