#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/trainer-bot/backups"
DATE=$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/clients_$DATE.db"

mkdir -p "$BACKUP_DIR"

# Copy DB from Docker volume
docker run --rm \
  -v trainer-bot_sqlite_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine cp /data/clients.db "/backup/clients_$DATE.db"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/clients_*.db | tail -n +8 | xargs -r rm

# Send to Telegram
source /opt/trainer-bot/.env
curl -s -F "chat_id=$TRAINER_TELEGRAM_ID" \
     -F "document=@$BACKUP_FILE" \
     -F "caption=💾 Резервна копія бази: $DATE" \
     "https://api.telegram.org/bot$BOT_TOKEN/sendDocument" > /dev/null

echo "Backup done: $BACKUP_FILE"
