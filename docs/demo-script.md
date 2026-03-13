# Demo Script

Use this sequence to record a short terminal demo in about 20 seconds.

## Flow

1. Generate tweet candidates from an article URL.

```bash
./tweet.sh generate --url "https://night-sky.example.com/winter-triangle"
```

2. Show the full autopilot flow without posting.

```bash
./tweet.sh autopilot --dry-run
```

3. Show the manual safety check before a live post.

```bash
./tweet.sh post --text "星座に詳しくなくても、冬の大三角だけ覚えると夜空を見るハードルが一気に下がります。" --dry-run
```

## Recording Notes

- Start in the repository root with a clean terminal.
- Keep `default_ai_backend` set to `mock` for stable output.
- Crop to the terminal window and keep the clip under 20 seconds.
- If needed, speed the final video up slightly instead of showing extra commands.
