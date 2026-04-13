# pkg-upgrade bash completion

_pkg_upgrade_managers() {
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/pkg-upgrade/managers.list"
  if [[ -r "$cache" ]]; then
    cat "$cache"
  else
    printf '%s\n' brew cask gem npm pip system
  fi
}

_pkg_upgrade_complete_list() {
  local cur="$1"
  local prefix tail sep used all m
  if [[ "$cur" == *","* ]]; then
    prefix="${cur%,*}"
    tail="${cur##*,}"
    sep=","
  else
    prefix=""
    tail="$cur"
    sep=""
  fi
  used=()
  if [[ -n "$prefix" ]]; then
    IFS=',' read -ra used <<<"$prefix"
  fi
  all=$(_pkg_upgrade_managers)
  for m in $all; do
    local skip=""
    for u in "${used[@]}"; do
      [[ "$u" == "$m" ]] && skip=1 && break
    done
    [[ -z "$skip" && "$m" == "$tail"* ]] && COMPREPLY+=("${m}")
  done
}

_pkg_upgrade_completions() {
  local cur prev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  COMPREPLY=()

  case "$prev" in
    --only|--skip)
      _pkg_upgrade_complete_list "$cur"
      return 0
      ;;
    --log-dir)
      COMPREPLY=( $(compgen -d -- "$cur") )
      return 0
      ;;
    --max-parallel)
      return 0
      ;;
  esac

  if [[ "$cur" == --* ]]; then
    local flags="--only --skip --yes --dry-run --no-notify --no-log --log-dir --list --plain --onboard --show-graph --max-parallel --version --self-update"
    COMPREPLY=( $(compgen -W "$flags" -- "$cur") )
    return 0
  fi

  if [[ "$COMP_CWORD" == "1" ]]; then
    COMPREPLY=( $(compgen -W "completion" -- "$cur") )
    return 0
  fi

  if [[ "${COMP_WORDS[1]}" == "completion" && "$COMP_CWORD" == "2" ]]; then
    COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- "$cur") )
    return 0
  fi
}

complete -F _pkg_upgrade_completions pkg-upgrade
complete -F _pkg_upgrade_completions pkgup
