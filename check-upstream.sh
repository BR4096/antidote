#!/bin/bash
# Antidote — Check upstream for new commits
# Runs on a schedule via launchd. Notifies if updates are available.

REPO_DIR="$(cd "$(dirname "$0")/antidote" && pwd)"
UPSTREAM="upstream"
BRANCH="main"

cd "$REPO_DIR" || exit 1

# Fetch upstream silently
git fetch "$UPSTREAM" --quiet 2>/dev/null

# Compare local main with upstream/main
LOCAL=$(git rev-parse "$BRANCH" 2>/dev/null)
REMOTE=$(git rev-parse "$UPSTREAM/$BRANCH" 2>/dev/null)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$(date): Antidote is up to date with upstream."
    exit 0
fi

# Count new upstream commits
BEHIND=$(git rev-list --count "$BRANCH".."$UPSTREAM/$BRANCH" 2>/dev/null)

if [ "$BEHIND" -gt 0 ]; then
    MSG="Antidote: $BEHIND new commit(s) available from upstream (earlyaidopters/antidote). Run: cd ~/webdev/github/antidote/antidote && git fetch upstream && git merge upstream/main"
    echo "$(date): $MSG"

    # macOS notification
    osascript -e "display notification \"$BEHIND new commit(s) from earlyaidopters/antidote\" with title \"Antidote Upstream Update\" subtitle \"Run git fetch upstream && git merge upstream/main\"" 2>/dev/null
fi
