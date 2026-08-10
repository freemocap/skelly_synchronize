# Integration test fixtures

Tiny, synthetic, checked-in video pairs used by `tests/integration/`. Each pair
simulates two cameras recording the same real-world sync event (an audio tone
or a brightness flash) starting at different wall-clock times -- exactly the
scenario the sync algorithms are meant to solve -- without needing the full
Figshare sample dataset. Real ffmpeg/deffcode subprocesses run against these
files, so they exercise real codec/container behavior, unlike the mocked unit
tests elsewhere in `core`.

Both `cam_a`/`cam_b` pairs are 4 seconds, 64x64, 10fps. `cam_a`'s sync event
fires 1 second later in its own timeline than `cam_b`'s -- equivalent to
`cam_a` having started recording 1 second earlier than `cam_b` relative to the
same real event. The expected post-sync lags are therefore `cam_a: 0.0s`,
`cam_b: 1.0s` (brightness) and `cam_a: 1.0s`, `cam_b: 0.0s` (audio -- lag
direction is inverted from brightness because of how each raw lag is
normalized, see `LagResult`/KI-02).

## Regenerating

```bash
# audio_sync/ -- 880Hz, 1s tone. cam_a: tone at t=2s. cam_b: tone at t=1s.
ffmpeg -y -f lavfi -i "testsrc2=size=64x64:rate=10:duration=4" \
       -f lavfi -i "sine=frequency=880:duration=1" \
       -filter_complex "[1:a]adelay=2000,apad=whole_dur=4[a]" \
       -map 0:v -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest \
       audio_sync/cam_a.mp4

ffmpeg -y -f lavfi -i "testsrc2=size=64x64:rate=10:duration=4" \
       -f lavfi -i "sine=frequency=880:duration=1" \
       -filter_complex "[1:a]adelay=1000,apad=whole_dur=4[a]" \
       -map 0:v -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest \
       audio_sync/cam_b.mp4

# brightness_sync/ -- 0.3s white flash. cam_a: flash at t=2s. cam_b: flash at t=1s.
ffmpeg -y -f lavfi -i "color=c=black:s=64x64:r=10:d=4" \
       -vf "drawbox=x=0:y=0:w=64:h=64:color=white:t=fill:enable='between(t,2,2.3)'" \
       -pix_fmt yuv420p -c:v libx264 \
       brightness_sync/cam_a.mp4

ffmpeg -y -f lavfi -i "color=c=black:s=64x64:r=10:d=4" \
       -vf "drawbox=x=0:y=0:w=64:h=64:color=white:t=fill:enable='between(t,1,1.3)'" \
       -pix_fmt yuv420p -c:v libx264 \
       brightness_sync/cam_b.mp4
```
