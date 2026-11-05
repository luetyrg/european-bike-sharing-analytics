"""Create local credentials once. Never prints secrets or overwrites existing files."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
if not (root/'.env').exists():
    pg=secrets.token_hex(24)
    (root/'.env').write_text('\n'.join([
        'POSTGRES_USER=redash','POSTGRES_DB=redash',f'POSTGRES_PASSWORD={pg}',
        f'REDASH_DATABASE_URL=postgresql://redash:{pg}@postgres/redash',
        'REDASH_REDIS_URL=redis://redis:6379/0',
        f'REDASH_SECRET_KEY={secrets.token_hex(32)}',f'REDASH_COOKIE_SECRET={secrets.token_hex(32)}',
        'REDASH_HOST=http://localhost:5001','REDASH_LOG_LEVEL=INFO',
        'REDASH_ENABLED_QUERY_RUNNERS=redash.query_runner.pg',
        'REDASH_ADDITIONAL_QUERY_RUNNERS=','REDASH_DISABLE_REFRESH_QUERIES=true',
        'REDASH_ALLOW_SCRIPTS_IN_USER_INPUT=false','REDASH_DISABLE_PUBLIC_URLS=true',
        'REDASH_REPORT_USAGE=false','REDASH_ENFORCE_CSRF=true',''
    ]),encoding='utf-8')
    print('Local environment created.')
else: print('Existing local environment retained.')
