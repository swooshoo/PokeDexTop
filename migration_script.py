#!/usr/bin/env python3
"""
Find All PyQt6 Issues Script
This will show you exactly what needs to be fixed and where
"""

import re

def find_all_qt_issues(file_path):
    """Find all PyQt5 patterns that need to be updated for PyQt6"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Patterns to find
    patterns_to_fix = [
        (r'Qt\.Alignment\.AlignCenter', 'Qt.AlignmentFlag.AlignCenter'),
        (r'Qt\.AlignCenter(?!Flag)', 'Qt.AlignmentFlag.AlignCenter'),
        (r'Qt\.AlignLeft(?!Flag)', 'Qt.AlignmentFlag.AlignLeft'),
        (r'Qt\.AlignRight(?!Flag)', 'Qt.AlignmentFlag.AlignRight'),
        (r'Qt\.AlignTop(?!Flag)', 'Qt.AlignmentFlag.AlignTop'),
        (r'Qt\.AlignBottom(?!Flag)', 'Qt.AlignmentFlag.AlignBottom'),
        (r'Qt\.KeepAspectRatio', 'Qt.AspectRatioMode.KeepAspectRatio'),
        (r'Qt\.SmoothTransformation', 'Qt.TransformationMode.SmoothTransformation'),
        (r'Qt\.PointingHandCursor', 'Qt.CursorShape.PointingHandCursor'),
        (r'Qt\.ArrowCursor', 'Qt.CursorShape.ArrowCursor'),
        (r'Qt\.UserRole', 'Qt.ItemDataRole.UserRole'),
        (r'QSizePolicy\.Fixed', 'QSizePolicy.Policy.Fixed'),
        (r'QSizePolicy\.Preferred', 'QSizePolicy.Policy.Preferred'),
        (r'QFrame\.Box', 'QFrame.Shape.Box'),
        (r'QFrame\.Raised', 'QFrame.Shadow.Raised'),
        (r'QFrame\.HLine', 'QFrame.Shape.HLine'),
        (r'QFrame\.Sunken', 'QFrame.Shadow.Sunken'),
        (r'QHeaderView\.Stretch', 'QHeaderView.ResizeMode.Stretch'),
        (r'QHeaderView\.ResizeToContents', 'QHeaderView.ResizeMode.ResizeToContents'),
        (r'QAbstractItemView\.SelectRows', 'QAbstractItemView.SelectionBehavior.SelectRows'),
        (r'QAbstractItemView\.SingleSelection', 'QAbstractItemView.SelectionMode.SingleSelection'),
        (r'QDialog\.Accepted', 'QDialog.DialogCode.Accepted'),
        (r'QDialog\.Rejected', 'QDialog.DialogCode.Rejected'),
        (r'QMessageBox\.Yes', 'QMessageBox.StandardButton.Yes'),
        (r'QMessageBox\.No', 'QMessageBox.StandardButton.No'),
    ]
    
    print("🔍 SCANNING FOR PyQt6 ISSUES...")
    print("=" * 60)
    
    issues_found = []
    
    for line_num, line in enumerate(lines, 1):
        for pattern, replacement in patterns_to_fix:
            matches = re.findall(pattern, line)
            if matches:
                issues_found.append({
                    'line_num': line_num,
                    'line_content': line.strip(),
                    'pattern': pattern,
                    'replacement': replacement,
                    'old_match': matches[0] if isinstance(matches[0], str) else pattern.replace(r'\.', '.').replace(r'(?!Flag)', '')
                })
    
    if issues_found:
        print(f"❌ FOUND {len(issues_found)} ISSUES TO FIX:")
        print()
        
        for i, issue in enumerate(issues_found, 1):
            print(f"Issue #{i} - Line {issue['line_num']}:")
            print(f"   Current: {issue['line_content']}")
            print(f"   Fix: Replace '{issue['old_match']}' with '{issue['replacement']}'")
            print()
        
        print("🔧 QUICK FIXES:")
        print("Use Find & Replace in your editor:")
        print()
        
        # Group by unique replacements
        unique_replacements = {}
        for issue in issues_found:
            key = issue['old_match']
            if key not in unique_replacements:
                unique_replacements[key] = issue['replacement']
        
        for old, new in unique_replacements.items():
            print(f"FIND: {old}")
            print(f"REPLACE: {new}")
            print()
        
    else:
        print("✅ NO PyQt6 ISSUES FOUND!")
    
    # Also check for desktop() usage
    desktop_issues = []
    for line_num, line in enumerate(lines, 1):
        if 'QApplication.desktop()' in line:
            desktop_issues.append((line_num, line.strip()))
    
    if desktop_issues:
        print("🖥️  DESKTOP() ISSUES FOUND:")
        for line_num, line in desktop_issues:
            print(f"Line {line_num}: {line}")
            print("   Fix: Replace 'QApplication.desktop().availableGeometry().center()' ")
            print("        with 'QApplication.primaryScreen().availableGeometry().center()'")
            print()
    
    return len(issues_found) + len(desktop_issues)

def auto_fix_qt_issues(file_path):
    """Automatically fix all PyQt6 issues"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    backup_path = file_path + '.qt6_backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ Backup created: {backup_path}")
    
    # All replacements
    replacements = [
        ('Qt.Alignment.AlignCenter', 'Qt.AlignmentFlag.AlignCenter'),
        ('Qt.AlignCenter', 'Qt.AlignmentFlag.AlignCenter'),
        ('Qt.AlignLeft', 'Qt.AlignmentFlag.AlignLeft'),
        ('Qt.AlignRight', 'Qt.AlignmentFlag.AlignRight'),
        ('Qt.AlignTop', 'Qt.AlignmentFlag.AlignTop'),
        ('Qt.AlignBottom', 'Qt.AlignmentFlag.AlignBottom'),
        ('Qt.KeepAspectRatio', 'Qt.AspectRatioMode.KeepAspectRatio'),
        ('Qt.SmoothTransformation', 'Qt.TransformationMode.SmoothTransformation'),
        ('Qt.PointingHandCursor', 'Qt.CursorShape.PointingHandCursor'),
        ('Qt.ArrowCursor', 'Qt.CursorShape.ArrowCursor'),
        ('Qt.UserRole', 'Qt.ItemDataRole.UserRole'),
        ('QSizePolicy.Fixed', 'QSizePolicy.Policy.Fixed'),
        ('QSizePolicy.Preferred', 'QSizePolicy.Policy.Preferred'),
        ('QFrame.Box', 'QFrame.Shape.Box'),
        ('QFrame.Raised', 'QFrame.Shadow.Raised'),
        ('QFrame.HLine', 'QFrame.Shape.HLine'),
        ('QFrame.Sunken', 'QFrame.Shadow.Sunken'),
        ('QHeaderView.Stretch', 'QHeaderView.ResizeMode.Stretch'),
        ('QHeaderView.ResizeToContents', 'QHeaderView.ResizeMode.ResizeToContents'),
        ('setResizeMode(', 'setSectionResizeMode('),
        ('QAbstractItemView.SelectRows', 'QAbstractItemView.SelectionBehavior.SelectRows'),
        ('QAbstractItemView.SingleSelection', 'QAbstractItemView.SelectionMode.SingleSelection'),
        ('QDialog.Accepted', 'QDialog.DialogCode.Accepted'),
        ('QDialog.Rejected', 'QDialog.DialogCode.Rejected'),
        ('QMessageBox.Yes', 'QMessageBox.StandardButton.Yes'),
        ('QMessageBox.No', 'QMessageBox.StandardButton.No'),
        ('QApplication.desktop().availableGeometry().center()', 'QApplication.primaryScreen().availableGeometry().center()'),
    ]
    
    changes_made = 0
    for old, new in replacements:
        old_content = content
        content = content.replace(old, new)
        if content != old_content:
            changes_made += 1
            print(f"✓ Fixed: {old} → {new}")
    
    # Write fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n🎉 AUTO-FIX COMPLETE! Made {changes_made} changes.")
    print("Your app should now work with PyQt6!")
    
    return changes_made

if __name__ == "__main__":
    import sys
    import os
    
    app_file = 'app.py'
    
    if not os.path.exists(app_file):
        print(f"❌ {app_file} not found!")
        sys.exit(1)
    
    print("Choose an option:")
    print("1. Scan and show issues (recommended first)")
    print("2. Auto-fix all issues")
    
    choice = input("Enter 1 or 2: ").strip()
    
    if choice == '1':
        issues_count = find_all_qt_issues(app_file)
        if issues_count > 0:
            print(f"\n📋 SUMMARY: Found {issues_count} issues to fix")
            print("Run this script again with option 2 to auto-fix them all!")
        else:
            print("\n✅ No issues found! Your code should work with PyQt6.")
    
    elif choice == '2':
        changes = auto_fix_qt_issues(app_file)
        if changes > 0:
            print("\n🚀 Try running your app now!")
        else:
            print("\n🤔 No changes made. Your code might already be PyQt6 compatible.")
    
    else:
        print("❌ Invalid choice. Please run again and choose 1 or 2.")