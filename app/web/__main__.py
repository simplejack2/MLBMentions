"""Entry point: python -m app.web"""

import uvicorn

uvicorn.run("app.web.app:app", host="0.0.0.0", port=8000, reload=False)
