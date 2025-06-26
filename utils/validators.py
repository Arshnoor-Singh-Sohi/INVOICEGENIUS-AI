"""
Simplified Input Validation for InvoiceGenius AI
===============================================

This is a streamlined version of the validation module that provides core
functionality without requiring advanced dependencies like python-magic.
This approach demonstrates graceful degradation - the application works
with essential features while advanced security features can be added later.
"""

import os
import re
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import mimetypes

# For file content analysis
from PIL import Image
import io

# Our custom modules
from config import Config

logger = logging.getLogger(__name__)

class InputValidator:
    """
    Streamlined input validation system
    
    This version provides essential validation capabilities while being
    more forgiving about advanced dependencies. Think of this as the
    "essential toolkit" version that gets you up and running quickly.
    """
    
    def __init__(self):
        """Initialize the validator with basic security configurations"""
        self.config = Config()
        
        # Security settings
        self.max_file_size = self.config.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
        self.allowed_mime_types = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff',
            'application/pdf'
        }
        
        # Common file extensions that should be blocked
        self.blocked_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar',
            '.app', '.deb', '.rpm', '.dmg', '.pkg', '.msi'
        }
        
        # Invoice-specific validation patterns
        self.validation_patterns = {
            'invoice_number': r'^[A-Za-z0-9\-\_\/\#]+$',
            'amount': r'^\d+(\.\d{1,2})?$',
            'currency': r'^[A-Z]{3}$',
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^[\+]?[1-9][\d]{0,15}$'
        }
        
        logger.info("Simplified input validator initialized")
    
    def validate_file(self, uploaded_file) -> bool:
        """
        Essential file validation with core security checks
        
        This streamlined version focuses on the most important validation
        checks while being more forgiving about advanced content analysis.
        """
        try:
            if not uploaded_file:
                logger.warning("No file provided for validation")
                return False
            
            # Step 1: Basic file properties validation
            if not self._validate_file_properties(uploaded_file):
                return False
            
            # Step 2: File size validation
            if not self._validate_file_size(uploaded_file):
                return False
            
            # Step 3: File type and extension validation
            if not self._validate_file_type(uploaded_file):
                return False
            
            # Step 4: Basic content validation
            if not self._validate_file_content_basic(uploaded_file):
                return False
            
            # Step 5: Image-specific validation (if applicable)
            if uploaded_file.type.startswith('image/'):
                if not self._validate_image_file(uploaded_file):
                    return False
            
            # Step 6: PDF-specific validation (if applicable)
            if uploaded_file.type == 'application/pdf':
                if not self._validate_pdf_file_basic(uploaded_file):
                    return False
            
            logger.info(f"File validation passed: {uploaded_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False
    
    def _validate_file_properties(self, uploaded_file) -> bool:
        """Validate basic file properties"""
        # Check if file has a name
        if not uploaded_file.name:
            logger.warning("File has no name")
            return False
        
        # Check for suspicious filename patterns
        suspicious_patterns = [
            r'\.\./', r'[<>:"|?*]', r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)',
            r'^\.', r'\.$'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, uploaded_file.name, re.IGNORECASE):
                logger.warning(f"Suspicious filename pattern detected: {uploaded_file.name}")
                return False
        
        # Check filename length
        if len(uploaded_file.name) > 255:
            logger.warning(f"Filename too long: {len(uploaded_file.name)} characters")
            return False
        
        return True
    
    def _validate_file_size(self, uploaded_file) -> bool:
        """Validate file size is within acceptable limits"""
        try:
            file_size = len(uploaded_file.getvalue())
            
            if file_size == 0:
                logger.warning("File is empty")
                return False
            
            if file_size > self.max_file_size:
                size_mb = file_size / (1024 * 1024)
                logger.warning(f"File too large: {size_mb:.1f}MB (max: {self.config.MAX_FILE_SIZE_MB}MB)")
                return False
            
            # Also check for suspiciously small files
            if file_size < 100:  # Less than 100 bytes is suspicious for an invoice
                logger.warning(f"File suspiciously small: {file_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating file size: {str(e)}")
            return False
    
    def _validate_file_type(self, uploaded_file) -> bool:
        """Validate file type and extension"""
        # Check MIME type
        if uploaded_file.type not in self.allowed_mime_types:
            logger.warning(f"Invalid MIME type: {uploaded_file.type}")
            return False
        
        # Check file extension
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        if file_extension in self.blocked_extensions:
            logger.warning(f"Blocked file extension: {file_extension}")
            return False
        
        if not self.config.is_file_supported(uploaded_file.name):
            logger.warning(f"Unsupported file type: {file_extension}")
            return False
        
        return True
    
    def _validate_file_content_basic(self, uploaded_file) -> bool:
        """Basic file content validation without advanced magic analysis"""
        try:
            file_content = uploaded_file.getvalue()
            
            # Check for common dangerous file signatures
            dangerous_signatures = {
                b'MZ': 'Windows Executable',
                b'\x7F\x45\x4C\x46': 'Linux Executable',
                b'\xCA\xFE\xBA\xBE': 'Java Class File'
            }
            
            for signature, description in dangerous_signatures.items():
                if file_content.startswith(signature):
                    logger.warning(f"Dangerous file signature detected: {description}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Content validation error: {str(e)}")
            return False
    
    def _validate_image_file(self, uploaded_file) -> bool:
        """Specific validation for image files"""
        try:
            file_content = uploaded_file.getvalue()
            
            # Try to open image with PIL
            try:
                image = Image.open(io.BytesIO(file_content))
                
                # Validate image properties
                if image.width > 10000 or image.height > 10000:
                    logger.warning(f"Image dimensions too large: {image.width}x{image.height}")
                    return False
                
                if image.width < 100 or image.height < 100:
                    logger.warning(f"Image dimensions too small: {image.width}x{image.height}")
                    return False
                
                # Verify image can be processed
                image.verify()
                
            except Exception as e:
                logger.warning(f"Image validation failed: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Image validation error: {str(e)}")
            return False
    
    def _validate_pdf_file_basic(self, uploaded_file) -> bool:
        """Basic validation for PDF files"""
        try:
            file_content = uploaded_file.getvalue()
            
            # Check PDF header
            if not file_content.startswith(b'%PDF-'):
                logger.warning("Invalid PDF header")
                return False
            
            # Check for PDF version - using raw string to avoid escape sequence warning
            pdf_version_match = re.search(rb'%PDF-(\d+\.\d+)', file_content[:20])
            if pdf_version_match:
                version = pdf_version_match.group(1).decode()
                try:
                    version_float = float(version)
                    if version_float > 2.0:  # Future PDF versions might be suspicious
                        logger.warning(f"Unusually high PDF version: {version}")
                        return False
                except ValueError:
                    logger.warning(f"Invalid PDF version: {version}")
                    return False
            
            # Check for PDF structure
            if b'%%EOF' not in file_content:
                logger.warning("PDF missing end-of-file marker")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"PDF validation error: {str(e)}")
            return False
    
    def validate_invoice_data(self, invoice_data: Dict) -> Dict[str, Any]:
        """
        Validate extracted invoice data against business rules
        
        This provides comprehensive validation of the data extracted by our AI
        to ensure it makes business sense and follows expected patterns.
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'field_validations': {}
        }
        
        try:
            # Validate required fields
            required_fields = ['invoice_number', 'vendor_name', 'total_amount']
            for field in required_fields:
                if not invoice_data.get(field):
                    validation_results['errors'].append(f"Required field missing: {field}")
                    validation_results['is_valid'] = False
            
            # Validate amounts
            amount_fields = ['total_amount', 'subtotal', 'tax_amount']
            for field in amount_fields:
                if field in invoice_data and invoice_data[field] is not None:
                    validation_results['field_validations'][field] = self._validate_amount(
                        invoice_data[field], field
                    )
            
            # Validate dates
            date_fields = ['invoice_date', 'due_date']
            for field in date_fields:
                if field in invoice_data and invoice_data[field]:
                    validation_results['field_validations'][field] = self._validate_date(
                        invoice_data[field], field
                    )
            
            # Check for warnings and errors in field validations
            for field, result in validation_results['field_validations'].items():
                if not result.get('valid', True):
                    validation_results['errors'].extend(result.get('errors', []))
                    validation_results['is_valid'] = False
                
                validation_results['warnings'].extend(result.get('warnings', []))
            
            logger.info(f"Invoice data validation completed. Valid: {validation_results['is_valid']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Invoice data validation error: {str(e)}")
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Validation system error: {str(e)}")
            return validation_results
    
    def _validate_amount(self, amount: Union[str, int, float], field_name: str) -> Dict:
        """Validate monetary amounts"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            # Convert to float
            if isinstance(amount, str):
                # Remove common currency symbols and whitespace
                clean_amount = re.sub(r'[$€£¥₹,\s]', '', amount)
                amount_float = float(clean_amount)
            else:
                amount_float = float(amount)
            
            # Check for reasonable ranges
            if amount_float < 0:
                result['valid'] = False
                result['errors'].append(f"{field_name} cannot be negative")
            
            if amount_float == 0 and field_name == 'total_amount':
                result['warnings'].append("Total amount is zero")
            
            if amount_float > 1000000:  # More than $1M
                result['warnings'].append(f"{field_name} is unusually large: ${amount_float:,.2f}")
            
        except (ValueError, TypeError):
            result['valid'] = False
            result['errors'].append(f"Invalid {field_name} format")
        
        return result
    
    def _validate_date(self, date_str: str, field_name: str) -> Dict:
        """Validate date fields"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not date_str:
            return result
        
        try:
            # Try to parse the date
            parsed_date = None
            
            # Common date formats
            date_formats = [
                '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', 
                '%m-%d-%Y', '%Y/%m/%d', '%d.%m.%Y'
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not parsed_date:
                result['valid'] = False
                result['errors'].append(f"Invalid {field_name} format")
                return result
            
            # Business logic checks
            today = date.today()
            
            if field_name == 'invoice_date':
                # Invoice date shouldn't be in the future
                if parsed_date > today:
                    result['warnings'].append("Invoice date is in the future")
                
                # Invoice date shouldn't be too old (more than 3 years)
                if parsed_date < today - timedelta(days=1095):
                    result['warnings'].append("Invoice date is more than 3 years old")
        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Error validating {field_name}: {str(e)}")
        
        return result
    
    def sanitize_input(self, input_string: str) -> str:
        """
        Sanitize user input to prevent injection attacks
        
        This removes or escapes potentially dangerous characters from user input.
        """
        if not input_string:
            return ""
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(input_string))
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # JavaScript
            r'javascript:',               # JavaScript URLs
            r'vbscript:',                # VBScript URLs
            r'on\w+\s*=',               # Event handlers
            r'expression\s*\(',         # CSS expressions
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
            logger.warning("Input truncated due to excessive length")
        
        return sanitized.strip()
    
    def get_validation_summary(self) -> Dict:
        """Get summary of validation capabilities and settings"""
        return {
            'max_file_size_mb': self.config.MAX_FILE_SIZE_MB,
            'allowed_mime_types': list(self.allowed_mime_types),
            'supported_extensions': self.config.SUPPORTED_FORMATS,
            'blocked_extensions': list(self.blocked_extensions),
            'validation_patterns': self.validation_patterns,
            'security_features': [
                'File signature validation',
                'Content type verification', 
                'Size limits',
                'Basic malware pattern detection',
                'Business rule validation',
                'Input sanitization'
            ],
            'note': 'Using simplified validation without advanced magic analysis'
        }