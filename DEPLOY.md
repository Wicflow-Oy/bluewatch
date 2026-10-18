# Deploying BlueWatch

One container serves the API and the built front end on port 8787. It is set up for a public demo with no login: a read-only file system with `/tmp` as the only writable place, no access log, a memory limit and a health check. Put it behind a reverse proxy that terminates TLS.

## 1. Settings

```bash
cp .env.example .env && chmod 600 .env
```

Everything works with the file left empty: the app then serves the precomputed demo from recorded data. `.env.example` lists every variable with its default. The ones a deployment usually sets:
- `BLUEWATCH_LIVE_LOOKUPS=1` turns on the live register lookups and name search.
- `ANTHROPIC_API_KEY` turns on the website reader. Use a key for this app only, in a workspace with its own spend limit; the app's daily cap (`BLUEWATCH_DAILY_SPEND_CAP_USD`, default 40) is the first guard.
- `BLUEWATCH_HOST` is the public hostname the proxy routes to the container.
- `FORWARDED_ALLOW_IPS` is the reverse proxy's address or subnet (for Traefik, its container IP or the proxy network's subnet). Uvicorn trusts `X-Forwarded-For` only from there, so the per-IP limits see each visitor's real address and no other container on the network can fake one. Left empty it stays `*`.

Keys belong in `.env` on the host only, never in git.

## 2. Start

Behind Traefik running in Docker, set `TRAEFIK_NETWORK`, `TRAEFIK_ENTRYPOINT` and `TRAEFIK_CERTRESOLVER` in `.env` to your proxy's values; `deploy/compose.yml` turns them into the container's routing labels:

```bash
BLUEWATCH_BUILD=$(git rev-parse --short HEAD) docker compose -p jx-bluewatch --env-file .env -f deploy/compose.yml up -d --build
```

`BLUEWATCH_BUILD` stamps the deployed commit into `/api/meta` (`"build"`) and the avatar's status panel, so anyone can check that the site runs the latest commit. Without it the build reads `dev`.

Behind Caddy, nginx or any proxy on the host, publish on loopback only (`BLUEWATCH_PORT`, default 18787) and point the proxy at it:

```bash
BLUEWATCH_BUILD=$(git rev-parse --short HEAD) docker compose -p jx-bluewatch --env-file .env -f deploy/compose.port.yml up -d --build
```

```
bluewatch.example.com {
    reverse_proxy 127.0.0.1:18787
}
```

## 3. Check

The container reports healthy once `GET /api/health` answers; the compose files check it every 30 seconds.

```bash
docker inspect --format '{{.State.Health.Status}}' jx-bluewatch     # healthy
curl -fsS https://<host>/api/health                                 # {"ok":true}
curl -sI https://<host>/ | grep -i x-robots-tag                      # noindex, nofollow
curl -fsS https://<host>/api/meta | grep -o '"build":"[^"]*"'         # the commit you deployed
```

## 4. Update, roll back, stop

```bash
git pull && BLUEWATCH_BUILD=$(git rev-parse --short HEAD) docker compose -p jx-bluewatch --env-file .env -f deploy/compose.yml up -d --build              # update
git checkout <commit> && BLUEWATCH_BUILD=$(git rev-parse --short HEAD) docker compose -p jx-bluewatch --env-file .env -f deploy/compose.yml up -d --build  # roll back
docker compose -p jx-bluewatch -f deploy/compose.yml down                                                       # stop
```

Use `deploy/compose.port.yml` in place of `deploy/compose.yml` if that is how you started it.

## What the public container guarantees

- The compose files force `BLUEWATCH_PUBLIC=1` and `OUTREACH_MODE=demo`, so no e-mail can be sent whatever `.env` says. Leave the `SMTP_*` variables empty.
- What a visitor types is never written to disk or logged: the access log is off and the file system is read-only.
- The daily spend counter is kept on the small `jx-bluewatch-state` volume (mounted at `/state`), so a restart does not reset it; the provider's workspace limit is the second guard.
- Behind a reverse proxy on a shared Docker network, set `FORWARDED_ALLOW_IPS` in `.env` to the proxy's address or subnet so per-IP limits see the visitor's real address and other containers cannot spoof one.
- Uploads are capped while they stream in: the blind-set evaluation stops reading at 200 KB and the Idea Harbour forms at 16 KB, with or without a `Content-Length`.
