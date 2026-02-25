#!/bin/bash
# Claudia Dashboard Auto-Update Script - Fixed Version

set -e

WORKSPACE="/home/ubuntu/.openclaw/workspace"
DASHBOARD_DIR="$WORKSPACE/claudia-dashboard"
REPO_DIR="/home/ubuntu/claudia-gh"

echo "[$(date)] Starting Claudia Dashboard update..."

# Gather system data
UPTIME_DAYS=$(awk '{print int($1/86400)}' /proc/uptime)
DISK_USED=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
FILE_COUNT=$(find $WORKSPACE -type f 2>/dev/null | wc -l)

# Get recent files (last 24 hours) - simple format
RECENT_FILES=""
for file in $(find $WORKSPACE -type f -mtime -1 2>/dev/null | head -5); do
    if [ -f "$file" ]; then
        RECENT_FILES="$RECENT_FILES, \"$(basename "$file")\""
    fi
done
RECENT_FILES="[${RECENT_FILES#, }]"

# Generate timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOCAL_TIME=$(date '+%Y-%m-%d %H:%M UTC')

# Create updated dashboard data - no jq needed
cat > $DASHBOARD_DIR/dashboard-data.json << EOFDATA
{
  "lastUpdated": "$TIMESTAMP",
  "localTime": "$LOCAL_TIME",
  "system": {
    "model": "moonshot/kimi-k2.5",
    "contextUsed": "96k",
    "contextTotal": "262k",
    "contextPercent": "37%",
    "uptimeDays": $UPTIME_DAYS,
    "sessionKey": "agent:main:main",
    "status": "active"
  },
  "workspace": {
    "totalFiles": $FILE_COUNT,
    "recentFiles": $RECENT_FILES,
    "diskUsedPercent": $DISK_USED
  },
  "integrations": [
    {"name": "Email (Himalaya)", "status": "active", "details": "claudiadavesva@gmail.com"},
    {"name": "Telegram", "status": "active", "details": "Connected to Dave"},
    {"name": "GitHub", "status": "active", "details": "hot-10-dashboard repo"},
    {"name": "Google Sheets", "status": "active", "details": "Connected to CCFAP Leads"},
    {"name": "Image Gen", "status": "active", "details": "OpenAI connected"},
    {"name": "Kimi API", "status": "active", "details": "Moonshot configured"},
    {"name": "Last30Days Skill", "status": "active", "details": "Research tool ready"}
  ],
  "projects": [
    {
      "name": "Hot 10 Lead Scoring",
      "status": "deployed",
      "progress": 85,
      "blocker": "Waiting for Bubble API connection",
      "nextStep": "Connect sales data"
    },
    {
      "name": "Weekly Marketing Reports",
      "status": "building",
      "progress": 70,
      "blocker": "Need sales data integration",
      "nextStep": "Automate report generation"
    },
    {
      "name": "Claudia Dashboard",
      "status": "live",
      "progress": 100,
      "blocker": null,
      "nextStep": "Auto-refresh working"
    },
    {
      "name": "Sales Meeting Topics",
      "status": "active",
      "progress": 100,
      "blocker": null,
      "nextStep": "Weekly updates ready"
    }
  ],
  "recentActivity": [
    {"time": "$(date '+%H:%M')", "action": "Dashboard auto-updated"},
    {"time": "Recent", "action": "Sales meeting topics generated"},
    {"time": "Recent", "action": "Google Sheets connected"},
    {"time": "Feb 13", "action": "Update button added to dashboard"}
  ]
}
EOFDATA

echo "[$(date)] Dashboard data updated with timestamp: $TIMESTAMP"

# Update the HTML file's last-updated timestamp
sed -i "s/Last update:.*/Last update: $LOCAL_TIME/" $DASHBOARD_DIR/index.html 2>/dev/null || true
sed -i "s/Last updated:.*/Last updated: $LOCAL_TIME/" $DASHBOARD_DIR/index.html 2>/dev/null || true

echo "[$(date)] HTML timestamp updated"

# Copy to GitHub repo
cd $REPO_DIR
cp -r $DASHBOARD_DIR/* claudia-dashboard/ 2>/dev/null || cp $DASHBOARD_DIR/* claudia-dashboard/ 2>/dev/null || true

# Git commit and push
git add .
if git diff --cached --quiet; then
    echo "[$(date)] No changes to commit"
else
    git commit -m "Auto-update: Dashboard refresh $LOCAL_TIME" || echo "Commit failed"
    
    # Push with token from environment
    if [ -n "$GITHUB_TOKEN" ]; then
        git push https://$GITHUB_TOKEN@github.com/brightstarsolar/hot-10-dashboard.git main 2>&1 | grep -v "$GITHUB_TOKEN" || echo "Push may have failed"
    else
        echo "[$(date)] No GITHUB_TOKEN set, skipping push"
        echo "To enable auto-push, set GITHUB_TOKEN environment variable"
    fi
fi

echo "[$(date)] Dashboard update complete"
echo "[$(date)] Live at: https://brightstarsolar.github.io/hot-10-dashboard/claudia-dashboard/"