"""
AI Processing Pipeline Service
Handles OCR, speech-to-text, document parsing, and OpenAI text standardization
"""

import asyncio
import io
import json
import logging
import mimetypes
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import aiofiles
import aiohttp
import openai
import pytesseract
import speech_recognition as sr
from PIL import Image
from pydub import AudioSegment
import docx2txt
import PyPDF2
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from models import AIProcessing, ParticipantResponse
from services.audit_service import AuditService

# Configure logging
logger = logging.getLogger(__name__)

class AIProcessingStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class AIInputType(Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"

class AIProcessingPipeline:
    """Comprehensive AI processing pipeline for input standardization"""
    
    def __init__(self, openai_api_key: str, db: Session):
        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.db = db
        self.audit_service = AuditService(db)
        self.recognizer = sr.Recognizer()
        
        # Configure Tesseract if custom path needed
        # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
        
    async def process_response_content(
        self, 
        response_id: int, 
        content_data: bytes, 
        content_type: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing response content
        Determines input type and routes to appropriate processor
        """
        
        # Create processing record
        ai_processing = AIProcessing(
            response_id=response_id,
            processing_status=AIProcessingStatus.PENDING,
            input_type=self._determine_input_type(content_type, filename),
            original_content={"filename": filename, "content_type": content_type, "size": len(content_data)},
            processing_steps=[],
            started_at=datetime.now(timezone.utc)
        )
        
        self.db.add(ai_processing)
        self.db.commit()
        
        try:
            # Update status to processing
            ai_processing.processing_status = AIProcessingStatus.PROCESSING
            ai_processing.processing_steps.append({
                "step": "started_processing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_type": ai_processing.input_type.value
            })
            self.db.commit()
            
            # Route to appropriate processor
            if ai_processing.input_type == AIInputType.TEXT:
                extracted_text = content_data.decode('utf-8')
            elif ai_processing.input_type == AIInputType.IMAGE:
                extracted_text = await self._process_image_ocr(content_data, ai_processing)
            elif ai_processing.input_type == AIInputType.AUDIO:
                extracted_text = await self._process_audio_speech_to_text(content_data, ai_processing)
            elif ai_processing.input_type == AIInputType.DOCUMENT:
                extracted_text = await self._process_document(content_data, content_type, ai_processing)
            else:
                raise ValueError(f"Unsupported input type: {ai_processing.input_type}")
            
            # Standardize text using OpenAI
            standardized_text, confidence_score = await self._standardize_text_openai(
                extracted_text, ai_processing
            )
            
            # Update processing record with results
            ai_processing.processed_content = {"extracted_text": extracted_text}
            ai_processing.standardized_text = standardized_text
            ai_processing.confidence_score = confidence_score
            ai_processing.processing_status = AIProcessingStatus.COMPLETED
            ai_processing.completed_at = datetime.now(timezone.utc)
            ai_processing.processing_steps.append({
                "step": "completed_successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence_score": confidence_score
            })
            
            self.db.commit()
            
            # Log audit trail
            await self.audit_service.log_ai_processing(
                user_id=None,  # System processing
                response_id=response_id,
                processing_id=ai_processing.id,
                status="completed",
                confidence_score=confidence_score
            )
            
            return {
                "processing_id": ai_processing.id,
                "status": "completed",
                "standardized_text": standardized_text,
                "confidence_score": confidence_score,
                "processing_time": (ai_processing.completed_at - ai_processing.started_at).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"AI processing failed for response {response_id}: {str(e)}")
            return await self._handle_processing_error(ai_processing, str(e))
    
    def _determine_input_type(self, content_type: str, filename: Optional[str]) -> AIInputType:
        """Determine the input type based on content type and filename"""
        
        if content_type.startswith('image/'):
            return AIInputType.IMAGE
        elif content_type.startswith('audio/'):
            return AIInputType.AUDIO
        elif content_type in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            return AIInputType.DOCUMENT
        elif content_type.startswith('text/'):
            return AIInputType.TEXT
        
        # Fallback to filename extension
        if filename:
            ext = filename.lower().split('.')[-1]
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
                return AIInputType.IMAGE
            elif ext in ['mp3', 'wav', 'ogg', 'flac', 'm4a']:
                return AIInputType.AUDIO
            elif ext in ['pdf', 'docx', 'doc']:
                return AIInputType.DOCUMENT
            elif ext in ['txt', 'md', 'rtf']:
                return AIInputType.TEXT
        
        # Default to text
        return AIInputType.TEXT
    
    async def _process_image_ocr(self, image_data: bytes, ai_processing: AIProcessing) -> str:
        """Extract text from image using Tesseract OCR"""
        
        ai_processing.processing_steps.append({
            "step": "ocr_processing_started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "tesseract"
        })
        self.db.commit()
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Perform OCR with multiple language support
            extracted_text = pytesseract.image_to_string(
                image, 
                lang='eng+spa+fra+deu',  # English, Spanish, French, German
                config='--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
            )
            
            ai_processing.processing_steps.append({
                "step": "ocr_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "extracted_length": len(extracted_text),
                "languages_detected": "eng+spa+fra+deu"
            })
            self.db.commit()
            
            return extracted_text.strip()
            
        except Exception as e:
            ai_processing.processing_steps.append({
                "step": "ocr_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            })
            self.db.commit()
            raise Exception(f"OCR processing failed: {str(e)}")
    
    async def _process_audio_speech_to_text(self, audio_data: bytes, ai_processing: AIProcessing) -> str:
        """Convert audio to text using speech recognition"""
        
        ai_processing.processing_steps.append({
            "step": "speech_to_text_started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "speech_recognition"
        })
        self.db.commit()
        
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Convert audio to WAV format if needed
                audio_segment = AudioSegment.from_file(temp_path)
                wav_data = audio_segment.export(format="wav")
                
                # Perform speech recognition
                with sr.AudioFile(wav_data) as source:
                    audio = self.recognizer.record(source)
                    extracted_text = self.recognizer.recognize_google(
                        audio, 
                        language='en-US',
                        show_all=False
                    )
                
                ai_processing.processing_steps.append({
                    "step": "speech_to_text_completed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extracted_length": len(extracted_text),
                    "audio_duration": len(audio_segment) / 1000.0  # Duration in seconds
                })
                self.db.commit()
                
                return extracted_text
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except Exception as e:
            ai_processing.processing_steps.append({
                "step": "speech_to_text_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            })
            self.db.commit()
            raise Exception(f"Speech-to-text processing failed: {str(e)}")
    
    async def _process_document(self, document_data: bytes, content_type: str, ai_processing: AIProcessing) -> str:
        """Extract text from documents (PDF, DOCX)"""
        
        ai_processing.processing_steps.append({
            "step": "document_parsing_started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type
        })
        self.db.commit()
        
        try:
            extracted_text = ""
            
            if content_type == 'application/pdf':
                # Process PDF
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(document_data))
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"
                    
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                # Process DOCX
                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                    temp_file.write(document_data)
                    temp_path = temp_file.name
                
                try:
                    extracted_text = docx2txt.process(temp_path)
                finally:
                    os.unlink(temp_path)
            
            ai_processing.processing_steps.append({
                "step": "document_parsing_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "extracted_length": len(extracted_text),
                "document_type": content_type
            })
            self.db.commit()
            
            return extracted_text.strip()
            
        except Exception as e:
            ai_processing.processing_steps.append({
                "step": "document_parsing_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            })
            self.db.commit()
            raise Exception(f"Document parsing failed: {str(e)}")
    
    async def _standardize_text_openai(self, extracted_text: str, ai_processing: AIProcessing) -> Tuple[str, float]:
        """Standardize and clean text using OpenAI"""
        
        ai_processing.processing_steps.append({
            "step": "openai_standardization_started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_length": len(extracted_text)
        })
        self.db.commit()
        
        try:
            # Create standardization prompt
            system_prompt = """You are a text standardization expert. Your job is to:

1. Clean and standardize the input text
2. Fix OCR/speech recognition errors
3. Correct grammar and spelling
4. Maintain the original meaning and intent
5. Format consistently
6. Remove irrelevant noise or artifacts

Return only the standardized text. Do not add commentary or explanations."""

            user_prompt = f"""Please standardize this text:

{extracted_text[:4000]}"""  # Limit input to prevent token limit issues
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            standardized_text = response.choices[0].message.content.strip()
            
            # Calculate confidence score based on text similarity and processing quality
            confidence_score = self._calculate_confidence_score(
                extracted_text, 
                standardized_text, 
                response.usage.total_tokens
            )
            
            ai_processing.processing_steps.append({
                "step": "openai_standardization_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "output_length": len(standardized_text),
                "tokens_used": response.usage.total_tokens,
                "confidence_score": confidence_score
            })
            self.db.commit()
            
            return standardized_text, confidence_score
            
        except Exception as e:
            ai_processing.processing_steps.append({
                "step": "openai_standardization_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            })
            self.db.commit()
            raise Exception(f"OpenAI standardization failed: {str(e)}")
    
    def _calculate_confidence_score(self, original_text: str, standardized_text: str, tokens_used: int) -> float:
        """Calculate confidence score for the processing result"""
        
        # Base confidence
        confidence = 0.8
        
        # Adjust based on text length changes (dramatic changes reduce confidence)
        length_ratio = len(standardized_text) / max(len(original_text), 1)
        if length_ratio < 0.5 or length_ratio > 2.0:
            confidence -= 0.2
        
        # Adjust based on token usage (higher usage might indicate more complex processing)
        if tokens_used > 1500:
            confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    async def _handle_processing_error(self, ai_processing: AIProcessing, error_message: str) -> Dict[str, Any]:
        """Handle processing errors with retry logic"""
        
        ai_processing.retry_count += 1
        ai_processing.error_message = error_message
        ai_processing.processing_steps.append({
            "step": "error_occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error_message,
            "retry_count": ai_processing.retry_count
        })
        
        if ai_processing.retry_count < ai_processing.max_retries:
            ai_processing.processing_status = AIProcessingStatus.RETRYING
            self.db.commit()
            
            # Log retry attempt
            await self.audit_service.log_ai_processing(
                user_id=None,
                response_id=ai_processing.response_id,
                processing_id=ai_processing.id,
                status="retrying",
                error_message=error_message
            )
            
            return {
                "processing_id": ai_processing.id,
                "status": "retrying",
                "retry_count": ai_processing.retry_count,
                "error": error_message
            }
        else:
            ai_processing.processing_status = AIProcessingStatus.FAILED
            ai_processing.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Log final failure
            await self.audit_service.log_ai_processing(
                user_id=None,
                response_id=ai_processing.response_id,
                processing_id=ai_processing.id,
                status="failed",
                error_message=error_message
            )
            
            return {
                "processing_id": ai_processing.id,
                "status": "failed",
                "error": error_message,
                "retry_count": ai_processing.retry_count
            }
    
    async def get_processing_status(self, processing_id: int) -> Optional[Dict[str, Any]]:
        """Get the current status of an AI processing job"""
        
        ai_processing = self.db.query(AIProcessing).filter(
            AIProcessing.id == processing_id
        ).first()
        
        if not ai_processing:
            return None
        
        return {
            "processing_id": ai_processing.id,
            "response_id": ai_processing.response_id,
            "status": ai_processing.processing_status.value,
            "input_type": ai_processing.input_type.value,
            "standardized_text": ai_processing.standardized_text,
            "confidence_score": ai_processing.confidence_score,
            "retry_count": ai_processing.retry_count,
            "error_message": ai_processing.error_message,
            "started_at": ai_processing.started_at.isoformat() if ai_processing.started_at else None,
            "completed_at": ai_processing.completed_at.isoformat() if ai_processing.completed_at else None,
            "processing_steps": ai_processing.processing_steps
        }
    
    async def retry_failed_processing(self, processing_id: int) -> Dict[str, Any]:
        """Manually retry a failed processing job"""
        
        ai_processing = self.db.query(AIProcessing).filter(
            AIProcessing.id == processing_id
        ).first()
        
        if not ai_processing:
            raise ValueError("Processing record not found")
        
        if ai_processing.processing_status not in [AIProcessingStatus.FAILED, AIProcessingStatus.RETRYING]:
            raise ValueError("Can only retry failed or retrying processing jobs")
        
        # Reset for retry
        ai_processing.retry_count = 0
        ai_processing.processing_status = AIProcessingStatus.PENDING
        ai_processing.error_message = None
        ai_processing.started_at = None
        ai_processing.completed_at = None
        ai_processing.processing_steps.append({
            "step": "manual_retry_initiated",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        self.db.commit()
        
        # Get original response data and reprocess
        response = self.db.query(ParticipantResponse).filter(
            ParticipantResponse.id == ai_processing.response_id
        ).first()
        
        if not response or not hasattr(response, 'file_data'):
            raise ValueError("Original response data not found")
        
        # Restart processing (this would typically be called by a background job)
        return {
            "processing_id": processing_id,
            "status": "retry_initiated",
            "message": "Processing job queued for retry"
        }