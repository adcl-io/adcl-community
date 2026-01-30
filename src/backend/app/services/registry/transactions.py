# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Transaction Logger

Single responsibility: Log and retrieve transactions (append-only JSONL)
"""

import json
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

from app.models.registry_models import (
    TransactionRecord,
    TransactionOperation,
    TransactionStatus
)

logger = logging.getLogger(__name__)


class TransactionLogger:
    """Manages transaction logging to append-only JSONL file"""

    def __init__(self, log_file: Path):
        """
        Initialize transaction logger.

        Args:
            log_file: Path to transactions.jsonl
        """
        self.log_file = log_file

        # Ensure log file exists
        if not self.log_file.exists():
            self.log_file.touch()

    def create_transaction(
        self,
        operation: TransactionOperation,
        package_name: str,
        version: Optional[str] = None
    ) -> TransactionRecord:
        """
        Create a new transaction record.

        Args:
            operation: Type of operation
            package_name: Package name
            version: Package version

        Returns:
            New transaction record
        """
        return TransactionRecord(
            id=f"txn-{uuid.uuid4().hex[:12]}",
            operation=operation,
            package_name=package_name,
            version=version,
            status=TransactionStatus.PENDING,
            started_at=datetime.now(UTC)
        )

    def log(self, transaction: TransactionRecord):
        """
        Append transaction to JSONL log file.

        Args:
            transaction: Transaction record to log
        """
        log_line = json.dumps(transaction.to_dict())
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def list_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent transactions from log.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction records (most recent first)
        """
        if not self.log_file.exists():
            return []

        transactions = []
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    txn = json.loads(line.strip())
                    transactions.append(txn)
                except Exception as e:
                    logger.error(f"Failed to parse transaction log line: {e}")

        # Return most recent first
        return list(reversed(transactions[-limit:]))

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction record or None if not found
        """
        if not self.log_file.exists():
            return None

        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    txn = json.loads(line.strip())
                    if txn.get("id") == transaction_id:
                        return txn
                except Exception:
                    pass

        return None
