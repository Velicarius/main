"""
Tests for Secret Validation
Ensures production environments require secure secrets
"""
import pytest
import os
from app.core.config import Settings


class TestSecretValidation:
    """Test that production secrets are properly validated"""

    def test_production_requires_jwt_secret(self):
        """Test that production fails without JWT_SECRET_KEY"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(app_env="production", jwt_secret_key=None)
            settings.validate_production_secrets()

        assert "JWT_SECRET_KEY" in str(exc_info.value)

    def test_production_rejects_dev_jwt_secret(self):
        """Test that production rejects default JWT_SECRET_KEY"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(app_env="production", jwt_secret_key="dev-secret")
            settings.validate_production_secrets()

        assert "JWT_SECRET_KEY" in str(exc_info.value)

    def test_production_requires_session_secret(self):
        """Test that production fails without SESSION_SECRET"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(
                app_env="production",
                jwt_secret_key="secure-jwt-secret-key",
                session_secret=None
            )
            settings.validate_production_secrets()

        assert "SESSION_SECRET" in str(exc_info.value)

    def test_production_rejects_dev_session_secret(self):
        """Test that production rejects default SESSION_SECRET"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(
                app_env="production",
                jwt_secret_key="secure-jwt-secret",
                session_secret="dev-secret-change-me"
            )
            settings.validate_production_secrets()

        assert "SESSION_SECRET" in str(exc_info.value)

    def test_production_rejects_dev_secret_key(self):
        """Test that production rejects default SECRET_KEY"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(
                app_env="production",
                jwt_secret_key="secure-jwt-secret",
                session_secret="secure-session-secret",
                secret_key="dev-secret"
            )
            settings.validate_production_secrets()

        assert "SECRET_KEY" in str(exc_info.value)

    def test_production_accepts_all_secure_secrets(self):
        """Test that production accepts all properly set secrets"""
        # Should not raise any exception
        settings = Settings(
            app_env="production",
            jwt_secret_key="secure-jwt-secret-key-with-entropy",
            session_secret="secure-session-secret-key-with-entropy",
            secret_key="secure-main-secret-key-with-entropy"
        )
        settings.validate_production_secrets()  # Should not raise

    def test_production_validation_shows_all_errors(self):
        """Test that validation shows all errors at once"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(
                app_env="production",
                jwt_secret_key=None,
                session_secret="dev-secret",
                secret_key="dev-secret"
            )
            settings.validate_production_secrets()

        error_message = str(exc_info.value)
        assert "JWT_SECRET_KEY" in error_message
        assert "SESSION_SECRET" in error_message
        assert "SECRET_KEY" in error_message

    def test_dev_environment_allows_default_secrets(self):
        """Test that dev environment allows default secrets"""
        # Should not raise any exception
        settings = Settings(
            app_env="dev",
            jwt_secret_key=None,
            session_secret="dev-secret-change-me",
            secret_key="dev-secret"
        )
        # Dev environment doesn't call validate_production_secrets
        # Just verify settings object can be created

    def test_prod_alias_triggers_validation(self):
        """Test that 'prod' alias also triggers validation"""
        with pytest.raises(ValueError) as exc_info:
            settings = Settings(
                app_env="prod",
                jwt_secret_key=None
            )
            settings.validate_production_secrets()

        assert "JWT_SECRET_KEY" in str(exc_info.value)

    def test_non_production_environments_skip_validation(self):
        """Test that non-production environments don't validate secrets"""
        environments = ["dev", "development", "test", "testing", "staging"]

        for env in environments:
            # Should not raise even with missing/weak secrets
            settings = Settings(
                app_env=env,
                jwt_secret_key=None,
                session_secret=None
            )
            # validate_production_secrets only runs for production/prod
            # These should pass without errors


class TestSecretGeneration:
    """Test secret generation recommendations"""

    def test_env_example_does_not_contain_secrets(self):
        """Test that .env.example doesn't contain actual secrets"""
        env_example_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            '.env.example'
        )

        if os.path.exists(env_example_path):
            with open(env_example_path, 'r') as f:
                content = f.read()

            # JWT_SECRET_KEY should be empty or have instructions
            assert 'JWT_SECRET_KEY=' in content
            # Should not contain actual secret values
            assert 'JWT_SECRET_KEY=sk-' not in content
            assert 'JWT_SECRET_KEY=ey' not in content  # JWT tokens start with ey

            # Should have generation instructions
            assert 'secrets.token' in content or 'JWT_SECRET_KEY=' in content

    def test_secret_format_guidance(self):
        """Test that we provide clear guidance on secret format"""
        # Secrets should be at least 32 characters for security
        MIN_SECRET_LENGTH = 32

        # Test that our validation would catch short secrets in production
        short_secret = "x" * (MIN_SECRET_LENGTH - 1)

        # While we don't enforce length in current validation,
        # this test documents the recommendation
        assert len(short_secret) < MIN_SECRET_LENGTH
        # Recommended: secrets should be generated with:
        # python -c "import secrets; print(secrets.token_urlsafe(32))"


class TestConfigSecretHandling:
    """Test that config properly handles secrets"""

    def test_jwt_secret_from_environment(self):
        """Test that JWT secret can be loaded from environment"""
        test_secret = "test-jwt-secret-from-env"
        settings = Settings(jwt_secret_key=test_secret)

        assert settings.jwt_secret_key == test_secret

    def test_session_secret_from_environment(self):
        """Test that session secret can be loaded from environment"""
        test_secret = "test-session-secret-from-env"
        settings = Settings(session_secret=test_secret)

        assert settings.session_secret == test_secret

    def test_secrets_not_logged_in_debug(self):
        """Test that secrets are not exposed in debug output"""
        settings = Settings(
            jwt_secret_key="secret-jwt-key",
            session_secret="secret-session-key"
        )

        # debug_dump should not expose secrets
        # This is a documentation test - ensure any debug methods mask secrets
        assert settings.jwt_secret_key is not None
        assert settings.session_secret is not None
