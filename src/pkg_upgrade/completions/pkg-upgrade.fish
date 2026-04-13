# pkg-upgrade fish completion

function __pkg_upgrade_managers
    set -l cache "$XDG_CACHE_HOME/pkg-upgrade/managers.list"
    if test -z "$XDG_CACHE_HOME"
        set cache "$HOME/.cache/pkg-upgrade/managers.list"
    end
    if test -r "$cache"
        cat "$cache"
    else
        printf '%s\n' brew cask gem npm pip system
    end
end

complete -c pkg-upgrade -l only  -d 'Run only these managers' -x -a '(__pkg_upgrade_managers)'
complete -c pkg-upgrade -l skip  -d 'Skip these managers'     -x -a '(__pkg_upgrade_managers)'
complete -c pkg-upgrade -l yes       -s y -d 'Auto-confirm'
complete -c pkg-upgrade -l dry-run              -d 'Print plan without running'
complete -c pkg-upgrade -l no-notify            -d 'Disable completion notification'
complete -c pkg-upgrade -l no-log               -d 'Disable log file'
complete -c pkg-upgrade -l log-dir -r           -d 'Log directory' -a '(__fish_complete_directories)'
complete -c pkg-upgrade -l list                 -d 'List managers'
complete -c pkg-upgrade -l plain                -d 'Plain output with --list'
complete -c pkg-upgrade -l onboard              -d 'Run onboarding wizard'
complete -c pkg-upgrade -l show-graph           -d 'Print execution plan'
complete -c pkg-upgrade -l max-parallel -r      -d 'Cap concurrency'
complete -c pkg-upgrade -l version              -d 'Print version'
complete -c pkg-upgrade -l self-update          -d 'Upgrade pkg-upgrade itself'

complete -c pkg-upgrade -n '__fish_use_subcommand' -a completion -d 'Print shell completion script'
complete -c pkg-upgrade -n '__fish_seen_subcommand_from completion' -a 'bash zsh fish powershell'

complete -c pkgup -w pkg-upgrade
