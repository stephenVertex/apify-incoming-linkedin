# Git Worktree Setup Guide

## Overview

This repository uses git worktrees to enable parallel feature development. Multiple features can be worked on simultaneously without branch switching, with shared resources (data, cache, environment) accessed via symlinks.

## Directory Structure

```
~/dev/social-tui-dev/
├── main/                       # Main worktree (default branch)
├── feature-s3-upload/          # Feature worktree (S3 archiving)
├── feature-ai-analysis/        # Feature worktree (AI image analysis)
├── feature-youtube-import/     # Feature worktree (YouTube integration)
└── shared/
    ├── data/                   # Shared input data (read-only)
    ├── cache/                  # Shared media cache (read-only)
    └── .env                    # Shared environment variables
```

**Note**: Data, cache, and .env are safe to share because we only read from them, never write to them.

## Initial Setup

### 1. Create Directory Structure

```bash
# Move current repo to be the "main" worktree
cd ~/dev
mkdir social-tui-dev
mv social-tui social-tui-dev/main
cd social-tui-dev/main

# Create shared resources directory
mkdir -p ../shared

# Move shared resources from main to shared
mv data ../shared/
mv cache ../shared/
mv .env ../shared/

# Create symlinks in main worktree
ln -s ../shared/data data
ln -s ../shared/cache cache
ln -s ../shared/.env .env

# Add symlinks to .gitignore (already ignored as they point to ignored dirs)
# Verify with: git status (should show no changes to data/, cache/, .env)
```

### 2. Verify Setup

```bash
# Should see symlinks
ls -la | grep "^l"

# Should show: data -> ../shared/data
# Should show: cache -> ../shared/cache
# Should show: .env -> ../shared/.env

# Verify data is accessible
ls shared/data/
ls shared/cache/media/
```

## Creating New Worktrees

### Create a Feature Worktree

```bash
cd ~/dev/social-tui-dev/main

# Create new worktree with feature branch
git worktree add ../feature-s3-upload -b feature/s3-upload

# Set up symlinks in the new worktree
cd ../feature-s3-upload
ln -s ../shared/data data
ln -s ../shared/cache cache
ln -s ../shared/.env .env

# Verify symlinks
ls -la data cache .env

# Start working on the feature
code .  # Or your preferred editor
```

### Example: Create Multiple Features

```bash
cd ~/dev/social-tui-dev/main

# Create worktree for S3 upload feature
git worktree add ../feature-s3-upload -b feature/s3-upload
cd ../feature-s3-upload && ln -s ../shared/data data && ln -s ../shared/cache cache && ln -s ../shared/.env .env

# Create worktree for AI analysis feature
cd ~/dev/social-tui-dev/main
git worktree add ../feature-ai-analysis -b feature/ai-analysis
cd ../feature-ai-analysis && ln -s ../shared/data data && ln -s ../shared/cache cache && ln -s ../shared/.env .env

# Create worktree for YouTube import
cd ~/dev/social-tui-dev/main
git worktree add ../feature-youtube-import -b feature/youtube-import
cd ../feature-youtube-import && ln -s ../shared/data data && ln -s ../shared/cache cache && ln -s ../shared/.env .env
```

## Working with Worktrees

### List All Worktrees

```bash
git worktree list
```

Output:
```
/Users/stephen/dev/social-tui-dev/main              abc1234 [main]
/Users/stephen/dev/social-tui-dev/feature-s3-upload def5678 [feature/s3-upload]
/Users/stephen/dev/social-tui-dev/feature-ai-analysis ghi9012 [feature/ai-analysis]
```

### Switch Between Worktrees

Simply `cd` to the worktree directory:

```bash
# Work on S3 feature
cd ~/dev/social-tui-dev/feature-s3-upload

# Work on AI feature
cd ~/dev/social-tui-dev/feature-ai-analysis

# Back to main
cd ~/dev/social-tui-dev/main
```

### Running Scripts in Different Worktrees

Each worktree is independent:

```bash
# Terminal 1: Test S3 upload
cd ~/dev/social-tui-dev/feature-s3-upload
uv run python3 upload_to_s3.py

# Terminal 2: Test AI analysis (simultaneously!)
cd ~/dev/social-tui-dev/feature-ai-analysis
uv run python3 analyze_images.py

# Terminal 3: Run viewer on main
cd ~/dev/social-tui-dev/main
uv run python3 interactive_posts.py
```

## Merging Features

### Option 1: Merge via GitHub PR (Recommended)

```bash
# Push feature branch
cd ~/dev/social-tui-dev/feature-s3-upload
git push -u origin feature/s3-upload

# Create PR on GitHub, review, merge
# Then update main worktree
cd ~/dev/social-tui-dev/main
git pull
```

### Option 2: Merge Locally

```bash
# Switch to main worktree
cd ~/dev/social-tui-dev/main

# Merge feature branch
git merge feature/s3-upload

# Push to remote
git push
```

## Removing Worktrees

### When Feature is Complete

```bash
# First, merge or delete the branch
cd ~/dev/social-tui-dev/main
git branch -d feature/s3-upload  # Delete if merged
# Or: git branch -D feature/s3-upload  # Force delete if not merged

# Remove the worktree
git worktree remove ../feature-s3-upload

# Clean up directory (if needed)
rm -rf ../feature-s3-upload  # Usually not needed, worktree remove handles it
```

### Clean Up Stale Worktrees

```bash
# If a worktree directory was manually deleted
git worktree prune

# List worktrees to verify
git worktree list
```

## Shared Resources

### Data Directory (`shared/data/`)

Contains input data from LinkedIn exports:

```
shared/data/
└── 20251201_120000/
    └── linkedin/
        ├── Posts.csv
        ├── Reactions.csv
        └── Comments.csv
```

**Usage**: Read-only access for importing data into database

### Cache Directory (`shared/cache/`)

Contains downloaded media files:

```
shared/cache/media/
├── images/
│   └── a1b2c3d4e5f6.jpg
├── videos/
│   └── x9y8z7w6v5u4.mp4
└── documents/
```

**Usage**: Read-only access for viewing media, all worktrees share the same cache

### Environment File (`shared/.env`)

Contains API keys and database connection:

```bash
SUPABASE_URL=https://...
SUPABASE_KEY=...
OPENAI_API_KEY=...
```

**Usage**: All worktrees use the same Supabase database and API keys

## Best Practices

### 1. Keep Shared Resources Read-Only

- Never modify files in `shared/data/`
- Never write to `shared/cache/` (use backfill scripts from main)
- Never edit `shared/.env` from feature branches

### 2. Naming Convention

Use descriptive feature names:
- `feature-{name}` for feature directories
- `feature/{name}` for branch names

### 3. Regular Sync

Keep worktrees updated with main:

```bash
cd ~/dev/social-tui-dev/feature-s3-upload
git fetch origin
git merge origin/main  # Or: git rebase origin/main
```

### 4. Clean Up After Merging

Remove worktrees for merged features to save disk space:

```bash
git worktree remove ../feature-completed
```

## Troubleshooting

### Symlink Shows as Broken

If a symlink appears broken:

```bash
# Check if it points to the right location
ls -la data

# Recreate if needed
rm data
ln -s ../shared/data data
```

### Worktree Won't Remove

If `git worktree remove` fails:

```bash
# Force removal
git worktree remove --force ../feature-name

# Or manually clean up
rm -rf ../feature-name
git worktree prune
```

### Database Conflicts

All worktrees share the same database. If you need isolation:

1. Use Supabase branches (see Supabase docs)
2. Or use different `.env` per worktree (copy instead of symlink)

### Can't Check Out Same Branch Twice

Git prevents checking out the same branch in multiple worktrees:

```bash
# Error: branch 'feature/foo' is already checked out at '...'
```

**Solution**: Each worktree needs a unique branch.

## Quick Reference

```bash
# Create worktree
git worktree add ../feature-name -b feature/name
cd ../feature-name && ln -s ../shared/{data,cache,.env} .

# List worktrees
git worktree list

# Remove worktree
git worktree remove ../feature-name

# Clean stale worktrees
git worktree prune
```

## Current Worktree Status

After setup, verify with:

```bash
cd ~/dev/social-tui-dev/main
git worktree list
ls -la shared/
```

## Related Documentation

- Git Worktree Docs: https://git-scm.com/docs/git-worktree
- Media Cache: `MEDIA_CACHE_QUICKSTART.md`
- Media Import: `MEDIA_IMPORT_QUICKSTART.md`
- Phase 3 Summary: `specs/phase3_completion_summary.md`
