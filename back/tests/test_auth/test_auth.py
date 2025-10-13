"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from unittest.mock import patch, MagicMock
from argon2.exceptions import VerifyMismatchError
from back.auth.auth import (
    authenticate_user,
    generate_access_token,
    validate_access_token,
)


class TestAuthenticateUser:
    """Test authenticate_user function."""

    @patch("back.auth.auth.generate_access_token")
    @patch("back.auth.auth.user_crud.get_by_username")
    @patch("back.auth.auth.get_db")
    def test_authenticate_user_valid_credentials(
        self,
        mock_get_db: MagicMock,
        mock_get_by_username: MagicMock,
        mock_generate_token: MagicMock,
    ) -> None:
        """Test authenticate_user with valid credentials."""
        # Setup mocks
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.password_hash = "hashed_password"
        mock_get_by_username.return_value = mock_user

        mock_generate_token.return_value = "valid_token"

        # Patch the ph object directly
        with patch("back.auth.auth.ph") as mock_ph:
            mock_ph.verify.return_value = None  # ph.verify returns None on success

            result = authenticate_user("testuser", "password")

            assert result == "valid_token"
            mock_get_by_username.assert_called_once_with(mock_db, "testuser")
            mock_ph.verify.assert_called_once_with("hashed_password", "password")
            mock_generate_token.assert_called_once_with(123)

    @patch("back.auth.auth.user_crud.get_by_username")
    @patch("back.auth.auth.get_db")
    def test_authenticate_user_invalid_user(
        self, mock_get_db: MagicMock, mock_get_by_username: MagicMock
    ) -> None:
        """Test authenticate_user with non-existent user."""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_by_username.return_value = None

        result = authenticate_user("nonexistent", "password")

        assert result is None
        mock_get_by_username.assert_called_once_with(mock_db, "nonexistent")

    @patch("back.auth.auth.user_crud.get_by_username")
    @patch("back.auth.auth.get_db")
    def test_authenticate_user_invalid_password(
        self, mock_get_db: MagicMock, mock_get_by_username: MagicMock
    ) -> None:
        """Test authenticate_user with invalid password."""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])

        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.password_hash = "hashed_password"
        mock_get_by_username.return_value = mock_user

        # Patch the ph object directly
        with patch("back.auth.auth.ph") as mock_ph:
            mock_ph.verify.side_effect = VerifyMismatchError("Password mismatch")

            result = authenticate_user("testuser", "wrong_password")

            assert result is None
            mock_ph.verify.assert_called_once_with("hashed_password", "wrong_password")

    def test_authenticate_user_none_username(self) -> None:
        """Test authenticate_user with None username."""
        result = authenticate_user(None, "password")
        assert result is None

    def test_authenticate_user_none_password(self) -> None:
        """Test authenticate_user with None password."""
        result = authenticate_user("username", None)
        assert result is None

    def test_authenticate_user_both_none(self) -> None:
        """Test authenticate_user with both None."""
        result = authenticate_user(None, None)
        assert result is None


class TestGenerateAccessToken:
    """Test generate_access_token function."""

    @patch("back.auth.auth.jwt.encode")
    @patch("back.auth.auth.datetime")
    def test_generate_access_token_success(
        self, mock_datetime: MagicMock, mock_jwt_encode: MagicMock
    ) -> None:
        """Test generate_access_token creates valid token."""
        from datetime import datetime, timezone

        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_jwt_encode.return_value = "encoded_token"

        result = generate_access_token(123)

        assert result == "encoded_token"
        mock_jwt_encode.assert_called_once()

        # Verify the payload structure
        call_args = mock_jwt_encode.call_args[0]
        payload = call_args[0]
        assert payload["sub"] == "user:123"
        assert "iat" in payload
        assert "exp" in payload

    @patch("back.auth.auth.jwt.encode")
    def test_generate_access_token_different_user_ids(
        self, mock_jwt_encode: MagicMock
    ) -> None:
        """Test generate_access_token with different user IDs."""
        mock_jwt_encode.return_value = "token"

        generate_access_token(456)

        call_args = mock_jwt_encode.call_args[0]
        payload = call_args[0]
        assert payload["sub"] == "user:456"


class TestValidateAccessToken:
    """Test validate_access_token function."""

    @patch("back.auth.auth.jwt.decode")
    @patch("back.auth.auth.datetime")
    def test_validate_access_token_valid(
        self, mock_datetime: MagicMock, mock_jwt_decode: MagicMock
    ) -> None:
        """Test validate_access_token with valid token."""
        from datetime import datetime, timezone

        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_payload: dict[str, str | int] = {
            "iat": 1672574400,  # Valid issued at time
            "exp": 1672576200,  # Valid expiration time
            "sub": "user:123",
        }
        mock_jwt_decode.return_value = mock_payload

        result = validate_access_token("valid_token")

        assert result == 123
        mock_jwt_decode.assert_called_once()

    @patch("back.auth.auth.jwt.decode")
    def test_validate_access_token_invalid_signature(
        self, mock_jwt_decode: MagicMock
    ) -> None:
        """Test validate_access_token with invalid signature."""
        from jwt.exceptions import InvalidTokenError

        mock_jwt_decode.side_effect = InvalidTokenError("Invalid signature")

        result = validate_access_token("invalid_token")

        assert result is None

    @patch("back.auth.auth.jwt.decode")
    @patch("back.auth.auth.datetime")
    def test_validate_access_token_expired(
        self, mock_datetime: MagicMock, mock_jwt_decode: MagicMock
    ) -> None:
        """Test validate_access_token with expired token."""
        from datetime import datetime, timezone

        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_payload: dict[str, str | int] = {
            "iat": 1672574400,
            "exp": 1672574300,  # Expired (before current time)
            "sub": "user:123",
        }
        mock_jwt_decode.return_value = mock_payload

        result = validate_access_token("expired_token")

        assert result is None

    @patch("back.auth.auth.jwt.decode")
    @patch("back.auth.auth.datetime")
    def test_validate_access_token_invalid_subject(
        self, mock_datetime: MagicMock, mock_jwt_decode: MagicMock
    ) -> None:
        """Test validate_access_token with invalid subject format."""
        from datetime import datetime, timezone

        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_payload: dict[str, str | int] = {
            "iat": 1672574400,
            "exp": 1672576200,
            "sub": "admin:123",  # Invalid prefix
        }
        mock_jwt_decode.return_value = mock_payload

        result = validate_access_token("invalid_subject_token")

        assert result is None

    @patch("back.auth.auth.jwt.decode")
    @patch("back.auth.auth.datetime")
    def test_validate_access_token_missing_fields(
        self, mock_datetime: MagicMock, mock_jwt_decode: MagicMock
    ) -> None:
        """Test validate_access_token with missing required fields."""
        from datetime import datetime, timezone

        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        # Missing 'exp' field
        mock_payload: dict[str, str | int] = {"iat": 1672574400, "sub": "user:123"}
        mock_jwt_decode.return_value = mock_payload

        result = validate_access_token("incomplete_token")

        assert result is None

    @patch("back.auth.auth.jwt.decode")
    @patch("back.auth.auth.datetime")
    def test_validate_access_token_future_issued_at(
        self, mock_datetime: MagicMock, mock_jwt_decode: MagicMock
    ) -> None:
        """Test validate_access_token with future issued at time."""
        from datetime import datetime, timezone

        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_payload: dict[str, str | int] = {
            "iat": 1672576200,  # Future time
            "exp": 1672578000,
            "sub": "user:123",
        }
        mock_jwt_decode.return_value = mock_payload

        result = validate_access_token("future_token")

        assert result is None
