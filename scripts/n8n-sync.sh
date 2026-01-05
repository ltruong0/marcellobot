#!/bin/bash
#
# Bidirectional n8n workflow sync (scoped to this repo's workflows only)
#
# Commands:
#   push [file.json]   - Push local workflows to n8n (default)
#   pull [name]        - Pull updates for local workflows from n8n
#   pull --all         - Pull ALL workflows from n8n (including unmanaged)
#   diff               - Show differences between local and remote
#   list               - List all workflows on n8n (marks managed ones)
#
# Environment variables:
#   N8N_URL     - n8n server URL (default: https://workflows.marcellolab.com)
#   N8N_TOKEN   - n8n API token (required)
#   DRY_RUN     - Set to "true" to preview changes without applying
#

set -euo pipefail

# Load .env file if it exists (check repo root first, then scripts dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
for ENV_FILE in "${REPO_ROOT}/.env" "${SCRIPT_DIR}/.env"; do
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi
done

# Configuration
N8N_URL="${N8N_URL:-https://workflows.marcellolab.com}"
DRY_RUN="${DRY_RUN:-false}"
WORKFLOWS_DIR="${REPO_ROOT}/workflows"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

check_requirements() {
    if [[ -z "${N8N_TOKEN:-}" ]]; then
        log_error "N8N_TOKEN must be set in environment or .env file"
        exit 1
    fi

    for cmd in jq curl; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done

    mkdir -p "$WORKFLOWS_DIR"
}

# Make API request to n8n
n8n_api() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local args=(
        -s
        -X "$method"
        -H "X-N8N-API-KEY: ${N8N_TOKEN}"
        -H "Content-Type: application/json"
    )

    if [[ -n "$data" ]]; then
        args+=(-d "$data")
    fi

    curl "${args[@]}" "${N8N_URL}/api/v1${endpoint}"
}

# Get all existing workflows from n8n
get_remote_workflows() {
    n8n_api GET "/workflows" | jq -r '.data // []'
}

# Get a single workflow by ID
get_workflow_by_id() {
    local id="$1"
    n8n_api GET "/workflows/${id}"
}

# Find workflow ID by name
find_workflow_id() {
    local name="$1"
    local workflows="$2"
    echo "$workflows" | jq -r --arg name "$name" '.[] | select(.name == $name) | .id' | head -1
}

# Clean workflow JSON for API submission
clean_workflow_for_push() {
    local file="$1"
    jq '{name, nodes, connections, settings} | with_entries(select(.value != null))' "$file"
}

# Clean workflow JSON for local storage
clean_workflow_for_save() {
    jq 'del(.staticData, .triggerCount, .pinData, .versionId, .meta.instanceId) | .meta.templateCredsSetupCompleted = false'
}

# Convert workflow name to filename
name_to_filename() {
    local name="$1"
    echo "$name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//'
}

# ============================================================================
# PUSH: Local -> n8n
# ============================================================================

push_workflow() {
    local file="$1"
    local existing_workflows="$2"

    if [[ ! -f "$file" ]]; then
        log_error "File not found: $file"
        return 1
    fi

    local name
    name=$(jq -r '.name' "$file")

    if [[ -z "$name" || "$name" == "null" ]]; then
        log_error "Invalid workflow file (no name): $file"
        return 1
    fi

    local existing_id
    existing_id=$(find_workflow_id "$name" "$existing_workflows")

    if [[ -n "$existing_id" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would update: $name (ID: $existing_id)"
            return 0
        fi

        local workflow_data
        workflow_data=$(clean_workflow_for_push "$file")

        local response
        response=$(n8n_api PUT "/workflows/${existing_id}" "$workflow_data")

        if echo "$response" | jq -e '.id' > /dev/null 2>&1; then
            log_info "Updated: $name (ID: $existing_id)"
        else
            local error
            error=$(echo "$response" | jq -r '.message // "Unknown error"')
            log_error "Failed to update $name: $error"
            return 1
        fi
    else
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would create: $name"
            return 0
        fi

        local workflow_data
        workflow_data=$(clean_workflow_for_push "$file")

        local response
        response=$(n8n_api POST "/workflows" "$workflow_data")

        if echo "$response" | jq -e '.id' > /dev/null 2>&1; then
            local new_id
            new_id=$(echo "$response" | jq -r '.id')
            log_info "Created: $name (ID: $new_id)"
        else
            local error
            error=$(echo "$response" | jq -r '.message // "Unknown error"')
            log_error "Failed to create $name: $error"
            return 1
        fi
    fi
}

cmd_push() {
    log_info "Pushing workflows to n8n..."
    log_info "Server: ${N8N_URL}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN mode - no changes will be made"
    fi

    check_requirements

    log_info "Fetching existing workflows..."
    local existing_workflows
    existing_workflows=$(get_remote_workflows)

    local files=()
    if [[ $# -gt 0 ]]; then
        for arg in "$@"; do
            if [[ "$arg" == /* ]]; then
                files+=("$arg")
            else
                files+=("${WORKFLOWS_DIR}/${arg}")
            fi
        done
    else
        while IFS= read -r -d '' file; do
            files+=("$file")
        done < <(find "$WORKFLOWS_DIR" -name "*.json" -type f -print0 2>/dev/null)
    fi

    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No workflow files found in $WORKFLOWS_DIR"
        exit 0
    fi

    log_info "Pushing ${#files[@]} workflow(s)..."

    local success=0 failed=0
    for file in "${files[@]}"; do
        if push_workflow "$file" "$existing_workflows"; then
            ((success++))
        else
            ((failed++))
        fi
    done

    echo ""
    log_info "Push complete: ${success} succeeded, ${failed} failed"
    [[ $failed -gt 0 ]] && exit 1
}

# ============================================================================
# PULL: n8n -> Local
# ============================================================================

pull_workflow() {
    local workflow_json="$1"
    local name id filename filepath

    name=$(echo "$workflow_json" | jq -r '.name')
    id=$(echo "$workflow_json" | jq -r '.id')
    filename=$(name_to_filename "$name")
    filepath="${WORKFLOWS_DIR}/${filename}.json"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would save: $name -> ${filename}.json"
        return 0
    fi

    # Get full workflow data
    local full_workflow
    full_workflow=$(get_workflow_by_id "$id")

    # Clean and save
    echo "$full_workflow" | clean_workflow_for_save | jq '.' > "$filepath"
    log_info "Saved: $name -> ${filename}.json"
}

# Get list of workflow names managed by this repo
get_local_workflow_names() {
    local names=()
    while IFS= read -r -d '' file; do
        local name
        name=$(jq -r '.name' "$file")
        if [[ -n "$name" && "$name" != "null" ]]; then
            names+=("$name")
        fi
    done < <(find "$WORKFLOWS_DIR" -name "*.json" -type f -print0 2>/dev/null)
    printf '%s\n' "${names[@]}"
}

cmd_pull() {
    local pull_all=false

    # Check for --all flag
    if [[ "${1:-}" == "--all" ]]; then
        pull_all=true
        shift
    fi

    log_info "Pulling workflows from n8n..."
    log_info "Server: ${N8N_URL}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN mode - no files will be written"
    fi

    check_requirements

    log_info "Fetching workflows..."
    local workflows
    workflows=$(get_remote_workflows)

    local count
    count=$(echo "$workflows" | jq 'length')
    log_info "Found ${count} remote workflow(s)"

    if [[ $# -gt 0 ]]; then
        # Pull specific workflow by name
        local name="$1"
        local workflow
        workflow=$(echo "$workflows" | jq --arg name "$name" '.[] | select(.name == $name)')

        if [[ -z "$workflow" || "$workflow" == "null" ]]; then
            log_error "Workflow not found: $name"
            exit 1
        fi

        pull_workflow "$workflow"
    elif [[ "$pull_all" == "true" ]]; then
        # Pull all workflows (explicit --all flag)
        log_warn "Pulling ALL remote workflows (including unmanaged)"
        echo "$workflows" | jq -c '.[]' | while read -r workflow; do
            pull_workflow "$workflow"
        done
    else
        # Default: Only pull workflows that exist locally
        log_info "Pulling only workflows managed by this repo..."
        log_info "(use 'pull --all' to pull all remote workflows)"

        local local_names
        local_names=$(get_local_workflow_names)

        if [[ -z "$local_names" ]]; then
            log_warn "No local workflows found. Use 'pull --all' to pull from remote."
            exit 0
        fi

        local pulled=0
        local skipped=0
        echo "$workflows" | jq -c '.[]' | while read -r workflow; do
            local name
            name=$(echo "$workflow" | jq -r '.name')
            if echo "$local_names" | grep -qxF "$name"; then
                pull_workflow "$workflow"
                ((pulled++)) || true
            else
                ((skipped++)) || true
            fi
        done

        log_info "Skipped ${skipped} unmanaged workflow(s)"
    fi

    echo ""
    log_info "Pull complete!"
}

# ============================================================================
# LIST: Show remote workflows
# ============================================================================

cmd_list() {
    check_requirements

    log_info "Workflows on ${N8N_URL}:"
    echo ""

    local workflows
    workflows=$(get_remote_workflows)

    # Get local workflow names for comparison
    local local_names
    local_names=$(get_local_workflow_names)

    # Display with managed indicator
    echo "$workflows" | jq -r '.[] | "\(.id)\t\(.active | if . then "✓" else "○" end)\t\(.name)"' | while IFS=$'\t' read -r id active name; do
        local managed=""
        if echo "$local_names" | grep -qxF "$name"; then
            managed="${GREEN}[managed]${NC}"
        fi
        printf "  %-8s %s  %-40s %b\n" "$id" "$active" "$name" "$managed"
    done

    echo ""
    local total
    total=$(echo "$workflows" | jq 'length')
    local managed_count
    managed_count=$(echo "$local_names" | grep -c . || echo 0)
    log_info "Total: ${total} workflow(s), ${managed_count} managed by this repo"
}

# ============================================================================
# DIFF: Compare local and remote
# ============================================================================

cmd_diff() {
    check_requirements

    log_info "Comparing local and remote workflows..."

    local remote_workflows
    remote_workflows=$(get_remote_workflows)

    # Get local workflow names
    local local_names=()
    while IFS= read -r -d '' file; do
        local name
        name=$(jq -r '.name' "$file")
        local_names+=("$name")
    done < <(find "$WORKFLOWS_DIR" -name "*.json" -type f -print0 2>/dev/null)

    # Get remote workflow names
    local remote_names=()
    while IFS= read -r name; do
        remote_names+=("$name")
    done < <(echo "$remote_workflows" | jq -r '.[].name')

    echo ""
    echo -e "${CYAN}Local only (will be created on push):${NC}"
    for name in "${local_names[@]}"; do
        if [[ ! " ${remote_names[*]} " =~ " ${name} " ]]; then
            echo "  + $name"
        fi
    done

    echo ""
    echo -e "${CYAN}Synced (exist in both local and remote):${NC}"
    for name in "${local_names[@]}"; do
        if [[ " ${remote_names[*]} " =~ " ${name} " ]]; then
            echo "  = $name"
        fi
    done

    echo ""
    echo -e "${CYAN}Unmanaged (remote only, not tracked by this repo):${NC}"
    for name in "${remote_names[@]}"; do
        if [[ ! " ${local_names[*]} " =~ " ${name} " ]]; then
            echo "  · $name"
        fi
    done

    echo ""
    log_info "Only workflows in 'Local only' and 'Synced' are managed by this repo"
}

# ============================================================================
# Main
# ============================================================================

usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  push [file.json]   Push local workflows to n8n"
    echo "  pull [name]        Pull updates for workflows managed by this repo"
    echo "  pull --all         Pull ALL workflows from n8n (including unmanaged)"
    echo "  diff               Show differences between local and remote"
    echo "  list               List all workflows on n8n (marks managed ones)"
    echo ""
    echo "Environment:"
    echo "  N8N_URL            n8n server URL (default: https://workflows.marcellolab.com)"
    echo "  N8N_TOKEN          n8n API token (required)"
    echo "  DRY_RUN=true       Preview changes without applying"
    echo ""
    echo "This script only syncs workflows defined in the workflows/ directory."
    echo "Other workflows in your n8n instance are not affected."
}

main() {
    local cmd="${1:-push}"
    shift || true

    case "$cmd" in
        push)
            cmd_push "$@"
            ;;
        pull)
            cmd_pull "$@"
            ;;
        diff)
            cmd_diff "$@"
            ;;
        list)
            cmd_list "$@"
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            log_error "Unknown command: $cmd"
            usage
            exit 1
            ;;
    esac
}

main "$@"
