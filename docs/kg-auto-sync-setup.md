# Knowledge Graph Auto-Sync Setup

This guide shows how to automatically keep the knowledge graph synchronized with FHIR data changes.

## Overview

Three approaches for automatic knowledge graph updates:

1. **✅ RECOMMENDED: Scheduled Incremental Sync** - Run sync script every 5 minutes
2. **Advanced: IRIS Triggers** - Real-time updates using ObjectScript triggers
3. **Manual: On-Demand** - Run build script when needed

## Option 1: Scheduled Incremental Sync (RECOMMENDED)

### How It Works

- Runs `python3 src/setup/fhir_graphrag_setup.py --mode=sync` on a schedule
- Queries FHIR resources WHERE `LastUpdated > MAX(ExtractedAt)`
- Only processes new/changed resources since last sync
- Typical sync time: 0.1-2 seconds for 1-10 changed resources

### Setup with Cron (macOS/Linux)

```bash
# Open crontab editor
crontab -e

# Add this line to run sync every 5 minutes
*/5 * * * * cd /Users/tdyar/ws/FHIR-AI-Hackathon-Kit && /usr/bin/python3 src/setup/fhir_graphrag_setup.py --mode=sync >> logs/kg_sync.log 2>&1

# Or every minute for near real-time
* * * * * cd /Users/tdyar/ws/FHIR-AI-Hackathon-Kit && /usr/bin/python3 src/setup/fhir_graphrag_setup.py --mode=sync >> logs/kg_sync.log 2>&1
```

### Setup with systemd Timer (Linux)

Create `/etc/systemd/system/fhir-kg-sync.service`:

```ini
[Unit]
Description=FHIR Knowledge Graph Incremental Sync
After=network.target

[Service]
Type=oneshot
User=tdyar
WorkingDirectory=/Users/tdyar/ws/FHIR-AI-Hackathon-Kit
ExecStart=/usr/bin/python3 src/setup/fhir_graphrag_setup.py --mode=sync
StandardOutput=append:/var/log/fhir-kg-sync.log
StandardError=append:/var/log/fhir-kg-sync.log
```

Create `/etc/systemd/system/fhir-kg-sync.timer`:

```ini
[Unit]
Description=Run FHIR Knowledge Graph Sync every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Unit=fhir-kg-sync.service

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable fhir-kg-sync.timer
sudo systemctl start fhir-kg-sync.timer

# Check status
sudo systemctl status fhir-kg-sync.timer
sudo systemctl list-timers
```

### Setup with launchd (macOS)

Create `~/Library/LaunchAgents/com.fhir.kg-sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fhir.kg-sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>src/setup/fhir_graphrag_setup.py</string>
        <string>--mode=sync</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/tdyar/ws/FHIR-AI-Hackathon-Kit</string>

    <key>StartInterval</key>
    <integer>300</integer> <!-- 300 seconds = 5 minutes -->

    <key>StandardOutPath</key>
    <string>/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/logs/kg-sync.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/logs/kg-sync-error.log</string>
</dict>
</plist>
```

Load and start:

```bash
# Create logs directory
mkdir -p logs

# Load the agent
launchctl load ~/Library/LaunchAgents/com.fhir.kg-sync.plist

# Check status
launchctl list | grep fhir

# View logs
tail -f logs/kg-sync.log
```

## Option 2: IRIS Triggers (Advanced)

For true real-time updates, you can use IRIS ObjectScript triggers.

### Prerequisites

- IRIS Management Portal access
- ObjectScript knowledge
- IRIS Embedded Python enabled

### Setup

```bash
# Run trigger setup script
python3 src/setup/fhir_kg_trigger.py
```

Follow the instructions to:
1. Create the `User.FHIRKGTrigger` ObjectScript class
2. Create triggers on `HSFHIR_X0001_R.Rsrc` table
3. Test the trigger functionality

### Trigger Benefits

- ✅ Immediate updates (< 1 second latency)
- ✅ Automatic on any INSERT/UPDATE/DELETE
- ✅ No polling/scheduling required

### Trigger Limitations

- ❌ Requires ObjectScript knowledge
- ❌ More complex to debug
- ❌ Harder to version control
- ❌ Tightly coupled to IRIS

## Testing the Sync

### Manual Test

```bash
# Run incremental sync manually
python3 src/setup/fhir_graphrag_setup.py --mode=sync

# Expected output if no changes:
# [INFO] ✅ No new or updated resources to process
# [INFO] Sync completed in 0.05 seconds
```

### Simulate FHIR Data Change

```sql
-- Update a DocumentReference to trigger sync
UPDATE HSFHIR_X0001_R.Rsrc
SET LastUpdated = CURRENT_TIMESTAMP
WHERE ResourceType = 'DocumentReference'
AND ID = 1474;

-- Now run sync
```

```bash
python3 src/setup/fhir_graphrag_setup.py --mode=sync

# Expected output:
# [INFO] Found 1 resources to process
# [INFO] Processing resource 1/1 (ID: 1474)...
# [INFO]   ✅ Extracted X entities
# [INFO]   ✅ Identified Y relationships
```

## Monitoring

### View Sync Logs

```bash
# View cron logs (if using cron)
tail -f logs/kg_sync.log

# View launchd logs (if using launchd)
tail -f ~/Library/Logs/kg-sync.log

# View systemd logs (if using systemd)
sudo journalctl -u fhir-kg-sync.service -f
```

### Check Knowledge Graph Stats

```bash
python3 src/setup/fhir_graphrag_setup.py --mode=stats
```

### Query Last Sync Time

```sql
SELECT MAX(ExtractedAt) as LastSync FROM RAG.Entities;
```

## Performance Tuning

### Sync Frequency Recommendations

| Update Frequency | Sync Interval | Rationale |
|------------------|---------------|-----------|
| Real-time critical | 1 minute | Near real-time, minimal delay |
| Important | 5 minutes | Good balance of freshness vs. load |
| Normal | 15 minutes | Low overhead, acceptable delay |
| Low priority | 1 hour | Batch processing, efficient |

### Resource Limits

```yaml
# In config/fhir_graphrag_config.yaml
pipelines:
  graphrag:
    sync_batch_size: 100  # Max resources per sync run
    sync_timeout: 60      # Max seconds per sync
```

## Troubleshooting

### Sync Not Running

```bash
# Check cron is running (macOS)
sudo launchctl list | grep cron

# Check cron logs
grep CRON /var/log/system.log

# Test script manually
cd /Users/tdyar/ws/FHIR-AI-Hackathon-Kit
python3 src/setup/fhir_graphrag_setup.py --mode=sync
```

### Sync Failing

```bash
# Check logs for errors
cat logs/kg_sync.log | grep ERROR

# Run with verbose output
python3 src/setup/fhir_graphrag_setup.py --mode=sync 2>&1 | tee debug.log
```

### Performance Issues

```bash
# Check sync duration
grep "Sync completed" logs/kg_sync.log

# If slow (> 5 seconds), check:
# 1. Number of resources being processed
# 2. Database connection latency
# 3. Reduce batch size in config
```

## Production Deployment

### Checklist

- [ ] Logs directory created with appropriate permissions
- [ ] Cron/systemd/launchd configured and tested
- [ ] Log rotation configured (logrotate/newsyslog)
- [ ] Monitoring alerts for sync failures
- [ ] Database backup before enabling auto-sync
- [ ] Test sync with sample FHIR data changes
- [ ] Document sync schedule in operations runbook

### Monitoring Integration

```bash
# Prometheus metrics (future enhancement)
# Export sync metrics to Prometheus/Grafana
# - kg_sync_duration_seconds
# - kg_sync_resources_processed_total
# - kg_sync_errors_total
```

## Summary

**For most use cases, use Option 1: Scheduled Incremental Sync**

✅ Easy to setup and maintain
✅ Pure Python, no ObjectScript required
✅ Good performance (processes only changed resources)
✅ Configurable sync frequency
✅ Easy to monitor and debug

Run every 5 minutes with cron/systemd/launchd for near real-time knowledge graph updates!
