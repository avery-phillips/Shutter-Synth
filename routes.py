from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from app import app, db
from models import User, GearItem, ChatSession, ChatMessage, UploadedImage
from chat_engine import SynthiaChatEngine
import uuid
import logging
import os
import time
from collections import defaultdict

# Configure upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Flask app for file uploads
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize chat engine
chat_engine = SynthiaChatEngine()

# Simple rate limiting storage (in production, use Redis or similar)
rate_limit_storage = defaultdict(list)

def check_rate_limit(ip_address, limit=5, window_seconds=60):
    """Simple rate limiting: 5 requests per 60 seconds per IP"""
    now = time.time()
    requests = rate_limit_storage[ip_address]
    
    # Remove old requests outside the window
    requests[:] = [req_time for req_time in requests if now - req_time < window_seconds]
    
    # Check if limit exceeded
    if len(requests) >= limit:
        return False
    
    # Add current request
    requests.append(now)
    return True

def allowed_file(filename):
    """Check if uploaded file has allowed extension and is safe"""
    if not filename or not isinstance(filename, str):
        return False
    
    # Check for basic path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check file extension
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS

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
        main_specialization = request.form.get('main_specialization')
        
        # Input validation and sanitization
        if not username or len(username) < 2 or len(username) > 50:
            flash('Username must be between 2 and 50 characters', 'error')
            return render_template('onboarding.html')
        
        # Sanitize username - allow only alphanumeric, spaces, and basic punctuation
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', username):
            flash('Username contains invalid characters. Use only letters, numbers, spaces, hyphens, underscores, and periods.', 'error')
            return render_template('onboarding.html')
        
        if skill_level not in ['Beginner', 'Intermediate', 'Advanced']:
            flash('Invalid skill level selected', 'error')
            return render_template('onboarding.html')
        
        if not main_specialization:
            flash('Photography specialization is required', 'error')
            return render_template('onboarding.html')
        
        # Validate specialization against allowed values (matching template options)
        valid_specializations = [
            'Portrait', 'Fashion', 'Sports', 'Glamour', 'Boudoir', 'Headshot', 'General'
        ]
        if main_specialization not in valid_specializations:
            flash('Invalid photography specialization selected', 'error')
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
        user.main_specialization = main_specialization
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
        
        # Process camera bodies (multiple cameras supported)
        camera_index = 0
        while True:
            camera_brand = gear_data.get(f'camera_brand_{camera_index}')
            camera_model = gear_data.get(f'camera_model_{camera_index}')
            
            if not camera_brand or not camera_model:
                break
                
            camera = GearItem()
            camera.user_id = user.id
            camera.category = 'camera_body'
            camera.brand = camera_brand
            camera.model = camera_model
            db.session.add(camera)
            camera_index += 1
        
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
    """Handle chat message submission with rate limiting"""
    # Apply rate limiting
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
    if not check_rate_limit(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please wait before sending another message.',
            'status': 'rate_limited'
        }), 429
    
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Handle both JSON and form data (for file uploads)
    if request.content_type and 'multipart/form-data' in request.content_type:
        message_content = request.form.get('message', '').strip()
        session_token = request.form.get('session_token')
        uploaded_files = request.files.getlist('images')
    else:
        data = request.get_json()
        message_content = data.get('message', '').strip()
        session_token = data.get('session_token')
        uploaded_files = []
    
    # Validate message content length and content
    if message_content:
        if len(message_content) > 5000:  # Reasonable message limit
            return jsonify({'error': 'Message too long (max 5000 characters)'}), 400
        
        # Basic XSS prevention - escape HTML if needed
        # Jinja2 auto-escapes by default, but additional validation here
        if '<script>' in message_content.lower() or 'javascript:' in message_content.lower():
            return jsonify({'error': 'Invalid message content'}), 400
    
    if not message_content and not uploaded_files:
        return jsonify({'error': 'Message content or image is required'}), 400
    
    # Find chat session
    chat_session = ChatSession.query.filter_by(session_token=session_token, user_id=user.id).first()
    if not chat_session:
        return jsonify({'error': 'Invalid session'}), 400
    
    # Save user message
    user_message = ChatMessage()
    user_message.session_id = chat_session.id
    user_message.message_type = 'user'
    user_message.content = message_content or "Uploaded image for analysis"
    db.session.add(user_message)
    db.session.commit()  # Commit to get message ID
    
    # Handle file uploads
    uploaded_images = []
    for file in uploaded_files:
        if file and file.filename and allowed_file(file.filename):
            try:
                # Generate unique filename with additional security
                timestamp = str(int(time.time()))
                filename = secure_filename(file.filename)
                
                # Additional filename sanitization
                filename = filename.replace(' ', '_').replace('-', '_')
                if not filename:
                    filename = f"upload_{timestamp}.jpg"
                
                unique_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Ensure upload directory exists and is secure
                os.makedirs(app.config['UPLOAD_FOLDER'], mode=0o755, exist_ok=True)
                
                # Check file size before saving
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    logging.error(f"File too large: {file_size} bytes")
                    return jsonify({'error': 'File size exceeds 16MB limit'}), 413
                
                # Save file with restrictive permissions
                file.save(file_path)
                os.chmod(file_path, 0o644)  # Read-only for group/others
                
                # Create UploadedImage record
                uploaded_image = UploadedImage()
                uploaded_image.message_id = user_message.id
                uploaded_image.filename = unique_filename
                uploaded_image.original_filename = filename
                uploaded_image.file_path = file_path
                uploaded_image.file_size = os.path.getsize(file_path)
                uploaded_image.mime_type = file.content_type or 'image/jpeg'
                
                db.session.add(uploaded_image)
                uploaded_images.append(uploaded_image)
                
            except Exception as e:
                logging.error(f"Error saving uploaded file: {str(e)}")
                return jsonify({'error': 'Failed to save uploaded image'}), 500
    
    # Generate bot response
    user_gear = GearItem.query.filter_by(user_id=user.id).all()
    response_data = chat_engine.generate_response(
        message_content,
        user.skill_level,
        user_gear,
        chat_session,
        uploaded_images,
        user.main_specialization
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
    
    # Merge context properly - preserve existing context and add new context
    new_context = response_data.get('context', {})
    if chat_session.conversation_context:
        chat_session.conversation_context.update(new_context)
    else:
        chat_session.conversation_context = new_context
    
    db.session.commit()
    
    return jsonify({
        'response': response_data['content'],
        'step_number': response_data.get('step_number'),
        'awaiting_continuation': response_data.get('awaiting_continuation', False),
        'uploaded_images': len(uploaded_images)
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
        new_specialization = request.form.get('main_specialization')
        
        if new_skill_level in ['Beginner', 'Intermediate', 'Advanced']:
            user.skill_level = new_skill_level
            session['skill_level'] = new_skill_level
            
        if new_specialization:
            user.main_specialization = new_specialization
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    
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

@app.route('/logout')
def logout():
    """Clear session and return to home page"""
    session.clear()
    flash('Session cleared. You can now create a new profile.', 'info')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
