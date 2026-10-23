"""Legacy entry point: no longer calls Gemini. Use check_copa_compatibility.py."""
if __name__ == '__main__':
    print('Gemini connection check is retired on this branch. Use scripts/check_copa_compatibility.py; --run-live explicitly consumes Codyssey quota.')
    raise SystemExit(2)
