# ollama-mcp

Prototype multi-container MCP architecture integrating 3 Ollama instances and small wrapper services.

Overview, safety notes, and quick-run instructions are included in the repository. This is a developer prototype — read safety notes before enabling execution.

Quick start

1. Build images:

```bash
cd ollama-mcp
docker compose build
```

2. Start stack (dry-run first):

```bash
docker compose up
```

3. Pull models into each Ollama container (example):

```bash
docker exec -it ollama1 ollama pull llama3.2
docker exec -it ollama2 ollama pull codellama:code
docker exec -it ollama3 ollama pull mistral
```

4. Test the pipeline (dry-run):

```bash
curl -X POST "http://localhost:8080/submit" -H "Content-Type: application/json" -d '{"prompt":"Open Gmail, compose a message to bob@example.com saying hi and send", "execute": false}'
```

Important: do NOT enable `ALLOW_EXECUTION=true` in the executor unless you understand the safety risks and run in a sandbox/VM.
