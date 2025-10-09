"""
Test git security - verify .env files are not tracked
"""
import subprocess
import os
import pytest


def test_env_files_not_in_git():
    """Verify that .env files are not tracked in git"""
    # Get list of tracked files
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )

    tracked_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

    # Check for .env files (except .env.example)
    forbidden_patterns = ['.env', 'backend/.env.dev', 'infra/.env']
    found_env_files = []

    for file in tracked_files:
        if file.endswith('.env') and file != '.env.example':
            found_env_files.append(file)
        if file.endswith('.env.dev') or file.endswith('infra/.env'):
            found_env_files.append(file)

    assert len(found_env_files) == 0, f"Found tracked .env files: {found_env_files}. These should not be in git!"


def test_gitignore_contains_env_patterns():
    """Verify .gitignore has proper .env patterns"""
    gitignore_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '.gitignore'
    )

    with open(gitignore_path, 'r') as f:
        content = f.read()

    # Check for essential patterns
    required_patterns = [
        '.env',
        '.env.*',
        'backend/.env',
        'infra/.env'
    ]

    for pattern in required_patterns:
        assert pattern in content, f".gitignore missing pattern: {pattern}"

    # Verify .env.example is not ignored (should have !.env.example)
    assert '!.env.example' in content or '.env.example' not in content


def test_env_example_exists():
    """Verify .env.example exists as a template"""
    env_example = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '.env.example'
    )

    assert os.path.exists(env_example), ".env.example should exist as a template"


def test_no_secrets_in_env_example():
    """Verify .env.example doesn't contain real secrets"""
    env_example = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '.env.example'
    )

    with open(env_example, 'r') as f:
        content = f.read()

    # Check that API keys are empty or contain placeholders
    forbidden_values = [
        'sk-',  # OpenAI API key prefix
        'Bearer ',  # Auth tokens
    ]

    for forbidden in forbidden_values:
        assert forbidden not in content, f".env.example contains potential secret: {forbidden}"

    # Verify it has placeholder patterns
    assert 'SECRET_KEY=dev-secret-change-me' in content or 'SECRET_KEY=' in content
    assert 'OPENAI_API_KEY=' in content
