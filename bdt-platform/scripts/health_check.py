#!/usr/bin/env python3
"""
BDT Platform Health Check Script
Comprehensive health monitoring for all platform components
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import logging

import aiohttp
import asyncpg
import redis.asyncio as aioredis
from prometheus_client.parser import text_string_to_metric_families
import psutil
from tabulate import tabulate
from colorama import init, Fore, Back, Style


# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive health checker for BDT platform"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_all_checks(self) -> Dict:
        """Run all health checks"""
        self.start_time = datetime.now()
        
        checks = [
            self.check_api_services(),
            self.check_databases(),
            self.check_cache(),
            self.check_message_queue(),
            self.check_vector_db(),
            self.check_system_resources(),
            self.check_ingestion_pipeline(),
            self.check_security_services(),
            self.check_monitoring_stack(),
            self.check_network_connectivity()
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        self.end_time = datetime.now()
        return self.compile_results()
    
    async def check_api_services(self) -> Dict:
        """Check all API services health"""
        services = {
            "orchestration": f"{self.config['orchestration_url']}/",
            "security": f"{self.config['security_url']}/",
            "ingestion": f"{self.config['ingestion_url']}/",
            "processing": f"{self.config['processing_url']}/",
            "analysis": f"{self.config['analysis_url']}/",
            "ui_backend": f"{self.config['ui_backend_url']}/",
            "monitoring": f"{self.config['monitoring_url']}/api/v1/health"
        }
        
        results = {}
        async with aiohttp.ClientSession() as session:
            for service_name, url in services.items():
                try:
                    start = time.time()
                    async with session.get(url, timeout=5) as response:
                        response_time = (time.time() - start) * 1000  # ms
                        
                        if response.status == 200:
                            results[service_name] = {
                                "status": "healthy",
                                "response_time_ms": round(response_time, 2),
                                "status_code": response.status
                            }
                        else:
                            results[service_name] = {
                                "status": "degraded",
                                "response_time_ms": round(response_time, 2),
                                "status_code": response.status,
                                "error": f"HTTP {response.status}"
                            }
                
                except asyncio.TimeoutError:
                    results[service_name] = {
                        "status": "unhealthy",
                        "error": "Timeout (>5s)"
                    }
                except Exception as e:
                    results[service_name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
        
        self.results["api_services"] = results
        return results
    
    async def check_databases(self) -> Dict:
        """Check PostgreSQL database health"""
        results = {}
        
        databases = {
            "main": self.config['database_url'],
            "security": self.config.get('security_db_url', self.config['database_url'].replace('bdt_poc', 'bdt_security')),
            "monitoring": self.config.get('monitoring_db_url', self.config['database_url'].replace('bdt_poc', 'bdt_monitoring'))
        }
        
        for db_name, db_url in databases.items():
            try:
                conn = await asyncpg.connect(db_url, timeout=5)
                
                # Check basic connectivity
                start = time.time()
                await conn.fetchval("SELECT 1")
                query_time = (time.time() - start) * 1000
                
                # Get database size
                db_size = await conn.fetchval("""
                    SELECT pg_database_size(current_database())
                """)
                
                # Get connection count
                conn_count = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity
                """)
                
                # Get slow query count
                slow_queries = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_statements 
                    WHERE mean_exec_time > 1000
                """) if db_name == 'main' else 0
                
                # Check replication lag (if applicable)
                replication_lag = await conn.fetchval("""
                    SELECT extract(epoch from (now() - pg_last_xact_replay_timestamp()))::int
                """) if await self.is_replica(conn) else None
                
                results[db_name] = {
                    "status": "healthy",
                    "query_time_ms": round(query_time, 2),
                    "database_size_mb": round(db_size / 1024 / 1024, 2),
                    "connections": conn_count,
                    "slow_queries": slow_queries,
                    "replication_lag_s": replication_lag
                }
                
                await conn.close()
                
            except asyncio.TimeoutError:
                results[db_name] = {
                    "status": "unhealthy",
                    "error": "Connection timeout"
                }
            except Exception as e:
                results[db_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        self.results["databases"] = results
        return results
    
    async def check_cache(self) -> Dict:
        """Check Redis cache health"""
        try:
            redis = await aioredis.from_url(
                self.config['redis_url'],
                socket_connect_timeout=5
            )
            
            # Ping
            start = time.time()
            await redis.ping()
            ping_time = (time.time() - start) * 1000
            
            # Get info
            info = await redis.info()
            
            # Get memory usage
            memory_used = info.get('used_memory', 0)
            memory_peak = info.get('used_memory_peak', 0)
            
            # Get key count
            key_count = await redis.dbsize()
            
            # Get connected clients
            connected_clients = info.get('connected_clients', 0)
            
            # Get ops/sec
            ops_per_sec = info.get('instantaneous_ops_per_sec', 0)
            
            result = {
                "status": "healthy",
                "ping_time_ms": round(ping_time, 2),
                "memory_used_mb": round(memory_used / 1024 / 1024, 2),
                "memory_peak_mb": round(memory_peak / 1024 / 1024, 2),
                "key_count": key_count,
                "connected_clients": connected_clients,
                "ops_per_sec": ops_per_sec
            }
            
            await redis.close()
            
        except Exception as e:
            result = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        self.results["redis"] = result
        return result
    
    async def check_message_queue(self) -> Dict:
        """Check RabbitMQ health"""
        try:
            async with aiohttp.ClientSession() as session:
                # RabbitMQ Management API
                url = f"{self.config['rabbitmq_mgmt_url']}/api/overview"
                auth = aiohttp.BasicAuth('bdt', 'bdt123')
                
                async with session.get(url, auth=auth, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result = {
                            "status": "healthy",
                            "queue_count": len(data.get('queue_totals', {}).get('messages', 0)),
                            "message_count": data.get('queue_totals', {}).get('messages', 0),
                            "message_rate": data.get('message_stats', {}).get('publish_details', {}).get('rate', 0),
                            "connections": len(data.get('contexts', [])),
                            "channels": len(data.get('channels', []))
                        }
                    else:
                        result = {
                            "status": "degraded",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            result = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        self.results["rabbitmq"] = result
        return result
    
    async def check_vector_db(self) -> Dict:
        """Check Qdrant vector database health"""
        try:
            async with aiohttp.ClientSession() as session:
                # Qdrant health endpoint
                url = f"{self.config['qdrant_url']}/health"
                
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        # Get collections info
                        collections_url = f"{self.config['qdrant_url']}/collections"
                        async with session.get(collections_url, timeout=5) as coll_response:
                            if coll_response.status == 200:
                                coll_data = await coll_response.json()
                                collections = coll_data.get('result', {}).get('collections', [])
                                
                                result = {
                                    "status": "healthy",
                                    "collections": len(collections),
                                    "total_vectors": sum(c.get('vectors_count', 0) for c in collections)
                                }
                            else:
                                result = {
                                    "status": "degraded",
                                    "warning": "Could not get collection info"
                                }
                    else:
                        result = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            result = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        self.results["qdrant"] = result
        return result
    
    async def check_system_resources(self) -> Dict:
        """Check system resource utilization"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            result = {
                "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning",
                "cpu_percent": cpu_percent,
                "cpu_cores": cpu_count,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "network_sent_mb": round(net_io.bytes_sent / 1024 / 1024, 2),
                "network_recv_mb": round(net_io.bytes_recv / 1024 / 1024, 2),
                "process_count": process_count
            }
        except Exception as e:
            result = {
                "status": "unknown",
                "error": str(e)
            }
        
        self.results["system_resources"] = result
        return result
    
    async def check_ingestion_pipeline(self) -> Dict:
        """Check ingestion pipeline status"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check ingestion queue
                url = f"{self.config['orchestration_url']}/api/v1/ingestion/status"
                
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result = {
                            "status": "healthy",
                            "active_jobs": data.get('active_jobs', 0),
                            "queued_jobs": data.get('queued_jobs', 0),
                            "completed_today": data.get('completed_today', 0),
                            "failed_today": data.get('failed_today', 0),
                            "avg_processing_time_s": data.get('avg_processing_time', 0)
                        }
                        
                        # Check for warnings
                        if data.get('queued_jobs', 0) > 100:
                            result["status"] = "warning"
                            result["warning"] = "High queue backlog"
                        
                        if data.get('failed_today', 0) > 10:
                            result["status"] = "warning"
                            result["warning"] = "High failure rate"
                    else:
                        result = {
                            "status": "unknown",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            result = {
                "status": "unknown",
                "error": str(e)
            }
        
        self.results["ingestion_pipeline"] = result
        return result
    
    async def check_security_services(self) -> Dict:
        """Check security services status"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check auth service
                auth_url = f"{self.config['security_url']}/api/v1/auth/health"
                
                async with session.get(auth_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result = {
                            "status": "healthy",
                            "active_sessions": data.get('active_sessions', 0),
                            "failed_login_attempts_1h": data.get('failed_attempts_1h', 0),
                            "mfa_enabled_users": data.get('mfa_users', 0),
                            "audit_logs_today": data.get('audit_logs_today', 0)
                        }
                        
                        # Check for security warnings
                        if data.get('failed_attempts_1h', 0) > 100:
                            result["status"] = "warning"
                            result["warning"] = "High failed login attempts"
                    else:
                        result = {
                            "status": "unknown",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            result = {
                "status": "unknown",
                "error": str(e)
            }
        
        self.results["security"] = result
        return result
    
    async def check_monitoring_stack(self) -> Dict:
        """Check monitoring stack (Prometheus, Grafana, Jaeger)"""
        results = {}
        
        # Check Prometheus
        try:
            async with aiohttp.ClientSession() as session:
                prom_url = f"{self.config['prometheus_url']}/api/v1/query"
                params = {"query": "up"}
                
                async with session.get(prom_url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        up_targets = sum(1 for r in data['data']['result'] if r['value'][1] == '1')
                        total_targets = len(data['data']['result'])
                        
                        results["prometheus"] = {
                            "status": "healthy",
                            "up_targets": up_targets,
                            "total_targets": total_targets
                        }
                    else:
                        results["prometheus"] = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            results["prometheus"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Grafana
        try:
            async with aiohttp.ClientSession() as session:
                grafana_url = f"{self.config['grafana_url']}/api/health"
                
                async with session.get(grafana_url, timeout=5) as response:
                    if response.status == 200:
                        results["grafana"] = {"status": "healthy"}
                    else:
                        results["grafana"] = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            results["grafana"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Jaeger
        try:
            async with aiohttp.ClientSession() as session:
                jaeger_url = f"{self.config['jaeger_url']}/api/services"
                
                async with session.get(jaeger_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        results["jaeger"] = {
                            "status": "healthy",
                            "services_tracked": len(data.get('data', []))
                        }
                    else:
                        results["jaeger"] = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            results["jaeger"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        self.results["monitoring_stack"] = results
        return results
    
    async def check_network_connectivity(self) -> Dict:
        """Check network connectivity to external services"""
        results = {}
        
        endpoints = {
            "openai_api": "https://api.openai.com/v1/models",
            "microsoft_graph": "https://graph.microsoft.com/v1.0/$metadata",
            "google_apis": "https://www.googleapis.com/discovery/v1/apis"
        }
        
        async with aiohttp.ClientSession() as session:
            for name, url in endpoints.items():
                try:
                    start = time.time()
                    async with session.head(url, timeout=5) as response:
                        latency = (time.time() - start) * 1000
                        
                        results[name] = {
                            "status": "reachable" if response.status < 500 else "degraded",
                            "latency_ms": round(latency, 2),
                            "status_code": response.status
                        }
                except Exception as e:
                    results[name] = {
                        "status": "unreachable",
                        "error": str(e)
                    }
        
        self.results["network_connectivity"] = results
        return results
    
    async def is_replica(self, conn) -> bool:
        """Check if database is a replica"""
        try:
            is_replica = await conn.fetchval("SELECT pg_is_in_recovery()")
            return is_replica
        except:
            return False
    
    def compile_results(self) -> Dict:
        """Compile all health check results"""
        # Determine overall status
        all_statuses = []
        
        def extract_status(obj):
            if isinstance(obj, dict):
                if 'status' in obj:
                    all_statuses.append(obj['status'])
                for value in obj.values():
                    extract_status(value)
        
        extract_status(self.results)
        
        if any(s == 'unhealthy' for s in all_statuses):
            overall_status = 'unhealthy'
        elif any(s in ['degraded', 'warning'] for s in all_statuses):
            overall_status = 'degraded'
        elif all(s == 'healthy' for s in all_statuses):
            overall_status = 'healthy'
        else:
            overall_status = 'unknown'
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "check_duration_ms": (self.end_time - self.start_time).total_seconds() * 1000,
            "checks": self.results
        }
    
    def print_results(self):
        """Print formatted health check results"""
        print("\n" + "="*80)
        print(f"{Style.BRIGHT}BDT Platform Health Check Results{Style.RESET_ALL}")
        print("="*80)
        
        # Overall status
        overall = self.compile_results()
        status_color = {
            'healthy': Fore.GREEN,
            'degraded': Fore.YELLOW,
            'unhealthy': Fore.RED,
            'unknown': Fore.CYAN
        }.get(overall['overall_status'], Fore.WHITE)
        
        print(f"\n{Style.BRIGHT}Overall Status:{Style.RESET_ALL} {status_color}{overall['overall_status'].upper()}{Fore.RESET}")
        print(f"Check Duration: {overall['check_duration_ms']:.2f}ms")
        print(f"Timestamp: {overall['timestamp']}")
        
        # API Services
        print(f"\n{Style.BRIGHT}API Services:{Style.RESET_ALL}")
        if 'api_services' in self.results:
            table_data = []
            for service, data in self.results['api_services'].items():
                status = data.get('status', 'unknown')
                color = {
                    'healthy': Fore.GREEN,
                    'degraded': Fore.YELLOW,
                    'unhealthy': Fore.RED
                }.get(status, Fore.WHITE)
                
                table_data.append([
                    service,
                    f"{color}{status}{Fore.RESET}",
                    f"{data.get('response_time_ms', 'N/A')}ms" if 'response_time_ms' in data else data.get('error', 'N/A')
                ])
            
            print(tabulate(table_data, headers=["Service", "Status", "Response Time/Error"], tablefmt="grid"))
        
        # Databases
        print(f"\n{Style.BRIGHT}Databases:{Style.RESET_ALL}")
        if 'databases' in self.results:
            table_data = []
            for db, data in self.results['databases'].items():
                status = data.get('status', 'unknown')
                color = {
                    'healthy': Fore.GREEN,
                    'unhealthy': Fore.RED
                }.get(status, Fore.WHITE)
                
                table_data.append([
                    db,
                    f"{color}{status}{Fore.RESET}",
                    f"{data.get('database_size_mb', 'N/A')}MB" if 'database_size_mb' in data else 'N/A',
                    data.get('connections', 'N/A'),
                    data.get('error', 'OK') if 'error' in data else 'OK'
                ])
            
            print(tabulate(table_data, headers=["Database", "Status", "Size", "Connections", "Notes"], tablefmt="grid"))
        
        # System Resources
        print(f"\n{Style.BRIGHT}System Resources:{Style.RESET_ALL}")
        if 'system_resources' in self.results:
            res = self.results['system_resources']
            table_data = [
                ["CPU", f"{res.get('cpu_percent', 'N/A')}%", f"{res.get('cpu_cores', 'N/A')} cores"],
                ["Memory", f"{res.get('memory_percent', 'N/A')}%", f"{res.get('memory_available_gb', 'N/A')}GB available"],
                ["Disk", f"{res.get('disk_percent', 'N/A')}%", f"{res.get('disk_free_gb', 'N/A')}GB free"],
                ["Network", f"↑{res.get('network_sent_mb', 'N/A')}MB", f"↓{res.get('network_recv_mb', 'N/A')}MB"]
            ]
            print(tabulate(table_data, headers=["Resource", "Usage", "Details"], tablefmt="grid"))
        
        print("\n" + "="*80)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='BDT Platform Health Check')
    parser.add_argument('--config', default='config.json', help='Configuration file')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    # Default configuration
    config = {
        "orchestration_url": "http://localhost:8000",
        "security_url": "http://localhost:8005",
        "ingestion_url": "http://localhost:8001",
        "processing_url": "http://localhost:8002",
        "analysis_url": "http://localhost:8003",
        "ui_backend_url": "http://localhost:8004",
        "monitoring_url": "http://localhost:9090",
        "database_url": "postgresql://bdt:bdt123@localhost/bdt_poc",
        "redis_url": "redis://localhost:6379",
        "rabbitmq_mgmt_url": "http://localhost:15672",
        "qdrant_url": "http://localhost:6333",
        "prometheus_url": "http://localhost:9091",
        "grafana_url": "http://localhost:3001",
        "jaeger_url": "http://localhost:16686"
    }
    
    # Load config from file if provided
    try:
        import os
        if os.path.exists(args.config):
            with open(args.config, 'r') as f:
                config.update(json.load(f))
    except Exception as e:
        logger.warning(f"Could not load config file: {e}")
    
    # Create health checker
    checker = HealthChecker(config)
    
    # Run checks
    if args.continuous:
        print(f"Starting continuous health monitoring (interval: {args.interval}s)")
        while True:
            results = await checker.run_all_checks()
            
            if args.format == 'json':
                print(json.dumps(results, indent=2))
            else:
                checker.print_results()
            
            await asyncio.sleep(args.interval)
    else:
        results = await checker.run_all_checks()
        
        if args.format == 'json':
            print(json.dumps(results, indent=2))
        else:
            checker.print_results()
        
        # Exit with appropriate code
        if results['overall_status'] == 'unhealthy':
            sys.exit(2)
        elif results['overall_status'] == 'degraded':
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
