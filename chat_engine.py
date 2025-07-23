import json
import logging
import re
from typing import Dict, List, Any, Optional
from models import GearItem, ChatSession, UploadedImage
from image_analysis import create_image_analysis_service

class SynthiaChatEngine:
    """Synthia - The photography shoot planning assistant"""
    
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
        self.image_analysis_service = create_image_analysis_service()
        
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load photography knowledge base from JSON file"""
        try:
            with open('photography_knowledge.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error("Photography knowledge base not found")
            return {}
        except json.JSONDecodeError:
            logging.error("Error decoding photography knowledge base")
            return {}
    
    def generate_response(self, message: str, skill_level: str, user_gear: List[GearItem], 
                         chat_session: ChatSession, uploaded_images: Optional[List[UploadedImage]] = None) -> Dict[str, Any]:
        """Generate appropriate response based on skill level and context"""
        
        # Handle image analysis if images are uploaded
        if uploaded_images:
            return self._handle_image_analysis(message, skill_level, user_gear, uploaded_images)
        
        # Parse user input and detect intent
        intent = self._classify_intent(message)
        
        # Handle continuation responses for beginners
        if skill_level == 'Beginner' and self._is_continuation_response(message):
            return self._handle_beginner_continuation(chat_session, user_gear)
        
        # Handle decline responses for beginners
        if skill_level == 'Beginner' and self._is_decline_response(message):
            return self._handle_decline_response()
        
        # Generate new response based on photography request
        photography_style = self._extract_photography_style(message)
        
        if photography_style:
            matched_gear = self._match_user_gear(user_gear, photography_style)
            
            if skill_level == 'Beginner':
                return self._generate_beginner_response(photography_style, matched_gear, message, chat_session)
            else:
                return self._generate_comprehensive_response(photography_style, matched_gear, skill_level, message)
        else:
            return self._generate_general_response(message, skill_level)
    
    def _classify_intent(self, message: str) -> str:
        """Classify the user's intent from their message"""
        message_lower = message.lower()
        
        # Photography style requests
        style_keywords = ['portrait', 'fashion', 'glamour', 'boudoir', 'headshot', 'sports', 
                         'moody', 'high-key', 'low-key', 'dramatic', 'soft', 'natural']
        
        if any(keyword in message_lower for keyword in style_keywords):
            return 'photography_style_request'
        
        # Technical questions
        technical_keywords = ['settings', 'camera', 'lens', 'lighting', 'exposure', 'aperture', 'iso']
        if any(keyword in message_lower for keyword in technical_keywords):
            return 'technical_question'
        
        # General advice
        return 'general_advice'
    
    def _is_continuation_response(self, message: str) -> bool:
        """Check if user wants to continue to next step"""
        continuation_words = ['yes', 'y', 'continue', 'next', 'proceed', 'go ahead', 'sure', 'ok', 'okay']
        return message.lower().strip() in continuation_words
    
    def _is_decline_response(self, message: str) -> bool:
        """Check if user wants to stop the step-by-step process"""
        decline_words = ['no', 'n', 'stop', 'enough', 'good', "i'm good", 'thanks', 'thank you']
        return message.lower().strip() in decline_words
    
    def _extract_photography_style(self, message: str) -> Optional[str]:
        """Extract photography style from user message"""
        message_lower = message.lower()
        
        # Match against knowledge base
        for style_key, style_data in self.knowledge_base.items():
            keywords = style_data.get('keywords', [])
            if any(keyword in message_lower for keyword in keywords):
                return style_key
        
        return None
    
    def _match_user_gear(self, user_gear: List[GearItem], photography_style: str) -> Dict[str, List[GearItem]]:
        """Match user's gear to photography requirements"""
        matched_gear = {
            'cameras': [],
            'lenses': [],
            'lighting': [],
            'backdrops': [],
            'accessories': []
        }
        
        for gear in user_gear:
            if gear.category == 'camera_body':
                matched_gear['cameras'].append(gear)
            elif gear.category == 'lens':
                matched_gear['lenses'].append(gear)
            elif gear.category == 'lighting':
                matched_gear['lighting'].append(gear)
            elif gear.category == 'backdrop':
                matched_gear['backdrops'].append(gear)
            elif gear.category == 'accessory':
                matched_gear['accessories'].append(gear)
        
        return matched_gear
    
    def _generate_beginner_response(self, photography_style: str, matched_gear: Dict[str, List[GearItem]], 
                                  message: str, chat_session: ChatSession) -> Dict[str, Any]:
        """Generate step-by-step response for beginners"""
        
        style_data = self.knowledge_base.get(photography_style, {})
        beginner_steps = style_data.get('beginner_steps', {})
        
        # Start with intake summary and step 1
        if chat_session.current_step == 0:
            intake_summary = f"**Intake Summary:** I understand you want to create a {photography_style.replace('_', ' ')} look. "
            intake_summary += "Let me walk you through this step by step to help you achieve the perfect shot."
            
            step1_content = beginner_steps.get('step1', {}).get('scene_gear_overview', '')
            step1_content = self._personalize_gear_recommendations(step1_content, matched_gear)
            
            # Handle special cases
            step1_content = self._apply_special_case_triggers(step1_content, message, matched_gear)
            
            full_content = f"{intake_summary}\n\n🟦 **Step 1: Scene & Gear Overview**\n{step1_content}\n\nReady for Step 2: Lighting Setup?"
            
            return {
                'content': full_content,
                'step_number': 1,
                'next_step': 1,
                'awaiting_continuation': True,
                'context': {'photography_style': photography_style, 'matched_gear': self._serialize_gear(matched_gear)}
            }
        
        return self._handle_beginner_continuation(chat_session, user_gear)
    
    def _handle_beginner_continuation(self, chat_session: ChatSession, user_gear: List[GearItem]) -> Dict[str, Any]:
        """Handle continuation to next step for beginners"""
        
        context = chat_session.conversation_context or {}
        if isinstance(context, str):
            context = {}
        photography_style = context.get('photography_style', '') if context else ''
        
        if not photography_style:
            return {
                'content': "I'm sorry, I lost track of our conversation. Could you please tell me what kind of shot you'd like to work on?",
                'step_number': 0,
                'next_step': 0,
                'awaiting_continuation': False
            }
        
        style_data = self.knowledge_base.get(photography_style, {})
        beginner_steps = style_data.get('beginner_steps', {})
        
        current_step = chat_session.current_step or 0
        next_step = current_step + 1
        
        if next_step == 2:
            # Step 2: Lighting Setup
            step2_content = beginner_steps.get('step2', {}).get('lighting_setup', '')
            full_content = f"🟦 **Step 2: Lighting Setup**\n{step2_content}\n\nReady for Step 3: Posing & Composition?"
            
            return {
                'content': full_content,
                'step_number': 2,
                'next_step': 2,
                'awaiting_continuation': True,
                'context': context
            }
            
        elif next_step == 3:
            # Step 3: Posing & Composition
            step3_content = beginner_steps.get('step3', {}).get('posing_composition', '')
            full_content = f"🟦 **Step 3: Posing & Composition**\n{step3_content}\n\nWant a final pro tip before you shoot?"
            
            return {
                'content': full_content,
                'step_number': 3,
                'next_step': 3,
                'awaiting_continuation': True,
                'context': context
            }
            
        elif next_step == 4:
            # Step 4: Final Pro Tip
            step4_content = beginner_steps.get('step4', {}).get('final_pro_tip', '')
            full_content = f"🟦 **Step 4: Final Pro Tip**\n{step4_content}\n\n📌 These tips should give you a solid foundation — but every shoot is different. Adjust on the fly, and trust your eye. If anything changes, I've got your back."
            
            return {
                'content': full_content,
                'step_number': 4,
                'next_step': 0,  # Reset for new conversation
                'awaiting_continuation': False,
                'context': {}
            }
        
        # Fallback
        return {
            'content': "We've completed all the steps for your shoot! Feel free to ask about another photography style or technique.",
            'step_number': 0,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {}
        }
    
    def _handle_decline_response(self) -> Dict[str, Any]:
        """Handle when user declines to continue"""
        return {
            'content': "Got it. If anything changes, I'm here when you need me. Good luck with the shoot!",
            'step_number': 0,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {}
        }
    
    def _generate_comprehensive_response(self, photography_style: str, matched_gear: Dict[str, List[GearItem]], 
                                       skill_level: str, message: str) -> Dict[str, Any]:
        """Generate comprehensive response for intermediate/advanced users"""
        
        style_data = self.knowledge_base.get(photography_style, {})
        comprehensive_data = style_data.get('comprehensive', {})
        
        # Build comprehensive response
        setup_info = comprehensive_data.get('setup', '')
        gear_info = self._personalize_gear_recommendations(comprehensive_data.get('gear', ''), matched_gear)
        angles_info = comprehensive_data.get('angles', '')
        camera_settings = comprehensive_data.get('camera_settings', '')
        
        response_content = f"""**Setup:** {setup_info}

**Recommended Gear from Your Collection:** {gear_info}

**Angles & Composition:** {angles_info}

**Camera Settings:** {camera_settings}

**Pro Tip:** {comprehensive_data.get('pro_tip', 'Adjust these settings based on your specific lighting conditions and creative vision.')}"""
        
        return {
            'content': response_content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {}
        }
    
    def _generate_general_response(self, message: str, skill_level: str) -> Dict[str, Any]:
        """Generate general photography advice"""
        
        general_responses = [
            "I'm Synthia, your photography shoot planning assistant! I can help you plan creative setups based on your gear and goals. Try asking me about specific looks like 'dark and moody fashion portrait' or 'high-key glamour shot'.",
            "What kind of photography look are you trying to achieve? I can provide detailed guidance for Fashion, Portrait, Sports, Glamour, Boudoir, and Headshot photography.",
            "Tell me about the vibe or style you're going for, and I'll help you plan the perfect setup using your equipment!"
        ]
        
        import random
        response = random.choice(general_responses)
        
        return {
            'content': response,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {}
        }
    
    def _personalize_gear_recommendations(self, content: str, matched_gear: Dict[str, List[GearItem]]) -> str:
        """Personalize recommendations based on user's actual gear"""
        
        # Replace generic gear mentions with user's specific gear
        if matched_gear['cameras']:
            camera = matched_gear['cameras'][0]
            content = content.replace('[CAMERA]', f"{camera.brand} {camera.model}")
        
        if matched_gear['lenses']:
            lens_names = [f"{lens.brand} {lens.model}" for lens in matched_gear['lenses']]
            content = content.replace('[LENS]', ', '.join(lens_names))
        
        if matched_gear['lighting']:
            lighting_names = [f"{light.brand} {light.model}" for light in matched_gear['lighting']]
            content = content.replace('[LIGHTING]', ', '.join(lighting_names))
        
        return content
    
    def _apply_special_case_triggers(self, content: str, message: str, matched_gear: Dict[str, List[GearItem]]) -> str:
        """Apply special case triggers for specific photography types"""
        
        message_lower = message.lower()
        
        # Astrophotography trigger
        if any(word in message_lower for word in ['astrophotography', 'stars', 'milky way', 'night sky']):
            if not matched_gear['lighting']:  # Skip Step 2 if no lighting gear
                content += "\n\n**Note:** Since this is astrophotography, we'll focus on exposure, tripod use, and mobile workflow rather than artificial lighting."
        
        # Infrared triggers
        if '590nm infrared' in message_lower:
            content += "\n\n**Infrared Note:** 590nm creates Aerochrome-style looks with red/gold foliage. Consider custom white balance and channel swapping in post."
        elif '720nm infrared' in message_lower:
            content += "\n\n**Infrared Note:** 720nm produces the traditional IR look with white foliage and dark skies."
        
        # Drone trigger
        if any(word in message_lower for word in ['drone', 'aerial', 'flying']):
            content += "\n\n⚠️ **Drone Disclaimer:** FAA rules regarding drone registration, Remote ID, and airspace limits vary by location. Users should consult faa.gov/uas or the B4UFLY app before flying."
        
        # Group photography trigger
        if any(word in message_lower for word in ['group', 'event', 'party']) and 'group' in message_lower:
            content += "\n\n**Group Photography Tip:** When photographing groups of 3 or more, consider using f/4 or f/5.6 instead of f/2.8 to keep multiple faces sharp, especially if people are on different planes."
        
        return content
    
    def _serialize_gear(self, matched_gear: Dict[str, List[GearItem]]) -> Dict[str, List[Dict]]:
        """Serialize gear for JSON storage"""
        serialized = {}
        for category, items in matched_gear.items():
            serialized[category] = [{'brand': item.brand, 'model': item.model} for item in items]
        return serialized
    
    def _handle_image_analysis(self, message: str, skill_level: str, user_gear: List[GearItem], 
                              uploaded_images: List[UploadedImage]) -> Dict[str, Any]:
        """Handle image analysis requests"""
        
        # Determine analysis type based on message content
        analysis_type = "inspiration"
        if any(word in message.lower() for word in ["feedback", "critique", "improve", "better", "review"]):
            analysis_type = "technique"
        
        # Analyze the first uploaded image
        image = uploaded_images[0]
        analysis_result = self.image_analysis_service.analyze_photography_image(
            image.file_path, 
            analysis_type
        )
        
        if not analysis_result["success"]:
            return {
                'content': f"I'm sorry, I had trouble analyzing your image: {analysis_result['error']}. Please try uploading a different image.",
                'message_type': 'error',
                'metadata': {'has_images': True, 'analysis_type': analysis_type}
            }
        
        # Store analysis result in the image record
        image.analysis_result = analysis_result["analysis"]
        
        # Generate personalized response based on analysis and skill level
        if analysis_type == "inspiration":
            return self._generate_inspiration_response(analysis_result["analysis"], skill_level, user_gear, message)
        else:
            return self._generate_technique_feedback_response(analysis_result["analysis"], skill_level, user_gear, message)
    
    def _generate_inspiration_response(self, analysis: Dict[str, Any], skill_level: str, 
                                     user_gear: List[GearItem], message: str) -> Dict[str, Any]:
        """Generate response for inspiration image analysis"""
        
        # Extract key information from analysis
        lighting = analysis.get("lighting_analysis", {})
        composition = analysis.get("composition", {})
        settings = analysis.get("camera_settings", {})
        recreate_tips = analysis.get("recreate_tips", {})
        
        # Check user's gear against requirements
        available_gear = [f"{item.brand} {item.model}" for item in user_gear]
        equipment_needed = recreate_tips.get("equipment_needed", [])
        
        # Build personalized response
        response_parts = []
        
        if skill_level == 'Beginner':
            response_parts.append("Great inspiration image! Let me break down how to recreate this look in simple steps:")
            response_parts.append(f"\n**📸 Lighting Setup:**\n{lighting.get('lighting_setup', 'Natural lighting recommended')}")
            response_parts.append(f"\n**📐 Camera Position:**\n{composition.get('camera_angle', 'Standard positioning')}")
            response_parts.append(f"\n**⚙️ Camera Settings:**")
            response_parts.append(f"• Aperture: {settings.get('estimated_aperture', 'f/5.6')}")
            response_parts.append(f"• ISO: {settings.get('estimated_iso', '400')}")
            response_parts.append(f"• Focus: {settings.get('focus_point', 'Subject')}")
        else:
            response_parts.append("Excellent choice for inspiration! Here's my technical analysis:")
            response_parts.append(f"\n**Lighting Analysis:**\n{lighting.get('primary_light_source', 'Analysis unavailable')} - {lighting.get('light_quality', '')}")
            response_parts.append(f"\n**Technical Settings:**")
            response_parts.append(f"• Estimated aperture: {settings.get('estimated_aperture', 'f/5.6')} - {settings.get('estimated_shutter_speed', '1/125s')}")
            response_parts.append(f"• ISO: {settings.get('estimated_iso', '400')}")
            response_parts.append(f"• Estimated focal length: {composition.get('focal_length', '85mm')}")
        
        # Add gear-specific recommendations
        response_parts.append(f"\n**🎯 With Your Gear:**")
        gear_advice = []
        for item in user_gear:
            if item.category == 'camera_body':
                gear_advice.append(f"• Your {item.brand} {item.model} will work perfectly for this shot")
            elif item.category == 'lens' and any(focal in item.model.lower() for focal in ['85', '50', '35']):
                gear_advice.append(f"• Use your {item.brand} {item.model} for similar focal length")
        
        if gear_advice:
            response_parts.extend(gear_advice)
        else:
            response_parts.append("• Consider using a portrait lens (85mm or 50mm) for best results")
        
        # Add step-by-step recreation guide
        steps = recreate_tips.get("step_by_step", [])
        if steps and skill_level == 'Beginner':
            response_parts.append(f"\n**📋 Step-by-Step Guide:**")
            for i, step in enumerate(steps[:4], 1):
                response_parts.append(f"{i}. {step}")
        
        content = "\n".join(response_parts)
        
        return {
            'content': content,
            'message_type': 'image_analysis',
            'metadata': {
                'analysis_type': 'inspiration',
                'has_images': True,
                'gear_matched': len(gear_advice) > 0
            }
        }
    
    def _generate_technique_feedback_response(self, analysis: Dict[str, Any], skill_level: str,
                                            user_gear: List[GearItem], message: str) -> Dict[str, Any]:
        """Generate response for technique feedback analysis"""
        
        # Extract key information from analysis
        technical = analysis.get("technical_assessment", {})
        strengths = analysis.get("strengths", [])
        improvements = analysis.get("improvements", {})
        tips = analysis.get("specific_tips", {})
        rating = analysis.get("overall_rating", "No rating available")
        
        response_parts = []
        
        response_parts.append("Thanks for sharing your photo! Here's my analysis and feedback:")
        response_parts.append(f"\n**⭐ Overall Assessment:** {rating}")
        
        # Highlight strengths
        if strengths:
            response_parts.append(f"\n**✅ What's Working Well:**")
            for strength in strengths[:3]:  # Limit to top 3
                response_parts.append(f"• {strength}")
        
        # Technical assessment
        response_parts.append(f"\n**🔍 Technical Review:**")
        if technical.get("exposure"):
            response_parts.append(f"• **Exposure:** {technical['exposure']}")
        if technical.get("focus"):
            response_parts.append(f"• **Focus:** {technical['focus']}")
        if technical.get("composition"):
            response_parts.append(f"• **Composition:** {technical['composition']}")
        
        # Improvement suggestions based on skill level
        if skill_level == 'Beginner':
            immediate_improvements = improvements.get("immediate", [])
            if immediate_improvements:
                response_parts.append(f"\n**🎯 Quick Improvements to Try:**")
                for improvement in immediate_improvements[:3]:
                    response_parts.append(f"• {improvement}")
        else:
            technique_improvements = improvements.get("technique", [])
            if technique_improvements:
                response_parts.append(f"\n**📈 Technique Development:**")
                for improvement in technique_improvements:
                    response_parts.append(f"• {improvement}")
        
        # Specific tips
        if tips.get("camera_settings"):
            response_parts.append(f"\n**⚙️ Settings Suggestion:** {tips['camera_settings']}")
        
        content = "\n".join(response_parts)
        
        return {
            'content': content,
            'message_type': 'image_analysis',
            'metadata': {
                'analysis_type': 'technique',
                'has_images': True,
                'rating': rating
            }
        }
