#!/usr/bin/env python3
"""
BDT Platform API Testing Script
Tests all endpoints and functionality
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Optional

# Configuration
BASE_URL = "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net"
# BASE_URL = "http://localhost:8000"  # For local testing

class BDTPlatformTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.twin_id: Optional[str] = None
        self.task_id: Optional[str] = None
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️ "
        }.get(level, "")
        print(f"[{timestamp}] {prefix} {message}")
    
    def test_endpoint(self, name: str, method: str, endpoint: str, **kwargs) -> bool:
        """Test a single endpoint"""
        try:
            self.log(f"Testing {name}...")
            
            # Add auth header if token exists
            if self.token and "headers" in kwargs:
                kwargs["headers"]["Authorization"] = f"Bearer {self.token}"
            elif self.token:
                kwargs["headers"] = {"Authorization": f"Bearer {self.token}"}
            
            # Make request
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, **kwargs)
            
            # Check response
            if response.status_code >= 200 and response.status_code < 300:
                self.log(f"{name} passed", "SUCCESS")
                self.results["passed"].append(name)
                return True
            else:
                self.log(f"{name} failed: {response.status_code} - {response.text[:200]}", "ERROR")
                self.results["failed"].append(name)
                return False
                
        except Exception as e:
            self.log(f"{name} error: {str(e)}", "ERROR")
            self.results["failed"].append(name)
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        self.log("Starting BDT Platform API Tests", "INFO")
        self.log(f"Target: {self.base_url}", "INFO")
        print("=" * 50)
        
        # 1. Health Check
        self.test_health()
        
        # 2. Authentication
        self.test_demo_login()
        
        # 3. Twin Operations
        self.test_get_twins()
        
        # 4. Query Operations
        self.test_query_twin()
        
        # 5. Dashboard Views
        self.test_all_dashboards()
        
        # 6. Microsoft Auth (info only)
        self.test_microsoft_auth()
        
        # 7. Task Operations
        self.test_task_operations()
        
        # 8. Analytics
        self.test_analytics()
        
        # Print results
        self.print_results()
    
    def test_health(self):
        """Test health endpoint"""
        response = requests.get(f"{self.base_url}/health")
        if response.status_code == 200:
            data = response.json()
            self.log(f"Health: {data.get('status')}", "SUCCESS")
            
            # Check services
            checks = data.get("checks", {})
            for service, status in checks.items():
                level = "SUCCESS" if status else "WARNING"
                self.log(f"  {service}: {'✓' if status else '✗'}", level)
            
            self.results["passed"].append("Health Check")
            return True
        else:
            self.log("Health check failed", "ERROR")
            self.results["failed"].append("Health Check")
            return False
    
    def test_demo_login(self):
        """Test demo login"""
        response = requests.post(f"{self.base_url}/api/auth/demo-login")
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.log(f"Demo login successful", "SUCCESS")
            self.log(f"  Token: {self.token[:20]}...", "INFO")
            self.results["passed"].append("Demo Login")
            return True
        else:
            self.log("Demo login failed", "ERROR")
            self.results["failed"].append("Demo Login")
            return False
    
    def test_get_twins(self):
        """Test getting twins"""
        if not self.token:
            self.log("Skipping twins test - no token", "WARNING")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/twins", headers=headers)
        
        if response.status_code == 200:
            twins = response.json()
            self.log(f"Retrieved {len(twins)} twins", "SUCCESS")
            
            if twins:
                self.twin_id = twins[0]["id"]
                self.log(f"  Twin ID: {self.twin_id}", "INFO")
                self.log(f"  Name: {twins[0]['name']}", "INFO")
            
            self.results["passed"].append("Get Twins")
            return True
        else:
            self.log("Get twins failed", "ERROR")
            self.results["failed"].append("Get Twins")
            return False
    
    def test_query_twin(self):
        """Test querying twin"""
        if not self.token:
            self.log("Skipping query test - no token", "WARNING")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Test different queries
        queries = [
            {
                "query": "What are my recent activities?",
                "source_filters": ["ALL DATA"]
            },
            {
                "query": "Show me email insights",
                "source_filters": ["Email"]
            },
            {
                "query": "What's on my calendar?",
                "source_filters": ["Calendar"]
            }
        ]
        
        twin_id = self.twin_id or "demo-twin"
        passed = 0
        
        for q in queries:
            response = requests.post(
                f"{self.base_url}/api/twin/{twin_id}/query",
                headers=headers,
                json=q
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  Query: '{q['query'][:30]}...' ✓", "SUCCESS")
                self.log(f"    Confidence: {data.get('confidence', 0):.2f}", "INFO")
                passed += 1
            else:
                self.log(f"  Query failed: {q['query'][:30]}...", "ERROR")
        
        if passed == len(queries):
            self.results["passed"].append("Query Twin")
        elif passed > 0:
            self.results["warnings"].append("Query Twin (partial)")
        else:
            self.results["failed"].append("Query Twin")
        
        return passed > 0
    
    def test_all_dashboards(self):
        """Test all dashboard views"""
        if not self.token:
            self.log("Skipping dashboard tests - no token", "WARNING")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        views = [
            "knowledge", "processes", "calendar", "relationships",
            "persona", "tools", "tasks", "growth", "content"
        ]
        
        self.log("Testing dashboard views...", "INFO")
        passed = 0
        
        for view in views:
            response = requests.get(
                f"{self.base_url}/api/dashboard/{view}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                metrics = data.get("metrics", {})
                self.log(f"  {view.capitalize()}: ✓", "SUCCESS")
                
                # Show a key metric
                if metrics:
                    key = list(metrics.keys())[0]
                    self.log(f"    {key}: {metrics[key]}", "INFO")
                
                passed += 1
            else:
                self.log(f"  {view.capitalize()}: ✗", "ERROR")
        
        if passed == len(views):
            self.results["passed"].append("All Dashboards")
        elif passed > 0:
            self.results["warnings"].append(f"Dashboards ({passed}/{len(views)})")
        else:
            self.results["failed"].append("All Dashboards")
        
        return passed > 0
    
    def test_microsoft_auth(self):
        """Test Microsoft auth endpoint (info only)"""
        response = requests.get(f"{self.base_url}/api/auth/microsoft")
        
        if response.status_code == 200:
            data = response.json()
            auth_url = data.get("auth_url", "")
            
            if auth_url:
                self.log("Microsoft Auth configured", "SUCCESS")
                self.log(f"  Auth URL: {auth_url[:50]}...", "INFO")
                self.results["passed"].append("Microsoft Auth")
                return True
            else:
                self.log("Microsoft Auth URL missing", "WARNING")
                self.results["warnings"].append("Microsoft Auth")
        else:
            self.log("Microsoft Auth not available", "ERROR")
            self.results["failed"].append("Microsoft Auth")
        
        return False
    
    def test_task_operations(self):
        """Test task operations"""
        if not self.token:
            self.log("Skipping task tests - no token", "WARNING")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get task list
        response = requests.get(
            f"{self.base_url}/api/tasks",
            headers=headers
        )
        
        if response.status_code == 200:
            tasks = response.json()
            self.log(f"Retrieved {len(tasks)} tasks", "SUCCESS")
            
            if tasks:
                # Check status of first task
                task_id = tasks[0]["task_id"]
                status_response = requests.get(
                    f"{self.base_url}/api/tasks/{task_id}",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status = status_response.json()
                    self.log(f"  Task {task_id[:8]}... status: {status.get('status')}", "INFO")
            
            self.results["passed"].append("Task Operations")
            return True
        else:
            self.log("Task operations failed", "ERROR")
            self.results["failed"].append("Task Operations")
            return False
    
    def test_analytics(self):
        """Test analytics endpoint"""
        if not self.token:
            self.log("Skipping analytics test - no token", "WARNING")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/analytics/overview",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("summary", {})
            
            self.log("Analytics retrieved", "SUCCESS")
            self.log(f"  Total records: {summary.get('total_records', 0)}", "INFO")
            self.log(f"  Sources: {summary.get('sources', 0)}", "INFO")
            
            # Show insights
            insights = data.get("insights", [])
            if insights:
                self.log(f"  Insights: {insights[0]}", "INFO")
            
            self.results["passed"].append("Analytics")
            return True
        else:
            self.log("Analytics failed", "ERROR")
            self.results["failed"].append("Analytics")
            return False
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 50)
        self.log("TEST RESULTS SUMMARY", "INFO")
        print("=" * 50)
        
        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["warnings"])
        
        # Passed tests
        if self.results["passed"]:
            self.log(f"PASSED: {len(self.results['passed'])}/{total}", "SUCCESS")
            for test in self.results["passed"]:
                print(f"  ✅ {test}")
        
        # Warning tests
        if self.results["warnings"]:
            self.log(f"WARNINGS: {len(self.results['warnings'])}", "WARNING")
            for test in self.results["warnings"]:
                print(f"  ⚠️  {test}")
        
        # Failed tests
        if self.results["failed"]:
            self.log(f"FAILED: {len(self.results['failed'])}", "ERROR")
            for test in self.results["failed"]:
                print(f"  ❌ {test}")
        
        # Overall result
        print("\n" + "=" * 50)
        if not self.results["failed"]:
            self.log("🎉 ALL CRITICAL TESTS PASSED!", "SUCCESS")
            print("Your BDT Platform is working correctly!")
        elif len(self.results["failed"]) <= 2:
            self.log("⚠️  MOSTLY WORKING - Minor issues detected", "WARNING")
            print("Platform is functional but some features may not work")
        else:
            self.log("❌ CRITICAL ISSUES DETECTED", "ERROR")
            print("Please check logs and fix the issues")
        
        print("=" * 50)
        
        # Return exit code
        return 0 if not self.results["failed"] else 1

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test BDT Platform API")
    parser.add_argument("--url", default=BASE_URL, help="API base URL")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    args = parser.parse_args()
    
    tester = BDTPlatformTester(args.url)
    
    if args.quick:
        # Quick test - just health and auth
        tester.test_health()
        tester.test_demo_login()
        tester.print_results()
    else:
        # Full test suite
        tester.run_all_tests()
    
    sys.exit(0 if not tester.results["failed"] else 1)

if __name__ == "__main__":
    main()
