
import unittest
from unittest.mock import MagicMock, patch
import json
import os
import glob
from datetime import datetime
from interactive_posts import MainScreen

class TestSaveFunctionality(unittest.TestCase):
    def setUp(self):
        self.data_dir = "data/20251125/linkedin"
        self.screen = MainScreen(self.data_dir)
        # Mock the app and notify method
        self.screen.app = MagicMock()
        self.screen.notify = MagicMock()
        
        # Load posts manually since on_mount is not called in this test setup
        self.screen.posts = self.screen.load_posts()
        # Filter posts logic from load_and_display_posts to ensure we have valid posts
        thirty_days_ago = datetime.now()
        # Just use all posts for testing purposes
        for post in self.screen.posts:
             post["datetime_obj"] = datetime.now() # Mock datetime
        
    def test_save_marked_posts(self):
        # Mark some posts
        if not self.screen.posts:
            self.skipTest("No posts found to test with")
            
        self.screen.marked_posts.add(0)
        if len(self.screen.posts) > 1:
            self.screen.marked_posts.add(1)
            
        # Mock filter text
        self.screen.filter_active = True
        self.screen.filter_text = "test query"
        
        # Call save action
        self.screen.action_save_marked()
        
        # Check if file was created
        files = glob.glob("marked_posts_*.json")
        self.assertTrue(len(files) > 0, "No saved file found")
        
        # Get the latest file
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
            
        # Verify structure
        self.assertIn("search", data)
        self.assertIn("matching_elements", data)
        self.assertEqual(data["search"]["query_string"], "test query")
        self.assertEqual(len(data["matching_elements"]), len(self.screen.marked_posts))
        
        # Clean up
        os.remove(latest_file)
        print(f"Verified save functionality with file: {latest_file}")

if __name__ == '__main__':
    unittest.main()
