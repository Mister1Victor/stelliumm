"""astro12 REST API server (FastAPI).

Isolation notes (licensing):
- This service imports ONLY the MIT package ``astro12`` in *direct* mode
  (pyswisseph), never ``stellium``. The whole deployable stays MIT-clean.
- LLM keys live on the server only; clients never see them.
"""
