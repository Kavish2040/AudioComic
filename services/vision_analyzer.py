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
            print(f"🤖 Raw AI response: {analysis_text[:500]}...")
            
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
        6. **CRITICAL**: Identify the speaker/character for each text element with specific gender detection

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
                            "speaker": "Male character"
                        },
                        {
                            "type": "thought",
                            "text": "I wonder what's happening...",
                            "speaker": "Female character"
                        },
                        {
                            "type": "narration",
                            "text": "Meanwhile, in another part of the city..."
                        },
                        {
                            "type": "sound_effect",
                            "text": "BOOM!"
                        }
                    ],
                    "description": "Brief description of what's happening in this panel"
                }
            ],
            "page_summary": "Overall summary of what happens on this page",
            "total_panels": 4
        }

        **SPEAKER IDENTIFICATION GUIDELINES:**
        - Look at the character speaking in each panel
        - Examine visual characteristics: facial features, clothing, body type, hair style
        - Consider context and character roles
        - Use these specific speaker labels:
          * "Male character" - for any male-appearing character
          * "Female character" - for any female-appearing character  
          * "Child" - for young characters
          * "Narrator" - for narration boxes/captions
          * Specific names if clearly visible (e.g., "Superman", "Batman")
        
        **GENDER DETECTION CLUES:**
        - Male indicators: facial hair, masculine features, male clothing, male names
        - Female indicators: feminine features, female clothing, female names, long hair (context-dependent)
        - When in doubt, look for the most obvious visual gender markers
        
        Notes:
        - Bounds should be approximate percentages (0-100) of the page dimensions
        - Text types can be: "speech", "thought", "narration", "sound_effect"
        - Reading order should follow typical comic conventions
        - If you can't determine exact bounds, provide reasonable estimates
        - Include ALL visible text, even small sound effects
        - **BE SPECIFIC about speaker gender** - this is crucial for voice selection
        """
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response and extract structured data from visual analysis."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Try to extract JSON from the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                print(f"❌ No JSON brackets found in response: {response_text[:200]}...")
                raise ValueError("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            print(f"🔍 Extracted JSON string: {json_str[:200]}...")
            
            # Try to parse the JSON
            analysis = json.loads(json_str)
            
            # Validate the structure
            if not isinstance(analysis.get('panels'), list):
                print(f"❌ Invalid panels structure: {type(analysis.get('panels'))}")
                raise ValueError("Invalid panels structure")
            
            # Sort panels by reading order
            analysis['panels'].sort(key=lambda x: x.get('reading_order', 999))
            
            # Add panel navigation info
            for i, panel in enumerate(analysis['panels']):
                panel['panel_index'] = i
                panel['is_first'] = i == 0
                panel['is_last'] = i == len(analysis['panels']) - 1
                
                # Ensure text_elements is a list
                if 'text_elements' not in panel:
                    panel['text_elements'] = []
                
                # Ensure each text element has required fields
                for text_elem in panel['text_elements']:
                    if 'type' not in text_elem:
                        text_elem['type'] = 'speech'
                    if 'speaker_gender' not in text_elem:
                        text_elem['speaker_gender'] = 'unknown'
                    if 'visual_description' not in text_elem:
                        text_elem['visual_description'] = 'Character description not available'
            
            print(f"✅ Successfully parsed analysis with {len(analysis['panels'])} panels")
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            print(f"🔍 Problematic JSON: {json_str[:500]}...")
            # Fallback: create a simple single-panel analysis
            return self._create_fallback_analysis(f"JSON parsing failed: {str(e)}")
            
        except Exception as e:
            print(f"❌ Error parsing analysis response: {str(e)}")
            return self._create_fallback_analysis(f"Parsing error: {str(e)}")
    
    def _create_fallback_analysis(self, error_message: str) -> Dict[str, Any]:
        """Create a fallback analysis when parsing fails"""
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
                            "text": "Unable to parse comic text automatically. Please check the image quality or try again.",
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
            "error": error_message
        }
    
    async def get_panel_text(self, panel_data: Dict[str, Any]) -> str:
        """Extract and format all text from a panel for TTS"""
        try:
            text_parts = []
            
            # Group text by type for better narration flow
            speech_texts = []
            thought_texts = []
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
                        thought_texts.append(f"{speaker} thinks: {text_content}")
                    else:
                        thought_texts.append(f"Thinking: {text_content}")
                        
                elif text_type == 'narration':
                    narration_texts.append(text_content)
                    
                elif text_type == 'sound_effect':
                    sound_effects.append(f"Sound effect: {text_content}")
            
            # Combine in logical order: speech first (primary dialogue), then thoughts, then narration, then sound effects
            if speech_texts:
                text_parts.extend(speech_texts)
            
            if thought_texts:
                text_parts.extend(thought_texts)
            
            if narration_texts:
                text_parts.extend(narration_texts)
            
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