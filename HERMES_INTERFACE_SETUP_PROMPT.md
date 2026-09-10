# Hermes voice-interface bridge setup

I have a browser-based voice interface running on a different computer on my LAN. The frontend performs speech-to-text locally in the browser, sends the resulting text to Hermes, and displays Hermes's text reply. It must never generate or play audio.

Please inspect this Hermes installation and implement the smallest reliable HTTP bridge that invokes the existing Hermes agent correctly. Reuse Hermes's existing runtime, configuration, model provider, system prompt, tools, and conversation machinery; do not create a second assistant implementation or duplicate credentials.

## Existing interface sample and design source

The complete browser client is already implemented here:

- Repository: <https://github.com/murderszn/cerberus>
- Interface source and working sample: <https://github.com/murderszn/cerberus/blob/main/assistant-eyes.html>
- Direct raw HTML: <https://raw.githubusercontent.com/murderszn/cerberus/main/assistant-eyes.html>
- Main visual concept: <https://github.com/murderszn/cerberus/blob/main/assets/concepts/assistant-eyes-ui-v1.png>
- Eye-animation concept sheet: <https://github.com/murderszn/cerberus/blob/main/assets/concepts/assistant-eyes-working-sprites-v1.png>

Use `assistant-eyes.html` as the client and interface contract. Do not redesign or replace it. The only required client-side configuration is the Hermes bridge URL entered through the gear icon. If a small compatibility change is genuinely necessary, explain it and keep the current visual design and interaction behavior intact.

## Required HTTP contract

Run a service reachable from other approved devices on the LAN:

- Bind to `0.0.0.0` on port `8787` by default, with host and port configurable through environment variables.
- `GET /health` returns HTTP 200 JSON such as `{"ok": true, "service": "hermes-bridge"}`.
- `POST /api/chat` accepts JSON:

```json
{
  "message": "The user's transcribed or typed request",
  "sessionId": "A stable browser-generated conversation ID"
}
```

- Validate that `message` is a non-empty string and apply a sensible maximum length.
- Use `sessionId` to preserve separate Hermes conversation context when Hermes supports sessions. If Hermes cannot persist sessions yet, keep an in-memory session map with bounded history and document that it resets when the bridge restarts.
- Send `message` through the real installed Hermes agent and wait for its final text response.
- Return HTTP 200 JSON in this exact shape:

```json
{
  "reply": "Hermes's final text response"
}
```

- Return structured JSON errors with appropriate 4xx/5xx status codes. Never return stack traces, credentials, model keys, internal prompts, or filesystem details to the browser.
- Implement `OPTIONS` preflight and CORS for the frontend origin. During initial LAN testing, make allowed origins configurable with an environment variable rather than hard-coding one. Do not use wildcard CORS together with credentials.
- Set a reasonable request timeout, but allow enough time for agent tool calls. Do not silently retry non-idempotent agent actions.

## Security requirements

- Keep all model/API credentials on the Hermes PC. No provider or Hermes secret may be placed in the HTML or sent to the browser.
- Restrict port `8787` to my private LAN or private overlay network (for example, Tailscale) using the host firewall. Do not expose it to the public internet or add router port forwarding.
- Treat browser input as untrusted. Validate JSON, reject unexpected content types, cap request size, and sanitize logs so credentials and sensitive user content are not dumped unnecessarily.
- If this Hermes installation already has authentication middleware, preserve and use it. If it does not, first deliver the LAN/firewall-restricted bridge above and explain the safest compatible authentication upgrade instead of inventing a provider credential for the frontend.

## Browser client compatibility

The existing client will be configured with a URL like:

```text
http://192.168.1.50:8787/api/chat
```

It reads the reply from `reply`. It also tolerates `response`, `message`, `output`, or an OpenAI-compatible `choices[0].message.content`, but `reply` is the preferred field.

The interface intentionally has no text-to-speech. Do not add audio generation, voice playback, streaming audio, or an autoplay response.

## Implementation expectations

1. Inspect the installed Hermes project and identify the supported programmatic entry point before writing the bridge.
2. Use the project's existing language, dependency manager, logging conventions, and service patterns.
3. Keep the bridge small and isolated. Avoid unrelated refactors.
4. Add automated tests for health, validation, a successful mocked Hermes response, Hermes failure, timeout, and CORS preflight.
5. Provide a service definition appropriate for this PC's operating system so the bridge can restart automatically, but do not enable it until the tests pass.
6. Print the exact LAN URL I should enter in the interface's connection settings.
7. Verify from another LAN device with commands equivalent to:

```bash
curl http://HERMES_PC_IP:8787/health
curl -X POST http://HERMES_PC_IP:8787/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Reply with exactly: bridge connected","sessionId":"setup-test"}'
```

## Definition of done

- The health request succeeds from the interface computer.
- The chat request reaches the real Hermes agent and returns `{"reply":"..."}`.
- A second request using the same `sessionId` retains conversational context.
- The browser's CORS preflight and POST both succeed.
- Provider secrets never leave the Hermes machine.
- No audio is produced.
- Tests pass, the exact files changed are listed, and startup/shutdown instructions are documented.

Start by reporting the Hermes entry point and proposed bridge file location you found, then implement and verify the bridge end-to-end. Do not stop at a code sample if you have access to the machine and repository—set it up and test it.
