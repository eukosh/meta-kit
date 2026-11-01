#!/bin/sh
# PROTOTYPE: generates the test media into media/ (gitignored).
set -e
cd "$(dirname "$0")" && mkdir -p media && cd media
ffmpeg -loglevel error -y -f lavfi -i "testsrc2=s=1080x1350" -frames:v 1 -q:v 3 photo.jpg
ffmpeg -loglevel error -y -f lavfi -i "smptebars=s=1080x1350" -frames:v 1 -q:v 3 photo2.jpg
ffmpeg -loglevel error -y -f lavfi -i "testsrc=s=1080x1080" -frames:v 1 photo.png
ffmpeg -loglevel error -y -f lavfi -i "testsrc2=s=1080x1920:r=30" -f lavfi -i "sine=f=440:sample_rate=48000" -t 6 -c:v libx264 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart reel.mp4
ffmpeg -loglevel error -y -f lavfi -i "testsrc2=s=1080x1920:r=30" -f lavfi -i "sine=f=330:sample_rate=48000" -t 60 -vf "noise=alls=40:allf=t" -c:v libx264 -b:v 10M -maxrate 12M -bufsize 20M -profile:v high -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart big.mp4
# Cuts and a low-bitrate long file, to separate size from duration on rupload.
ffmpeg -loglevel error -y -i big.mp4 -t 20 -c copy mid25.mp4
ffmpeg -loglevel error -y -i big.mp4 -t 40 -c copy mid50.mp4
ffmpeg -loglevel error -y -f lavfi -i "testsrc2=s=1080x1920:r=30" -f lavfi -i "sine=f=550:sample_rate=48000" -t 40 -c:v libx264 -b:v 900k -profile:v high -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart long-small.mp4
ls -la
