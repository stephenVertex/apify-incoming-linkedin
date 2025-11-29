# Profile Management System Design

## Overview
Add tabular profile management with tagging capabilities to social-tui. This will allow users to manage the profiles in `data/input-data.csv` with categories and filtering.

## Requirements
1. Add profile
2. Delete profile
3. Tag a profile with categories (aws, ai, startup, etc.)
4. View profiles by tags
5. Manage tags (add, edit, delete tags)
6. Tabular view of profiles with inline actions

## Database Schema

### profiles table
```sql
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    post_count INTEGER DEFAULT 0,
    last_synced_at TIMESTAMP
);

CREATE INDEX idx_profiles_username ON profiles(username);
CREATE INDEX idx_profiles_active ON profiles(is_active);
```

### tags table
```sql
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT 'cyan',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tags_name ON tags(name);
```

### profile_tags junction table
```sql
CREATE TABLE IF NOT EXISTS profile_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(profile_id, tag_id)
);

CREATE INDEX idx_profile_tags_profile ON profile_tags(profile_id);
CREATE INDEX idx_profile_tags_tag ON profile_tags(tag_id);
```

## Data Model Classes

### ProfileManager
Handles all profile-related database operations:
- `add_profile(username, name)` - Add new profile
- `delete_profile(profile_id)` - Delete profile
- `update_profile(profile_id, **kwargs)` - Update profile fields
- `get_all_profiles()` - Get all profiles
- `get_profile_by_id(profile_id)` - Get single profile
- `get_profiles_by_tag(tag_name)` - Filter profiles by tag
- `sync_from_csv(csv_path)` - Import profiles from CSV
- `export_to_csv(csv_path)` - Export profiles to CSV

### TagManager
Handles tag operations:
- `add_tag(name, color='cyan')` - Create new tag
- `delete_tag(tag_id)` - Delete tag
- `rename_tag(tag_id, new_name)` - Rename tag
- `get_all_tags()` - Get all tags
- `tag_profile(profile_id, tag_id)` - Add tag to profile
- `untag_profile(profile_id, tag_id)` - Remove tag from profile
- `get_profile_tags(profile_id)` - Get all tags for a profile

## UI Components

### ProfileManagementScreen (Textual Screen)
Main screen for managing profiles with DataTable widget.

**Table Columns:**
| ID | Username | Name | Tags | Posts | Active | Actions |
|----|----------|------|------|-------|--------|---------|

**Key Bindings:**
- `a` - Add new profile
- `d` - Delete selected profile
- `t` - Tag selected profile
- `T` (Shift+t) - Manage tags
- `f` - Filter by tag
- `c` - Clear filters
- `e` - Edit profile
- `s` - Sync from/to CSV
- `Escape` - Back to main app
- `Enter` - View profile details
- `↑`/`↓` or `j`/`k` - Navigate

### AddProfileModal
Modal dialog for adding new profiles.

**Fields:**
- Username (required)
- Name (required)
- Tags (multi-select)

### TagProfileModal
Modal for managing tags on a profile.

**Features:**
- Checkbox list of available tags
- Create new tag inline
- Save/Cancel

### ManageTagsModal
Modal for managing global tags.

**Features:**
- List all tags with usage count
- Add new tag
- Rename tag
- Delete tag (with confirmation if in use)

### FilterByTagModal
Modal for filtering profiles by tags.

**Features:**
- Checkbox list of tags
- AND/OR logic selector
- Apply/Clear

## File Structure

```
social-tui/
├── profile_manager.py          # ProfileManager class
├── tag_manager.py              # TagManager class
├── profile_ui.py               # ProfileManagementScreen + modals
├── interactive_posts.py        # Modified: add profile mgmt integration
└── data/
    ├── input-data.csv          # Source CSV
    └── posts.db                # SQLite database (extended schema)
```

## Integration with Existing App

### Keyboard Shortcut
Add `p` key binding in MainScreen to launch ProfileManagementScreen:
```python
Binding("p", "show_profiles", "Profiles")
```

### CSV Sync
- On first launch: Import all profiles from `data/input-data.csv`
- Bidirectional sync: Changes in UI update CSV, CSV changes can be imported
- Preserve tags when re-importing

## Data Flow

```
1. Initial Import:
   data/input-data.csv → ProfileManager.sync_from_csv() → SQLite

2. Add Profile:
   UI → ProfileManager.add_profile() → SQLite + CSV export

3. Tag Profile:
   UI → TagManager.tag_profile() → SQLite

4. Filter by Tag:
   UI → ProfileManager.get_profiles_by_tag() → Filtered DataTable

5. Export:
   ProfileManager.export_to_csv() → data/input-data.csv
```

## Example Usage

### Adding a Profile
```python
pm = ProfileManager(db_path)
profile_id = pm.add_profile(
    username="sdouglasaau",
    name="Stephen Douglas"
)
```

### Tagging a Profile
```python
tm = TagManager(db_path)
tag_id = tm.add_tag("aws")
tm.tag_profile(profile_id, tag_id)
```

### Filtering by Tag
```python
aws_profiles = pm.get_profiles_by_tag("aws")
```

## Color Scheme
Use Rich/Textual colors for tags:
- `aws` - cyan
- `ai` - magenta
- `startup` - green
- Custom tags - yellow/blue/red rotation

## Testing Strategy
1. Unit tests for ProfileManager CRUD operations
2. Unit tests for TagManager operations
3. Integration test for CSV sync
4. Manual UI testing with keyboard navigation

## Migration Path
1. Create new tables (profiles, tags, profile_tags)
2. Import existing CSV data
3. Create default tags (aws, ai, startup)
4. Add UI components
5. Test CSV bidirectional sync
