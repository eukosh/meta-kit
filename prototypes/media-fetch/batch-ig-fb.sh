#!/bin/sh
# PROTOTYPE: non-public probes, paced. Nothing here publishes.
cd "$(dirname "$0")"
export TUNNEL=$(cat tunnel.url)
p() { echo "### $*"; python3 probe.py "$@"; sleep 30; }
p ig ig-img-plain photo.jpg
p ig ig-img-302 photo.jpg --route r302
p ig ig-img-301 photo.jpg --route r301
p ig ig-img-query photo.jpg --query
p ig ig-img-noct photo.jpg --route noct
p ig ig-img-octet photo.jpg --route octet
p ig ig-img-png photo.png
p ig ig-story-img photo.jpg --kind STORIES
p ig ig-reel reel.mp4
p ig ig-reel-302 reel.mp4 --route r302
p ig ig-reel-octet reel.mp4 --route octet
p ig ig-story-vid reel.mp4 --kind STORIES
p ig ig-reel-big big.mp4
p ig-carousel ig-car photo.jpg photo2.jpg reel.mp4
p ig-resumable ig-rup-bytes reel.mp4
p ig-resumable ig-rup-url reel.mp4 --file-url
p ig-resumable ig-rup-story reel.mp4 --kind STORIES
p ig-resumable ig-rup-big big.mp4
p fb-photo fb-photo-plain photo.jpg
p fb-photo fb-photo-png photo.png
p fb-photo fb-photo-302 photo.jpg --route r302
p fb-photo fb-photo-query photo.jpg --query
p fb-photo fb-photo-noct photo.jpg --route noct
p fb-video fb-video reel.mp4
p fb-reel fb-reel reel.mp4
echo "### done"
