"""
CSV Parser Module

Handles reading and parsing CSV files containing Instagram reel URLs.
Provides validation, deduplication, and error handling.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pandas as pd
from loguru import logger

from config import InputConfig
from utils import validate_instagram_url, extract_reel_id


class CSVParser:
    """
    Parser for CSV files containing Instagram reel URLs.
    
    Features:
    - Read CSV files with custom column selection
    - Validate Instagram URLs
    - Deduplicate URLs
    - Skip already processed URLs
    - Comprehensive error handling
    """
    
    def __init__(self, config: InputConfig, processed_urls: Optional[set] = None):
        """
        Initialize CSV parser.
        
        Args:
            config: Input configuration
            processed_urls: Set of already processed URLs (for resume capability)
        """
        self.config = config
        self.processed_urls = processed_urls or set()
        
        logger.info(f"CSV Parser initialized")
        logger.info(f"CSV path: {config.csv_path}")
        logger.info(f"URL column: {config.url_column}")
        logger.info(f"Skip processed: {config.skip_processed}")
    
    def parse(self) -> Tuple[List[Dict], Dict]:
        """
        Parse CSV file and return list of valid URLs with metadata.
        
        Returns:
            Tuple of (list of URL records, statistics dict)
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV is invalid or URL column not found
        """
        logger.info("Starting CSV parsing...")
        
        # Check if file exists
        csv_path = Path(self.config.csv_path)
        if not csv_path.exists():
            error_msg = f"CSV file not found: {self.config.csv_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Read CSV file
        try:
            df = self._read_csv(csv_path)
        except Exception as e:
            error_msg = f"Failed to read CSV file: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate URL column exists
        if self.config.url_column not in df.columns:
            error_msg = f"URL column '{self.config.url_column}' not found in CSV"
            logger.error(f"{error_msg}. Available columns: {list(df.columns)}")
            raise ValueError(error_msg)
        
        # Process URLs
        url_records, stats = self._process_urls(df)
        
        # Log statistics
        self._log_statistics(stats)
        
        logger.info(f"CSV parsing complete: {len(url_records)} valid URLs ready")
        
        return url_records, stats
    
    def _read_csv(self, csv_path: Path) -> pd.DataFrame:
        """
        Read CSV file with pandas.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            DataFrame with CSV contents
        """
        logger.debug(f"Reading CSV file: {csv_path}")
        
        # Try different encodings if UTF-8 fails
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                logger.debug(f"CSV read successfully with {encoding} encoding")
                logger.debug(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
                logger.debug(f"Columns: {list(df.columns)}")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Failed to read CSV with {encoding}: {e}")
                continue
        
        # If all encodings fail
        raise ValueError("Failed to read CSV with any supported encoding")
    
    def _process_urls(self, df: pd.DataFrame) -> Tuple[List[Dict], Dict]:
        """
        Process and validate URLs from DataFrame.
        
        Args:
            df: DataFrame containing URLs
            
        Returns:
            Tuple of (list of valid URL records, statistics dict)
        """
        url_records = []
        stats = {
            'total_rows': len(df),
            'valid_urls': 0,
            'invalid_urls': 0,
            'duplicate_urls': 0,
            'already_processed': 0,
            'final_count': 0
        }
        
        seen_urls = set()
        seen_reel_ids = set()
        
        logger.info(f"Processing {stats['total_rows']} rows from CSV...")
        
        for idx, row in df.iterrows():
            try:
                # Get URL from specified column
                url = str(row[self.config.url_column]).strip()
                
                # Skip empty URLs
                if pd.isna(url) or url == '' or url.lower() == 'nan':
                    logger.debug(f"Row {idx}: Empty URL, skipping")
                    stats['invalid_urls'] += 1
                    continue
                
                # Validate URL format
                if self.config.validate_urls:
                    if not validate_instagram_url(url):
                        logger.debug(f"Row {idx}: Invalid Instagram URL: {url}")
                        stats['invalid_urls'] += 1
                        continue
                
                # Extract reel ID
                reel_id = extract_reel_id(url)
                if not reel_id:
                    logger.debug(f"Row {idx}: Could not extract reel ID from: {url}")
                    stats['invalid_urls'] += 1
                    continue
                
                # Check for duplicates within this CSV
                if url in seen_urls or reel_id in seen_reel_ids:
                    logger.debug(f"Row {idx}: Duplicate URL/reel ID: {reel_id}")
                    stats['duplicate_urls'] += 1
                    continue
                
                # Check if already processed (from previous runs)
                if self.config.skip_processed and url in self.processed_urls:
                    logger.debug(f"Row {idx}: Already processed: {reel_id}")
                    stats['already_processed'] += 1
                    continue
                
                # URL is valid, add to results
                url_record = {
                    'url': url,
                    'reel_id': reel_id,
                    'row_index': idx,
                }
                
                # Add any additional columns as metadata
                for col in df.columns:
                    if col != self.config.url_column:
                        url_record[col] = row[col] if not pd.isna(row[col]) else None
                
                url_records.append(url_record)
                seen_urls.add(url)
                seen_reel_ids.add(reel_id)
                stats['valid_urls'] += 1
                
            except Exception as e:
                logger.warning(f"Row {idx}: Error processing row: {e}")
                stats['invalid_urls'] += 1
                continue
        
        stats['final_count'] = len(url_records)
        
        return url_records, stats
    
    def _log_statistics(self, stats: Dict) -> None:
        """
        Log parsing statistics.
        
        Args:
            stats: Statistics dictionary
        """
        logger.info("=" * 60)
        logger.info("CSV Parsing Statistics")
        logger.info("=" * 60)
        logger.info(f"Total rows in CSV:        {stats['total_rows']}")
        logger.info(f"Valid Instagram URLs:     {stats['valid_urls']}")
        logger.info(f"Invalid URLs:             {stats['invalid_urls']}")
        logger.info(f"Duplicate URLs:           {stats['duplicate_urls']}")
        logger.info(f"Already processed:        {stats['already_processed']}")
        logger.info(f"Final URLs to process:    {stats['final_count']}")
        logger.info("=" * 60)
    
    def get_column_names(self) -> List[str]:
        """
        Get list of column names from CSV file.
        Useful for letting users select which column contains URLs.
        
        Returns:
            List of column names
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
        """
        csv_path = Path(self.config.csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.config.csv_path}")
        
        try:
            df = pd.read_csv(csv_path, nrows=0)  # Read only headers
            return list(df.columns)
        except Exception as e:
            logger.error(f"Failed to read CSV columns: {e}")
            raise
    
    @staticmethod
    def validate_csv_file(csv_path: str) -> Tuple[bool, str, List[str]]:
        """
        Validate CSV file without parsing all data.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (is_valid, error_message, column_names)
        """
        csv_file = Path(csv_path)
        
        # Check if file exists
        if not csv_file.exists():
            return False, f"File not found: {csv_path}", []
        
        # Check if file is empty
        if csv_file.stat().st_size == 0:
            return False, "File is empty", []
        
        # Try to read headers
        try:
            df = pd.read_csv(csv_path, nrows=0)
            columns = list(df.columns)
            
            if len(columns) == 0:
                return False, "No columns found in CSV", []
            
            return True, "", columns
            
        except Exception as e:
            return False, f"Failed to read CSV: {e}", []


def parse_csv(
    csv_path: str,
    url_column: str = "url",
    validate_urls: bool = True,
    skip_processed: bool = False,
    processed_urls: Optional[set] = None
) -> Tuple[List[Dict], Dict]:
    """
    Convenience function to parse CSV file.
    
    Args:
        csv_path: Path to CSV file
        url_column: Name of column containing URLs
        validate_urls: Whether to validate URL format
        skip_processed: Whether to skip already processed URLs
        processed_urls: Set of already processed URLs
        
    Returns:
        Tuple of (list of URL records, statistics dict)
        
    Example:
        >>> urls, stats = parse_csv("data/input/reels.csv", url_column="reel_url")
        >>> print(f"Found {len(urls)} valid URLs")
        >>> for url_record in urls:
        ...     print(url_record['url'], url_record['reel_id'])
    """
    from config import InputConfig
    
    config = InputConfig(
        csv_path=csv_path,
        url_column=url_column,
        validate_urls=validate_urls,
        skip_processed=skip_processed
    )
    
    parser = CSVParser(config, processed_urls)
    return parser.parse()


# Example usage and testing
if __name__ == "__main__":
    # This block runs when the file is executed directly
    # Useful for testing the CSV parser independently
    
    import sys
    from pathlib import Path
    
    # Add src to path for imports
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import load_config, InputConfig
    from logger import setup_logger
    
    print("=" * 70)
    print("CSV Parser - Test Mode")
    print("=" * 70)
    print()
    
    # Test 1: Validate sample CSV
    sample_csv = "data/input/sample_reels.csv"
    print(f"Test 1: Validating {sample_csv}")
    
    is_valid, error, columns = CSVParser.validate_csv_file(sample_csv)
    
    if is_valid:
        print(f"✓ CSV is valid")
        print(f"  Columns found: {columns}")
    else:
        print(f"✗ CSV validation failed: {error}")
    
    print()
    
    # Test 2: Parse sample CSV
    if is_valid and columns:
        print(f"Test 2: Parsing {sample_csv}")
        
        try:
            # Use first column as URL column for testing
            url_column = columns[0] if 'url' not in columns else 'url'
            
            urls, stats = parse_csv(
                sample_csv,
                url_column=url_column,
                validate_urls=True,
                skip_processed=False
            )
            
            print(f"✓ Parsing successful")
            print(f"  Found {len(urls)} valid URLs")
            
            if urls:
                print(f"\n  Sample URL:")
                print(f"    URL: {urls[0]['url']}")
                print(f"    Reel ID: {urls[0]['reel_id']}")
                
        except Exception as e:
            print(f"✗ Parsing failed: {e}")
    
    print()
    print("=" * 70)
    print("Test complete!")
    print("=" * 70)
