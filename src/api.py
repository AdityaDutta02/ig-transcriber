"""
API Module for Web UI

Provides REST API endpoints for the web interface.
Will be expanded in Phase 2 for full web deployment.
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from csv_status_manager import CSVStatusManager
from config import load_config


class API:
    """
    API interface for web UI.
    
    Features:
    - Get processing status
    - Start/stop processing
    - Get statistics
    - Upload CSV
    - Download results
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        """Initialize API."""
        self.config = load_config(config_path)
        self.pipeline = None
    
    def get_status(self, csv_path: str) -> Dict:
        """
        Get processing status for a CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Status dictionary
        """
        try:
            manager = CSVStatusManager(csv_path)
            stats = manager.get_processing_stats()
            
            return {
                'success': True,
                'stats': stats,
                'message': 'Status retrieved successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get status'
            }
    
    def get_unprocessed(self, csv_path: str) -> Dict:
        """
        Get unprocessed URLs.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Unprocessed URLs
        """
        try:
            manager = CSVStatusManager(csv_path)
            unprocessed = manager.get_unprocessed_urls()
            
            return {
                'success': True,
                'count': len(unprocessed),
                'urls': unprocessed[:10],  # First 10 for preview
                'message': 'Unprocessed URLs retrieved'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get unprocessed URLs'
            }
    
    def get_failed(self, csv_path: str) -> Dict:
        """
        Get failed URLs.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Failed URLs
        """
        try:
            manager = CSVStatusManager(csv_path)
            failed = manager.get_failed_urls()
            
            return {
                'success': True,
                'count': len(failed),
                'urls': failed,
                'message': 'Failed URLs retrieved'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get failed URLs'
            }
    
    def get_transcriptions(self, limit: int = 50) -> Dict:
        """
        Get recent transcriptions.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of transcription files
        """
        try:
            output_dir = Path(self.config.output.directory)
            
            if not output_dir.exists():
                return {
                    'success': True,
                    'count': 0,
                    'files': [],
                    'message': 'No transcriptions yet'
                }
            
            # Get all transcription files
            files = sorted(
                output_dir.glob("*.txt"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]
            
            file_info = []
            for f in files:
                file_info.append({
                    'filename': f.name,
                    'path': str(f),
                    'size': f.stat().st_size,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
            
            return {
                'success': True,
                'count': len(file_info),
                'files': file_info,
                'message': 'Transcriptions retrieved'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get transcriptions'
            }
    
    def start_processing(
        self,
        csv_path: str,
        resume: bool = True
    ) -> Dict:
        """
        Start processing pipeline.
        
        Args:
            csv_path: Path to CSV file
            resume: Resume from last checkpoint
            
        Returns:
            Status dictionary
        """
        try:
            # This will be expanded in Phase 2 with async processing
            return {
                'success': True,
                'message': 'Processing started',
                'job_id': 'placeholder'  # Will be real job ID in Phase 2
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to start processing'
            }
    
    def stop_processing(self, job_id: str) -> Dict:
        """
        Stop processing pipeline.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Status dictionary
        """
        try:
            # This will be expanded in Phase 2
            return {
                'success': True,
                'message': 'Processing stopped',
                'job_id': job_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to stop processing'
            }


# Convenience functions for direct API usage
def get_processing_status(csv_path: str) -> Dict:
    """Get processing status."""
    api = API()
    return api.get_status(csv_path)


def get_recent_transcriptions(limit: int = 50) -> Dict:
    """Get recent transcriptions."""
    api = API()
    return api.get_transcriptions(limit)


if __name__ == "__main__":
    # Test API
    print("API Module - Test Mode")
    print("=" * 70)
    
    api = API()
    
    # Test status
    print("\nTesting get_status:")
    result = api.get_status("data/input/sample_reels.csv")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Stats: {result['stats']}")
    
    # Test transcriptions
    print("\nTesting get_transcriptions:")
    result = api.get_transcriptions(limit=5)
    print(f"Success: {result['success']}")
    print(f"Count: {result['count']}")
    
    print("\nAPI module working correctly!")
