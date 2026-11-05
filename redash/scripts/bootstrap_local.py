"""Run inside this new Redash server only: create local owner and a read-only data role."""
import json
import secrets
import sys
from pathlib import Path
sys.path.insert(0, '/app')
from sqlalchemy import text
from redash import create_app, models

app=create_app()
with app.app_context():
    credential_file=Path('/private/credentials.json')
    if credential_file.exists():
        print('Existing local owner retained.')
    else:
        assert models.User.query.count()==0, 'Unexpected existing users; refusing to replace them'
        org=models.Organization(name='Bike Sharing Analytics',slug='default',settings={})
        admin=models.Group(name='admin',permissions=models.Group.ADMIN_PERMISSIONS,org=org,type=models.Group.BUILTIN_GROUP)
        default=models.Group(name='default',permissions=models.Group.DEFAULT_PERMISSIONS,org=org,type=models.Group.BUILTIN_GROUP)
        models.db.session.add_all([org,admin,default])
        models.db.session.flush()
        password=secrets.token_urlsafe(20)
        user=models.User(org=org,email='boris@localhost.invalid',name='Борис Пупырев',group_ids=[admin.id,default.id])
        user.hash_password(password)
        models.db.session.add(user)
        models.db.session.commit()
        reader_password=secrets.token_hex(24)
        with models.db.engine.begin() as conn:
            conn.execute(text(f"CREATE ROLE bike_reader LOGIN PASSWORD '{reader_password}'"))
            conn.execute(text('GRANT USAGE ON SCHEMA bike TO bike_reader'))
            conn.execute(text('GRANT SELECT ON ALL TABLES IN SCHEMA bike TO bike_reader'))
            conn.execute(text('ALTER ROLE bike_reader SET statement_timeout=15000'))
            conn.execute(text('ALTER ROLE bike_reader SET default_transaction_read_only=on'))
        credential_file.write_text(json.dumps({'email':user.email,'password':password,'api_key':user.api_key,'reader_password':reader_password},ensure_ascii=False),encoding='utf-8')
        Path('/private/login.txt').write_text('Local Redash: http://localhost:5001\nEmail: '+user.email+'\nPassword: '+password+'\n',encoding='utf-8')
        print('Local owner and read-only analytics role created; credentials saved privately.')
