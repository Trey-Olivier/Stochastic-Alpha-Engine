import os
import pathlib
import asyncio

from src.clients.client import Client

import backoff
import dotenv
import wrds
import polars as pl

class WRDS_Client(Client):
    
    _BASEPATH = pathlib.Path(__file__).resolve().parent.parent.parent

    def __init__(self, config: dict) -> None:
        
        self._config = config

        dotenv.load_dotenv(dotenv_path=self._BASEPATH / "my_env" / ".env")
        self._wrds_username        = os.getenv("WRDS_USERNAME")
        self._wrds_password        = os.getenv("WRDS_PASSWORD")

    @staticmethod
    def _is_retryable_wrds_error(e: Exception) -> bool:
        msg = str(e).lower()

        # --- Retryable network / connection issues ---
        retryable_keywords = [
        "early eof",
        "connection reset",
        "broken pipe",
        "timeout",
        "timed out",
        "server closed the connection",
        "connection aborted",
        "connection refused",]

        if any(k in msg for k in retryable_keywords):
            return True

        # --- Known transient Python exceptions ---
        if isinstance(e, (ConnectionError, TimeoutError, OSError)):
            return True

        # --- Database driver transient errors (generic fallback) ---
        # Some psycopg2 errors may fall here but are often retryable if not SQL-related
        if "could not connect" in msg:
            return True

        return False
    
    def is_connected(self):
        return self._connected
    
    def connect(self):
        try:
            self._logger.info("Attempting connection to wrds...")
            self._client = wrds.Connection(wrds_username=self._wrds_username)
            self._connected = True

        except Exception as e:
            self._logger.critical(f"WRDS COULD NOT CONNECT:\n{e} \nSHUTTING DOWN")
            raise
    
    def disconnect(self):
        self._wrds_client.close()
        self._connected = False

    @backoff.on_exception(
    backoff.expo,
    Exception,
    max_tries=5,
    jitter=backoff.full_jitter,
    giveup=lambda e: not WRDS_Client._is_retryable_wrds_error(e))

    def download(self, query: str):
        
        try:

            self._logger.trace("attempting download from WRDS...")
            df = self._client.raw_sql(query)

            if df.empty:
                self._logger.warning("query returned an empty dataframe")
            
            return pl.from_pandas(df)
        
        except Exception as e:

            self._logger.error(f"Wrds Download Failed:\n{e}")



    

    
    

        
        