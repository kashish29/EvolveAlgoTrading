from typing import Optional, Any
from .abstract_data_source import AbstractDataSource
from .csv_data_source import CSVDataSource

# Configuration for CSV data source path can be managed here or passed through kwargs.
# For simplicity, we'll expect 'csv_directory_path' in kwargs for CSVDataSource.

class DataSourceFactory:
    """
    Factory class for creating instances of data sources.
    This factory allows for easy extension to support new data source types in the future.
    """

    def __init__(self):
        # Potentially load configurations here if not passed directly to get_data_source
        print("DataSourceFactory initialized.")
        self._creators = {} # For registering creators if we want a more extensible system

    def register_data_source_creator(self, source_type: str, creator_func: callable):
        """
        Registers a function that creates a data source instance.
        Example: factory.register_data_source_creator("API", lambda **kwargs: APIDataSource(**kwargs))
        """
        self._creators[source_type.upper()] = creator_func

    def get_data_source(self, source_type: str, **kwargs: Any) -> Optional[AbstractDataSource]:
        """
        Creates and returns a data source instance based on the specified type.

        Args:
            source_type (str): The type of data source to create (e.g., "CSV", "API").
                               Case-insensitive.
            **kwargs: Arbitrary keyword arguments that will be passed to the
                      constructor of the requested data source.
                      For "CSV" source_type, expects 'csv_directory_path'.

        Returns:
            Optional[AbstractDataSource]: An instance of the requested data source,
                                          or None if the type is not supported or
                                          creation fails.
        """
        source_type_upper = source_type.upper()
        
        if source_type_upper == "CSV":
            csv_directory_path = kwargs.get("csv_directory_path")
            if not csv_directory_path:
                print("DataSourceFactory Error: 'csv_directory_path' is required for CSVDataSource.")
                return None
            try:
                print(f"DataSourceFactory: Creating CSVDataSource with path: {csv_directory_path}")
                return CSVDataSource(csv_directory_path=str(csv_directory_path))
            except Exception as e:
                print(f"DataSourceFactory Error: Failed to create CSVDataSource: {e}")
                return None
        
        # Example for a registered creator (more advanced)
        # elif source_type_upper in self._creators:
        #     try:
        #         print(f"DataSourceFactory: Creating {source_type_upper} source using registered creator.")
        #         return self._creators[source_type_upper](**kwargs)
        #     except Exception as e:
        #         print(f"DataSourceFactory Error: Failed to create {source_type_upper} source via creator: {e}")
        #         return None

        else:
            print(f"DataSourceFactory Error: Data source type '{source_type}' is not supported.")
            return None

    def __repr__(self) -> str:
        supported_types = ["CSV"] + list(self._creators.keys())
        return f"<DataSourceFactory(supported_types={supported_types})>"
