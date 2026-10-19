# Sonic identity (optional)

How the brand sounds: a sonic logo for the sting, music beds and sound effects for social video. **Optional:** offer
it once at intake ("¿Quieres también identidad sonora?"); never block the kit on it, never add it unasked. Tags:
`[practice]` `[judgement]`.

## Sonic brief (write in `WORK/sets/X/sonic/brief.md`)
Derive from the platform, voice and axes; show it as a proposal:
- Mood (3 words) and two "never" sounds (e.g. "no trap hi-hats", "no stock ukulele").
- Timbre: geometric/precise marks lean synthetic (sine, FM, plucks); organic/warm marks lean acoustic (piano,
  marimba, guitar, wood). Restrained brands: sparse, soft attacks; expressive: punchy, layered.
- Tempo (BPM) matched to motion tempo: slower for premium and serious, faster for playful.
- Sonic logo: 2-4 s, 3-5 notes or one rhythmic gesture, ends resolved, timed to `duration-sting`.
- Never name or imitate an artist, song or another brand's sound.

## Pieces
| Piece | Length | Notes |
|---|---|---|
| sonic logo | 2-4 s | 3 candidates, the user picks; goes on `logo-sting.html` and video end cards |
| music bed | 15 / 30 / 60 s | instrumental, steady, loopable; sits under voice |
| SFX kit | 0.3-2 s each | whoosh, pop, tap, notification, riser, success |

## Tools (the user chooses; ask which they have)
**ElevenLabs (API)** - key in env `ELEVENLABS_API_KEY`, never in files or chat. Check current docs first.
```bash
curl -s https://api.elevenlabs.io/v1/sound-generation -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" -d @sfx.json -o sfx-whoosh.mp3      # {"text": …, "duration_seconds": 1.5}
curl -s https://api.elevenlabs.io/v1/music -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" -d @bed.json -o bed-30s.mp3          # {"prompt": …, "music_length_ms": 30000}
```
Write the JSON bodies to files; never interpolate user text into the shell.

**Suno (manual, no official API)** - write per piece: *Style of Music* (≤ 200 characters: genre, instruments, BPM,
mood), *Instrumental* on, title. The user generates in suno.com, downloads WAV/MP3 into `sonic/` and tells you which
take they chose. Do not automate the Suno site.

## Finish (ffmpeg, if installed)
- Trim and fade: `ffmpeg -i in.mp3 -t 30 -af "afade=t=out:st=29.2:d=0.8" out.wav`.
- Loudness: `loudnorm=I=-14:TP=-1` for stand-alone pieces, `I=-18` for beds under voice; check with `ebur128`.
- Deliver WAV 48 kHz + MP3 320k named `sonic-logo`, `bed-15s`, `bed-30s`, `bed-60s`, `sfx-<name>`.

## Hand-off
Put the files in the kit (`sonic/`), add a line to `motion.logo_sting` ("sound: sonic-logo, 3 s"), and tell the
user: commercial use depends on their Suno/ElevenLabs plan (free plans are usually non-commercial), and platforms'
content matching cannot be guaranteed.
