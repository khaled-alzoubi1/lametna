import os
import sys
import subprocess
import pytest

# Helper to run a short script that imports app and prints success
def run_app_import(env_vars):
    env = os.environ.copy()
    env.update(env_vars)
    # python script that imports app
    script = '''
import sys
try:
    import app
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'''
    result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True)
    return result

def test_production_config_validation_passes():
    res = run_app_import({
        'FLASK_ENV': 'production',
        'SECRET_KEY': 'test_secret_key_12345',
        'DATABASE_URL': 'sqlite:///:memory:'
    })
    assert res.returncode == 0
    assert 'SUCCESS' in res.stdout

def test_production_missing_secret_key_fails():
    env = {
        'FLASK_ENV': 'production',
        'DATABASE_URL': 'sqlite:///:memory:'
    }
    # ensure SECRET_KEY is not in env
    if 'SECRET_KEY' in os.environ:
        del os.environ['SECRET_KEY']
        
    res = run_app_import(env)
    assert res.returncode == 1
    assert 'SECRET_KEY environment variable is missing' in res.stdout
    assert 'test_secret_key' not in res.stdout

def test_production_missing_database_url_fails():
    env = {
        'FLASK_ENV': 'production',
        'SECRET_KEY': 'test_secret_key_12345'
    }
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
        
    res = run_app_import(env)
    assert res.returncode == 1
    assert 'DATABASE_URL environment variable is missing' in res.stdout

def test_development_config_succeeds_without_env_vars():
    env = {
        'FLASK_ENV': 'development'
    }
    if 'SECRET_KEY' in os.environ:
        del os.environ['SECRET_KEY']
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
        
    res = run_app_import(env)
    assert res.returncode == 0
    assert 'SUCCESS' in res.stdout