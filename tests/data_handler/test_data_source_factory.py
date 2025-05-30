import unittest
from unittest.mock import patch, MagicMock

from src.data_handler.data_source_factory import DataSourceFactory
from src.data_handler.csv_data_source import CSVDataSource
from src.data_handler.abstract_data_source import AbstractDataSource

class TestDataSourceFactory(unittest.TestCase):

    def setUp(self):
        self.factory = DataSourceFactory()
        self.test_csv_dir = "/fake/csv/path"

    def test_get_data_source_csv_success(self):
        # We patch CSVDataSource to check if it's called correctly,
        # not to test CSVDataSource itself (that's done in its own test file).
        with patch('src.data_handler.data_source_factory.CSVDataSource', spec=CSVDataSource) as MockCSVDataSource:
            # Configure the mock constructor to return a mock instance
            mock_csv_instance = MockCSVDataSource.return_value 
            
            data_source = self.factory.get_data_source(
                "CSV", 
                csv_directory_path=self.test_csv_dir
            )
            
            self.assertIsNotNone(data_source)
            # self.assertIsInstance(data_source, AbstractDataSource) # This will check against the real AbstractDataSource
            self.assertTrue(isinstance(data_source, AbstractDataSource)) # Check if it's an instance of the mock's spec or real one
            MockCSVDataSource.assert_called_once_with(csv_directory_path=self.test_csv_dir)
            self.assertIs(data_source, mock_csv_instance)


    def test_get_data_source_csv_success_case_insensitive(self):
        with patch('src.data_handler.data_source_factory.CSVDataSource', spec=CSVDataSource) as MockCSVDataSource:
            self.factory.get_data_source("csv", csv_directory_path=self.test_csv_dir)
            MockCSVDataSource.assert_called_once_with(csv_directory_path=self.test_csv_dir)

            # Reset mock for the next call in the same test if needed, or make separate tests.
            # For this structure, subsequent calls accumulate. Let's make it count based.
            current_call_count = MockCSVDataSource.call_count
            self.factory.get_data_source("CsV", csv_directory_path=self.test_csv_dir)
            self.assertEqual(MockCSVDataSource.call_count, current_call_count + 1)


    def test_get_data_source_csv_missing_path(self):
        data_source = self.factory.get_data_source("CSV") # Missing csv_directory_path
        self.assertIsNone(data_source)

        data_source_with_none_path = self.factory.get_data_source("CSV", csv_directory_path=None)
        self.assertIsNone(data_source_with_none_path)
        
    def test_get_data_source_csv_creation_exception(self):
        # Test scenario where CSVDataSource constructor raises an exception
        with patch('src.data_handler.data_source_factory.CSVDataSource', side_effect=ValueError("Test Exception")) as MockCSVDataSource:
            data_source = self.factory.get_data_source("CSV", csv_directory_path=self.test_csv_dir)
            self.assertIsNone(data_source)
            MockCSVDataSource.assert_called_once_with(csv_directory_path=self.test_csv_dir)


    def test_get_data_source_unsupported_type(self):
        data_source = self.factory.get_data_source("API_XYZ") # Assuming API_XYZ is not supported
        self.assertIsNone(data_source)

    def test_get_data_source_unsupported_type_with_kwargs(self):
        data_source = self.factory.get_data_source("API_XYZ", api_key="testkey")
        self.assertIsNone(data_source)
        
    # Example for testing a registered creator, if that functionality was more developed
    # def test_get_data_source_with_registered_creator(self):
    #     mock_creator_func = MagicMock(return_value=MagicMock(spec=AbstractDataSource))
    #     self.factory.register_data_source_creator("CUSTOM", mock_creator_func)
        
    #     custom_source = self.factory.get_data_source("CUSTOM", arg1="val1")
        
    #     self.assertIsNotNone(custom_source)
    #     mock_creator_func.assert_called_once_with(arg1="val1")
    #     self.assertIsInstance(custom_source, AbstractDataSource)


if __name__ == '__main__':
    unittest.main()
