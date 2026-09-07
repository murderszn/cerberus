# cerberus-agent

Run the Cerberus Python security scanner and agent CLI through npm.

## Requirements

- Node.js 18+
- Python 3.10+

## Usage

```bash
npx cerberus-agent scan .
npx cerberus-agent agent "audit this repository"
```

The launcher installs the current Cerberus package from GitHub into the active
Python environment on first use, then forwards all arguments to `cerberus`.
For a persistent install:

```bash
npm install -g cerberus-agent
cerberus scan .
```

The browser-based Cerberus Agent remains available at
https://murderszn.github.io/cerberus/agent.html.
