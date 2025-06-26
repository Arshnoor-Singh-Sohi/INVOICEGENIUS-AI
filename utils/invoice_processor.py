"""
Invoice Processing Engine - The AI Brain of InvoiceGenius
========================================================

This module is the heart of our invoice processing system. Think of it as a skilled
accountant who can look at any invoice and instantly understand what information
is important and where to find it.

The key insight here is that we're not just doing basic OCR (text recognition).
We're using advanced AI that understands the context and meaning of different
parts of an invoice. This is like the difference between reading individual letters
versus understanding the meaning of entire sentences.

Why use Google Gemini?
- Multimodal: Can process both text and images natively
- Multilingual: Handles invoices in many languages automatically  
- Context-aware: Understands invoice layouts and business semantics
- Reliable: Consistent extraction with high accuracy
- Scalable: Can handle varying invoice formats and complexities
"""

import os
import json
import time
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Union, Any
from PIL import Image
import io
import base64
import re

# Google Gemini imports
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Our custom modules
from config import Config

logger = logging.getLogger(__name__)

class InvoiceProcessor:
    """
    The main AI processing engine for invoice extraction
    
    This class orchestrates the entire process:
    1. Takes an uploaded invoice (image or PDF)
    2. Prepares it for AI analysis
    3. Sends it to Google Gemini with carefully crafted prompts
    4. Processes and validates the AI response
    5. Returns structured, clean data
    
    Think of this as your AI assistant that never gets tired of reading invoices!
    """
    
    def __init__(self):
        """Initialize the processor with configuration and AI model"""
        self.config = Config()
        self._setup_gemini()
        self._initialize_models()
        
        # Processing statistics for monitoring
        self.processing_stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_processing_time': 0.0,
            'total_processing_time': 0.0
        }
    
    def _setup_gemini(self):
        """Configure Google Gemini AI with our API key and safety settings"""
        try:
            # Configure the Gemini API
            genai.configure(api_key=self.config.GOOGLE_API_KEY)
            
            # Set up safety settings - we want minimal filtering for business documents
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            logger.info("Gemini AI configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure Gemini AI: {str(e)}")
            raise RuntimeError("Could not initialize AI processing engine")
    
    def _initialize_models(self):
        """Initialize different AI models for different processing needs"""
        try:
            # Primary model for general invoice processing
            self.primary_model = GenerativeModel(
                model_name=self.config.gemini_model,
                safety_settings=self.safety_settings
            )
            
            # Specialized models for different scenarios
            self.models = {
                'general': self.primary_model,
                'detailed': GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    safety_settings=self.safety_settings
                ),
                'fast': GenerativeModel(
                    model_name="gemini-1.5-flash-latest", 
                    safety_settings=self.safety_settings
                )
            }
            
            logger.info(f"Initialized {len(self.models)} AI models")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {str(e)}")
            raise
    
    def process_invoice(self, uploaded_file, custom_prompt: str = "", settings: Dict = None) -> Optional[Dict]:
        """
        Main method to process an invoice file
        
        This is the orchestrator method that coordinates the entire processing pipeline.
        It's designed to handle various file types and gracefully manage errors.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            custom_prompt: Additional instructions from the user
            settings: Processing configuration options
            
        Returns:
            Dictionary containing extracted invoice data or None if processing failed
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate and prepare the input
            if not self._validate_input(uploaded_file):
                logger.warning(f"Invalid input file: {uploaded_file.name}")
                return None
            
            # Step 2: Convert file to format suitable for AI processing
            image_data = self._prepare_image_for_ai(uploaded_file)
            if not image_data:
                logger.error(f"Failed to prepare image: {uploaded_file.name}")
                return None
            
            # Step 3: Choose the right AI model based on settings
            model = self._select_model(settings)
            
            # Step 4: Create the processing prompt
            prompt = self._build_processing_prompt(custom_prompt, settings)
            
            # Step 5: Send to AI for processing
            ai_response = self._call_gemini_api(model, prompt, image_data)
            if not ai_response:
                logger.error(f"AI processing failed for: {uploaded_file.name}")
                return None
            
            # Step 6: Parse and validate the AI response
            extracted_data = self._parse_ai_response(ai_response)
            if not extracted_data:
                logger.error(f"Failed to parse AI response for: {uploaded_file.name}")
                return None
            
            # Step 7: Add metadata and processing information
            result = self._enrich_extraction_data(
                extracted_data, 
                uploaded_file, 
                start_time, 
                settings
            )
            
            # Step 8: Validate the extracted data
            validation_results = self._validate_extracted_data(result)
            result['validation_results'] = validation_results
            result['validation_score'] = self._calculate_validation_score(validation_results)
            
            # Update statistics
            self._update_processing_stats(start_time, success=True)
            
            logger.info(f"Successfully processed invoice: {uploaded_file.name}")
            return result
            
        except Exception as e:
            self._update_processing_stats(start_time, success=False)
            logger.error(f"Error processing invoice {uploaded_file.name}: {str(e)}")
            return None
    
    def _validate_input(self, uploaded_file) -> bool:
        """
        Validate that the uploaded file is suitable for processing
        
        This is our first line of defense - making sure we can actually
        work with what the user has given us.
        """
        if not uploaded_file:
            return False
        
        # Check file size
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > self.config.MAX_FILE_SIZE_MB:
            logger.warning(f"File too large: {file_size_mb:.1f}MB")
            return False
        
        # Check file format
        if not self.config.is_file_supported(uploaded_file.name):
            logger.warning(f"Unsupported file format: {uploaded_file.name}")
            return False
        
        return True
    
    def _prepare_image_for_ai(self, uploaded_file) -> Optional[Dict]:
        """
        Convert uploaded file into format that Gemini AI can process
        
        Gemini is multimodal, meaning it can work directly with images.
        But we need to prepare the data in the right format.
        """
        try:
            # Get file bytes
            file_bytes = uploaded_file.getvalue()
            
            # Handle different file types
            if uploaded_file.type.startswith('image/'):
                # Direct image processing
                mime_type = uploaded_file.type
                
                # Optional: Enhance image quality for better OCR
                if self.config.ENABLE_OCR_FALLBACK:
                    file_bytes = self._enhance_image_quality(file_bytes)
                
            elif uploaded_file.type == 'application/pdf':
                # Convert PDF to image (we'll implement this)
                file_bytes, mime_type = self._convert_pdf_to_image(file_bytes)
                
            else:
                logger.error(f"Unsupported file type: {uploaded_file.type}")
                return None
            
            # Prepare for Gemini API
            return {
                "mime_type": mime_type,
                "data": file_bytes
            }
            
        except Exception as e:
            logger.error(f"Error preparing image: {str(e)}")
            return None
    
    def _enhance_image_quality(self, image_bytes: bytes) -> bytes:
        """
        Enhance image quality for better AI recognition
        
        Sometimes invoices are scanned poorly or have low resolution.
        We can apply some basic image processing to improve results.
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too small (AI works better with higher resolution)
            width, height = image.size
            if width < 1000 or height < 1000:
                # Calculate new size maintaining aspect ratio
                scale_factor = max(1000/width, 1000/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG', quality=95)
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.warning(f"Image enhancement failed, using original: {str(e)}")
            return image_bytes
    
    def _convert_pdf_to_image(self, pdf_bytes: bytes) -> tuple:
        """
        Convert PDF to image for AI processing
        
        Many invoices come as PDFs. We need to convert them to images
        so our AI can analyze them visually.
        """
        try:
            # This is a simplified version - in production you might use pdf2image
            # For now, we'll assume single-page PDFs and use a basic approach
            
            # Import here to avoid dependency issues if not needed
            import fitz  # PyMuPDF - you'll need to add this to requirements
            
            # Open PDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Get first page (most invoices are single page)
            page = pdf_document[0]
            
            # Convert to image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            pdf_document.close()
            
            return img_data, "image/png"
            
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            # Fallback: try to process as text (basic OCR)
            return None, None
    
    def _select_model(self, settings: Dict) -> GenerativeModel:
        """
        Choose the best AI model based on processing requirements
        
        Different scenarios need different models:
        - Complex invoices: Use the most powerful model
        - Batch processing: Use faster model
        - High accuracy needed: Use detailed model
        """
        if not settings:
            return self.models['general']
        
        # Logic to select appropriate model
        if settings.get('extract_line_items', False) and settings.get('calculate_totals', False):
            # Complex processing needs powerful model
            return self.models['detailed']
        elif settings.get('batch_mode', False):
            # Speed priority for batch processing
            return self.models['fast']
        else:
            # Default case
            return self.models['general']
    
    def _build_processing_prompt(self, custom_prompt: str, settings: Dict) -> str:
        """
        Create the AI prompt that guides extraction
        
        This is crucial - the prompt is like giving instructions to a human assistant.
        The better our instructions, the better the results.
        """
        # Start with base template
        base_prompt = self.config.get_prompt_template("default")
        
        # Add language-specific instructions
        if settings and settings.get('language') != 'Auto-detect':
            language_instruction = f"\nSpecial instruction: This invoice is in {settings['language']}. Please extract information accordingly."
            base_prompt += language_instruction
        
        # Add line item extraction if requested
        if settings and settings.get('extract_line_items', True):
            line_item_instruction = """
            
            Pay special attention to line items. Extract each product/service with:
            - Description (what was sold)
            - Quantity (how many)
            - Unit price (price per item)
            - Total price (quantity × unit price)
            
            Ensure line items add up to the subtotal.
            """
            base_prompt += line_item_instruction
        
        # Add calculation verification if requested
        if settings and settings.get('calculate_totals', True):
            calculation_instruction = """
            
            Verify all calculations:
            - Line items should sum to subtotal
            - Subtotal + tax should equal total
            - Flag any discrepancies in your response
            """
            base_prompt += calculation_instruction
        
        # Add custom user instructions
        if custom_prompt:
            user_instruction = f"\n\nAdditional instructions from user: {custom_prompt}"
            base_prompt += user_instruction
        
        # Add quality requirements
        quality_instruction = """
        
        Quality requirements:
        - Double-check all extracted numbers
        - Ensure dates are in correct format
        - If unsure about any value, indicate uncertainty
        - Provide confidence levels where appropriate
        """
        base_prompt += quality_instruction
        
        return base_prompt
    
    def _call_gemini_api(self, model: GenerativeModel, prompt: str, image_data: Dict) -> Optional[str]:
        """
        Make the actual API call to Google Gemini
        
        This is where we send our invoice image and prompt to the AI
        and get back the structured response.
        """
        try:
            # Prepare the content for Gemini
            content = [
                prompt,
                {
                    "mime_type": image_data["mime_type"],
                    "data": image_data["data"]
                }
            ]
            
            # Generate response
            response = model.generate_content(
                content,
                generation_config={
                    "temperature": self.config.DEFAULT_TEMPERATURE,
                    "max_output_tokens": self.config.MAX_OUTPUT_TOKENS,
                }
            )
            
            # Check if response was blocked
            if response.candidates and response.candidates[0].finish_reason != 1:
                logger.warning("Response was filtered by safety settings")
                return None
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            return None
    
    def _parse_ai_response(self, ai_response: str) -> Optional[Dict]:
        """
        Parse the AI response into structured data
        
        The AI returns text, but we need structured data.
        We expect JSON, but we need to handle cases where
        the AI might not return perfect JSON.
        """
        try:
            # The AI should return JSON, but let's be flexible
            # First, try to find JSON in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback: try parsing entire response as JSON
                return json.loads(ai_response)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            # Could implement fallback parsing here
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing AI response: {str(e)}")
            return None
    
    def _enrich_extraction_data(self, extracted_data: Dict, uploaded_file, start_time: float, settings: Dict) -> Dict:
        """
        Add metadata and computed fields to the extracted data
        
        Beyond what the AI extracts, we add useful information like
        processing time, confidence scores, and system metadata.
        """
        processing_time = time.time() - start_time
        
        # Add system metadata
        extracted_data.update({
            'file_name': uploaded_file.name,
            'file_size': len(uploaded_file.getvalue()),
            'file_type': uploaded_file.type,
            'processed_at': datetime.now().isoformat(),
            'processing_time': round(processing_time, 2),
            'processor_version': self.config.APP_VERSION,
            'ai_model': self.config.gemini_model
        })
        
        # Add confidence score (we'll calculate this based on field completeness)
        extracted_data['confidence'] = self._calculate_confidence_score(extracted_data)
        
        # Add processing settings used
        extracted_data['processing_settings'] = settings or {}
        
        # Normalize and clean data
        extracted_data = self._normalize_extracted_data(extracted_data)
        
        return extracted_data
    
    def _calculate_confidence_score(self, data: Dict) -> float:
        """
        Calculate a confidence score based on data completeness and quality
        
        This gives users an idea of how reliable the extraction is.
        Higher scores mean more complete and consistent data.
        """
        required_fields = self.config.EXTRACTION_FIELDS['required']
        optional_fields = self.config.EXTRACTION_FIELDS['optional']
        
        # Count filled required fields
        required_filled = sum(1 for field in required_fields if data.get(field))
        required_score = required_filled / len(required_fields)
        
        # Count filled optional fields  
        optional_filled = sum(1 for field in optional_fields if data.get(field))
        optional_score = optional_filled / len(optional_fields) if optional_fields else 0
        
        # Weighted combination (required fields matter more)
        confidence = (required_score * 0.7) + (optional_score * 0.3)
        
        # Bonus points for data quality indicators
        if data.get('total_amount') and isinstance(data['total_amount'], (int, float)):
            confidence += 0.05
        
        if data.get('invoice_date') and self._is_valid_date(data['invoice_date']):
            confidence += 0.05
        
        return min(confidence, 1.0)  # Cap at 100%
    
    def _normalize_extracted_data(self, data: Dict) -> Dict:
        """
        Clean and normalize the extracted data
        
        The AI might return data in various formats. We normalize
        everything to consistent types and formats.
        """
        # Normalize amounts to float
        amount_fields = ['total_amount', 'subtotal', 'tax_amount']
        for field in amount_fields:
            if field in data and data[field]:
                data[field] = self._parse_amount(data[field])
        
        # Normalize dates
        date_fields = ['invoice_date', 'due_date']
        for field in date_fields:
            if field in data and data[field]:
                data[field] = self._parse_date(data[field])
        
        # Normalize currency
        if 'currency' in data and data['currency']:
            data['currency'] = data['currency'].upper()
        
        # Clean up line items
        if 'line_items' in data and isinstance(data['line_items'], list):
            data['line_items'] = [self._normalize_line_item(item) for item in data['line_items']]
        
        return data
    
    def _parse_amount(self, amount_str: Union[str, int, float]) -> Optional[float]:
        """Parse amount string into float, handling various formats"""
        if isinstance(amount_str, (int, float)):
            return float(amount_str)
        
        if isinstance(amount_str, str):
            # Remove currency symbols and spaces
            cleaned = re.sub(r'[^\d.,\-]', '', amount_str)
            # Handle decimal separators
            cleaned = cleaned.replace(',', '.')
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string into standardized YYYY-MM-DD format"""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d.%m.%Y', '%m.%d.%Y'
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def _normalize_line_item(self, item: Dict) -> Dict:
        """Normalize a single line item"""
        normalized = {}
        
        # Ensure required fields exist
        normalized['description'] = str(item.get('description', ''))
        normalized['quantity'] = self._parse_amount(item.get('quantity', 0)) or 0
        normalized['unit_price'] = self._parse_amount(item.get('unit_price', 0)) or 0
        normalized['total_price'] = self._parse_amount(item.get('total_price', 0)) or 0
        
        return normalized
    
    def _validate_extracted_data(self, data: Dict) -> Dict:
        """
        Validate extracted data against business rules
        
        This is our quality control - checking that the extracted
        data makes sense from a business perspective.
        """
        validation_results = {}
        rules = self.config.get_validation_rules()
        
        # Validate each field against its rules
        for field, rule_set in rules.items():
            if field in data:
                validation_results[field] = self._validate_field(data[field], rule_set)
            elif rule_set.get('required', False):
                validation_results[field] = {
                    'passed': False,
                    'message': f'Required field {field} is missing'
                }
        
        # Business logic validations
        validation_results.update(self._validate_business_logic(data))
        
        return validation_results
    
    def _validate_field(self, value, rules: Dict) -> Dict:
        """Validate a single field against its rules"""
        if value is None or value == '':
            if rules.get('required', False):
                return {'passed': False, 'message': 'Required field is empty'}
            else:
                return {'passed': True, 'message': 'Optional field is empty'}
        
        # Type-specific validations
        if isinstance(value, str):
            return self._validate_string_field(value, rules)
        elif isinstance(value, (int, float)):
            return self._validate_numeric_field(value, rules)
        else:
            return {'passed': True, 'message': 'Field validation passed'}
    
    def _validate_string_field(self, value: str, rules: Dict) -> Dict:
        """Validate string fields"""
        if 'min_length' in rules and len(value) < rules['min_length']:
            return {'passed': False, 'message': f'Value too short (min: {rules["min_length"]})'}
        
        if 'max_length' in rules and len(value) > rules['max_length']:
            return {'passed': False, 'message': f'Value too long (max: {rules["max_length"]})'}
        
        if 'pattern' in rules:
            if not re.match(rules['pattern'], value):
                return {'passed': False, 'message': 'Value format is invalid'}
        
        return {'passed': True, 'message': 'String validation passed'}
    
    def _validate_numeric_field(self, value: Union[int, float], rules: Dict) -> Dict:
        """Validate numeric fields"""
        if 'min_value' in rules and value < rules['min_value']:
            return {'passed': False, 'message': f'Value too small (min: {rules["min_value"]})'}
        
        if 'max_value' in rules and value > rules['max_value']:
            return {'passed': False, 'message': f'Value too large (max: {rules["max_value"]})'}
        
        return {'passed': True, 'message': 'Numeric validation passed'}
    
    def _validate_business_logic(self, data: Dict) -> Dict:
        """Validate business logic rules"""
        results = {}
        
        # Check if line items sum to subtotal
        if 'line_items' in data and 'subtotal' in data:
            line_total = sum(item.get('total_price', 0) for item in data['line_items'])
            subtotal = data.get('subtotal', 0)
            
            if abs(line_total - subtotal) > 0.01:  # Allow for small rounding differences
                results['line_items_sum'] = {
                    'passed': False,
                    'message': f'Line items sum ({line_total}) does not match subtotal ({subtotal})'
                }
            else:
                results['line_items_sum'] = {
                    'passed': True,
                    'message': 'Line items sum matches subtotal'
                }
        
        # Check if subtotal + tax = total
        if all(field in data for field in ['subtotal', 'tax_amount', 'total_amount']):
            calculated_total = data['subtotal'] + data['tax_amount']
            actual_total = data['total_amount']
            
            if abs(calculated_total - actual_total) > 0.01:
                results['total_calculation'] = {
                    'passed': False,
                    'message': f'Calculated total ({calculated_total}) does not match stated total ({actual_total})'
                }
            else:
                results['total_calculation'] = {
                    'passed': True,
                    'message': 'Total calculation is correct'
                }
        
        return results
    
    def _calculate_validation_score(self, validation_results: Dict) -> float:
        """Calculate overall validation score"""
        if not validation_results:
            return 0.0
        
        passed_count = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_count = len(validation_results)
        
        return passed_count / total_count if total_count > 0 else 0.0
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if a date string is valid"""
        return self._parse_date(date_str) is not None
    
    def _update_processing_stats(self, start_time: float, success: bool):
        """Update processing statistics"""
        processing_time = time.time() - start_time
        
        self.processing_stats['total_processed'] += 1
        self.processing_stats['total_processing_time'] += processing_time
        
        if success:
            self.processing_stats['successful_extractions'] += 1
        else:
            self.processing_stats['failed_extractions'] += 1
        
        # Update average
        self.processing_stats['average_processing_time'] = (
            self.processing_stats['total_processing_time'] / 
            self.processing_stats['total_processed']
        )
    
    def get_processing_stats(self) -> Dict:
        """Get current processing statistics"""
        return self.processing_stats.copy()
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.processing_stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_processing_time': 0.0,
            'total_processing_time': 0.0
        }