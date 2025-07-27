import os
import base64
import json
from typing import Dict, Any, Optional
from PIL import Image
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class ImageAnalysisService:
    """Service for analyzing photography images using OpenAI's vision capabilities"""
    
    def __init__(self):
        self.client = openai_client
    
    def analyze_photography_image(self, image_path: str, analysis_type: str = "inspiration") -> Dict[str, Any]:
        """
        Analyze a photography image to provide technical insights
        
        Args:
            image_path: Path to the uploaded image
            analysis_type: Type of analysis - "inspiration" or "technique"
        
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Convert image to base64
            base64_image = self._encode_image_to_base64(image_path)
            
            if analysis_type == "inspiration":
                prompt = self._get_inspiration_analysis_prompt()
            else:
                prompt = self._get_technique_analysis_prompt()
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Synthia, an expert photography assistant. Analyze images to provide detailed technical photography advice. Always respond in JSON format with structured insights."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            response_content = response.choices[0].message.content
            if not response_content:
                raise ValueError("Empty response from OpenAI")
            result = json.loads(response_content)
            return {
                "success": True,
                "analysis": result,
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to analyze image: {str(e)}",
                "analysis_type": analysis_type
            }
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string"""
        try:
            # Open and potentially resize image if too large
            with Image.open(image_path) as img:
                # Resize if image is too large (max 1024px on longest side)
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes
                import io
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=85)
                img_byte_arr = img_byte_arr.getvalue()
                
                # Encode to base64
                return base64.b64encode(img_byte_arr).decode('utf-8')
                
        except Exception as e:
            raise Exception(f"Failed to encode image: {str(e)}")
    
    def _get_inspiration_analysis_prompt(self) -> str:
        """Prompt for analyzing inspiration images"""
        return """Analyze this photography image to help someone recreate a similar look. Provide a detailed technical breakdown in JSON format with these sections:

{
  "lighting_analysis": {
    "primary_light_source": "description of main light direction and quality",
    "lighting_setup": "suggested lighting equipment and positioning",
    "light_quality": "hard/soft, warm/cool temperature description",
    "shadows": "description of shadow characteristics"
  },
  "composition": {
    "camera_angle": "estimated camera position and angle",
    "framing": "description of how subject is framed",
    "depth_of_field": "estimated aperture and DOF characteristics",
    "focal_length": "estimated lens focal length"
  },
  "camera_settings": {
    "estimated_aperture": "f-stop estimate with reasoning",
    "estimated_shutter_speed": "shutter speed estimate",
    "estimated_iso": "ISO estimate",
    "focus_point": "where the focus appears to be"
  },
  "styling_notes": {
    "background": "description of background elements",
    "props": "any props or accessories used",
    "clothing": "wardrobe considerations if applicable",
    "makeup_hair": "styling notes if applicable"
  },
  "recreate_tips": {
    "equipment_needed": ["list of recommended equipment"],
    "step_by_step": ["ordered list of steps to recreate this look"],
    "key_challenges": ["potential difficulties and how to overcome them"]
  }
}"""
    
    def _get_technique_analysis_prompt(self) -> str:
        """Prompt for analyzing technique in user's own photos"""
        return """Analyze this photograph to provide constructive feedback and improvement suggestions. Respond in JSON format:

{
  "technical_assessment": {
    "exposure": "evaluation of exposure quality and suggestions",
    "focus": "assessment of focus accuracy and sharpness",
    "composition": "composition strengths and areas for improvement",
    "lighting": "lighting quality and suggestions"
  },
  "strengths": ["list of what works well in this image"],
  "improvements": {
    "immediate": ["simple adjustments that could be made"],
    "technique": ["skill-based improvements to practice"],
    "equipment": ["equipment upgrades that might help"]
  },
  "specific_tips": {
    "camera_settings": "suggested setting adjustments",
    "positioning": "suggestions for camera or subject positioning",
    "timing": "timing considerations if applicable"
  },
  "overall_rating": "rating out of 10 with brief explanation"
}"""

def create_image_analysis_service() -> ImageAnalysisService:
    """Factory function to create image analysis service"""
    return ImageAnalysisService()