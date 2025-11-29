# Profile Management System

## Overview
The social-tui now includes a comprehensive profile management system with tagging capabilities. You can manage the profiles in `data/input-data.csv` with categories and filters.

## Getting Started

### Initial Setup
1. Run the test script to import existing profiles:
   ```bash
   python3 test_profile_system.py
   ```

   This will:
   - Create the database tables (profiles, tags, profile_tags)
   - Import all profiles from `data/input-data.csv`
   - Create default tags (aws, ai, startup)
   - Tag a few sample profiles for testing

### Accessing Profile Management
1. Launch the main app:
   ```bash
   python3 interactive_posts.py -d
   ```

2. Press `p` to open the Profile Management screen

## Features

### 1. View Profiles
The main profile table displays:
- ID
- Username
- Name
- Tags (color-coded)
- Active status
- Post count

### 2. Add Profile (`a` key)
- Enter username (required)
- Enter name (required)
- Add optional notes
- Profile is automatically added to the database and CSV

### 3. Delete Profile (`d` key)
- Select a profile using arrow keys or `j`/`k`
- Press `d` to delete
- Profile is removed from database and CSV

### 4. Edit Profile (`e` key)
- Select a profile
- Press `e` to edit
- Update name, notes, or toggle active status
- Press `a` within the modal to toggle active/inactive

### 5. Tag Profile (`t` key)
- Select a profile
- Press `t` to open tagging modal
- Use number keys to toggle tags on/off
- Press `n` to create a new tag
- Press `Save` to apply changes

### 6. Manage Tags (`Shift+T` key)
- View all tags with usage counts
- Create new tags (`n` key)
- Delete tags (`d` key) - select with number keys
- Each tag has a customizable color

### 7. Filter by Tags (`f` key)
- Select one or more tags using number keys
- Toggle between ANY (OR) and ALL (AND) matching modes with `m`
- Press `Apply` to filter
- Press `Clear` to remove filters

### 8. Clear Filter (`c` key)
- Instantly clear all active filters

### 9. Sync with CSV (`s` key)
- Import new profiles from `data/input-data.csv`
- Export current profiles back to CSV
- Shows statistics on added/updated/skipped profiles

## Keyboard Shortcuts

### Main Profile Screen
| Key | Action |
|-----|--------|
| `a` | Add new profile |
| `d` | Delete selected profile |
| `e` | Edit selected profile |
| `t` | Tag selected profile |
| `Shift+T` | Manage global tags |
| `f` | Filter by tags |
| `c` | Clear filters |
| `s` | Sync with CSV |
| `o` | Open LinkedIn profile in browser |
| `j`/`k` or `↑`/`↓` | Navigate |
| `Escape` | Return to posts view |

### Tagging Modal
| Key | Action |
|-----|--------|
| `1-9` | Toggle tag on/off |
| `n` | Create new tag |
| `Save` button | Apply changes |
| `Cancel` button | Discard changes |
| `Escape` | Cancel |

### Filter Modal
| Key | Action |
|-----|--------|
| `1-9` | Toggle tag selection |
| `m` | Toggle AND/OR mode |
| `Apply` button | Apply filter |
| `Clear` button | Clear all filters |
| `Escape` | Cancel |

## Tag System

### Default Tags
Three tags are created by default:
- `aws` (cyan) - For AWS-related profiles
- `ai` (magenta) - For AI/ML profiles
- `startup` (green) - For startup-focused profiles

### Creating Custom Tags
1. Press `Shift+T` to open tag management
2. Press `n` to create a new tag
3. Enter tag name (lowercase, e.g., "finops", "cloud")
4. Press `c` to cycle through colors:
   - cyan, magenta, green, yellow, blue, red, white

### Tag Colors
Tags are color-coded for easy visual identification:
- AWS: cyan
- AI: magenta
- Startup: green
- Custom: yellow, blue, red, white

## Data Storage

### Database Schema
Profiles and tags are stored in `data/posts.db` with three tables:

**profiles:**
- id, username (unique), name, notes, is_active, created_at, updated_at

**tags:**
- id, name (unique), color, created_at

**profile_tags:**
- id, profile_id, tag_id (junction table for many-to-many)

### CSV Export
The system maintains bidirectional sync with `data/input-data.csv`:
- Changes in the UI update the CSV
- CSV imports can update existing profiles
- Only active profiles are exported by default

## Examples

### Example 1: Tag AWS Employees
1. Press `p` to open Profile Management
2. Select "Jeff Barr" with arrow keys
3. Press `t` to open tagging modal
4. Press `1` to select "aws" tag
5. Press `Save`

### Example 2: Filter AI Profiles
1. Press `f` to open filter modal
2. Press `1` to select "ai" tag
3. Press `Apply`
4. Now only AI-tagged profiles are shown

### Example 3: Create Custom Tag
1. Press `Shift+T` to manage tags
2. Press `n` to create new tag
3. Type "finops" as the tag name
4. Press `c` to cycle to yellow color
5. Press `Create`

### Example 4: Multi-Tag Filter (AND)
1. Press `f` to open filter modal
2. Press `1` to select "aws"
3. Press `2` to select "ai"
4. Press `m` to switch to ALL (AND) mode
5. Press `Apply`
6. Now only profiles with BOTH aws AND ai tags are shown

### Example 5: Open LinkedIn Profile
1. Navigate to any profile using arrow keys or `j`/`k`
2. Press `o` to open their LinkedIn profile in your default browser
3. The URL will be `https://linkedin.com/in/{username}`

## Tips

- Use `j`/`k` for Vim-style navigation
- Tag profiles as you discover their focus areas
- Use filters to quickly find profiles by category
- The CSV is automatically updated when you add/delete profiles
- Inactive profiles are hidden from CSV export but remain in database
- Press `Escape` to go back to the main posts view

## Troubleshooting

### Profiles not showing up
- Press `c` to clear any active filters
- Check if "Active" column shows "No" - inactive profiles are hidden from some views

### Tags not appearing
- Make sure you pressed `Save` in the tagging modal
- Check the tag was created successfully in Manage Tags (`Shift+T`)

### CSV not updating
- Press `s` to manually sync
- Check file permissions on `data/input-data.csv`

## Technical Details

### Files
- `profile_manager.py` - Profile CRUD operations
- `tag_manager.py` - Tag operations and profile-tag associations
- `profile_ui.py` - Textual UI components (screens and modals)
- `interactive_posts.py` - Main app (integrated profile management)

### Database Location
- `data/posts.db` - SQLite database with profiles, tags, and posts

### API Examples

```python
from profile_manager import ProfileManager
from tag_manager import TagManager

# Initialize
pm = ProfileManager("data/posts.db")
tm = TagManager("data/posts.db")

# Add a profile
profile_id = pm.add_profile("johndoe", "John Doe", "Notes here")

# Tag the profile
aws_tag = tm.get_tag_by_name("aws")
tm.tag_profile(profile_id, aws_tag['id'])

# Get profiles by tag
aws_profiles = pm.get_profiles_by_tag("aws")

# Multi-tag filter (OR)
profiles = pm.get_profiles_by_tags(["aws", "ai"], match_all=False)

# Multi-tag filter (AND)
profiles = pm.get_profiles_by_tags(["aws", "ai"], match_all=True)
```

## Future Enhancements (Not Implemented)
- Profile statistics (posts count, engagement metrics)
- Bulk tag operations
- Tag renaming
- Import profiles from LinkedIn URL
- Profile notes/comments
- Custom tag colors
- Tag hierarchies/categories
