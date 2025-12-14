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

from typing import Any, List
from unittest.mock import Mock


def create_mock_db_session() -> Mock:
    """
    Create a mock database session with common methods.

    Returns:
        Mock: A configured mock database session.
    """
    mock_db = Mock()
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.delete = Mock()
    mock_db.refresh = Mock()
    mock_db.flush = Mock()
    mock_db.rollback = Mock()
    mock_db.close = Mock()
    return mock_db


def create_mock_query_result(return_value: Any) -> Mock:
    """
    Create a mock query chain that returns a specific value.

    Args:
        return_value: The value to return from the query.

    Returns:
        Mock: A configured mock query object.
    """
    mock_query = Mock()
    mock_filter = Mock()
    mock_filter.first.return_value = return_value
    mock_query.filter.return_value = mock_filter
    return mock_query


def create_mock_query_all(return_values: List[Any]) -> Mock:
    """
    Create a mock query chain that returns multiple values.

    Args:
        return_values: The list of values to return from the query.

    Returns:
        Mock: A configured mock query object.
    """
    mock_query = Mock()
    mock_filter = Mock()
    mock_filter.all.return_value = return_values
    mock_query.filter.return_value = mock_filter
    return mock_query


def create_mock_paginated_query(items: List[Any], total: int) -> tuple[Mock, Mock]:
    """
    Create mock query chains for paginated results.

    Args:
        items: The list of items to return.
        total: The total count to return.

    Returns:
        tuple: (count_query_mock, data_query_mock)
    """
    # Mock for count query
    mock_count_query = Mock()
    mock_count_filter = Mock()
    mock_count_filter.scalar.return_value = total
    mock_count_query.filter.return_value = mock_count_filter

    # Mock for data query
    mock_data_query = Mock()
    mock_data_filter = Mock()
    mock_order = Mock()
    mock_offset = Mock()
    mock_limit = Mock()

    mock_limit.all.return_value = items
    mock_offset.limit.return_value = mock_limit
    mock_order.offset.return_value = mock_offset
    mock_data_filter.order_by.return_value = mock_order
    mock_data_query.filter.return_value = mock_data_filter

    return mock_count_query, mock_data_query


def create_mock_query_count(count: int) -> Mock:
    """
    Create a mock query chain that returns a count.

    Args:
        count: The count to return.

    Returns:
        Mock: A configured mock query object.
    """
    mock_query = Mock()
    mock_query.count.return_value = count
    return mock_query


def setup_mock_db_add_with_id(mock_db: Mock, id_value: int = 1) -> None:
    """
    Configure a mock database to set ID on objects when refresh is called.

    Args:
        mock_db: The mock database session.
        id_value: The ID value to assign.
    """

    def mock_refresh(obj: Any) -> None:
        obj.id = id_value

    mock_db.refresh.side_effect = mock_refresh
