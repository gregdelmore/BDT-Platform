#!/usr/bin/env python3
"""
BDT Code Analysis Tool
Analyzes differences between duplicate files across sessions to help with consolidation decisions
"""

import os
import difflib
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

class BDTCodeAnalyzer:
    def __init__(self, session_dirs: List[str]):
        self.session_dirs = session_dirs
        self.file_map = defaultdict(list)  # filename -> [(session, full_path)]
        self.analysis_results = {}
        
    def scan_sessions(self):
        """Scan all sessions and build a map of files"""
        print("Scanning session directories...")
        
        for session_dir in self.session_dirs:
            session_num = session_dir.split('session')[-1]
            for root, dirs, files in os.walk(session_dir):
                # Skip hidden directories and node_modules
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
                
                for file in files:
                    # Skip non-code files
                    if not file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.yml', '.yaml', '.json', '.md')):
                        continue
                        
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, session_dir)
                    
                    # Group by filename
                    self.file_map[file].append((session_num, full_path, relative_path))
        
        print(f"Found {len(self.file_map)} unique filenames across sessions")
        
    def find_duplicates(self) -> Dict[str, List[Tuple[str, str]]]:
        """Find files that appear in multiple sessions"""
        duplicates = {}
        
        for filename, locations in self.file_map.items():
            if len(locations) > 1:
                duplicates[filename] = locations
                
        return duplicates
    
    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                hasher.update(f.read())
            return hasher.hexdigest()
        except:
            return ""
    
    def analyze_duplicate(self, filename: str, locations: List[Tuple[str, str, str]]) -> dict:
        """Analyze a duplicate file across sessions"""
        analysis = {
            'filename': filename,
            'sessions': [],
            'identical': False,
            'recommendation': '',
            'differences': []
        }
        
        hashes = {}
        contents = {}
        
        for session, full_path, relative_path in locations:
            file_hash = self.calculate_file_hash(full_path)
            hashes[session] = file_hash
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    contents[session] = content
                    
                analysis['sessions'].append({
                    'session': session,
                    'path': relative_path,
                    'size': len(content),
                    'lines': content.count('\n') + 1,
                    'hash': file_hash
                })
            except:
                analysis['sessions'].append({
                    'session': session,
                    'path': relative_path,
                    'error': 'Could not read file'
                })
        
        # Check if all files are identical
        unique_hashes = set(hashes.values())
        if len(unique_hashes) == 1:
            analysis['identical'] = True
            analysis['recommendation'] = f"Use any version (all identical)"
        else:
            # Analyze differences
            sessions = sorted(contents.keys())
            
            if len(sessions) >= 2:
                # Compare sequential sessions
                for i in range(len(sessions) - 1):
                    session1 = sessions[i]
                    session2 = sessions[i + 1]
                    
                    if session1 in contents and session2 in contents:
                        diff = self.get_diff_summary(
                            contents[session1], 
                            contents[session2],
                            f"Session {session1}",
                            f"Session {session2}"
                        )
                        
                        if diff['changes'] > 0:
                            analysis['differences'].append({
                                'from_session': session1,
                                'to_session': session2,
                                'added_lines': diff['added'],
                                'removed_lines': diff['removed'],
                                'changes': diff['changes']
                            })
            
            # Make recommendation based on latest session and complexity
            latest_session = max(sessions)
            analysis['recommendation'] = f"Use Session {latest_session} (most recent)"
            
            # Special cases
            if filename == 'requirements.txt':
                analysis['recommendation'] = "Merge all unique dependencies"
            elif filename == 'docker-compose.yml':
                if '5' in sessions:
                    analysis['recommendation'] = "Use Session 5 (production version)"
            elif filename.endswith('config.py'):
                analysis['recommendation'] = f"Use Session {latest_session} and merge any unique configs"
                
        return analysis
    
    def get_diff_summary(self, content1: str, content2: str, label1: str, label2: str) -> dict:
        """Get a summary of differences between two file contents"""
        lines1 = content1.splitlines()
        lines2 = content2.splitlines()
        
        differ = difflib.unified_diff(lines1, lines2, fromfile=label1, tofile=label2)
        
        added = 0
        removed = 0
        
        for line in differ:
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                removed += 1
                
        return {
            'added': added,
            'removed': removed,
            'changes': added + removed
        }
    
    def generate_report(self):
        """Generate a comprehensive analysis report"""
        duplicates = self.find_duplicates()
        
        report = {
            'total_files': len(self.file_map),
            'duplicate_files': len(duplicates),
            'analysis': []
        }
        
        print(f"\nAnalyzing {len(duplicates)} duplicate files...")
        
        for filename, locations in duplicates.items():
            analysis = self.analyze_duplicate(filename, locations)
            report['analysis'].append(analysis)
            
        return report
    
    def print_report(self, report: dict):
        """Print a formatted report"""
        print("\n" + "="*80)
        print("BDT CODE CONSOLIDATION ANALYSIS REPORT")
        print("="*80)
        
        print(f"\nSummary:")
        print(f"  Total unique files: {report['total_files']}")
        print(f"  Files appearing in multiple sessions: {report['duplicate_files']}")
        
        print("\n" + "-"*80)
        print("DUPLICATE FILE ANALYSIS")
        print("-"*80)
        
        # Group by recommendation
        by_recommendation = defaultdict(list)
        
        for analysis in report['analysis']:
            by_recommendation[analysis['recommendation']].append(analysis)
        
        # Identical files
        identical_files = [a for a in report['analysis'] if a['identical']]
        if identical_files:
            print(f"\n✓ Identical Files ({len(identical_files)} files - use any version):")
            for file in identical_files:
                sessions = [s['session'] for s in file['sessions']]
                print(f"  - {file['filename']} (Sessions: {', '.join(sessions)})")
        
        # Files needing merge
        merge_files = [a for a in report['analysis'] 
                      if 'merge' in a['recommendation'].lower() or 
                         'requirements.txt' in a['filename']]
        if merge_files:
            print(f"\n⚠ Files Requiring Merge ({len(merge_files)} files):")
            for file in merge_files:
                print(f"  - {file['filename']}")
                print(f"    Recommendation: {file['recommendation']}")
                for diff in file['differences']:
                    print(f"    Session {diff['from_session']}→{diff['to_session']}: "
                          f"+{diff['added_lines']} -{diff['removed_lines']} lines")
        
        # Files with clear winner
        latest_version = [a for a in report['analysis'] 
                         if not a['identical'] and 
                            'merge' not in a['recommendation'].lower() and
                            a['filename'] != 'requirements.txt']
        if latest_version:
            print(f"\n→ Use Latest Version ({len(latest_version)} files):")
            for file in latest_version:
                print(f"  - {file['filename']}: {file['recommendation']}")
                total_changes = sum(d['changes'] for d in file['differences'])
                if total_changes > 0:
                    print(f"    Total changes across sessions: {total_changes} lines")
        
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        
        print("""
1. Start with Session 4 as your base (most complete implementation)
2. Merge requirements.txt from all sessions to get all dependencies
3. Use Session 5's docker-compose.yml for production
4. Copy Session 2's MS365 connectors and Fourth Ontology ingestion
5. Add Session 3's service layer and models
6. Include Session 5's infrastructure (K8s, monitoring, CI/CD)
7. Review and update import paths after consolidation
8. Run tests to verify successful integration
        """)
        
    def save_report_json(self, report: dict, output_path: str):
        """Save the report as JSON"""
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nDetailed JSON report saved to: {output_path}")


def main():
    # Define session directories
    session_dirs = [
        'session1',
        'session2', 
        'session3',
        'session4',
        'session5'
    ]
    
    # Check if all directories exist
    missing_dirs = [d for d in session_dirs if not os.path.exists(d)]
    if missing_dirs:
        print(f"Error: Missing directories: {', '.join(missing_dirs)}")
        print("Please run this script in the directory containing all session folders")
        return
    
    # Run analysis
    analyzer = BDTCodeAnalyzer(session_dirs)
    analyzer.scan_sessions()
    report = analyzer.generate_report()
    
    # Print report
    analyzer.print_report(report)
    
    # Save detailed JSON
    analyzer.save_report_json(report, 'bdt_consolidation_analysis.json')
    
    print("\nAnalysis complete! Use the consolidate_bdt.sh script to perform the actual merge.")


if __name__ == "__main__":
    main()
