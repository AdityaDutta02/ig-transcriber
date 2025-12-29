"""
CSV Status Manager

Handles reading from and writing status updates to the input CSV file.
Tracks processing status (success/fail) directly in the source CSV.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from loguru import logger
from utils import extract_reel_id


class CSVStatusManager:
    """
    Manages CSV file with status tracking.
    
    Features:
    - Read/write CSV with status column
    - Update status for individual rows
    - Track processing timestamps
    - Maintain original CSV structure
    """
    
    def __init__(self, csv_path: str, url_column: str = "url"):
        """
        Initialize CSV status manager.
        
        Args:
            csv_path: Path to CSV file
            url_column: Name of column containing URLs
        """
        self.csv_path = Path(csv_path)
        self.url_column = url_column
        self.status_column = "processing_status"
        self.timestamp_column = "processed_at"
        self.error_column = "error_message"
        
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"CSV Status Manager initialized: {self.csv_path}")
    
    def read_csv(self) -> Tuple[List[Dict], List[str]]:
        """
        Read CSV file with all columns.
        
        Returns:
            Tuple of (records, column_names)
        """
        records = []
        
        with open(self.csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            
            for row in reader:
                records.append(row)
        
        logger.info(f"Read {len(records)} records from CSV")
        return records, list(columns)
    
    def ensure_status_columns(self, columns: List[str]) -> List[str]:
        """
        Ensure status columns exist in column list.
        
        Args:
            columns: Existing column list
            
        Returns:
            Updated column list with status columns
        """
        new_columns = columns.copy()
        
        # Add status columns if not present
        if self.status_column not in new_columns:
            new_columns.append(self.status_column)
        
        if self.timestamp_column not in new_columns:
            new_columns.append(self.timestamp_column)
        
        if self.error_column not in new_columns:
            new_columns.append(self.error_column)
        
        return new_columns
    
    def write_csv(self, records: List[Dict], columns: List[str]) -> None:
        """
        Write records back to CSV file.
        
        Args:
            records: List of record dictionaries
            columns: Column names
        """
        # Create backup
        backup_path = self.csv_path.with_suffix('.csv.bak')
        if self.csv_path.exists():
            import shutil
            shutil.copy2(self.csv_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # Write updated CSV
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)
        
        logger.info(f"Updated CSV with {len(records)} records")
    
    def update_status(
        self,
        url: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update status for a specific URL.
        
        Args:
            url: URL to update
            status: Status value ('success', 'failed', 'processing')
            error_message: Optional error message
        """
        records, columns = self.read_csv()
        columns = self.ensure_status_columns(columns)
        
        # Find and update record
        updated = False
        for record in records:
            if record.get(self.url_column) == url:
                record[self.status_column] = status
                record[self.timestamp_column] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if error_message:
                    record[self.error_column] = error_message
                else:
                    record[self.error_column] = ''
                updated = True
                break
        
        if updated:
            self.write_csv(records, columns)
            logger.debug(f"Updated status for {url}: {status}")
        else:
            logger.warning(f"URL not found in CSV: {url}")
    
    def batch_update_status(
        self,
        url_status_map: Dict[str, Tuple[str, Optional[str]]]
    ) -> None:
        """
        Update status for multiple URLs at once.
        
        Args:
            url_status_map: Dict mapping URL -> (status, error_message)
        """
        records, columns = self.read_csv()
        columns = self.ensure_status_columns(columns)
        
        # Update all matching records
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        updated_count = 0
        
        for record in records:
            url = record.get(self.url_column)
            if url in url_status_map:
                status, error_message = url_status_map[url]
                record[self.status_column] = status
                record[self.timestamp_column] = timestamp
                record[self.error_column] = error_message or ''
                updated_count += 1
        
        self.write_csv(records, columns)
        logger.info(f"Batch updated {updated_count} records")
    
    def get_unprocessed_urls(self) -> List[Dict]:
        """
        Get URLs that haven't been processed yet.
        
        Returns:
            List of unprocessed records
        """
        records, columns = self.read_csv()
        
        unprocessed = []
        for record in records:
            status = record.get(self.status_column, '').lower()
            if status not in ['success', 'completed']:
                # Extract reel_id if not present
                if 'reel_id' not in record or not record['reel_id']:
                    url = record.get(self.url_column, '')
                    reel_id = extract_reel_id(url)
                    if reel_id:
                        record['reel_id'] = reel_id
                unprocessed.append(record)
        
        logger.info(f"Found {len(unprocessed)} unprocessed records")
        return unprocessed
    
    def get_failed_urls(self) -> List[Dict]:
        """
        Get URLs that failed processing.
        
        Returns:
            List of failed records
        """
        records, columns = self.read_csv()
        
        failed = []
        for record in records:
            status = record.get(self.status_column, '').lower()
            if status in ['failed', 'error']:
                # Extract reel_id if not present
                if 'reel_id' not in record or not record['reel_id']:
                    url = record.get(self.url_column, '')
                    reel_id = extract_reel_id(url)
                    if reel_id:
                        record['reel_id'] = reel_id
                failed.append(record)
        
        logger.info(f"Found {len(failed)} failed records")
        return failed
    
    def get_processing_stats(self) -> Dict:
        """
        Get processing statistics.
        
        Returns:
            Dict with statistics
        """
        records, columns = self.read_csv()
        
        stats = {
            'total': len(records),
            'success': 0,
            'failed': 0,
            'unprocessed': 0,
            'processing': 0
        }
        
        for record in records:
            status = record.get(self.status_column, '').lower()
            
            if status in ['success', 'completed']:
                stats['success'] += 1
            elif status in ['failed', 'error']:
                stats['failed'] += 1
            elif status == 'processing':
                stats['processing'] += 1
            else:
                stats['unprocessed'] += 1
        
        return stats


# Convenience functions
def update_csv_status(
    csv_path: str,
    url: str,
    status: str,
    error_message: Optional[str] = None,
    url_column: str = "url"
) -> None:
    """
    Convenience function to update CSV status.
    
    Args:
        csv_path: Path to CSV file
        url: URL to update
        status: Status value
        error_message: Optional error message
        url_column: Column containing URLs
    """
    manager = CSVStatusManager(csv_path, url_column)
    manager.update_status(url, status, error_message)


def batch_update_csv_status(
    csv_path: str,
    url_status_map: Dict[str, Tuple[str, Optional[str]]],
    url_column: str = "url"
) -> None:
    """
    Batch update CSV status.
    
    Args:
        csv_path: Path to CSV file
        url_status_map: Dict mapping URL -> (status, error_message)
        url_column: Column containing URLs
    """
    manager = CSVStatusManager(csv_path, url_column)
    manager.batch_update_status(url_status_map)


def get_unprocessed_records(
    csv_path: str,
    url_column: str = "url"
) -> List[Dict]:
    """
    Get unprocessed records from CSV.
    
    Args:
        csv_path: Path to CSV file
        url_column: Column containing URLs
        
    Returns:
        List of unprocessed records
    """
    manager = CSVStatusManager(csv_path, url_column)
    return manager.get_unprocessed_urls()


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("=" * 70)
    print("CSV Status Manager - Test Mode")
    print("=" * 70)
    print()
    
    # Test with sample CSV
    csv_file = "data/input/sample_reels.csv"
    
    if not Path(csv_file).exists():
        print(f"Sample CSV not found: {csv_file}")
        sys.exit(1)
    
    try:
        manager = CSVStatusManager(csv_file)
        
        # Show stats
        stats = manager.get_processing_stats()
        print("Processing Statistics:")
        print(f"  Total: {stats['total']}")
        print(f"  Success: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Unprocessed: {stats['unprocessed']}")
        print(f"  Processing: {stats['processing']}")
        print()
        
        # Get unprocessed
        unprocessed = manager.get_unprocessed_urls()
        print(f"Unprocessed URLs: {len(unprocessed)}")
        
        print()
        print("CSV Status Manager working correctly!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
