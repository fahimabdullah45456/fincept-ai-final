"""Authenticated Settings commands using the existing session, database and hasher.

No provider callbacks, notification delivery, restore or account deletion are simulated.
Export queries are deliberately allowlisted; never export authentication/request tables.
"""
import csv
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from typing import Literal
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..finance.csv_safety import csv_safe


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Notifications(Model):
    budget_alerts: bool = False
    goal_updates: bool = False
    payment_reminders: bool = False
    product_updates: bool = False


class Financial(Model):
    number_grouping: bool = True
    decimal_style: Literal['flexible', 'fixed'] = 'flexible'


class Preferences(Model):
    notifications: Notifications = Field(default_factory=Notifications)
    financial: Financial = Field(default_factory=Financial)


class SavePreferences(Preferences):
    version: int = Field(ge=0)


class Profile(Model):
    full_name: str = Field(min_length=2, max_length=100)

    @field_validator('full_name', mode='before')
    @classmethod
    def normalize(cls, value):
        return ' '.join(value.split()) if isinstance(value, str) else value


class Reauthenticate(Model):
    current_password: str = Field(min_length=1, max_length=512)


class ChangePassword(Reauthenticate):
    new_password: str = Field(min_length=8, max_length=512)
    confirm_password: str = Field(min_length=8, max_length=512)


class ClearDemo(Model):
    confirmation: Literal['CLEAR DEMO DATA']


# Every table name is a constant, never derived from a URL or request body.
# Child metadata is selected only by an owned canonical parent.
EXPORTS = {
    'wallets': ('SELECT * FROM wallets WHERE user_id=? AND dataset=?', 'wallets'),
    'wallet_metadata': ('SELECT m.* FROM wallet_metadata m JOIN wallets p ON p.id=m.wallet_id WHERE p.user_id=? AND p.dataset=?', 'wallets'),
    'wallet_profiles': ('SELECT m.* FROM wallet_profiles m JOIN wallets p ON p.id=m.wallet_id WHERE p.user_id=? AND p.dataset=?', 'wallets'),
    'wallet_events': ('SELECT * FROM wallet_events WHERE user_id=? AND dataset=?', 'wallets'),
    'transactions': ('SELECT * FROM transactions WHERE user_id=? AND dataset=?', 'transactions'),
    'transaction_metadata': ('SELECT m.* FROM transaction_metadata m JOIN transactions p ON p.id=m.transaction_id WHERE p.user_id=? AND p.dataset=?', 'transactions'),
    'budgets': ('SELECT * FROM budgets WHERE user_id=? AND dataset=?', 'budgets'),
    'budget_metadata': ('SELECT m.* FROM budget_metadata m JOIN budgets p ON p.id=m.budget_id WHERE p.user_id=? AND p.dataset=?', 'budgets'),
    'financial_goals': ('SELECT * FROM financial_goals WHERE user_id=? AND dataset=?', 'goals'),
    'goal_metadata': ('SELECT m.* FROM goal_metadata m JOIN financial_goals p ON p.id=m.goal_id WHERE p.user_id=? AND p.dataset=?', 'goals'),
    'goal_contributions': ('SELECT * FROM goal_contributions WHERE user_id=? AND dataset=?', 'goals'),
    'custom_categories': ('SELECT * FROM custom_categories WHERE user_id=? AND dataset=?', 'categories'),
    'category_appearance': ('SELECT m.* FROM category_appearance m JOIN custom_categories p ON p.id=m.category_id WHERE p.user_id=? AND p.dataset=?', 'categories'),
    'planner_occasions': ('SELECT * FROM planner_occasions WHERE user_id=? AND dataset=?', 'planner'),
    'planner_tasks': ('SELECT * FROM planner_tasks WHERE user_id=? AND dataset=?', 'planner'),
    'debt_records': ('SELECT * FROM debt_records WHERE user_id=? AND dataset=?', 'debt'),
    'debt_payments': ('SELECT * FROM debt_payments WHERE user_id=? AND dataset=?', 'debt'),
    'shopping_lists': ('SELECT * FROM shopping_lists WHERE user_id=? AND dataset=?', 'shopping'),
    'shopping_items': ('SELECT * FROM shopping_items WHERE user_id=? AND dataset=?', 'shopping'),
}


def settings_router(db, current_user, config, hasher, password_valid, rate_limit,
                    cookie_name, token_hash, set_session):
    router = APIRouter(prefix='/api/settings', tags=['Settings'])

    def preference_result(conn, user_id):
        row = conn.execute('SELECT * FROM user_settings WHERE user_id=?', (user_id,)).fetchone()
        return {'preferences': Preferences.model_validate_json(row['preferences_json']).model_dump() if row else Preferences().model_dump(),
                'version': row['version'] if row else 0}

    def verify_password(conn, user_id, password):
        row = conn.execute('SELECT password_hash FROM users WHERE id=?', (user_id,)).fetchone()
        try:
            valid = row is not None and hasher.verify(row['password_hash'], password)
        except (VerificationError, InvalidHashError):
            valid = False
        if not valid:
            raise HTTPException(422, {'message': 'Your current password is incorrect.',
                                      'field_errors': {'current_password': 'Enter your current password.'}})

    @router.get('')
    def load(user=Depends(current_user)):
        with db() as conn:
            result = preference_result(conn, user['id'])
        return {**result, 'notification_delivery': False, 'currency': 'BDT',
                'capabilities': {'restore': False, 'delete_account': False,
                                 'clear_demo': config.environment != 'production'},
                'integrations': [
                    {'id': 'google', 'name': 'Google sign-in', 'status': 'not_configured',
                     'description': 'Google authentication is not configured. Your email and password sign-in remains available.'},
                    {'id': 'bank', 'name': 'Bank connections', 'status': 'unavailable',
                     'description': 'No bank-linking provider is implemented. Wallets are managed manually; no bank access is active.'}
                ]}

    @router.patch('/profile')
    def update_profile(data: Profile, user=Depends(current_user)):
        with db() as conn:
            conn.execute('UPDATE users SET full_name=? WHERE id=?', (data.full_name, user['id']))
        return {'user': {**user, 'full_name': data.full_name}}

    @router.patch('/preferences')
    def save_preferences(data: SavePreferences, user=Depends(current_user)):
        prefs = Preferences(notifications=data.notifications, financial=data.financial).model_dump_json()
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            saved = preference_result(conn, user['id'])
            if saved['version'] != data.version:
                raise HTTPException(409, 'Settings changed in another window. Reload saved settings before trying again.')
            now = datetime.now(timezone.utc).isoformat()
            conn.execute('''INSERT INTO user_settings VALUES (?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET preferences_json=excluded.preferences_json,
                version=excluded.version,updated_at=excluded.updated_at''',
                         (user['id'], prefs, data.version + 1, now))
            return preference_result(conn, user['id'])

    @router.get('/security')
    def security(request: Request, user=Depends(current_user)):
        with db() as conn:
            sessions = conn.execute('SELECT token_hash,expires_at FROM sessions WHERE user_id=? AND expires_at>?',
                                    (user['id'], int(time.time()))).fetchall()
        current = token_hash(request.cookies.get(cookie_name, ''))
        expiry = next((r['expires_at'] for r in sessions if r['token_hash'] == current), None)
        return {'active_sessions': len(sessions),
                'current_expires_at': datetime.fromtimestamp(expiry, timezone.utc).isoformat() if expiry else None}

    @router.post('/password')
    def change_password(data: ChangePassword, request: Request, response: Response, user=Depends(current_user)):
        rate_limit(request, 'settings-security', user['email'])
        errors = {}
        if not password_valid(data.new_password):
            errors['new_password'] = 'Use 8+ characters, upper and lowercase letters, a number and a symbol.'
        if data.new_password != data.confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'
        if data.new_password == data.current_password:
            errors['new_password'] = 'Choose a different password.'
        if errors:
            raise HTTPException(422, {'message': 'Check the highlighted fields.', 'field_errors': errors})
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            verify_password(conn, user['id'], data.current_password)
            conn.execute('UPDATE users SET password_hash=? WHERE id=?', (hasher.hash(data.new_password), user['id']))
            conn.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
            set_session(conn, request, response, user['id'], False)
        return {'message': 'Password updated. Other sessions were signed out. This session was renewed.'}

    @router.post('/sessions/revoke-others')
    def revoke_others(data: Reauthenticate, request: Request, user=Depends(current_user)):
        rate_limit(request, 'settings-security', user['email'])
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            verify_password(conn, user['id'], data.current_password)
            result = conn.execute('DELETE FROM sessions WHERE user_id=? AND token_hash<>? AND expires_at>?',
                                  (user['id'], token_hash(request.cookies.get(cookie_name, '')), int(time.time())))
        return {'revoked': result.rowcount}

    @router.get('/export')
    def export(format: Literal['csv', 'json'] = 'csv',
               scope: Literal['all', 'transactions', 'wallets', 'budgets', 'goals'] = 'all',
               dataset: Literal['live', 'demo'] = 'live', user=Depends(current_user)):
        if dataset == 'demo' and config.environment == 'production':
            raise HTTPException(403, 'Sample workspaces are disabled in production.')
        tables, headers = {}, {}
        with db() as conn:
            # One SQLite read snapshot, not separately inconsistent per-table reads.
            conn.execute('BEGIN')
            schema_version = conn.execute('PRAGMA user_version').fetchone()[0]
            for name, (query, group) in EXPORTS.items():
                if scope != 'all' and group != scope:
                    continue
                cursor = conn.execute(query, (user['id'], dataset))
                headers[name] = [d[0] for d in cursor.description]
                tables[name] = [dict(row) for row in cursor.fetchall()]
        now = datetime.now(timezone.utc)
        manifest = {'product': 'FINCEPT AI', 'export_format_version': 1, 'schema_version': schema_version,
                    'generated_at': now.isoformat(), 'scope': scope, 'dataset': dataset,
                    'amounts': 'Original integer minor units. No conversion or masking applied.',
                    'restorable': False, 'includes': {name: len(rows) for name, rows in tables.items()},
                    'excludes': ['authentication credentials and sessions', 'AI conversations', 'idempotency receipts', 'account preferences']}
        filename = f'fincept-{dataset}-{scope}-{now.strftime("%Y%m%d-%H%M%S")}'
        if format == 'json':
            return Response(json.dumps({'manifest': manifest, 'data': tables}, ensure_ascii=False, indent=2),
                            media_type='application/json',
                            headers={'Content-Disposition': f'attachment; filename="{filename}.json"'})
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps(manifest, indent=2))
            for name, rows in tables.items():
                text = io.StringIO(newline='')
                writer = csv.writer(text, lineterminator='\r\n')
                writer.writerow(headers[name])
                for row in rows:
                    writer.writerow([csv_safe(row[column]) if isinstance(row[column], str) else row[column]
                                     for column in headers[name]])
                # UTF-8 BOM supports spreadsheet readers. Empty tables still have headers.
                archive.writestr(name + '.csv', '\ufeff' + text.getvalue())
        return Response(output.getvalue(), media_type='application/zip',
                        headers={'Content-Disposition': f'attachment; filename="{filename}.zip"'})

    @router.post('/demo/clear')
    def clear_demo(data: ClearDemo, user=Depends(current_user)):
        if config.environment == 'production':
            raise HTTPException(403, 'Sample workspaces are disabled in production.')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute("SELECT 1 FROM assistant_requests WHERE user_id=? AND dataset='demo' AND status='pending' LIMIT 1", (user['id'],)).fetchone():
                raise HTTPException(409, 'Finish the pending sample AI request before clearing sample data.')
            params = (user['id'],)
            counts = {}
            # Reverse dependency order; demo is explicit schema classification, never a title guess.
            for table in ('assistant_messages', 'assistant_requests', 'assistant_conversations', 'planner_tasks',
                          'planner_occasions', 'goal_contributions'):
                counts[table] = conn.execute(f"DELETE FROM {table} WHERE user_id=? AND dataset='demo'", params).rowcount
            for table, parent, key in (('goal_metadata', 'financial_goals', 'goal_id'),
                                       ('budget_metadata', 'budgets', 'budget_id'),
                                       ('transaction_metadata', 'transactions', 'transaction_id'),
                                       ('wallet_profiles', 'wallets', 'wallet_id'),
                                       ('wallet_metadata', 'wallets', 'wallet_id'),
                                       ('category_appearance', 'custom_categories', 'category_id')):
                conn.execute(f"DELETE FROM {table} WHERE {key} IN (SELECT id FROM {parent} WHERE user_id=? AND dataset='demo')", params)
            for table in ('financial_goals', 'budgets', 'debt_payments', 'debt_records', 'shopping_items',
                          'shopping_lists', 'wallet_events', 'transactions', 'wallets', 'custom_categories', 'financial_workspaces'):
                counts[table] = conn.execute(f"DELETE FROM {table} WHERE user_id=? AND dataset='demo'", params).rowcount
        return {'deleted': counts, 'message': 'Sample workspace cleared. Live records and other accounts were not changed.'}

    return router
