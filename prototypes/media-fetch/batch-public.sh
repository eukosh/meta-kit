#!/bin/sh
# PROTOTYPE: the approved public writes, 15 min apart.
cd "$(dirname "$0")"
export TUNNEL=$(cat tunnel.url)
at() { while [ "$(date +%H:%M)" != "$1" ]; do sleep 10; done; }
at 13:37
echo "### threads carousel (media 404)"
python3 probe.py th-publish th-car-pub 17999636339841079
if ! tail -1 results.jsonl | grep -q '"ok": true' && ! grep -q '"test": "th-car-pub", "step": "th_publish", .*"ok": true' results.jsonl; then
  echo "### retry with media back"; python3 probe.py kill off; python3 probe.py th-publish th-car-pub-retry 17999636339841079
fi
at 13:52
python3 probe.py kill off
echo "### fb photo story"; python3 probe.py fb-story fb-story-photo photo.jpg
at 14:07
echo "### fb video story (bytes)"; python3 probe.py fb-story fb-story-video reel.mp4 --bytes
echo "### done"
