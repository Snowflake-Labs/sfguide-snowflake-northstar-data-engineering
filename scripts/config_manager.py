"""
Configuration Management System for Snowflake Data Pipeline
Provides centralized configuration management and validation
"""

import yaml
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

@dataclass
class DatabaseConfig:
    name: str
    schemas: Dict[str, str]

@dataclass
class DataQualityRule:
    name: str
    type: str
    threshold: float
    critical: bool
    rules: Optional[Dict[str, List[float]]] = None

@dataclass
class PipelineStage:
    batch_size: Optional[int] = None
    parallel_workers: Optional[int] = None
    error_handling: Optional[str] = None
    warehouse_size: Optional[str] = None
    timeout_minutes: Optional[int] = None
    auto_suspend_minutes: Optional[int] = None
    export_formats: Optional[List[str]] = None
    compression: Optional[str] = None

class ConfigManager:
    """
    Centralized configuration management for the Snowflake data pipeline
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                self._validate_config(config)
                return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in config file: {e}")
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate required configuration sections"""
        required_sections = ['database', 'data_sources', 'data_quality', 'pipeline']
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
    
    def _setup_logging(self) -> None:
        """Setup logging based on configuration"""
        log_level = self.config.get('pipeline', {}).get('logging', {}).get('level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_config = self.config['database']
        return DatabaseConfig(
            name=db_config['name'],
            schemas=db_config['schemas']
        )
    
    def get_data_source_config(self, source_name: str) -> Dict[str, Any]:
        """Get configuration for a specific data source"""
        data_sources = self.config.get('data_sources', {})
        if source_name not in data_sources:
            raise KeyError(f"Data source '{source_name}' not found in configuration")
        return data_sources[source_name]
    
    def get_data_quality_rules(self) -> List[DataQualityRule]:
        """Get data quality validation rules"""
        quality_config = self.config.get('data_quality', {})
        rules_config = quality_config.get('validation_rules', [])
        
        rules = []
        for rule_config in rules_config:
            rule = DataQualityRule(
                name=rule_config['name'],
                type=rule_config['type'],
                threshold=rule_config['threshold'],
                critical=rule_config['critical'],
                rules=rule_config.get('rules')
            )
            rules.append(rule)
        
        return rules
    
    def get_pipeline_stage_config(self, stage_name: str) -> PipelineStage:
        """Get configuration for a specific pipeline stage"""
        pipeline_config = self.config.get('pipeline', {})
        stages_config = pipeline_config.get('stages', {})
        
        if stage_name not in stages_config:
            raise KeyError(f"Pipeline stage '{stage_name}' not found in configuration")
        
        stage_config = stages_config[stage_name]
        return PipelineStage(**stage_config)
    
    def get_snowflake_connection_params(self) -> Dict[str, str]:
        """Get Snowflake connection parameters from environment variables"""
        required_params = [
            'SNOWFLAKE_ACCOUNT',
            'SNOWFLAKE_USER',
            'SNOWFLAKE_PASSWORD',
            'SNOWFLAKE_WAREHOUSE',
            'SNOWFLAKE_ROLE'
        ]
        
        connection_params = {}
        missing_params = []
        
        for param in required_params:
            value = os.getenv(param)
            if value:
                connection_params[param.lower().replace('snowflake_', '')] = value
            else:
                missing_params.append(param)
        
        if missing_params:
            raise ValueError(f"Missing required environment variables: {missing_params}")
        
        # Add database from config
        db_config = self.get_database_config()
        connection_params['database'] = db_config.name
        
        return connection_params
    
    def get_streamlit_config(self) -> Dict[str, Any]:
        """Get Streamlit application configuration"""
        return self.config.get('streamlit', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.config.get('monitoring', {})
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """Update a configuration value"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        self._save_config()
        self.logger.info(f"Updated configuration: {section}.{key} = {value}")
    
    def _save_config(self) -> None:
        """Save configuration back to file"""
        with open(self.config_path, 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False, indent=2)
    
    def validate_data_quality_thresholds(self) -> Dict[str, bool]:
        """Validate that data quality thresholds are reasonable"""
        rules = self.get_data_quality_rules()
        validation_results = {}
        
        for rule in rules:
            is_valid = True
            
            if rule.type == "completeness" and not (0 <= rule.threshold <= 100):
                is_valid = False
            elif rule.type == "uniqueness" and not (0 <= rule.threshold <= 100):
                is_valid = False
            elif rule.type == "timeliness" and rule.threshold < 0:
                is_valid = False
            
            validation_results[rule.name] = is_valid
            
            if not is_valid:
                self.logger.warning(f"Invalid threshold for rule '{rule.name}': {rule.threshold}")
        
        return validation_results
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        return {
            'database': self.get_database_config().name,
            'data_sources': list(self.config.get('data_sources', {}).keys()),
            'data_quality_rules': len(self.get_data_quality_rules()),
            'pipeline_stages': list(self.config.get('pipeline', {}).get('stages', {}).keys()),
            'monitoring_enabled': self.config.get('monitoring', {}).get('enabled', False),
            'config_file': str(self.config_path)
        }


def create_default_config(output_path: str = "config.yaml") -> None:
    """Create a default configuration file"""
    default_config = {
        'database': {
            'name': 'TASTY_BYTES',
            'schemas': {
                'raw': 'RAW_DATA',
                'harmonized': 'HARMONIZED',
                'analytics': 'ANALYTICS'
            }
        },
        'data_sources': {
            'weather_data': {
                'table': 'weather_hamburg',
                'schema': 'harmonized',
                'refresh_frequency': 'daily',
                'retention_days': 365
            }
        },
        'data_quality': {
            'validation_rules': [
                {
                    'name': 'null_check',
                    'type': 'completeness',
                    'threshold': 95,
                    'critical': True
                }
            ]
        },
        'pipeline': {
            'stages': {
                'ingestion': {
                    'batch_size': 10000,
                    'parallel_workers': 4
                }
            },
            'logging': {
                'level': 'INFO'
            }
        }
    }
    
    with open(output_path, 'w') as file:
        yaml.dump(default_config, file, default_flow_style=False, indent=2)


if __name__ == "__main__":
    # Example usage
    try:
        config_manager = ConfigManager("config.yaml")
        
        # Print configuration summary
        summary = config_manager.get_config_summary()
        print("Configuration Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Validate data quality thresholds
        validation_results = config_manager.validate_data_quality_thresholds()
        print(f"\nData Quality Validation: {validation_results}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Creating default configuration file...")
        create_default_config()
        print("Default config.yaml created successfully!")