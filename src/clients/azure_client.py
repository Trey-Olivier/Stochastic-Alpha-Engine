import pathlib
import os

from src.clients.client import Client

import backoff
import dotenv
import polars as pl
from adlfs import AzureBlobFileSystem 
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import (
    ServiceRequestError,
    ServiceResponseError,
    HttpResponseError)


class Azure_Client(Client):

    _BASEPATH = pathlib.Path(__file__).resolve().parent.parent.parent

    def __init__(self, config: dict):
            
            self._config = config

            dotenv.load_dotenv(dotenv_path=self._BASEPATH / "my_env" / ".env")
            self._connection_string    = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            self._account_url          = os.getenv("AZURE_ACCOUNT_URL")
            self._storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            self._storage_account_key  = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

    @staticmethod
    def _is_retryable(e):
        # Retry network + transient issues
        if isinstance(e, (ServiceRequestError, ServiceResponseError)):
            return True
    
        # Retry throttling (429)
        if isinstance(e, HttpResponseError) and e.status_code == 429:
            return True

        return False
    
    def connect(self) -> None:
        """Connect to Azure Storage 
        using multiple authentication 
        methods with backoff retries."""

        self._logger.info("Attempting connection to Azure...")
        
        try: #Storage Account Credentials
            self._azure_client = AzureBlobFileSystem(
                account_name=self._storage_account_name,
                credential=DefaultAzureCredential())
            self._connected = True
            return

        except Exception as e:
            self._logger.error(f"Azure Credentials Error:\n{e}" 
            "\nAttempting connection via Connection String...")
        
        try: #Connection String
            self._azure_client = AzureBlobFileSystem(
                connection_string=self._connection_string)
            self._connected = True
            return
        
        except Exception as e:
            self._logger.error(f"Azure Connection String Failed:\n{e}"
            "\n Attempting connection via Account Key...")
        
        try: #Account Key
            self._azure_client = AzureBlobFileSystem(
                account_name=self._storage_account_name,
                account_key=self._storage_account_key)
            self._connected = True
            return
        
        except Exception as e:
             self._logger.critical("No forms of Client Connection Worked! Ending Program.")
             raise
        
    #Backoff On Connection Error to prevent Throttle
    @backoff.on_exception(
        backoff.expo,
        (ServiceRequestError, ServiceResponseError, HttpResponseError),
        max_tries=5,
        jitter=backoff.full_jitter,
        giveup=lambda e: not Azure_Client._is_retryable(e))
    
    def health_check(self) -> bool:
        """Checks if the Azure Client is connected."""
        if(self._azure_client is not None):
            try:
                self._azure_client.ls("")
                return True
            
            except Exception as e: 
                self._logger.error(f"connection to Azure failed:\n{e}\nretrying...")
                raise
        
        else: 
            self._logger.critical("Azure Client has not been Initialized, Stopping Program...")
            raise

    #Backoff On Connection Error to prevent Throttle
    @backoff.on_exception(
        backoff.expo,
        (ServiceRequestError, ServiceResponseError, HttpResponseError),
        max_tries=5,
        jitter=backoff.full_jitter,
        giveup=lambda e: not Azure_Client._is_retryable(e))
    
    async def upload(self, metadata: dict):
        """Uploads a file to Azure Storage."""
        try:
            self._azure_client.upload(metadata["local_path"], metadata["remote_path"])
            self._logger.info(f"Successfully uploaded {metadata['local_path']} to {metadata['remote_path']}")
        
        except Exception as e:
            self._logger.error(f"Failed to upload {metadata['local_path']} to Azure:\n{e}\nRetrying...")
            raise

    #Backoff On Connection Error to prevent Throttle
    @backoff.on_exception(
        backoff.expo,
        (ServiceRequestError, ServiceResponseError, HttpResponseError),
        max_tries=5,
        jitter=backoff.full_jitter,
        giveup=lambda e: not Azure_Client._is_retryable(e))
    
    async def load_into_memory(self, metadata: dict) -> pl.LazyFrame:
        """Loads a file from Azure Storage into memory as a Polars Lazyframe."""
        try:
            with self._azure_client.open(metadata["remote_path"], "rb") as f:
                lf = pl.read_parquet(f).lazy()
                self._logger.info(f"Successfully loaded {metadata['remote_path']} into memory")
                
                return lf
        
        except Exception as e:
            
            self._logger.error(f"Failed to load {metadata['remote_path']} from Azure:\n{e}\nRetrying...")
            raise

    def is_connected(self):
        return self._connected
    
    

    
            
        

        
             
        

        
        

        
             
            
        
        

    