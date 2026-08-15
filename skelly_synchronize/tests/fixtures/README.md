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

`rotation/vertical_iphone_style.mp4` is a single 1 second, 64x48, 10fps clip
tagged with a display-matrix rotation, simulating an iPhone vertical
recording stored landscape with a rotation flag. Used by
`tests/integration/test_rotation.py` to guard against the trim backends
losing/ignoring that rotation tag (as happened when a downstream library's
rotation detection stopped matching newer ffmpeg's stderr wording).

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

# rotation/vertical_iphone_style.mp4 -- landscape-coded 64x48 clip with a
# display-matrix rotation tag, simulating an iPhone vertical recording.
# ffmpeg's own metadata/bitstream-filter options for setting this on encode
# are unreliable across versions, so the matrix is patched into the muxed
# file's `tkhd` atom directly afterwards.
ffmpeg -y -f lavfi -i "testsrc2=size=64x48:rate=10:duration=1" \
       -pix_fmt yuv420p -c:v libx264 \
       rotation/vertical_iphone_style.mp4

python3 - <<'PYEOF'
import struct, math

def set_rotation(path, degrees):
    with open(path, "rb") as f:
        data = bytearray(f.read())
    idx = data.find(b"tkhd")
    version = data[idx + 4]
    if version == 1:
        matrix_offset = idx + 4 + 4 + 8 + 8 + 4 + 4 + 8 + 8 + 2 + 2 + 2 + 2
    else:
        matrix_offset = idx + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 8 + 2 + 2 + 2 + 2
    theta = math.radians(degrees)
    a, b = round(math.cos(theta) * 65536), round(math.sin(theta) * 65536)
    c, d = round(-math.sin(theta) * 65536), round(math.cos(theta) * 65536)
    matrix = [a, b, 0, c, d, 0, 0, 0, 0x40000000]
    for i, v in enumerate(matrix):
        struct.pack_into(">i", data, matrix_offset + i * 4, v)
    with open(path, "wb") as f:
        f.write(data)

set_rotation("rotation/vertical_iphone_style.mp4", -90)
PYEOF
```
