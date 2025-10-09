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

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from back.auth.dependency import get_user_id, oauth2_scheme


class TestGetUserId:
    """Test get_user_id dependency function."""

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_valid_token(self, mock_validate_token: MagicMock) -> None:
        """Test get_user_id with valid token."""
        mock_validate_token.return_value = 123

        # Run async function synchronously
        result = asyncio.run(get_user_id("valid_token"))

        assert result == 123
        mock_validate_token.assert_called_once_with("valid_token")

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_invalid_token(self, mock_validate_token: MagicMock) -> None:
        """Test get_user_id with invalid token."""
        mock_validate_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_user_id("invalid_token"))

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Access token invalid"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
        mock_validate_token.assert_called_once_with("invalid_token")

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_expired_token(self, mock_validate_token: MagicMock) -> None:
        """Test get_user_id with expired token."""
        mock_validate_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_user_id("expired_token"))

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Access token invalid"

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_validate_raises_exception(
        self, mock_validate_token: MagicMock
    ) -> None:
        """Test get_user_id when validate_access_token raises exception."""
        mock_validate_token.side_effect = Exception("Token validation error")

        with pytest.raises(Exception, match="Token validation error"):
            asyncio.run(get_user_id("problematic_token"))

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_empty_token(self, mock_validate_token: MagicMock) -> None:
        """Test get_user_id with empty token."""
        mock_validate_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_user_id(""))

        assert exc_info.value.status_code == 401
        mock_validate_token.assert_called_once_with("")

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_different_user_ids(
        self, mock_validate_token: MagicMock
    ) -> None:
        """Test get_user_id returns different user IDs correctly."""
        # Test with different user IDs
        test_cases = [1, 42, 999, 12345]

        for user_id in test_cases:
            mock_validate_token.return_value = user_id
            result = asyncio.run(get_user_id(f"token_for_user_{user_id}"))
            assert result == user_id

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_none_token(self, mock_validate_token: MagicMock) -> None:
        """Test get_user_id with None token."""
        mock_validate_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_user_id(None))  # type: ignore # pyright: ignore[reportArgumentType]

        assert exc_info.value.status_code == 401
        mock_validate_token.assert_called_once_with(None)

    @patch("back.auth.dependency.validate_access_token")
    def test_get_user_id_zero_user_id(self, mock_validate_token: MagicMock) -> None:
        """Test get_user_id returns zero user ID correctly."""
        mock_validate_token.return_value = 0

        result = asyncio.run(get_user_id("token_for_user_0"))

        assert result == 0
        mock_validate_token.assert_called_once_with("token_for_user_0")


class TestOAuth2Scheme:
    def test_oauth2_scheme_type(self) -> None:
        """Test that oauth2_scheme is correct type."""
        from fastapi.security import OAuth2PasswordBearer

        assert isinstance(oauth2_scheme, OAuth2PasswordBearer)

    def test_oauth2_scheme_scheme_name(self) -> None:
        """Test that oauth2_scheme has correct scheme name."""
        assert oauth2_scheme.scheme_name == "OAuth2PasswordBearer"

    def test_oauth2_scheme_auto_error_default(self) -> None:
        """Test that oauth2_scheme has correct default auto_error setting."""
        # OAuth2PasswordBearer should have auto_error=True by default
        assert oauth2_scheme.auto_error is True

    def test_oauth2_scheme_callable(self) -> None:
        """Test that oauth2_scheme is callable."""
        assert callable(oauth2_scheme)
