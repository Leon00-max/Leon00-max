# Setup (about 10 minutes)

1. On GitHub, create a **public** repo named exactly `Leon00-max`.
2. Upload everything in this folder, including the hidden `.github` folder.
3. Go to the repo's **Actions** tab, open "Build profile card", click **Run workflow**.
   After about 1 minute, your profile page shows the card.

## Optional: count private work
The built-in token only sees public activity. To include private commits:
1. Settings > Developer settings > Personal access tokens > Fine-grained > Generate.
   Give it read-only access: Metadata + Contents (all repos).
2. In the `Leon00-max` repo: Settings > Secrets and variables > Actions >
   New secret named `ACCESS_TOKEN`, paste the token.
Never paste the token into any file.

## Editing
- Text: edit `config.json` (keep each value short, about 40 chars max, or lines overflow).
- Empty values (like LinkedIn) are hidden automatically.
- Photo: the card turns your GitHub avatar into ASCII. For a cleaner look, upload a
  `avatar.png` with a transparent or plain background (a face close-up works best).
- `coding_since` drives the "Uptime" line.
