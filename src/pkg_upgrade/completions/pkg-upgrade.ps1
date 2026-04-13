# pkg-upgrade PowerShell completion

function Get-PkgUpgradeManagers {
    $cache = Join-Path $env:LOCALAPPDATA 'pkg-upgrade\managers.list'
    if (Test-Path $cache) {
        Get-Content -LiteralPath $cache -Encoding UTF8
    } else {
        @('brew', 'cask', 'gem', 'npm', 'pip', 'system')
    }
}

$script:PkgUpgradeFlags = @(
    '--only', '--skip', '--yes', '--dry-run', '--no-notify', '--no-log',
    '--log-dir', '--list', '--plain', '--onboard', '--show-graph',
    '--max-parallel', '--version', '--self-update'
)

$completer = {
    param($wordToComplete, $commandAst, $cursorPosition)

    $tokens = $commandAst.CommandElements | ForEach-Object { $_.ToString() }
    $prev = if ($tokens.Count -ge 2) { $tokens[-2] } else { '' }

    if ($prev -in '--only', '--skip') {
        $cur  = $wordToComplete
        if ($cur -match ',') {
            $prefix = $cur -replace ',[^,]*$',''
            $tail   = ($cur -split ',')[-1]
        } else {
            $prefix = ''
            $tail   = $cur
        }
        $sep = if ($prefix) { ',' } else { '' }
        $used = if ($prefix) { $prefix -split ',' } else { @() }
        Get-PkgUpgradeManagers |
            Where-Object { $_ -like "$tail*" -and $used -notcontains $_ } |
            ForEach-Object {
                $val = "$prefix$sep$_"
                [System.Management.Automation.CompletionResult]::new($val, $val, 'ParameterValue', $_)
            }
        return
    }

    if ($wordToComplete -like '--*' -or $tokens.Count -le 1) {
        $script:PkgUpgradeFlags |
            Where-Object { $_ -like "$wordToComplete*" } |
            ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
            }
    }

    if ($tokens.Count -ge 2 -and $tokens[1] -eq 'completion') {
        'bash', 'zsh', 'fish', 'powershell' |
            Where-Object { $_ -like "$wordToComplete*" } |
            ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }
    }
}

Register-ArgumentCompleter -Native -CommandName pkg-upgrade -ScriptBlock $completer
Register-ArgumentCompleter -Native -CommandName pkgup       -ScriptBlock $completer
