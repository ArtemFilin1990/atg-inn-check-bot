# Infrastructure Validation Skill

When working in this repository, ALWAYS enforce the following configuration invariants:

1. **Entrypoint**: The application entrypoint is STRICTLY `src/main.py`. There is no `app.py` or `main.py` in the root directory.
2. **Amvera Config**: `amvera.yml` MUST contain a `run.command` explicitly pointing to `python src/main.py`. Do not let it fall back to default behavior.
3. **Docker**: `Dockerfile` MUST set `PYTHONPATH=/app/src` and run `CMD ["python", "src/main.py"]`.
4. **Environment**: All new environment variables used in Python code MUST be documented in `.env.example`.
5. **Dependencies**: Any new Python import must be added to `requirements.txt.