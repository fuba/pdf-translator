#!/bin/bash
# UV wrapper script to handle path issues

# Common UV installation paths (reordered to check .local/bin first)
UV_PATHS=(
    "$HOME/.local/bin/uv"
    "$HOME/.cargo/bin/uv"
    "/usr/local/bin/uv"
    "/opt/homebrew/bin/uv"
)

# Find UV executable
UV_CMD=""
for path in "${UV_PATHS[@]}"; do
    if [ -x "$path" ]; then
        UV_CMD="$path"
        break
    fi
done

# If not found in common paths, try which
if [ -z "$UV_CMD" ]; then
    UV_CMD=$(which uv 2>/dev/null)
fi

# If still not found, check if we need to source shell config
if [ -z "$UV_CMD" ]; then
    # Try sourcing shell configs
    if [ -f "$HOME/.zshrc" ]; then
        source "$HOME/.zshrc" 2>/dev/null
    elif [ -f "$HOME/.bashrc" ]; then
        source "$HOME/.bashrc" 2>/dev/null
    fi
    UV_CMD=$(which uv 2>/dev/null)
fi

# Final check
if [ -z "$UV_CMD" ] || [ ! -x "$UV_CMD" ]; then
    echo "Error: uv command not found. Please ensure uv is installed." >&2
    echo "You can install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Execute UV with all arguments
exec "$UV_CMD" "$@"