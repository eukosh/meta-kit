#!/bin/sh
# PROTOTYPE: non-public Page probes, paced. Nothing here publishes.
cd "$(dirname "$0")"
export TUNNEL=$(cat tunnel.url)
p() { echo "### $*"; python3 probe.py "$@"; sleep 30; }
p fb-photo fb-photo-plain photo.jpg
p fb-photo fb-photo-png photo.png
p fb-photo fb-photo-302 photo.jpg --route r302
p fb-photo fb-photo-query photo.jpg --query
p fb-photo fb-photo-noct photo.jpg --route noct
p fb-video fb-video reel.mp4
p fb-reel fb-reel reel.mp4
echo "### done"
