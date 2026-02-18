import traceback, sys
try:
    from app import create_app
    app = create_app()
except Exception:
    traceback.print_exc(file=sys.stderr)
    raise
