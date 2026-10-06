# Deploying

The Dockerfile is the deployment unit. It reads `$PORT`, warms the CRF model at
build time, and needs no secrets to run.

## The data problem, first

`dist/unified_lexicon.json` is **not in this repository** — that is deliberate
(see `dist/README.md`). A host that builds from GitHub therefore gets the
309-entry `dist/sample_lexicon.json`, which runs correctly but is not the full
dictionary.

Ways to give a deployment the full 6,702 entries:

| approach | how | when |
|---|---|---|
| **mounted bucket** (Cloud Run, used by `khmer-terminology`) | private GCS bucket mounted read-only, `LEXICON_PATH` pointing into it | Cloud Run gen2; no token, and the service account reads the object |
| **`LEXICON_URL`** | put the file in private storage; the app fetches it once at boot | building from GitHub — simplest |
| **bake into the image** | `COPY dist/unified_lexicon.json`, build locally, push to a private registry | you already push images |
| **sample only** | change nothing | a public demo where partial data is fine |

For `LEXICON_URL`, private storage can be a secret Gist, a release asset on a
private repo, or an R2/S3 object. Set `LEXICON_TOKEN` too if it needs auth; the
app sends it as `Authorization: Bearer …`. The file is fetched into the
container's temp directory at start-up — the data lives in the running process,
never on a public URL. A failed fetch logs and falls back to the bundled file
rather than refusing to boot.

## Koyeb

```bash
koyeb login                     # interactive; needs your account
koyeb app init khmer-lexicon \
  --git github.com/pr0meth4us/khmer-lexicon \
  --git-branch main \
  --git-builder docker \
  --git-docker-dockerfile web/Dockerfile \
  --ports 8000:http \
  --routes /:8000 \
  --instance-type small \
  --env LEXICON_URL=@lexicon-url \
  --env LEXICON_TOKEN=@lexicon-token
```

Create the two secrets first if you use them:

```bash
koyeb secret create lexicon-url --value "https://…/unified_lexicon.json"
koyeb secret create lexicon-token --value "…"
```

Notes:

- **Instance type `small`, not `nano`.** The automaton plus the khmer-nltk CRF
  model need roughly 400 MB resident; nano will OOM.
- **One worker.** Each gunicorn worker builds its own automaton and loads its own
  copy of the CRF model. The Dockerfile already sets `--workers 1 --threads 8`.
- Health check on `/healthz`, which reports the entry count actually loaded —
  check it after deploy to confirm you got 6,702 and not 309.

## Fly.io

`fly.toml` is committed and configured (Singapore, 1 GB, health check on
`/healthz`). Needs a payment method on the account, then `flyctl deploy`.

## Render (used by `khmer-terminology`)

Free, no card. `render.yaml` at the repository root defines the service:
Dashboard -> New -> Blueprint -> this repository. Then upload
`dist/unified_lexicon.json` as a Secret File named `unified_lexicon.json`;
`LEXICON_PATH` already points at `/etc/secrets/unified_lexicon.json`. Measured
resident memory with the full lexicon is ~200 MB, inside the free 512 MB.
Pushes to `main` redeploy.

## Hugging Face Spaces

Docker Spaces need a paid PRO account since 2026; the free tier only serves
static Spaces. Not usable for this app without paying.
