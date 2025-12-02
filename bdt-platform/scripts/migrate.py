#!/usr/bin/env python3
"""
BDT Platform Database Migration Manager
Handles schema migrations for all BDT databases using Alembic
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.engine import Engine
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigrationManager:
    """Manages database migrations for BDT platform"""
    
    def __init__(self, env: str = 'development'):
        self.env = env
        self.load_config()
        self.setup_alembic()
    
    def load_config(self):
        """Load database configuration from environment"""
        self.databases = {
            'main': {
                'url': os.getenv('DATABASE_URL', 'postgresql://bdt:bdt123@localhost/bdt_poc'),
                'name': 'bdt_poc'
            },
            'security': {
                'url': os.getenv('SECURITY_DB_URL', 'postgresql://bdt:bdt123@localhost/bdt_security'),
                'name': 'bdt_security'
            },
            'monitoring': {
                'url': os.getenv('MONITORING_DB_URL', 'postgresql://bdt:bdt123@localhost/bdt_monitoring'),
                'name': 'bdt_monitoring'
            }
        }
        
        # Migration directory
        self.migration_dir = Path(__file__).parent / 'migrations'
        self.migration_dir.mkdir(exist_ok=True)
    
    def setup_alembic(self):
        """Setup Alembic configuration"""
        self.alembic_ini = self.migration_dir / 'alembic.ini'
        
        # Create alembic.ini if it doesn't exist
        if not self.alembic_ini.exists():
            self.create_alembic_config()
        
        self.config = Config(str(self.alembic_ini))
    
    def create_alembic_config(self):
        """Create Alembic configuration file"""
        config_content = """
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://bdt:bdt123@localhost/bdt_poc

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 120

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
        self.alembic_ini.write_text(config_content.strip())
        logger.info(f"Created Alembic configuration at {self.alembic_ini}")
    
    def init_migrations(self, db_name: str = 'main'):
        """Initialize migration environment for a database"""
        logger.info(f"Initializing migrations for {db_name} database")
        
        # Set database URL in config
        self.config.set_main_option('sqlalchemy.url', self.databases[db_name]['url'])
        
        # Initialize Alembic
        migrations_path = self.migration_dir / db_name
        if not migrations_path.exists():
            command.init(self.config, str(migrations_path))
            logger.info(f"Initialized migrations at {migrations_path}")
        else:
            logger.info(f"Migrations already initialized at {migrations_path}")
    
    def create_migration(self, message: str, db_name: str = 'main'):
        """Create a new migration"""
        logger.info(f"Creating migration: {message} for {db_name}")
        
        self.config.set_main_option('sqlalchemy.url', self.databases[db_name]['url'])
        self.config.set_main_option('script_location', str(self.migration_dir / db_name))
        
        # Generate migration
        command.revision(self.config, autogenerate=True, message=message)
        logger.info(f"Migration created: {message}")
    
    def run_migrations(self, db_name: str = 'main', target: str = 'head'):
        """Run pending migrations"""
        logger.info(f"Running migrations for {db_name} to {target}")
        
        self.config.set_main_option('sqlalchemy.url', self.databases[db_name]['url'])
        self.config.set_main_option('script_location', str(self.migration_dir / db_name))
        
        # Run migrations
        command.upgrade(self.config, target)
        logger.info(f"Migrations completed for {db_name}")
    
    def rollback_migration(self, db_name: str = 'main', steps: int = 1):
        """Rollback migrations"""
        logger.info(f"Rolling back {steps} migration(s) for {db_name}")
        
        self.config.set_main_option('sqlalchemy.url', self.databases[db_name]['url'])
        self.config.set_main_option('script_location', str(self.migration_dir / db_name))
        
        # Rollback
        command.downgrade(self.config, f"-{steps}")
        logger.info(f"Rollback completed for {db_name}")
    
    def get_current_revision(self, db_name: str = 'main') -> str:
        """Get current migration revision"""
        self.config.set_main_option('sqlalchemy.url', self.databases[db_name]['url'])
        self.config.set_main_option('script_location', str(self.migration_dir / db_name))
        
        script = ScriptDirectory.from_config(self.config)
        
        def get_current_rev(rev, context):
            return context.get_current_revision()
        
        with self.get_engine(db_name).begin() as connection:
            self.config.attributes['connection'] = connection
            return script.run_env()
    
    def get_engine(self, db_name: str) -> Engine:
        """Get SQLAlchemy engine for database"""
        return create_engine(self.databases[db_name]['url'])
    
    def show_history(self, db_name: str = 'main'):
        """Show migration history"""
        logger.info(f"Migration history for {db_name}:")
        
        self.config.set_main_option('sqlalchemy.url', self.databases[db_name]['url'])
        self.config.set_main_option('script_location', str(self.migration_dir / db_name))
        
        command.history(self.config)
    
    def verify_database(self, db_name: str = 'main') -> bool:
        """Verify database connection and structure"""
        logger.info(f"Verifying {db_name} database...")
        
        try:
            engine = self.get_engine(db_name)
            with engine.connect() as conn:
                # Check connection
                result = conn.execute(text("SELECT 1"))
                
                # Check if alembic_version table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    )
                """))
                has_alembic = result.scalar()
                
                if not has_alembic:
                    logger.warning(f"Alembic version table not found in {db_name}")
                    self.create_alembic_table(db_name)
                
                logger.info(f"Database {db_name} verified successfully")
                return True
                
        except Exception as e:
            logger.error(f"Database verification failed for {db_name}: {e}")
            return False
    
    def create_alembic_table(self, db_name: str):
        """Create alembic version table"""
        engine = self.get_engine(db_name)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            conn.commit()
            logger.info(f"Created alembic_version table in {db_name}")
    
    def backup_database(self, db_name: str = 'main') -> str:
        """Backup database before migration"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"/backups/{db_name}_{timestamp}.sql"
        
        logger.info(f"Backing up {db_name} to {backup_file}")
        
        db_config = self.databases[db_name]
        # Parse connection URL
        # postgresql://user:password@host:port/dbname
        import re
        pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, db_config['url'])
        
        if match:
            user, password, host, port, dbname = match.groups()
            
            # Use pg_dump for backup
            cmd = f"PGPASSWORD={password} pg_dump -h {host} -p {port} -U {user} -d {dbname} -f {backup_file}"
            os.system(cmd)
            
            logger.info(f"Backup completed: {backup_file}")
            return backup_file
        else:
            logger.error(f"Failed to parse database URL for {db_name}")
            return ""
    
    def run_sql_script(self, db_name: str, script_path: str):
        """Run SQL script on database"""
        logger.info(f"Running SQL script {script_path} on {db_name}")
        
        engine = self.get_engine(db_name)
        with open(script_path, 'r') as f:
            sql = f.read()
        
        with engine.connect() as conn:
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for statement in statements:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    logger.error(f"Failed to execute statement: {e}")
                    logger.error(f"Statement: {statement[:100]}...")
            conn.commit()
        
        logger.info(f"SQL script executed successfully")
    
    def create_sample_migration(self):
        """Create a sample migration file"""
        sample_migration = '''"""Add Fourth Ontology enhancements

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    # Add new columns to personas table
    op.add_column('personas', 
        sa.Column('ontology_version', sa.Integer(), nullable=True, default=1)
    )
    op.add_column('personas',
        sa.Column('last_analysis', sa.DateTime(), nullable=True)
    )
    
    # Create new index
    op.create_index(
        'idx_personas_ontology_version',
        'personas',
        ['ontology_version']
    )
    
    # Add new table for ontology history
    op.create_table('ontology_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('decision_score', sa.Float(), nullable=True),
        sa.Column('power_score', sa.Float(), nullable=True),
        sa.Column('fear_score', sa.Float(), nullable=True),
        sa.Column('reward_score', sa.Float(), nullable=True),
        sa.Column('meaning_score', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ondelete='CASCADE'),
        sa.Index('idx_ontology_history_persona', 'persona_id'),
        sa.Index('idx_ontology_history_timestamp', 'timestamp')
    )


def downgrade():
    # Drop new table
    op.drop_table('ontology_history')
    
    # Drop index
    op.drop_index('idx_personas_ontology_version', 'personas')
    
    # Drop columns
    op.drop_column('personas', 'last_analysis')
    op.drop_column('personas', 'ontology_version')
'''
        
        # Save sample migration
        sample_path = self.migration_dir / 'sample_migration.py.example'
        sample_path.write_text(sample_migration)
        logger.info(f"Sample migration created at {sample_path}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='BDT Database Migration Manager')
    parser.add_argument('--env', default='development', 
                       choices=['development', 'staging', 'production'],
                       help='Environment to run migrations in')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize migrations')
    init_parser.add_argument('--db', default='main', 
                            choices=['main', 'security', 'monitoring'],
                            help='Database to initialize')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('message', help='Migration message')
    create_parser.add_argument('--db', default='main',
                              choices=['main', 'security', 'monitoring'],
                              help='Database to migrate')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.add_argument('--db', default='main',
                               choices=['main', 'security', 'monitoring', 'all'],
                               help='Database to migrate')
    migrate_parser.add_argument('--target', default='head', help='Target revision')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.add_argument('--db', default='main',
                                 choices=['main', 'security', 'monitoring'],
                                 help='Database to rollback')
    rollback_parser.add_argument('--steps', type=int, default=1, 
                                 help='Number of migrations to rollback')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show migration history')
    history_parser.add_argument('--db', default='main',
                               choices=['main', 'security', 'monitoring'],
                               help='Database to show history for')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify database')
    verify_parser.add_argument('--db', default='all',
                              choices=['main', 'security', 'monitoring', 'all'],
                              help='Database to verify')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup database')
    backup_parser.add_argument('--db', default='all',
                              choices=['main', 'security', 'monitoring', 'all'],
                              help='Database to backup')
    
    # SQL command
    sql_parser = subparsers.add_parser('sql', help='Run SQL script')
    sql_parser.add_argument('script', help='Path to SQL script')
    sql_parser.add_argument('--db', default='main',
                           choices=['main', 'security', 'monitoring'],
                           help='Database to run script on')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = DatabaseMigrationManager(env=args.env)
    
    # Execute command
    if args.command == 'init':
        manager.init_migrations(args.db)
    
    elif args.command == 'create':
        manager.create_migration(args.message, args.db)
    
    elif args.command == 'migrate':
        if args.db == 'all':
            for db in ['main', 'security', 'monitoring']:
                if manager.verify_database(db):
                    manager.run_migrations(db, args.target)
        else:
            if manager.verify_database(args.db):
                manager.run_migrations(args.db, args.target)
    
    elif args.command == 'rollback':
        if manager.verify_database(args.db):
            manager.backup_database(args.db)
            manager.rollback_migration(args.db, args.steps)
    
    elif args.command == 'history':
        manager.show_history(args.db)
    
    elif args.command == 'verify':
        if args.db == 'all':
            for db in ['main', 'security', 'monitoring']:
                manager.verify_database(db)
        else:
            manager.verify_database(args.db)
    
    elif args.command == 'backup':
        if args.db == 'all':
            for db in ['main', 'security', 'monitoring']:
                manager.backup_database(db)
        else:
            manager.backup_database(args.db)
    
    elif args.command == 'sql':
        manager.run_sql_script(args.db, args.script)
    
    else:
        parser.print_help()
        
        # Create sample migration for reference
        manager.create_sample_migration()


if __name__ == '__main__':
    main()
