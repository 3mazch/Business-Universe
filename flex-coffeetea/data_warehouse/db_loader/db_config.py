# -*- coding: utf-8 -*-
"""SQL Server connection factory for the FlexCoffeeTea DB Loader."""

import os
import sys
import pyodbc
from pathlib import Path

try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
    else:
        _root_env = Path(__file__).parent.parent.parent / ".env"
        if _root_env.exists():
            load_dotenv(_root_env)
except ImportError:
    pass

_SERVER = os.environ.get("DB_SERVER", "localhost").strip()
_DB = os.environ.get("DB_NAME", "FlexCoffeeTea").strip()
_USER = os.environ.get("DB_USER", "").strip()
_PASS = os.environ.get("DB_PASSWORD", "")
_TRUSTED_SETTING = os.environ.get("DB_TRUSTED")
_TRUSTED = (
    _TRUSTED_SETTING.lower() in ("yes", "true", "1")
    if _TRUSTED_SETTING is not None
    else not (_USER or _PASS)
)
_PORT = os.environ.get("DB_PORT", "").strip()
_DRIVER = os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server").strip()


def _pick_driver() -> str:
    """Auto-select an available ODBC driver if the configured one is missing."""
    available = pyodbc.drivers()
    if _DRIVER in available:
        return _DRIVER
    for candidate in (
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ):
        if candidate in available:
            print(f"[db_config] Using driver: {candidate}")
            return candidate
    raise RuntimeError(
        f"No suitable ODBC driver found. Installed drivers: {available}\n"
        "Install Microsoft ODBC Driver 17 or 18 for SQL Server."
    )


def _connection_string(driver: str, server: str | None = None) -> str:
    """Build a connection string for the selected authentication mode."""
    endpoint = server or _SERVER
    if _PORT:
        if "\\" in endpoint:
            raise ValueError("Set either DB_PORT or a named-instance DB_SERVER, not both.")
        endpoint = f"{endpoint},{_PORT}"

    def quote(value: str) -> str:
        return "{" + value.replace("}", "}}") + "}"

    parts = [
        f"DRIVER={quote(driver)}",
        f"SERVER={quote(endpoint)}",
        f"DATABASE={quote(_DB)}",
    ]
    if _TRUSTED:
        parts.append("Trusted_Connection=yes")
    else:
        if not _USER or not _PASS:
            raise ValueError(
                "Set DB_USER and DB_PASSWORD in .env, "
                "or set DB_TRUSTED=yes for Windows Authentication."
            )
        parts.extend((f"UID={quote(_USER)}", f"PWD={quote(_PASS)}"))
    parts.append("TrustServerCertificate=yes")
    return ";".join(parts) + ";"


def get_connection(autocommit: bool = False) -> pyodbc.Connection:
    """Return a pyodbc connection using the configured authentication mode."""
    driver = _pick_driver()
    conn = pyodbc.connect(
        _connection_string(driver),
        autocommit=autocommit,
        timeout=5,
    )
    conn.setdecoding(pyodbc.SQL_CHAR, encoding="utf-8")
    conn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-8")
    conn.setencoding(encoding="utf-8")
    return conn


def test_connection() -> bool:
    """Check connectivity to the configured database and report the endpoint."""
    driver = _pick_driver()
    endpoints = [("Configured endpoint", _SERVER)]
    if not _PORT:
        endpoints.append(("Named Pipe", f"np:{_SERVER}"))

    for label, server in endpoints:
        try:
            conn = pyodbc.connect(
                _connection_string(driver, server),
                autocommit=True,
                timeout=5,
            )
            try:
                cur = conn.cursor()
                cur.execute("SELECT @@VERSION, @@SERVERNAME, DB_NAME()")
                row = cur.fetchone()
                version = row[0].split("\n")[0]
                print(
                    f"[db_config] Connected via {label} | "
                    f"Server: {row[1]} | DB: {row[2]}"
                )
                print(f"[db_config] {version}")
                return True
            finally:
                conn.close()
        except (pyodbc.Error, ValueError) as exc:
            print(f"[db_config] {label} failed: {str(exc)[:120]}")

    print("\n[db_config] All connection strategies failed.")
    print("[db_config] Check that SQL Server is running and DB_SERVER identifies the instance.")
    print("[db_config] For a local default instance, leave DB_PORT unset.")
    print("[db_config] For Windows Authentication, set DB_TRUSTED=yes.")
    print("[db_config] For SQL Authentication, set DB_USER and DB_PASSWORD.")
    return False


if __name__ == "__main__":
    sys.exit(0 if test_connection() else 1)
