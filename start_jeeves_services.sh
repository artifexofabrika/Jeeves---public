#!/bin/bash
# Start Lake ingestion
nohup python3 /home/drinrin/lake_ingest.py > /mnt/lake/ingest.log 2>&1 &
# Start Telegram bridge
nohup python3 /home/drinrin/jeeves_telegram.py > /dev/null 2>&1 &
echo "Jeeves services started."
