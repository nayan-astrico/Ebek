# Systemd Timer Setup for Metric Queue Processor

This guide shows how to set up the metric queue processor to run automatically every 5 minutes using systemd.

---

## 📋 Prerequisites

- Linux system with systemd (Ubuntu, Debian, CentOS, etc.)
- Django project with `process_metric_queue` management command
- Python 3 installed
- Appropriate permissions (root/sudo access)

---

## 🚀 Installation Steps

### 1. Update Service File Paths

Edit `metric-queue-processor.service` and update these paths for your system:

```bash
# Edit the service file
nano metric-queue-processor.service
```

**Update these lines:**
- `WorkingDirectory=/path/to/ebek_django_app` - Your Django project path
- `ExecStart=/usr/bin/python3` - Path to your Python 3 executable
  - Or use virtual environment: `/path/to/venv/bin/python`
- `User=www-data` - User that runs your Django app (may be `nginx`, `apache`, etc.)
- `Group=www-data` - Group that runs your Django app
- `ReadWritePaths=/path/to/ebek_django_app` - Same as WorkingDirectory

**Example for production:**
```ini
WorkingDirectory=/var/www/ebek_django_app
ExecStart=/var/www/ebek_django_app/venv/bin/python manage.py process_metric_queue
User=www-data
Group=www-data
ReadWritePaths=/var/www/ebek_django_app
```

### 2. Copy Service Files to Systemd

```bash
# Copy service file
sudo cp metric-queue-processor.service /etc/systemd/system/

# Copy timer file
sudo cp metric-queue-processor.timer /etc/systemd/system/

# Reload systemd to recognize new files
sudo systemctl daemon-reload
```

### 3. Enable and Start the Timer

```bash
# Enable the timer (starts on boot)
sudo systemctl enable metric-queue-processor.timer

# Start the timer immediately
sudo systemctl start metric-queue-processor.timer

# Verify it's running
sudo systemctl status metric-queue-processor.timer
```

---

## ✅ Verification

### Check Timer Status

```bash
# Check timer status
sudo systemctl status metric-queue-processor.timer

# Expected output:
# ● metric-queue-processor.timer - EBEK OSCE Metrics Queue Processor Timer
#    Loaded: loaded (/etc/systemd/system/metric-queue-processor.timer; enabled)
#    Active: active (waiting) since ...
#    Trigger: ...
```

### Check Service Logs

```bash
# View recent logs
sudo journalctl -u metric-queue-processor.service -n 50

# Follow logs in real-time
sudo journalctl -u metric-queue-processor.service -f

# View logs with timestamps
sudo journalctl -u metric-queue-processor.service --since "1 hour ago"
```

### Test Manual Run

```bash
# Manually trigger the service (for testing)
sudo systemctl start metric-queue-processor.service

# Check if it ran successfully
sudo systemctl status metric-queue-processor.service
```

---

## 🔧 Management Commands

### Start/Stop Timer

```bash
# Start timer
sudo systemctl start metric-queue-processor.timer

# Stop timer
sudo systemctl stop metric-queue-processor.timer

# Restart timer
sudo systemctl restart metric-queue-processor.timer
```

### Enable/Disable on Boot

```bash
# Enable timer to start on boot
sudo systemctl enable metric-queue-processor.timer

# Disable timer from starting on boot
sudo systemctl disable metric-queue-processor.timer
```

### View Timer Schedule

```bash
# List all timers
systemctl list-timers

# List timers with details
systemctl list-timers --all

# Check next run time
systemctl list-timers metric-queue-processor.timer
```

---

## 📊 Monitoring

### Check Last Run Time

```bash
# Check when timer last triggered
systemctl list-timers metric-queue-processor.timer --all
```

### View Service Execution History

```bash
# View all service runs
sudo journalctl -u metric-queue-processor.service --since "today"

# View only errors
sudo journalctl -u metric-queue-processor.service -p err
```

### Check Processing Stats

The management command outputs stats. Check logs to see:
- Number of queue items processed
- Number of contexts updated
- Any errors or warnings

---

## 🐛 Troubleshooting

### Timer Not Running

```bash
# Check timer status
sudo systemctl status metric-queue-processor.timer

# Check if timer is enabled
systemctl is-enabled metric-queue-processor.timer

# Reload systemd and restart
sudo systemctl daemon-reload
sudo systemctl restart metric-queue-processor.timer
```

### Service Failing

```bash
# Check service status
sudo systemctl status metric-queue-processor.service

# View detailed error logs
sudo journalctl -u metric-queue-processor.service -n 100 --no-pager

# Test manual run to see errors
sudo systemctl start metric-queue-processor.service
sudo journalctl -u metric-queue-processor.service -n 50
```

### Permission Issues

```bash
# Check file permissions
ls -la /etc/systemd/system/metric-queue-processor.*

# Ensure service user has access
sudo -u www-data python3 /path/to/manage.py process_metric_queue
```

### Python Path Issues

If using a virtual environment, ensure the service file points to the venv Python:

```ini
ExecStart=/var/www/ebek_django_app/venv/bin/python manage.py process_metric_queue
```

---

## 🔄 Update Timer Schedule

To change the frequency (e.g., every 3 minutes instead of 5):

1. Edit the timer file:
   ```bash
   sudo nano /etc/systemd/system/metric-queue-processor.timer
   ```

2. Update the `OnCalendar` line:
   ```ini
   OnCalendar=*:0/3  # Every 3 minutes
   ```

3. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart metric-queue-processor.timer
   ```

**Common schedules:**
- `*:0/5` - Every 5 minutes
- `*:0/10` - Every 10 minutes
- `*:0/1` - Every minute
- `hourly` - Every hour
- `daily` - Once per day at midnight

---

## 📝 Service File Customization

### Add Environment Variables

If your Django app needs specific environment variables:

```ini
[Service]
Environment="DJANGO_SETTINGS_MODULE=ebek_django_app.settings"
Environment="PYTHONPATH=/var/www/ebek_django_app"
Environment="DATABASE_URL=postgresql://..."
Environment="FIREBASE_CREDENTIALS=/path/to/firebase_key.json"
```

### Use Virtual Environment

```ini
[Service]
ExecStart=/var/www/ebek_django_app/venv/bin/python manage.py process_metric_queue
```

### Adjust Resource Limits

```ini
[Service]
MemoryMax=1G        # Maximum memory
CPUQuota=50%        # CPU limit
LimitNOFILE=65536   # File descriptor limit
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Timer is enabled: `systemctl is-enabled metric-queue-processor.timer`
- [ ] Timer is active: `systemctl status metric-queue-processor.timer`
- [ ] Service runs successfully: `sudo systemctl start metric-queue-processor.service`
- [ ] Logs show processing: `journalctl -u metric-queue-processor.service -n 20`
- [ ] Next run time is scheduled: `systemctl list-timers metric-queue-processor.timer`
- [ ] Firestore collections are being updated (check `UnitMetrics` and `SemesterMetrics`)

---

## 🎯 Expected Behavior

- **Timer triggers** every 5 minutes
- **Service runs** the `process_metric_queue` command
- **Processes** unprocessed items from `MetricUpdateQueue` (last 10 minutes)
- **Updates** `UnitMetrics` and `SemesterMetrics` collections
- **Logs** all activity to systemd journal

---

## 📚 Additional Resources

- [systemd.timer Documentation](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
- [systemd.service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Journalctl Guide](https://www.freedesktop.org/software/systemd/man/journalctl.html)

---

**Status:** ✅ Ready for Production  
**Frequency:** Every 5 minutes  
**Auto-start:** Enabled on boot

