"""
Configuration Management for InvoiceGenius AI
============================================

This module centralizes all configuration settings for the application.
Think of it as the control center where we define how our app behaves,
what models to use, and various operational parameters.

Why centralize configuration?
- Makes it easy to change settings without hunting through code
- Provides a single source of truth for all app settings
- Enables different configurations for development vs production
- Improves maintainability and reduces errors
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional
import json

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Central configuration class for InvoiceGenius AI
    
    This class acts like a settings manager, organizing all the different
    configuration options our application needs. It's designed to be flexible
    and easy to extend as we add new features.
    """
    
    def __init__(self):
        """Initialize configuration with default values and environment overrides"""
        self._load_base_config()
        self._load_ai_config()
        self._load_database_config()
        self._load_processing_config()
        self._load_export_config()
        self._load_security_config()
        self._create_directories()
    
    def _load_base_config(self):
        """Load basic application configuration"""
        # Application metadata
        self.APP_NAME = "InvoiceGenius AI"
        self.APP_VERSION = "2.0.0"
        self.APP_DESCRIPTION = "Intelligent Multi-Language Invoice Processing & Analytics"
        
        # Environment settings
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        
        # File paths - using pathlib for cross-platform compatibility
        self.BASE_DIR = Path(__file__).parent
        self.DATA_DIR = self.BASE_DIR / "data"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.EXPORTS_DIR = self.BASE_DIR / "exports"
        self.ASSETS_DIR = self.BASE_DIR / "assets"
        self.TEMPLATES_DIR = self.BASE_DIR / "templates"
    
    def _load_ai_config(self):
        """Configure AI model settings and API connections"""
        # Google Gemini Configuration
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not self.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Model selection - we'll default to the best performing model
        self.gemini_model = "gemini-1.5-pro-latest"
        
        # Available models with their characteristics
        self.AVAILABLE_MODELS = {
            "gemini-1.5-pro-latest": {
                "name": "Gemini 1.5 Pro",
                "description": "Most capable model, best for complex invoices",
                "max_tokens": 2000000,
                "cost_per_1k_tokens": 0.001,
                "best_for": ["complex_layouts", "handwritten_text", "multiple_languages"]
            },
            "gemini-1.5-flash-latest": {
                "name": "Gemini 1.5 Flash", 
                "description": "Faster processing, good for standard invoices",
                "max_tokens": 1000000,
                "cost_per_1k_tokens": 0.0005,
                "best_for": ["batch_processing", "standard_formats", "speed_priority"]
            },
            "gemini-pro": {
                "name": "Gemini Pro",
                "description": "Reliable baseline model",
                "max_tokens": 30720,
                "cost_per_1k_tokens": 0.0005,
                "best_for": ["simple_invoices", "cost_optimization"]
            }
        }
        
        # Processing parameters
        self.DEFAULT_TEMPERATURE = 0.1  # Low temperature for factual extraction
        self.MAX_OUTPUT_TOKENS = 4096
        self.SAFETY_SETTINGS = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE", 
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
        }
    
    def _load_database_config(self):
        """Configure database settings"""
        # SQLite configuration (simple and reliable for this use case)
        self.DATABASE_URL = f"sqlite:///{self.DATA_DIR}/invoices.db"
        self.DATABASE_ECHO = self.DEBUG  # Log SQL queries in debug mode
        
        # Connection pool settings
        self.DB_POOL_SIZE = 10
        self.DB_MAX_OVERFLOW = 20
        self.DB_POOL_TIMEOUT = 30
        
        # Backup settings
        self.AUTO_BACKUP = True
        self.BACKUP_FREQUENCY_HOURS = 24
        self.MAX_BACKUP_FILES = 7  # Keep one week of backups
    
    def _load_processing_config(self):
        """Configure invoice processing parameters"""
        # File handling
        self.MAX_FILE_SIZE_MB = 50
        self.SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
        self.SUPPORTED_PDF_FORMATS = [".pdf"]
        self.SUPPORTED_FORMATS = self.SUPPORTED_IMAGE_FORMATS + self.SUPPORTED_PDF_FORMATS
        
        # Processing settings
        self.DEFAULT_CONFIDENCE_THRESHOLD = 0.85
        self.ENABLE_OCR_FALLBACK = True
        self.MAX_PROCESSING_TIME_SECONDS = 300  # 5 minutes timeout
        
        # Validation settings
        self.ENABLE_DUPLICATE_DETECTION = True
        self.ENABLE_AMOUNT_VALIDATION = True
        self.ENABLE_DATE_VALIDATION = True
        
        # Language support
        self.SUPPORTED_LANGUAGES = [
            "en", "es", "fr", "de", "it", "pt", "nl", 
            "zh", "ja", "ko", "ar", "hi", "ru"
        ]
        
        # Invoice field mapping - what we extract from each invoice
        self.EXTRACTION_FIELDS = {
            "required": [
                "invoice_number", "vendor_name", "invoice_date", 
                "total_amount", "currency"
            ],
            "optional": [
                "vendor_address", "billing_address", "due_date",
                "payment_terms", "po_number", "tax_amount",
                "subtotal", "line_items", "payment_method"
            ],
            "computed": [
                "confidence_score", "processing_time", "validation_results"
            ]
        }
    
    def _load_export_config(self):
        """Configure export and reporting settings"""
        # Export formats
        self.SUPPORTED_EXPORT_FORMATS = ["excel", "pdf", "json", "csv"]
        
        # Excel export settings
        self.EXCEL_SHEET_NAME = "Invoice_Data"
        self.EXCEL_INCLUDE_CHARTS = True
        
        # PDF report settings
        self.PDF_PAGE_SIZE = "A4"
        self.PDF_INCLUDE_LOGO = True
        self.PDF_COMPANY_NAME = "InvoiceGenius AI"
        
        # Report templates
        self.REPORT_TEMPLATES = {
            "summary": "Basic invoice summary report",
            "detailed": "Comprehensive analysis with charts",
            "compliance": "Compliance and audit report",
            "vendor_analysis": "Vendor performance analysis"
        }
    
    def _load_security_config(self):
        """Configure security and privacy settings"""
        # Data retention
        self.DATA_RETENTION_DAYS = 365  # Keep data for 1 year
        self.AUTO_DELETE_PROCESSED_FILES = False
        
        # Privacy settings
        self.ANONYMIZE_SENSITIVE_DATA = False
        self.LOG_SENSITIVE_DATA = False
        
        # Rate limiting
        self.API_RATE_LIMIT_PER_MINUTE = 60
        self.MAX_CONCURRENT_PROCESSING = 5
        
        # File validation
        self.SCAN_UPLOADS_FOR_MALWARE = True
        self.MAX_UPLOAD_SIZE_MB = 100
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.DATA_DIR, 
            self.LOGS_DIR, 
            self.EXPORTS_DIR,
            self.ASSETS_DIR,
            self.TEMPLATES_DIR
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)
    
    def get_prompt_template(self, template_type: str = "default") -> str:
        """
        Get AI prompt templates for different processing scenarios
        
        Templates are pre-written instructions that guide the AI model
        to extract information in a consistent, structured way.
        """
        templates = {
            "default": """
            You are an expert AI assistant specializing in invoice analysis and data extraction.
            Your task is to carefully analyze the provided invoice image and extract all relevant information.

            Please extract the following information in JSON format:
            {
                "invoice_number": "string",
                "vendor_name": "string", 
                "vendor_address": "string",
                "invoice_date": "YYYY-MM-DD",
                "due_date": "YYYY-MM-DD",
                "total_amount": "number",
                "subtotal": "number", 
                "tax_amount": "number",
                "currency": "string",
                "payment_terms": "string",
                "po_number": "string",
                "line_items": [
                    {
                        "description": "string",
                        "quantity": "number", 
                        "unit_price": "number",
                        "total_price": "number"
                    }
                ]
            }

            Guidelines:
            - Extract dates in YYYY-MM-DD format
            - Use numbers for all amounts (no currency symbols)
            - If information is not available, use null
            - Be as accurate as possible
            - Pay attention to currency symbols and decimal separators
            """,
            
            "multilingual": """
            You are an expert multilingual invoice processor. Analyze this invoice regardless of language.
            
            Key instructions:
            - Detect the language automatically
            - Extract information even from non-English invoices
            - Translate vendor names and descriptions to English when possible
            - Maintain original currency and number formats
            - Handle different date formats correctly
            
            Return the same JSON structure but include:
            - "detected_language": "language_code"
            - "original_text": "relevant original text for key fields"
            """,
            
            "detailed_analysis": """
            Perform comprehensive invoice analysis including validation and quality checks.
            
            Extract standard information plus:
            - Calculate confidence scores for each field
            - Identify any inconsistencies or errors
            - Flag unusual patterns or potential issues
            - Verify mathematical calculations
            - Assess invoice authenticity indicators
            
            Include additional fields:
            - "validation_results": {...}
            - "confidence_scores": {...}
            - "quality_indicators": {...}
            """
        }
        
        return templates.get(template_type, templates["default"])
    
    def get_validation_rules(self) -> Dict:
        """
        Define validation rules for invoice data
        
        These rules help ensure the extracted data is reasonable and consistent.
        Think of them as quality control checks.
        """
        return {
            "invoice_number": {
                "required": True,
                "min_length": 1,
                "max_length": 50,
                "pattern": r"^[A-Za-z0-9\-\_\/]+$"
            },
            "total_amount": {
                "required": True,
                "min_value": 0,
                "max_value": 1000000,  # Adjust based on your business
                "decimal_places": 2
            },
            "invoice_date": {
                "required": True,
                "format": "YYYY-MM-DD",
                "not_future": True,
                "max_age_days": 1095  # 3 years
            },
            "vendor_name": {
                "required": True,
                "min_length": 2,
                "max_length": 200
            },
            "currency": {
                "required": True,
                "valid_codes": ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"]
            }
        }
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for easy access"""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }
    
    def update_setting(self, key: str, value):
        """Update a configuration setting dynamically"""
        if hasattr(self, key):
            setattr(self, key, value)
            return True
        return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a specific AI model"""
        return self.AVAILABLE_MODELS.get(model_name)
    
    def is_file_supported(self, filename: str) -> bool:
        """Check if a file format is supported"""
        file_extension = Path(filename).suffix.lower()
        return file_extension in self.SUPPORTED_FORMATS