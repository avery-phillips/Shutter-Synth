from flask import render_template, request, redirect, url_for, session, flash, jsonify
from app import app, db
from models import User, GearItem, ChatSession, ChatMessage
from chat_engine import SynthiaChatEngine
import uuid
import logging

# Initialize chat engine
chat_engine = SynthiaChatEngine()

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    """User onboarding - skill level selection"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        skill_level = request.form.get('skill_level', 'Beginner')
        
        if not username:
            flash('Username is required', 'error')
            return render_template('onboarding.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('onboarding.html')
        
        # Create new user
        user = User()
        user.username = username
        user.skill_level = skill_level
        db.session.add(user)
        db.session.commit()
        
        # Store user in session
        session['user_id'] = user.id
        session['username'] = user.username
        session['skill_level'] = user.skill_level
        
        logging.info(f"New user created: {username} with skill level: {skill_level}")
        return redirect(url_for('gear_input'))
    
    return render_template('onboarding.html')

@app.route('/gear-input', methods=['GET', 'POST'])
def gear_input():
    """Gear input form"""
    if 'user_id' not in session:
        return redirect(url_for('onboarding'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('onboarding'))
    
    if request.method == 'POST':
        # Process gear input
        gear_data = request.form.to_dict()
        
        # Clear existing gear for this user
        GearItem.query.filter_by(user_id=user.id).delete()
        
        # Process camera bodies
        if gear_data.get('camera_brand') and gear_data.get('camera_model'):
            camera = GearItem()
            camera.user_id = user.id
            camera.category = 'camera_body'
            camera.brand = gear_data['camera_brand']
            camera.model = gear_data['camera_model']
            db.session.add(camera)
        
        # Process lenses
        lens_count = int(gear_data.get('lens_count', 0))
        for i in range(lens_count):
            lens_brand = gear_data.get(f'lens_brand_{i}')
            lens_model = gear_data.get(f'lens_model_{i}')
            if lens_brand and lens_model:
                lens_specs = {
                    'aperture_range': gear_data.get(f'lens_aperture_{i}', ''),
                    'type': gear_data.get(f'lens_type_{i}', 'prime')
                }
                lens = GearItem()
                lens.user_id = user.id
                lens.category = 'lens'
                lens.brand = lens_brand
                lens.model = lens_model
                lens.specifications = lens_specs
                db.session.add(lens)
        
        # Process lighting equipment
        lighting_count = int(gear_data.get('lighting_count', 0))
        for i in range(lighting_count):
            lighting_brand = gear_data.get(f'lighting_brand_{i}')
            lighting_model = gear_data.get(f'lighting_model_{i}')
            if lighting_brand and lighting_model:
                lighting_specs = {
                    'type': gear_data.get(f'lighting_type_{i}', ''),
                    'power': gear_data.get(f'lighting_power_{i}', ''),
                    'quantity': gear_data.get(f'lighting_quantity_{i}', '1')
                }
                lighting = GearItem()
                lighting.user_id = user.id
                lighting.category = 'lighting'
                lighting.brand = lighting_brand
                lighting.model = lighting_model
                lighting.specifications = lighting_specs
                db.session.add(lighting)
        
        # Process backdrops
        backdrop_count = int(gear_data.get('backdrop_count', 0))
        for i in range(backdrop_count):
            backdrop_brand = gear_data.get(f'backdrop_brand_{i}')
            backdrop_model = gear_data.get(f'backdrop_model_{i}')
            if backdrop_brand and backdrop_model:
                backdrop = GearItem()
                backdrop.user_id = user.id
                backdrop.category = 'backdrop'
                backdrop.brand = backdrop_brand
                backdrop.model = backdrop_model
                db.session.add(backdrop)
        
        # Process accessories
        accessory_count = int(gear_data.get('accessory_count', 0))
        for i in range(accessory_count):
            accessory_brand = gear_data.get(f'accessory_brand_{i}')
            accessory_model = gear_data.get(f'accessory_model_{i}')
            if accessory_brand and accessory_model:
                accessory = GearItem()
                accessory.user_id = user.id
                accessory.category = 'accessory'
                accessory.brand = accessory_brand
                accessory.model = accessory_model
                db.session.add(accessory)
        
        db.session.commit()
        flash('Gear profile saved successfully!', 'success')
        return redirect(url_for('chat'))
    
    # Get existing gear for pre-population
    existing_gear = {
        'camera_bodies': GearItem.query.filter_by(user_id=user.id, category='camera_body').all(),
        'lenses': GearItem.query.filter_by(user_id=user.id, category='lens').all(),
        'lighting': GearItem.query.filter_by(user_id=user.id, category='lighting').all(),
        'backdrops': GearItem.query.filter_by(user_id=user.id, category='backdrop').all(),
        'accessories': GearItem.query.filter_by(user_id=user.id, category='accessory').all()
    }
    
    return render_template('gear_input.html', user=user, existing_gear=existing_gear)

@app.route('/chat')
def chat():
    """Main chat interface"""
    if 'user_id' not in session:
        return redirect(url_for('onboarding'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('onboarding'))
    
    # Get or create active chat session
    active_session = ChatSession.query.filter_by(user_id=user.id, is_active=True).first()
    if not active_session:
        session_token = str(uuid.uuid4())
        active_session = ChatSession()
        active_session.user_id = user.id
        active_session.session_token = session_token
        db.session.add(active_session)
        db.session.commit()
    
    # Get recent messages
    recent_messages = ChatMessage.query.filter_by(session_id=active_session.id).order_by(ChatMessage.timestamp).limit(50).all()
    
    return render_template('chat.html', user=user, session_token=active_session.session_token, messages=recent_messages)

@app.route('/chat/send', methods=['POST'])
def send_message():
    """Handle chat message sending"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    message_content = data.get('message', '').strip()
    session_token = data.get('session_token')
    
    if not message_content:
        return jsonify({'error': 'Message content is required'}), 400
    
    # Find chat session
    chat_session = ChatSession.query.filter_by(session_token=session_token, user_id=user.id).first()
    if not chat_session:
        return jsonify({'error': 'Invalid session'}), 400
    
    # Save user message
    user_message = ChatMessage()
    user_message.session_id = chat_session.id
    user_message.message_type = 'user'
    user_message.content = message_content
    db.session.add(user_message)
    
    # Generate bot response
    user_gear = GearItem.query.filter_by(user_id=user.id).all()
    response_data = chat_engine.generate_response(
        message_content,
        user.skill_level,
        user_gear,
        chat_session
    )
    
    # Save bot response
    bot_message = ChatMessage()
    bot_message.session_id = chat_session.id
    bot_message.message_type = 'bot'
    bot_message.content = response_data['content']
    bot_message.step_number = response_data.get('step_number')
    bot_message.message_metadata = response_data.get('metadata')
    db.session.add(bot_message)
    
    # Update session context
    chat_session.current_step = response_data.get('next_step', chat_session.current_step)
    chat_session.conversation_context = response_data.get('context')
    
    db.session.commit()
    
    return jsonify({
        'response': response_data['content'],
        'step_number': response_data.get('step_number'),
        'awaiting_continuation': response_data.get('awaiting_continuation', False)
    })

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """User profile management"""
    if 'user_id' not in session:
        return redirect(url_for('onboarding'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('onboarding'))
    
    if request.method == 'POST':
        new_skill_level = request.form.get('skill_level')
        if new_skill_level in ['Beginner', 'Intermediate', 'Advanced']:
            user.skill_level = new_skill_level
            session['skill_level'] = new_skill_level
            db.session.commit()
            flash('Skill level updated successfully!', 'success')
        else:
            flash('Invalid skill level selected.', 'error')
    
    # Get user's gear summary
    gear_summary = {
        'camera_bodies': GearItem.query.filter_by(user_id=user.id, category='camera_body').count(),
        'lenses': GearItem.query.filter_by(user_id=user.id, category='lens').count(),
        'lighting': GearItem.query.filter_by(user_id=user.id, category='lighting').count(),
        'backdrops': GearItem.query.filter_by(user_id=user.id, category='backdrop').count(),
        'accessories': GearItem.query.filter_by(user_id=user.id, category='accessory').count()
    }
    
    return render_template('profile.html', user=user, gear_summary=gear_summary)

@app.route('/new-session')
def new_session():
    """Start a new chat session"""
    if 'user_id' not in session:
        return redirect(url_for('onboarding'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('onboarding'))
    
    # Deactivate current sessions
    ChatSession.query.filter_by(user_id=user.id, is_active=True).update({'is_active': False})
    db.session.commit()
    
    return redirect(url_for('chat'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
