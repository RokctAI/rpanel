# Cron Job Manager

## Overview
The Cron Job Manager allows you to schedule and manage automated tasks for your hosted websites.

## Features
- Visual cron expression builder
- Pre-built templates for common tasks
- Execution history and logs
- Email notifications on failures
- Manual execution for testing

## Usage

### Creating a Cron Job
1. Navigate to Hosting > Cron Job > New
2. Enter job name and select website
3. Enter command to execute
4. Set cron schedule (or use template)
5. Optionally enable email notifications
6. Save

### Cron Expression Format
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Examples
- `0 2 * * *` - Daily at 2 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 3 1 * *` - Monthly on 1st at 3 AM

### Available Templates
- Daily Backup
- Clear Cache
- Update WordPress
- Database Optimization
- Log Rotation

## Security
- Commands execute in website directory
- 5-minute timeout for safety
- Execution logs tracked
- Email alerts for failures
