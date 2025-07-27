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
                         chat_session: ChatSession, uploaded_images: Optional[List[UploadedImage]] = None, 
                         user_specialization: Optional[str] = None) -> Dict[str, Any]:
        """Generate appropriate response based on skill level and context"""
        
        # Handle image analysis if images are uploaded
        if uploaded_images:
            return self._handle_image_analysis(message, skill_level, user_gear, uploaded_images)
        
        # Get current conversation context
        current_scenario = self._get_current_scenario(chat_session)
        
        # Handle continuation responses for beginners
        if skill_level == 'Beginner' and self._is_continuation_response(message):
            matched_gear = self._match_user_gear(user_gear, current_scenario or "portrait")
            return self._handle_beginner_continuation(chat_session, matched_gear)
        
        # Handle decline responses for beginners
        if skill_level == 'Beginner' and self._is_decline_response(message):
            return self._handle_decline_response()
        
        # Check if this is a follow-up question to existing context
        if current_scenario and self._is_followup_question(message):
            return self._handle_followup_question(message, current_scenario, skill_level, user_gear, chat_session)
        
        # Generate new response based on photography request
        photography_style = self._extract_photography_style(message)
        
        if photography_style:
            # Store new scenario in context and reset step count
            self._set_current_scenario(chat_session, photography_style)
            chat_session.current_step = 0  # Reset for new conversation
            matched_gear = self._match_user_gear(user_gear, photography_style)
            
            if skill_level == 'Beginner':
                return self._generate_beginner_response(photography_style, matched_gear, message, chat_session)
            else:
                return self._generate_comprehensive_response(photography_style, matched_gear, skill_level, message)
        else:
            # If no specific style mentioned, use user's specialization for default advice
            return self._generate_general_response(message, skill_level, user_specialization)
    
    def _get_current_scenario(self, chat_session: ChatSession) -> Optional[str]:
        """Get the current conversation scenario from session context"""
        if chat_session.conversation_context and isinstance(chat_session.conversation_context, dict):
            return chat_session.conversation_context.get('current_scenario')
        return None
    
    def _set_current_scenario(self, chat_session: ChatSession, scenario: str):
        """Set the current conversation scenario in session context"""
        if not chat_session.conversation_context:
            chat_session.conversation_context = {}
        elif not isinstance(chat_session.conversation_context, dict):
            chat_session.conversation_context = {}
        chat_session.conversation_context['current_scenario'] = scenario
    
    def _is_followup_question(self, message: str) -> bool:
        """Check if message is a follow-up question to existing context"""
        message_lower = message.lower()
        
        # Follow-up keywords that suggest building on existing context
        followup_keywords = [
            'posing', 'pose', 'poses', 'positioning',
            'lighting', 'light', 'lights', 'illumination',
            'gear', 'equipment', 'lens', 'camera',
            'settings', 'exposure', 'aperture', 'iso', 'shutter',
            'angles', 'composition', 'framing',
            'tips', 'advice', 'suggestions', 'help',
            'how to', 'what about', 'any', 'also',
            'more', 'additional', 'other', 'different'
        ]
        
        # Check for follow-up patterns
        for keyword in followup_keywords:
            if keyword in message_lower:
                return True
        
        # Question patterns that suggest follow-ups
        question_patterns = [
            'any suggestions', 'what about', 'how about', 'can you',
            'do you have', 'what would', 'how do i', 'how should i'
        ]
        
        for pattern in question_patterns:
            if pattern in message_lower:
                return True
        
        return False
    
    def _handle_followup_question(self, message: str, current_scenario: str, skill_level: str, 
                                 user_gear: List[GearItem], chat_session: ChatSession) -> Dict[str, Any]:
        """Handle follow-up questions within existing scenario context"""
        message_lower = message.lower()
        
        # Get the scenario data
        scenario_data = self.knowledge_base.get(current_scenario, {})
        if not scenario_data:
            # Fallback to general response if scenario not found
            return self._generate_general_response(message, skill_level)
        
        # Determine what aspect they're asking about
        if any(word in message_lower for word in ['posing', 'pose', 'poses', 'positioning']):
            return self._generate_posing_advice(current_scenario, scenario_data, skill_level, user_gear)
        
        elif any(word in message_lower for word in ['lighting', 'light', 'lights', 'illumination']):
            return self._generate_lighting_advice(current_scenario, scenario_data, skill_level, user_gear)
        
        elif any(word in message_lower for word in ['gear', 'equipment', 'lens', 'camera']):
            return self._generate_gear_advice(current_scenario, scenario_data, skill_level, user_gear)
        
        elif any(word in message_lower for word in ['settings', 'exposure', 'aperture', 'iso', 'shutter']):
            return self._generate_settings_advice(current_scenario, scenario_data, skill_level)
        
        elif any(word in message_lower for word in ['angles', 'composition', 'framing']):
            return self._generate_composition_advice(current_scenario, scenario_data, skill_level)
        
        else:
            # General follow-up - provide additional tips or clarification
            return self._generate_general_followup(current_scenario, scenario_data, skill_level, message)
    
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
    
    def _generate_posing_advice(self, scenario: str, scenario_data: Dict[str, Any], skill_level: str, user_gear: List[GearItem]) -> Dict[str, Any]:
        """Generate posing advice for current scenario"""
        comprehensive_data = scenario_data.get('comprehensive', {})
        
        # Extract posing/composition guidance
        angles_info = comprehensive_data.get('angles', '')
        
        # Add scenario-specific posing tips
        posing_tips = self._get_posing_tips_for_scenario(scenario)
        
        content = f"**Posing & Composition for {scenario.replace('_', ' ').title()}:**\n\n"
        content += f"{angles_info}\n\n"
        content += f"**Additional Posing Tips:**\n{posing_tips}"
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'current_scenario': scenario}
        }
    
    def _generate_lighting_advice(self, scenario: str, scenario_data: Dict[str, Any], skill_level: str, user_gear: List[GearItem]) -> Dict[str, Any]:
        """Generate lighting advice for current scenario"""
        comprehensive_data = scenario_data.get('comprehensive', {})
        setup_info = comprehensive_data.get('setup', '')
        
        # Filter for lighting-specific content
        lighting_content = self._extract_lighting_content(setup_info)
        matched_gear = self._match_user_gear(user_gear, scenario)
        lighting_gear = self._personalize_gear_recommendations("Use your lighting equipment for ", matched_gear)
        
        content = f"**Lighting Setup for {scenario.replace('_', ' ').title()}:**\n\n"
        content += f"{lighting_content}\n\n"
        content += f"**Your Lighting Gear:** {lighting_gear}"
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'current_scenario': scenario}
        }
    
    def _generate_gear_advice(self, scenario: str, scenario_data: Dict[str, Any], skill_level: str, user_gear: List[GearItem]) -> Dict[str, Any]:
        """Generate gear advice for current scenario"""
        comprehensive_data = scenario_data.get('comprehensive', {})
        gear_info = comprehensive_data.get('gear', '')
        
        matched_gear = self._match_user_gear(user_gear, scenario)
        personalized_gear = self._personalize_gear_recommendations(gear_info, matched_gear)
        
        content = f"**Recommended Gear for {scenario.replace('_', ' ').title()}:**\n\n"
        content += f"{personalized_gear}\n\n"
        content += "**From Your Collection:** "
        
        # Enhanced camera body recommendations
        camera_advice = self._get_best_camera_for_scenario(matched_gear['cameras'], scenario)
        gear_summary = []
        
        if camera_advice:
            gear_summary.append(f"Camera: {camera_advice}")
        
        if matched_gear['lenses']:
            lens_advice = self._get_best_lens_for_scenario(matched_gear['lenses'], scenario)
            gear_summary.append(f"Lens: {lens_advice}")
        
        if matched_gear['lighting']:
            gear_summary.append(f"Lighting: {len(matched_gear['lighting'])} item(s)")
        
        content += " • ".join(gear_summary) if gear_summary else "Add your gear in the profile for personalized recommendations"
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'current_scenario': scenario}
        }
    
    def _generate_settings_advice(self, scenario: str, scenario_data: Dict[str, Any], skill_level: str) -> Dict[str, Any]:
        """Generate camera settings advice for current scenario"""
        comprehensive_data = scenario_data.get('comprehensive', {})
        camera_settings = comprehensive_data.get('camera_settings', '')
        
        content = f"**Camera Settings for {scenario.replace('_', ' ').title()}:**\n\n"
        content += f"{camera_settings}\n\n"
        content += "**Remember:** These are starting points - adjust based on your specific lighting conditions and creative vision."
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'current_scenario': scenario}
        }
    
    def _generate_composition_advice(self, scenario: str, scenario_data: Dict[str, Any], skill_level: str) -> Dict[str, Any]:
        """Generate composition advice for current scenario"""
        comprehensive_data = scenario_data.get('comprehensive', {})
        angles_info = comprehensive_data.get('angles', '')
        
        content = f"**Composition & Angles for {scenario.replace('_', ' ').title()}:**\n\n"
        content += f"{angles_info}\n\n"
        content += "**Pro Tip:** Try multiple angles and compositions during your shoot - you can always narrow down to the best shots later."
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'current_scenario': scenario}
        }
    
    def _generate_general_followup(self, scenario: str, scenario_data: Dict[str, Any], skill_level: str, message: str) -> Dict[str, Any]:
        """Generate general follow-up advice for current scenario"""
        comprehensive_data = scenario_data.get('comprehensive', {})
        pro_tip = comprehensive_data.get('pro_tip', '')
        
        content = f"**Additional Tips for {scenario.replace('_', ' ').title()}:**\n\n"
        content += f"{pro_tip}\n\n"
        content += "Feel free to ask about specific aspects like posing, lighting, gear, or camera settings for more detailed guidance!"
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'current_scenario': scenario}
        }
    
    def _get_posing_tips_for_scenario(self, scenario: str) -> str:
        """Get scenario-specific posing tips"""
        posing_tips = {
            'beach_golden_hour': "• Use backlighting for rim lighting effects\n• Have model face the golden light for warm skin tones\n• Try walking shots and flowing movements\n• For swimwear: confident poses, elongated lines",
            'dark_moody_fashion': "• Strong, angular poses\n• Dramatic shadows across face\n• Minimal movement, controlled poses\n• Hands and body positioning matter",
            'high_key_glamour': "• Soft, elegant poses\n• Avoid harsh angles\n• Gentle hand placement\n• Relaxed, approachable expressions",
            'natural_outdoor_portrait': "• Candid, relaxed poses\n• Interaction with environment\n• Natural expressions\n• Comfortable positioning"
        }
        return posing_tips.get(scenario, "• Work with your model to find comfortable, natural poses\n• Try multiple angles and expressions\n• Consider the mood and style you want to convey")
    
    def _extract_lighting_content(self, setup_info: str) -> str:
        """Extract lighting-specific information from setup content"""
        # Split setup info and filter for lighting-related content
        sentences = setup_info.split('.')
        lighting_sentences = []
        
        lighting_keywords = ['light', 'lighting', 'illumination', 'shadow', 'highlight', 'backlight', 'fill', 'key light', 'rim light']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in lighting_keywords):
                lighting_sentences.append(sentence.strip())
        
        return '. '.join(lighting_sentences) if lighting_sentences else setup_info
    
    def _generate_specialization_advice(self, specialization: str, skill_level: str) -> Dict[str, Any]:
        """Generate advice based on user's main specialization"""
        
        specialization_tips = {
            'Portrait': {
                'focus': 'connecting with subjects and creating flattering lighting',
                'key_advice': '• Focus on eyes and expressions\n• Use soft, flattering lighting\n• Pay attention to posing and comfort\n• Consider background simplicity',
                'gear_tips': 'Use 85mm or 135mm lenses for compression and flattering perspective'
            },
            'Fashion': {
                'focus': 'creating striking, editorial looks with dramatic lighting',
                'key_advice': '• Strong poses and confident expressions\n• Dramatic lighting and shadows\n• Pay attention to styling and wardrobe\n• Consider location and mood consistency',
                'gear_tips': 'Use 85mm-135mm lenses and consider off-camera flash for dramatic effects'
            },
            'Sports': {
                'focus': 'capturing action and peak moments',
                'key_advice': '• Fast shutter speeds (1/500s or faster)\n• Continuous autofocus modes\n• Anticipate the action\n• Use burst mode for key moments',
                'gear_tips': 'Use telephoto lenses (70-200mm or longer) and fast apertures'
            },
            'Glamour': {
                'focus': 'creating polished, elegant beauty shots',
                'key_advice': '• Soft, even lighting is key\n• Focus on makeup and styling details\n• Use flattering angles\n• Consider retouching workflow',
                'gear_tips': 'Use portrait lenses (85mm+) and large softboxes or beauty dishes'
            },
            'Boudoir': {
                'focus': 'creating intimate, tasteful portraits',
                'key_advice': '• Comfort and trust are essential\n• Use soft, warm lighting\n• Focus on curves and shadows\n• Respect boundaries always',
                'gear_tips': 'Use 85mm or 135mm lenses and continuous lighting for comfortable environment'
            },
            'Headshot': {
                'focus': 'professional portraits for business use',
                'key_advice': '• Even, professional lighting\n• Focus on eyes and expression\n• Clean, simple backgrounds\n• Consistent style for multiple subjects',
                'gear_tips': 'Use 85mm-135mm lenses and studio lighting or large windows'
            }
        }
        
        spec_info = specialization_tips.get(specialization, specialization_tips['Portrait'])
        
        content = f"**{specialization} Photography Tips:**\n\n"
        content += f"As a {specialization.lower()} photographer, your main focus should be on {spec_info['focus']}.\n\n"
        content += f"**Key Techniques:**\n{spec_info['key_advice']}\n\n"
        content += f"**Gear Recommendations:**\n{spec_info['gear_tips']}\n\n"
        content += "Feel free to ask about specific scenarios, lighting setups, or techniques for your shoots!"
        
        return {
            'content': content,
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {'specialization_advice': True}
        }
    
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
            
            # Handle special cases and triggers
            step1_content = self._apply_special_case_triggers(step1_content, message, matched_gear)
            
            # Check if we need to skip lighting step for certain scenarios
            skip_lighting = self._should_skip_lighting_step(message, matched_gear)
            next_step_text = "Lighting Setup" if not skip_lighting else "Posing & Composition"
            
            full_content = f"{intake_summary}\n\n🟦 **Step 1: Scene & Gear Overview**\n{step1_content}\n\nReady for Step 2: {next_step_text}?"
            
            return {
                'content': full_content,
                'step_number': 1,
                'next_step': 1,
                'awaiting_continuation': True,
                'context': {
                    'photography_style': photography_style, 
                    'matched_gear': self._serialize_gear(matched_gear),
                    'skip_lighting': skip_lighting
                }
            }
        
        # This should not be reached for new conversations
        logging.warning("Unexpected code path in _generate_beginner_response")
        return {
            'content': "I'm ready to help you with your photography! What style or look are you going for?",
            'step_number': None,
            'next_step': 0,
            'awaiting_continuation': False,
            'context': {}
        }
    
    def _should_skip_lighting_step(self, message: str, matched_gear: Dict[str, List[GearItem]]) -> bool:
        """Check if we should skip the lighting step for special cases like astrophotography"""
        message_lower = message.lower()
        
        # Astrophotography cases - skip lighting unless user has lighting gear
        astro_keywords = ['astrophotography', 'stars', 'milky way', 'night sky', 'astro']
        if any(keyword in message_lower for keyword in astro_keywords):
            return len(matched_gear.get('lighting', [])) == 0
        
        return False
    
    def _apply_special_case_triggers(self, content: str, message: str, matched_gear: Dict[str, List[GearItem]]) -> str:
        """Apply special case triggers based on user message"""
        message_lower = message.lower()
        
        # Group photography trigger
        group_keywords = ['group', 'event', 'party', 'people', 'multiple people']
        if any(keyword in message_lower for keyword in group_keywords):
            content += "\n\n**Important for Groups:** When photographing groups of 3 or more, an aperture of f/2.8 may result in only part of the group being in focus, especially if people are on different planes. Suggest stopping down to f/4 or f/5.6 to keep multiple faces sharp, and adjust ISO or shutter speed accordingly to maintain exposure."
        
        # Astrophotography trigger
        astro_keywords = ['astrophotography', 'stars', 'milky way', 'night sky', 'astro']
        if any(keyword in message_lower for keyword in astro_keywords):
            content += "\n\n**Astrophotography Notes:** Focus on exposure, tripod use, and mobile workflow. Use manual focus set to infinity, ISO 1600-6400, aperture f/2.8-f/4, and 15-30 second exposures depending on focal length (500 rule)."
        
        # Infrared triggers
        if '590nm' in message_lower or '590 nm' in message_lower:
            content += "\n\n**590nm Infrared:** This creates Aerochrome-style looks with red/gold foliage. Set custom white balance around 2500K and consider channel swapping in post-processing for dramatic color effects."
        
        if '720nm' in message_lower or '720 nm' in message_lower:
            content += "\n\n**720nm Infrared:** This produces the traditional IR look with white foliage and dark skies. Set custom white balance around 3000K for best starting point."
        
        # Drone photography trigger
        drone_keywords = ['drone', 'aerial', 'flying', 'dji', 'uav']
        if any(keyword in message_lower for keyword in drone_keywords):
            content += "\n\n**Drone Safety:** Recommend ND filters for smooth footage and slow pans for cinematic movement. ⚠️ **Important:** FAA rules regarding drone registration, Remote ID, and airspace limits vary by location. Users should consult faa.gov/uas or the B4UFLY app before flying."
        
        # Underwater trigger
        if 'underwater' in message_lower:
            content += "\n\n**Underwater Photography:** Use underwater housing, shoot in RAW, and consider red filters at depth. Manual white balance is crucial due to color loss underwater."
        
        return content
    
    def _handle_beginner_continuation(self, chat_session: ChatSession, matched_gear: Dict[str, List[GearItem]]) -> Dict[str, Any]:
        """Handle continuation to next step for beginners"""
        
        context = chat_session.conversation_context or {}
        if isinstance(context, str):
            context = {}
        photography_style = context.get('photography_style', '') if context else ''
        skip_lighting = context.get('skip_lighting', False)
        
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
            # Step 2: Lighting Setup (or skip to posing if no lighting needed)
            if skip_lighting:
                next_step = 3  # Skip to step 3
            else:
                step2_content = beginner_steps.get('step2', {}).get('lighting_setup', '')
                # Add mobile flash tip
                step2_content += "\n\n**Mobile Flash Tip:** If you want to stay mobile, use handheld or on-camera flash with diffusers (e.g., MagMod Sphere). Start with flash power at 1/64 or 1/128 as a starting point. **Optional Color Balance Tip:** If you have an orange gel (½ CTO - Color Temperature Orange), place it over your flash to better match warm indoor lighting."
                full_content = f"🟦 **Step 2: Lighting Setup**\n{step2_content}\n\nReady for Step 3: Posing & Composition?"
                
                return {
                    'content': full_content,
                    'step_number': 2,
                    'next_step': 2,
                    'awaiting_continuation': True
                }
        
        if next_step == 3:
            # Step 3: Posing & Composition
            step3_content = beginner_steps.get('step3', {}).get('posing_composition', '')
            full_content = f"🟦 **Step 3: Posing & Composition**\n{step3_content}\n\nWant a final pro tip before you shoot?"
            
            return {
                'content': full_content,
                'step_number': 3,
                'next_step': 3,
                'awaiting_continuation': True
            }
        
        if next_step == 4:
            # Step 4: Final Pro Tip
            step4_content = beginner_steps.get('step4', {}).get('final_pro_tip', '')
            full_content = f"🟦 **Step 4: Final Pro Tip**\n{step4_content}\n\n📌 These tips should give you a solid foundation — but every shoot is different. Adjust on the fly, and trust your eye. If anything changes, I've got your back."
            
            return {
                'content': full_content,
                'step_number': 4,
                'next_step': 0,  # Reset for new conversation
                'awaiting_continuation': False
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
    
    def _get_best_camera_for_scenario(self, cameras: List[GearItem], scenario: str) -> str:
        """Get the best camera recommendation for a specific scenario"""
        if not cameras:
            return "No cameras in collection"
        
        if len(cameras) == 1:
            return f"{cameras[0].brand} {cameras[0].model}"
        
        # Camera recommendations based on scenario characteristics
        camera_preferences = {
            'dark_moody_fashion': ['A7S', 'A7R', '5D Mark IV', 'Z6', 'low light'],
            'high_key_glamour': ['A7R', 'D850', '5D Mark IV', 'high resolution'],
            'sports_action': ['A9', 'D6', '1DX', 'R3', 'fast burst'],
            'beach_golden_hour': ['A7', '5D', 'Z6', 'dynamic range'],
            'natural_outdoor_portrait': ['A7', '5D', 'Z6', 'general purpose']
        }
        
        scenario_keywords = camera_preferences.get(scenario, ['general'])
        
        # Score cameras based on scenario fit
        best_camera = cameras[0]
        best_score = 0
        
        for camera in cameras:
            score = 0
            camera_name = f"{camera.brand} {camera.model}".lower()
            
            for keyword in scenario_keywords:
                if keyword.lower() in camera_name:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_camera = camera
        
        # Add reasoning for the recommendation
        camera_name = f"{best_camera.brand} {best_camera.model}"
        if best_score > 0:
            reason = self._get_camera_reason(best_camera, scenario)
            return f"{camera_name} {reason}"
        else:
            return camera_name
    
    def _get_camera_reason(self, camera: GearItem, scenario: str) -> str:
        """Get reasoning for camera selection"""
        camera_name = f"{camera.brand} {camera.model}".lower()
        
        if 'a7s' in camera_name:
            return "(excellent for low-light scenarios)"
        elif 'a7r' in camera_name or 'd850' in camera_name:
            return "(high resolution for detailed shots)"
        elif any(x in camera_name for x in ['a9', 'd6', '1dx', 'r3']):
            return "(fast burst rate for action)"
        elif any(x in camera_name for x in ['5d', 'z6', 'a7']):
            return "(versatile full-frame option)"
        else:
            return ""
    
    def _get_best_lens_for_scenario(self, lenses: List[GearItem], scenario: str) -> str:
        """Get the best lens recommendation for a specific scenario"""
        if not lenses:
            return "No lenses in collection"
        
        if len(lenses) == 1:
            return f"{lenses[0].brand} {lenses[0].model}"
        
        # Return all suitable lenses for now, can be enhanced with specific recommendations
        lens_names = [f"{lens.brand} {lens.model}" for lens in lenses[:2]]  # Limit to 2 for readability
        return ", ".join(lens_names)
    
    def _generate_general_response(self, message: str, skill_level: str, user_specialization: Optional[str] = None) -> Dict[str, Any]:
        """Generate general photography advice based on user's specialization"""
        
        # If user has a specialization and message is general, provide specialized advice
        if user_specialization and user_specialization != 'General' and any(word in message.lower() for word in ['tips', 'advice', 'help', 'suggest']):
            return self._generate_specialization_advice(user_specialization, skill_level)
        
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
