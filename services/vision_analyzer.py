import base64
import json
from typing import List, Dict, Any
import asyncio
from openai import AsyncOpenAI
from PIL import Image
import io

from config import config

class VisionAnalyzer:
    """Service for analyzing comic pages using vision AI"""
    
    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for vision analysis")
        
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
    async def analyze_page(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze a comic page to identify panels, text, and reading order
        
        Args:
            image_path: Path to the comic page image
            
        Returns:
            Dictionary containing panel information and text
        """
        try:
            # Encode image to base64
            base64_image = self._encode_image(image_path)
            
            # Create the prompt for comic analysis
            prompt = self._create_analysis_prompt()
            
            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            analysis = self._parse_analysis_response(analysis_text)
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Error analyzing comic page: {str(e)}")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large to save on API costs
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                img_bytes = buffer.getvalue()
                
                return base64.b64encode(img_bytes).decode('utf-8')
                
        except Exception as e:
            raise Exception(f"Error encoding image: {str(e)}")
    
    def _create_analysis_prompt(self) -> str:
        """Create the prompt for comic page analysis"""
        return """
        Analyze this comic page and provide a detailed breakdown in JSON format. I need you to:

        1. Identify all panels/frames in the comic page
        2. Determine the correct reading order (typically left-to-right, top-to-bottom)
        3. Extract all text from speech bubbles, thought bubbles, captions, and sound effects
        4. Identify the approximate coordinates/bounds of each panel
        5. Describe what's happening in each panel briefly
        6. **VISUALLY ANALYZE EACH CHARACTER** who is speaking and determine their gender based on visual appearance (facial features, hair style, clothing, body shape, etc.)
        7. Match each text element to the visually identified character who is speaking

        Please respond with a JSON object in this exact format:
        {
            "panels": [
                {
                    "panel_id": 1,
                    "reading_order": 1,
                    "bounds": {"x": 0, "y": 0, "width": 100, "height": 100},
                    "text_elements": [
                        {
                            "type": "speech",
                            "text": "Hello there!",
                            "speaker": "Character name or description",
                            "speaker_gender": "male/female/unknown",
                            "visual_description": "Brief description of the character's visual appearance"
                        },
                        {
                            "type": "narration",
                            "text": "Meanwhile...",
                            "speaker": "Narrator",
                            "speaker_gender": "unknown",
                            "visual_description": "Narration text"
                        },
                        {
                            "type": "sound_effect",
                            "text": "BOOM!",
                            "speaker": "Sound effect",
                            "speaker_gender": "unknown",
                            "visual_description": "Sound effect"
                        }
                    ],
                    "description": "Brief description of what's happening in this panel"
                }
            ],
            "page_summary": "Overall summary of what happens on this page",
            "total_panels": 4
        }

        **IMPORTANT VISUAL ANALYSIS INSTRUCTIONS:**
        - Look at the actual drawn characters in each panel
        - Analyze visual cues like: facial features, hair style/length, clothing, body shape, facial hair, makeup, etc.
        - Determine gender based on visual appearance, not text content
        - For each speech bubble, identify which character is speaking by their visual appearance
        - Assign "male", "female", or "unknown" based on visual analysis
        - Include a brief visual description of each speaking character
        - If multiple characters are in a panel, distinguish between them visually
        - For thought bubbles, identify the character thinking
        - For narration, use "unknown" gender

        Notes:
        - Bounds should be approximate percentages (0-100) of the page dimensions
        - Text types can be: "speech", "thought", "narration", "sound_effect"
        - Reading order should follow typical comic conventions
        - If you can't determine exact bounds, provide reasonable estimates
        - Include ALL visible text, even small sound effects
        - Focus on visual character analysis for accurate gender detection
        """
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response and extract structured data from visual analysis."""
        try:
            # Try to extract JSON from the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            json_str = response_text[start_idx:end_idx]
            analysis = json.loads(json_str)
            # Validate the structure
            if not isinstance(analysis.get('panels'), list):
                raise ValueError("Invalid panels structure")
            # Sort panels by reading order
            analysis['panels'].sort(key=lambda x: x.get('reading_order', 999))
            # Add panel navigation info
            for i, panel in enumerate(analysis['panels']):
                panel['panel_index'] = i
                panel['is_first'] = i == 0
                panel['is_last'] = i == len(analysis['panels']) - 1
                # The AI now provides speaker_gender directly from visual analysis
                # No need for additional gender detection logic
            return analysis
        except json.JSONDecodeError as e:
            # Fallback: create a simple single-panel analysis
            return {
                "panels": [
                    {
                        "panel_id": 1,
                        "reading_order": 1,
                        "panel_index": 0,
                        "is_first": True,
                        "is_last": True,
                        "bounds": {"x": 0, "y": 0, "width": 100, "height": 100},
                        "text_elements": [
                            {
                                "type": "narration",
                                "text": "Unable to parse comic text automatically. Please check the image quality.",
                                "speaker": "System",
                                "speaker_gender": "unknown",
                                "visual_description": "Error message"
                            }
                        ],
                        "description": "Comic panel analysis failed - manual review needed"
                    }
                ],
                "page_summary": "Page analysis incomplete due to parsing error",
                "total_panels": 1,
                "error": f"JSON parsing failed: {str(e)}"
            }
        except Exception as e:
            raise Exception(f"Error parsing analysis response: {str(e)}")
    
    async def get_panel_text(self, panel_data: Dict[str, Any]) -> str:
        """Extract and format all text from a panel for TTS"""
        try:
            text_parts = []
            
            # Group text by type for better narration flow
            speech_texts = []
            narration_texts = []
            sound_effects = []
            
            for text_element in panel_data.get('text_elements', []):
                text_type = text_element.get('type', 'speech')
                text_content = text_element.get('text', '').strip()
                
                if not text_content:
                    continue
                
                if text_type == 'speech':
                    speaker = text_element.get('speaker', 'Character')
                    if speaker and speaker.lower() != 'unknown':
                        speech_texts.append(f"{speaker} says: {text_content}")
                    else:
                        speech_texts.append(text_content)
                        
                elif text_type == 'thought':
                    speaker = text_element.get('speaker', 'Character')
                    if speaker and speaker.lower() != 'unknown':
                        speech_texts.append(f"{speaker} thinks: {text_content}")
                    else:
                        speech_texts.append(f"Thinking: {text_content}")
                        
                elif text_type == 'narration':
                    narration_texts.append(text_content)
                    
                elif text_type == 'sound_effect':
                    sound_effects.append(f"Sound effect: {text_content}")
            
            # Combine in logical order: narration first, then speech, then sound effects
            if narration_texts:
                text_parts.extend(narration_texts)
            
            if speech_texts:
                text_parts.extend(speech_texts)
            
            if sound_effects:
                text_parts.extend(sound_effects)
            
            # If no text found, use the panel description
            if not text_parts:
                description = panel_data.get('description', '')
                if description:
                    text_parts.append(f"Scene: {description}")
            
            return '. '.join(text_parts) if text_parts else "No text in this panel."
            
        except Exception as e:
            return f"Error extracting panel text: {str(e)}" 