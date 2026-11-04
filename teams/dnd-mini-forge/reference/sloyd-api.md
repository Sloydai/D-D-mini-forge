# Sloyd API: how every Mini Forge skill talks to Sloyd

Source of truth: the Sloyd API docs (`api-dashboard/documentation/` in Sloydai/Horizon, published at
https://www.sloyd.ai/api). Use only the tools below. Never invent tools or parameters.

## Connection

The plugin ships `.mcp.json`, which connects the hosted Sloyd MCP server automatically if
`SLOYD_CLIENT_ID` and `SLOYD_CLIENT_SECRET` are set in the shell that starts Claude Code.
Manual setup (same server):

```bash
claude mcp add --transport http sloyd https://api.sloyd.ai/api/mcp \
  --header "x-client-id: $SLOYD_CLIENT_ID" \
  --header "x-client-secret: $SLOYD_CLIENT_SECRET"
```

Tool names show up with a server prefix (for example `mcp__sloyd__generate_image` or
`mcp__plugin_dnd-mini-forge_sloyd__generate_image`). Any prefix is fine.

Never echo, log or write the client secret into a file. Keys come from https://api-dashboard.sloyd.ai.

## Tools

| Tool | Used for | Key arguments |
|---|---|---|
| `get_credit_balance` | check credits before every batch | none |
| `get_generation_styles` | list `genStyleId` values | none |
| `generate_image` | concept art, battle maps | `prompt`, `aspectRatio` (`1:1`, `4:3`, `3:4`, `3:2`, `2:3`, `16:9`, `9:16`), `genStyleId`, `referenceImageJobId` (an `upload_image` job) |
| `edit_image` | turnaround views, variants | `jobId` (source image job), `prompt`, `genStyleId` |
| `upload_image` | reuse a user image or a style anchor | `file: {url}` or `file: {base64, mimeType}` |
| `generate_3d_from_images` | character minis from a turnaround | `frontImage` (required) + at least one of `leftImage` / `backImage` / `rightImage`, each `{url}`; `EnablePBR: "true"` for texture; `FaceCount: "300000"` |
| `generate_3d_from_image` | beasts, single-view props | `file: {url}` or `imageJobId`; `textureResolution`; `targetFaceCount` |
| `generate_3d_from_text` | simple scatter props | `prompt`, `genStyleId`, `textureResolution` (`"none"` = geometry only, cheaper) |
| `split_model_into_parts` | modular terrain, bed-size splits | `jobId`, `method` (`partition` for printing), `numberOfParts` 4-16, `attachmentPoints: true` |
| `retexture_model` | paint variants of the same sculpt | `jobId`, `prompt`, `textureResolution` |
| `generate_skybox` | 360 backdrops | `prompt`, `genStyleId` |
| `generate_skybox_from_image` | expand a battle map / art into 360 | `imageJobId` (from `upload_image`), `prompt` |
| `edit_skybox` | same place, new mood | `jobId`, `prompt` |
| `get_job` | poll + get outputs | `jobId`, `wait: 30` |

## The job loop

1. Call the generation tool. It returns `{ "jobId": ... }` in under a second.
2. Call `get_job` with `{ "jobId": ..., "wait": 30 }`. Repeat until `done` is `true`.
   Typical times: image 15-60 s, image edit 20-60 s, 3D 1-4 min, skybox 1-2 min, split ~4 min.
3. Read the URLs from `outputs`: `imageUrl` (images), `glbUrl` (3D), `panoramaUrl` and
   `cubemapFaceUrls` (skyboxes). 3D results are also at
   `https://storage.googleapis.com/ai-services-quality/jobs/{jobId}.glb`.
4. Download with `curl -sL -o <file> <url>` into the project's output folder.

Keep at most **5 jobs running at once** per key. Start independent jobs in parallel, then poll each.

## Credits: check and state the cost first

Before any batch: call `get_credit_balance`, add up the plan, and tell the user, for example
"This party is 4 minis x 70 = 280 credits (about $3.73). You have 880. Go?" Wait for a yes
unless the user already approved a budget. 75 credits = $1.

| Job | Credits |
|---|---|
| `generate_image` | 10 |
| `edit_image` | 15 |
| `generate_3d_from_images`, textured (`EnablePBR: "true"`) | 30 (20 geometry only, +5 quads, +10 if FaceCount >= 500k) |
| `generate_3d_from_image`, textured | 20 (10 geometry only) |
| `generate_3d_from_text`, textured | 25 (15 with `textureResolution: "none"`) |
| `generate_skybox` / `generate_skybox_from_image` | 25 |
| `split_model_into_parts` | 40 |
| `retexture_model` | 15 |
| `upload_image`, `get_job`, `get_credit_balance`, `get_generation_styles` | 0 |

Prices are from https://www.sloyd.ai/api/pricing. A 402 response reports the exact `required` amount.
Credits are charged when a job starts and refunded automatically if it fails.

## Errors

| Error | What to do |
|---|---|
| 402 Payment Required (`required`, `available`) | Stop. Tell the user how many credits are missing and link https://api-dashboard.sloyd.ai. Nothing was charged. Retry the same call after top-up. |
| 429 Too Many Requests | 5 jobs are active on this key. Poll the running jobs, start the next one when one finishes. Don't spin-retry. |
| 401 | Keys missing or wrong. Check `SLOYD_CLIENT_ID` / `SLOYD_CLIENT_SECRET`. |
| 422 | A field is invalid. Fix the argument, don't retry blindly. |
| job `status: "error"` | Credits are refunded. Retry once with a simpler prompt or cleaner image, then report. |

## Fallback when MCP tools aren't available

`${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py` (Python stdlib only) does the same thing from the shell:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py balance
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py call generate_image '{"prompt":"..."}' --wait --download out/ --name concept
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py plan plan.json --out out/ --yes   # dependency batch, max 5 active
```

`--rest` switches to the documented REST endpoints (`POST https://api.sloyd.ai/api/jobs/text-to-image`,
`/jobs/image-edit`, `/jobs/multi-image-to-3d`, `/jobs/text-to-3d`, `/jobs/image-to-3d`,
`/jobs/text-to-worldbox`, `/jobs/skybox-edit`, `/jobs/split-to-parts`, `/jobs/retexture`,
`GET /jobs/{jobId}`, `GET /user/api-access/balance`) with the same `x-client-id` / `x-client-secret` headers.
